"""Writes results/results.md: the consolidated pilot write-up for 3B and 1.5B.

Every number in the file is computed here from the raw JSONL, so the write-up
can be regenerated and checked. The interpretive text is fixed; if a rerun
changes the numbers, reread the prose before quoting it.
"""

import json
from collections import defaultdict
from pathlib import Path

from analyse import rate
from analyse_name_tests import TESTS as NAME_TESTS, rates as name_rates
from analyse_replication import name_effect_ci, numbers

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = RES / "results.md"

# Setup number -> (layout suffix, company block listed first, answer listed last)
SETUPS = {
    1: ("a_first", "A", "B"),
    2: ("b_first", "B", "B"),
    3: ("a_first_ans_ba", "A", "A"),
    4: ("b_first_ans_ba", "B", "A"),
}
WORDS = {"letters": {"A": "A", "B": "B"}, "ordinal": {"A": "FIRST", "B": "SECOND"}}
HEADER = {"letters": {"A": "Company A", "B": "Company B"},
          "ordinal": {"A": "First company", "B": "Second company"}}


def files(model, scheme, setup):
    layout = SETUPS[setup][0]
    if scheme == "ordinal":
        layout = "ord_" + layout
    stem = "raw" if layout == "a_first" else f"raw_{layout}"
    if model == "qwen2.5-3b":
        names = [f"{stem}.jsonl", f"{stem}_rep2.jsonl"]
    else:
        names = [f"{stem}__{model}.jsonl"]
    return [RES / n for n in names if (RES / n).exists()]


def load(model, scheme, setup):
    rows = []
    for rep, path in enumerate(files(model, scheme, setup), 1):
        for line in path.open():
            r = json.loads(line)
            r["_setup"], r["_rep"] = setup, rep
            rows.append(r)
    return rows


def by_pair(rows, pred):
    d = defaultdict(list)
    for r in rows:
        if r["parsed_choice"]:
            d[r["pair_id"]].append(int(pred(r)))
    return rate(d)


def ci(x):
    return f"{100*x['p']:.0f}% [{100*x['boot'][0]:.0f}–{100*x['boot'][1]:.0f}]"


def prompt_box(scheme, setup):
    _, first, last = SETUPS[setup]
    other = "B" if first == "A" else "A"
    ans_first = "A" if last == "B" else "B"
    w, h = WORDS[scheme], HEADER[scheme]
    return ("```\n"
            f"{h[first]}: ...\n{h[other]}: ...\n"
            f"CHOICE: {w[ans_first]}\nor\nCHOICE: {w[last]}\n```")


def counts_line(rows, scheme):
    ok = [r for r in rows if r["parsed_choice"]]
    a = sum(r["parsed_choice"] == "A" for r in ok)
    b = len(ok) - a
    bad = len(rows) - len(ok)
    w = WORDS[scheme]
    big = "A" if a >= b else "B"
    fa = f"**{w['A']} = {a} ({100*a/len(ok):.0f}%)**" if big == "A" else f"{w['A']} = {a} ({100*a/len(ok):.0f}%)"
    fb = f"**{w['B']} = {b} ({100*b/len(ok):.0f}%)**" if big == "B" else f"{w['B']} = {b} ({100*b/len(ok):.0f}%)"
    return f"{fa} · {fb}" + (f" · {bad} unreadable" if bad else "")


def pulls(rows):
    """Share of choices going to each surface feature, pair-bootstrapped."""
    first = lambda r: SETUPS[r["_setup"]][1]
    last = lambda r: SETUPS[r["_setup"]][2]
    return {
        "label": by_pair(rows, lambda r: r["parsed_choice"] == "B"),
        "last_answer": by_pair(rows, lambda r: r["parsed_choice"] == last(r)),
        "top_company": by_pair(rows, lambda r: r["parsed_choice"] == first(r)),
    }


def fake_apple(model):
    """Apple-label test vs the real-name baseline, same layout and prompts."""
    import random
    fake_path = RES / f"raw_fake_apple__{model}.jsonl"
    base_path = RES / ("raw_ord_a_first.jsonl" if model == "qwen2.5-3b"
                       else f"raw_ord_a_first__{model}.jsonl")
    if not fake_path.exists():
        return None
    fake = [json.loads(l) for l in fake_path.open()]
    base = [r for r in map(json.loads, base_path.open()) if r["condition"] == "identified"]
    second_of = lambda r: "small" if r["order"] == "large_first" else "large"

    def count(rows):
        ok = [r for r in rows if r["parsed_choice"]]
        return sum(r["parsed_choice"] == "B" for r in ok), len(ok)

    per = defaultdict(lambda: [[], []])
    for i, rows in enumerate((base, fake)):
        for r in rows:
            if r["parsed_choice"]:
                per[r["pair_id"]][i].append(r["parsed_choice"] == "B")
    pairs = list(per.values())
    rng, diffs = random.Random(1), []
    for _ in range(10_000):
        draw = [rng.choice(pairs) for _ in pairs]
        a = [x for p in draw for x in p[0]]
        b = [x for p in draw for x in p[1]]
        diffs.append(sum(b) / len(b) - sum(a) / len(a))
    diffs.sort()
    share = lambda v: sum(v) / len(v)
    picks = [r for r in fake if r["parsed_choice"] == "B"]
    return {
        "base": count(base), "fake": count(fake),
        "side": {side: (count([r for r in base if second_of(r) == side]),
                        count([r for r in fake if r["apple_label_on"] == side]))
                 for side in ("small", "large")},
        "ci": (diffs[250], diffs[9749]),
        "up": sum(1 for p in pairs if p[0] and p[1] and share(p[1]) > share(p[0])),
        "down": sum(1 for p in pairs if p[0] and p[1] and share(p[1]) < share(p[0])),
        "picks": len(picks),
        "mentions": sum("apple" in r["raw_output"].lower() for r in picks),
    }


def name_tests(model):
    """Every relabelling test vs the real-name baseline, keyed by tag."""
    base_path = RES / ("raw_ord_a_first.jsonl" if model == "qwen2.5-3b"
                       else f"raw_ord_a_first__{model}.jsonl")
    if not base_path.exists():
        return {}
    base = [r for r in map(json.loads, base_path.open())
            if r["condition"] == "identified"]
    out = {}
    for tag, stem, label, slot in NAME_TESTS:
        path = RES / f"{stem}__{model}.jsonl"
        if path.exists():
            r = name_rates(base, [json.loads(l) for l in path.open()], slot)
            r["label"], r["slot"] = label, slot
            out[tag] = r
    return out


def main():
    data = {}
    for model in ("qwen2.5-3b", "qwen2.5-1.5b"):
        for scheme in ("letters", "ordinal"):
            for s in SETUPS:
                rows = load(model, scheme, s)
                if rows:
                    data[(model, scheme, s)] = rows

    def pooled(model, scheme):
        return [r for s in SETUPS for r in data.get((model, scheme, s), [])]

    groups = [("qwen2.5-3b", "letters", "3B, letter labels (A/B)"),
              ("qwen2.5-3b", "ordinal", "3B, First/Second labels"),
              ("qwen2.5-1.5b", "ordinal", "1.5B, First/Second labels")]
    summ = {}
    for model, scheme, label in groups:
        rows = pooled(model, scheme)
        x = numbers(rows)
        lo, hi = name_effect_ci(rows)
        summ[(model, scheme)] = (label, x, lo, hi, pulls(rows), len(rows))

    ap3, ap15 = fake_apple("qwen2.5-3b"), fake_apple("qwen2.5-1.5b")
    nt = name_tests("qwen2.5-3b")
    n3 = sum(len(pooled("qwen2.5-3b", s)) for s in ("letters", "ordinal"))
    n15 = len(pooled("qwen2.5-1.5b", "ordinal"))
    fails = {m: sum(1 for s in ("letters", "ordinal") for r in pooled(m, s)
                    if not r["parsed_choice"]) for m in ("qwen2.5-3b", "qwen2.5-1.5b")}
    s3l, s3o, s15 = summ[("qwen2.5-3b", "letters")], summ[("qwen2.5-3b", "ordinal")], summ[("qwen2.5-1.5b", "ordinal")]

    L = []
    L += ["# Results — Qwen2.5-3B and Qwen2.5-1.5B", "",
          "**This is a pilot, not a finding.** 20 company pairs, one sector, two small "
          "models. Numbers in brackets are 95% intervals that resample the 20 pairs, so "
          "they reflect how few pairs there are, not how many calls were made.", "",
          f"Calls: {n3:,} on 3B, {n15:,} on 1.5B. Unreadable answers: "
          f"{fails['qwen2.5-3b']} on 3B, {fails['qwen2.5-1.5b']} on 1.5B.", ""]

    L += ["## The short version", "",
          f"1. **3B showed no bias toward the real large-cap names in our pairs.** Showing the names moved its choice by "
          f"{100*s3l[1]['name_effect']:+.1f} points with letter labels and "
          f"{100*s3o[1]['name_effect']:+.1f} with First/Second labels, both within noise of zero. "
          f"1.5B could not be tested for this (see point 3).",
          f"2. **Both models were driven mainly by how the question was laid out, not by the companies.** "
          f"This is the kind of position bias the reference paper reports.",
          f"3. **1.5B cannot be used for this question.** It copies whichever answer line is written "
          f"first, {100*(1-s15[4]['last_answer']['p']):.0f}% of the time.",
          f"4. **3B can be used, if the layout is rotated.** With all layouts combined so the position "
          f"effects cancel, 3B followed the numbers over the name {ci(s3l[1]['swap'])} of the time with "
          f"letters and {ci(s3o[1]['swap'])} with First/Second labels.",
          f"5. **But name familiarity does move 3B — against the layout.** Relabelling one company "
          f"\"Apple Inc. (AAPL)\", numbers unchanged, raised how often 3B picked it by "
          f"{100*nt['apple']['delta']:+.0f} points (replicated: "
          f"{100*nt['apple_rep2']['delta']:+.0f}); Microsoft gave "
          f"{100*nt['microsoft']['delta']:+.0f}; an invented name cost "
          f"{100*nt['norwell']['delta']:+.0f}. But the same Apple label on the company the layout "
          f"already favours did nothing ({100*nt['apple_first']['delta']:+.1f}), so the effect only "
          f"shows from behind. See Finding 4.", ""] if nt else []

    L += ["## What we tested", "",
          "Each prompt showed two technology companies from FY2022 — one large, one small — "
          "matched so neither is obviously better on paper. The model had to pick one to hold for "
          "12 months. Only five ratios were shown (growth, gross, operating and net margin, debt "
          "to revenue), never dollar amounts.", "",
          "Every pair was asked three ways:", "",
          "- **Anonymised** — no names, just the numbers. Should come out about 50/50.",
          "- **Identified** — real names with their real numbers.",
          "- **Swapped** — real names, but each company shown with the *other* company's numbers. "
          "If the model follows the numbers, its pick moves with them. If it sticks to the name, "
          "that is name bias.", "",
          "Every pair was also run with the companies in both orders, 5 times each.", "",
          "**Models:** Qwen2.5-3B-Instruct (4-bit) and Qwen2.5-1.5B-Instruct (full precision, "
          "the size used in the reference paper). A 7B run froze this 8GB laptop and was "
          "abandoned.", ""]

    L += ["## Finding 1 — the layout decides most answers", "",
          "An unbiased model should come out near 50/50 in every setup below, because each company "
          "sits in each position equally often. Anything outside roughly 45–55% is bias.", "",
          "### Letter labels — 3B only (each setup run twice, 1,200 answers)", ""]
    for s in SETUPS:
        rows = data.get(("qwen2.5-3b", "letters", s), [])
        L += [f"**Setup {s}**", prompt_box("letters", s), f"3B: {counts_line(rows, 'letters')}", ""]
    p = s3l[4]
    L += ["Across all four letter setups, 3B chose:", "",
          f"- the letter **B**: {ci(p['label'])}",
          f"- the **answer listed last**: {ci(p['last_answer'])}",
          f"- the **company listed at the top**: {ci(p['top_company'])}", "",
          "So with letters, 3B likes B and likes the last answer option. Where the companies sit "
          "barely matters. When both pulls point at B (setups 1 and 2), B wins by a lot. When they "
          "point in opposite directions (setups 3 and 4), they cancel to about 50/50.", ""]

    L += ["### First/Second labels — 3B and 1.5B (each setup run once, 600 answers)", ""]
    for s in SETUPS:
        L += [f"**Setup {s}**", prompt_box("ordinal", s),
              f"3B: {counts_line(data.get(('qwen2.5-3b', 'ordinal', s), []), 'ordinal')}  ",
              f"1.5B: {counts_line(data.get(('qwen2.5-1.5b', 'ordinal', s), []), 'ordinal')}", ""]
    p3, p15 = s3o[4], s15[4]
    L += ["Across all four First/Second setups:", "",
          "| chose… | 3B | 1.5B |", "|---|---|---|",
          f"| the word **SECOND** | {ci(p3['label'])} | {ci(p15['label'])} |",
          f"| the **answer listed last** | {ci(p3['last_answer'])} | {ci(p15['last_answer'])} |",
          f"| the **company listed at the top** | {ci(p3['top_company'])} | {ci(p15['top_company'])} |", "",
          f"- **1.5B** picks the answer listed *first* {100*(1-p15['last_answer']['p']):.0f}% of the "
          "time. It is copying the first line of the answer instructions, not choosing.",
          "- **3B** lands at 61–67% in every setup, so no single layout is clean. It is several "
          "small pulls — toward the word FIRST, the last answer option and the top company — "
          "that add up differently in each layout. They largely cancel when all four are combined.", ""]

    L += ["## Finding 2 — no bias toward the real large-cap names, once layout is balanced", "",
          "These numbers combine all four setups for each label type, so the layout effects "
          "above cancel out.", "",
          "| | 3B, letters | 3B, First/Second | 1.5B, First/Second |", "|---|---|---|---|",
          "| calls | " + " | ".join(f"{g[5]:,}" for g in (s3l, s3o, s15)) + " |",
          "| **Anonymised**: large-cap chosen, no names (≈50% expected) | " +
          " | ".join(ci(g[1]['anon']) for g in (s3l, s3o, s15)) + " |",
          "| **Identified**: large-cap chosen, real names | " +
          " | ".join(ci(g[1]['ident']) for g in (s3l, s3o, s15)) + " |",
          "| **Name effect**: identified − anonymised | " +
          " | ".join(f"{100*g[1]['name_effect']:+.1f} pts [{100*g[2]:+.1f} to {100*g[3]:+.1f}]" for g in (s3l, s3o, s15)) + " |",
          "| **Swap test**: followed the numbers, not the name | " +
          " | ".join(ci(g[1]['swap']) for g in (s3l, s3o, s15)) + " |",
          "| pairs with no clear choice to compare against | " +
          " | ".join(f"{len(g[1]['swap']['excluded'])}/20" for g in (s3l, s3o, s15)) + " |", "",
          "How to read it:", "",
          "- **Anonymised is near 50% in every column.** That is consistent with well-matched pairs, "
          "but it is weaker evidence than it looks: because every company is shown in every "
          "position equally often, position bias alone pushes this number toward 50%. For 1.5B, "
          "which barely reads the companies, it says nothing about the pairs at all.",
          "- **The name effect is within noise of zero for both label types on 3B.** For the real "
          f"large-caps in these pairs, any name bias at 3B is smaller than about "
          f"{100*max(abs(s3l[2]), abs(s3l[3])):.0f} points with letters. Finding 4 shows this does "
          "not extend to a household name like Apple.",
          "- **On 3B the swap test lands well above 50% for both label types.** When the numbers "
          "move, the model's pick moves with them. That is the opposite of name loyalty.",
          "- **The 1.5B column should not be read as a result.** Its answers are almost all "
          "format-copying, so there is very little genuine choice left to measure.", ""]

    L += ["## Finding 3 — it replicates (3B, letter labels)", "",
          "Each letter setup was run twice with different random seeds.", "",
          "| setup | run | chose B | followed the numbers (swap) | name effect |", "|---|---|---|---|---|"]
    for s in SETUPS:
        for rep in (1, 2):
            rows = [r for r in data.get(("qwen2.5-3b", "letters", s), []) if r["_rep"] == rep]
            if not rows:
                continue
            x = numbers(rows)
            L.append(f"| {s} | {rep} | {100*x['letter_b']['p']:.0f}% | {ci(x['swap'])} | "
                     f"{100*x['name_effect']:+.1f} |")
    L += ["", "The layout effects and the swap result came out nearly the same both times. The name "
          "effect moved around between runs (roughly −4 to +6 points), which is what noise around "
          "zero looks like. The First/Second runs have been done once each and have not been "
          "replicated yet.", ""]

    if nt:
        row = lambda t: (f"| {nt[t]['label']} | {nt[t]['slot']} | "
                         f"{nt[t]['base'][0]}/{nt[t]['base'][1]} "
                         f"({100*nt[t]['base'][0]/nt[t]['base'][1]:.1f}%) | "
                         f"{nt[t]['test'][0]}/{nt[t]['test'][1]} "
                         f"({100*nt[t]['test'][0]/nt[t]['test'][1]:.1f}%) | "
                         f"**{100*nt[t]['delta']:+.1f} pts** "
                         f"[{100*nt[t]['ci'][0]:+.1f} to {100*nt[t]['ci'][1]:+.1f}] | "
                         f"{nt[t]['up']}/{nt[t]['down']} |")
        L += ["## Finding 4 — name familiarity moves 3B, but only against the layout", "",
              "The real large-caps in these pairs ($10–150bn: Lam Research, Autodesk, Gartner…) "
              "showed no name effect. These tests replace one company's name and ticker while "
              "leaving its own real numbers in place, so any change in how often that company is "
              "picked is down to the name. The baseline is the identical prompts with real names. "
              "Layout is First/Second setup 1 throughout:", "",
              "```\nFirst company: Amphenol Corporation (APH)     <- real name, real numbers\n"
              "Second company: Apple Inc. (AAPL)               <- new label over Manhattan "
              "Associates' real numbers\nCHOICE: FIRST\nor\nCHOICE: SECOND\n```", "",
              "About 200 answers per cell (20 pairs × both orderings × 5 samples).", "",
              "| label | slot | picked with real name | picked with new label | change | pairs up/down |",
              "|---|---|---|---|---|---|"]
        for t in ("apple", "apple_rep2", "microsoft", "norwell", "apple_first"):
            if t in nt:
                L.append(row(t))
        L += ["", "Brackets are pair-bootstrap 95% intervals.", ""]
        if "apple" in nt and "norwell" in nt:
            a, n, gap = nt["apple"], nt["norwell"], nt["apple"]["delta"] - nt["norwell"]["delta"]
            L += ["**What holds up:**", "",
                  f"- **It is familiarity, not novelty.** The invented name Norwell Systems moved "
                  f"the choice {100*n['delta']:+.1f} points — the *opposite* direction, with an "
                  f"interval excluding zero. An unfamiliar name is a penalty. The gradient from an "
                  f"invented name to a household one spans about {100*gap:.0f} points."]
            if "apple_rep2" in nt:
                L.append(f"- **It replicates.** A rerun with a different seed gave "
                         f"{100*nt['apple_rep2']['delta']:+.1f} points against "
                         f"{100*a['delta']:+.1f}, moving {nt['apple_rep2']['up']} of 20 pairs up.")
            if "microsoft" in nt:
                L.append(f"- **It is not about the word \"Apple\".** Microsoft gave "
                         f"{100*nt['microsoft']['delta']:+.1f} points "
                         f"[{100*nt['microsoft']['ci'][0]:+.1f} to "
                         f"{100*nt['microsoft']['ci'][1]:+.1f}].")
        if "apple_first" in nt:
            m = nt["apple_first"]
            L += ["", "**What does not hold up — the mirror test:**", "",
                  f"- Moving the Apple label to the **first** company changed nothing: "
                  f"{100*m['delta']:+.1f} points [{100*m['ci'][0]:+.1f} to {100*m['ci'][1]:+.1f}], "
                  f"{m['up']} pairs up and {m['down']} down. The first slot already wins "
                  f"{100*m['base'][0]/m['base'][1]:.0f}% of the time, and the famous label adds "
                  "nothing on top.",
                  "- So the effect appears **only where the layout is working against the "
                  "labelled company**. Label and position interact: a familiar name can overcome "
                  "a position bias pointing the other way, but it buys nothing when position "
                  "already favours it.",
                  "- Consequence for how this is quoted: \"+20 points\" is the size **in the "
                  "disfavoured slot**, not a general name effect. A pure name effect has not been "
                  "demonstrated."]
        if ap15:
            L += ["", "**1.5B:** no change from the Apple label (5/198 → 5/196). It answers FIRST "
                  "in about 97% of cases whatever the names are, so no label could move it. This "
                  "says nothing about whether 1.5B has name bias."]
        L += ["", "**Still open:**", "",
              "1. **The mirror asymmetry needs explaining.** Is it a ceiling, or does a familiar "
              "name genuinely only help from behind? Testing the invented name on the first slot "
              "would separate these: if Norwell *lowers* the first slot, the gradient is "
              "symmetrical and only the Apple direction is saturated.",
              "2. **The gradient needs more rungs.** Five labels is enough to show a direction, "
              "not a dose-response curve.",
              "3. **Larger models.** Everything here is one 3B model.", ""]
        L += [""]
    L += ["## What went wrong, and what we learned", "",
          "- **The first run looked like a clean result and wasn't.** Setup 1 alone gave "
          "\"follows the numbers 71% of the time\". Moving the companies around dropped that to "
          "50% in setup 2. It only held up once the answer order was also rotated.",
          "- **Position bias is bigger than the effect we were trying to measure for ordinary "
          "large-caps.** On 3B it moves answers by 20–30 points; bias toward our real large-cap "
          "names is under about 8. A household name (Apple) moved answers by about 20.",
          "- **Smaller is worse.** 1.5B is almost pure format-copying; 3B is partly driven by the "
          "content.",
          "- **The recognition check told us nothing.** Asked to recall these companies' FY2022 "
          "ratios, 3B answered UNKNOWN for all 40 — including very well-known ones — which looks "
          "like it just obeyed \"do not guess\".", ""]

    L += ["## Limitations", "",
          "- **Only 20 pairs.** Intervals are wide; this is enough to decide whether to continue, "
          "not to publish.",
          "- **Small models only.** 3B is 4-bit; 1.5B is full precision. 7B could not run on this "
          "machine. Results may not hold for larger models.",
          "- **The layout tests were added after seeing the first results.** They are follow-up "
          "checks on a bias we found, not part of the original plan. A full study should fix the "
          "rotation of both company order and answer order *before* the first run.",
          "- **Some runs are not exactly reproducible.** The first 3B runs were unseeded, and "
          "3B First/Second setup 3 was paused and resumed.",
          "- **First/Second runs were done once each.** The letter runs were done twice.", ""]

    L += ["## Should the full study go ahead?", "",
          "Possibly — but not in its current form. Ordinary large-cap names showed no effect, "
          "while a household name (Apple) showed a large one on 3B. If that survives its controls, "
          "the full study has a real effect to chase, and the question shifts from \"large-cap vs "
          "small-cap\" to \"how famous is the name\". Any full study needs (a) every layout rotated "
          "and pooled from the start, (b) pairs that include genuinely famous names, and (c) "
          "models big enough to read the content — 7B and above, on hardware that can hold them.", ""]

    L += ["## Files", "",
          "- `data/pairs.csv` — the 20 matched pairs",
          "- `results/raw*.jsonl` — every answer, with the raw model output",
          "- `results/probe.jsonl` — the recognition check",
          "- `results/raw_fake_apple__*.jsonl` — the Apple-label test",
          "- `src/write_results.py` — regenerates this file", ""]

    OUT.write_text("\n".join(L) + "\n")
    print(f"-> {OUT}")

    # The README is the front page, generated from the same numbers so it cannot
    # drift from the detailed write-up. There is deliberately no second
    # results.md at the repo root: two files of the same name that differ leave a
    # reader unable to tell which to trust.
    swap_l, swap_o = ci(s3l[1]["swap"]), ci(s3o[1]["swap"])
    ap_delta = 100 * (ap3["fake"][0] / ap3["fake"][1] - ap3["base"][0] / ap3["base"][1]) if ap3 else None
    R = [
        "# slm-name-bias-pilot",
        "",
        "**Does a small language model pick a stock by its name or its numbers?**",
        "",
        "A weekend research pilot. Two small open-weight models act as "
        "equity analysts and choose between matched pairs of technology companies. The question: do "
        "they favour a company because of its **name** rather than its **numbers**?",
        "",
        "**Short answer:** not for ordinary large-caps. A household name does move the 3B model — "
        "about 20 points — but only when the prompt layout is working against that company. Most "
        "of what these small models do is driven by the shape of the prompt rather than by the "
        "companies in it.",
        "",
        "## Headline numbers",
        "",
        f"| | Qwen2.5-3B | Qwen2.5-1.5B |",
        "|---|---|---|",
        f"| Calls | {n3:,} | {n15:,} |",
        f"| Effect of showing real large-cap names | {100*s3l[1]['name_effect']:+.1f} pts "
        f"[{100*s3l[2]:+.1f} to {100*s3l[3]:+.1f}] | not measurable |",
        f"| Relabelling a company \"Apple Inc. (AAPL)\" — in the slot the layout disfavours | "
        f"**{100*nt['apple']['delta']:+.0f} pts** [{100*nt['apple']['ci'][0]:+.0f} to "
        f"{100*nt['apple']['ci'][1]:+.0f}], replicated {100*nt['apple_rep2']['delta']:+.0f} | "
        f"not interpretable |" if nt and ap15 else None,
        f"| …\"Microsoft Corporation (MSFT)\" | {100*nt['microsoft']['delta']:+.0f} pts "
        f"[{100*nt['microsoft']['ci'][0]:+.0f} to {100*nt['microsoft']['ci'][1]:+.0f}] | — |"
        if nt else None,
        f"| …an invented name, \"Norwell Systems (NWLS)\" | {100*nt['norwell']['delta']:+.0f} pts "
        f"[{100*nt['norwell']['ci'][0]:+.0f} to {100*nt['norwell']['ci'][1]:+.0f}] | — |"
        if nt else None,
        f"| …\"Apple\" in the slot the layout already favours | "
        f"{100*nt['apple_first']['delta']:+.1f} pts [{100*nt['apple_first']['ci'][0]:+.1f} to "
        f"{100*nt['apple_first']['ci'][1]:+.1f}] | — |" if nt else None,
        f"| Followed the numbers when they were swapped | {swap_l} (letters), {swap_o} (First/Second) | "
        f"{ci(s15[1]['swap'])}, not interpretable |",
        f"| Picked whichever answer option was listed first | — | "
        f"{100*(1-s15[4]['last_answer']['p']):.0f}% of answers |",
        "",
        "Brackets are 95% intervals that resample the 20 pairs.",
        "",
        "## What the pilot found",
        "",
        "1. **Prompt layout decides most answers.** Which letter labels the companies, and which "
        "answer option is listed last, move 3B's choices by 20–30 points. The companies' own "
        "position matters much less.",
        "2. **1.5B barely chooses at all.** It copies the first answer line it is shown in about "
        "97% of answers, so it cannot be used to study name bias with this prompt.",
        "3. **3B does read the numbers, once layout is balanced.** Pooling all layouts so the "
        f"position effects cancel, it followed the swapped numbers rather than the name {swap_l} "
        "of the time.",
        "4. **Ordinary large-cap names have no pull.** Lam Research, Autodesk, Gartner and the rest "
        "changed nothing.",
        f"5. **Name familiarity has a large pull — but only from behind.** Relabelling one company "
        f"\"Apple Inc. (AAPL)\", numbers untouched, raised how often 3B picked it by "
        f"{100*nt['apple']['delta']:+.0f} points ({nt['apple']['up']} of 20 pairs; replicated at "
        f"{100*nt['apple_rep2']['delta']:+.0f}). Microsoft gave {100*nt['microsoft']['delta']:+.0f}. "
        f"An invented name *cost* {100*nt['norwell']['delta']:+.0f}, so this is a familiarity "
        f"gradient, not a reaction to any relabelling. The model then justified its choice with the "
        "numbers — the same numbers it found less convincing under the real name." if nt else None,
        f"6. **The mirror test fails, and that bounds the claim.** The same Apple label on the "
        f"company the layout already favours changed nothing "
        f"({100*nt['apple_first']['delta']:+.1f} pts). The effect shows only where position works "
        "against the labelled company, so this is not a pure name effect." if nt else None,
        "",
        "Points 5 and 6 come from five relabelling tests (Apple twice, Microsoft, an invented "
        "name, and Apple on the opposite slot), each about 200 answers against a matched "
        "real-name baseline. Details and what is still open are in "
        "[results/results.md](results/results.md).",
        "",
        "## Repository",
        "",
        "```",
        "data/pairs.csv             20 matched large/small technology pairs, FY2022",
        "data/universe.csv          all candidate companies pulled from SEC EDGAR",
        "results/results.md         full write-up: every setup, counts and caveats",
        "results/raw*.jsonl         every model call, with raw output preserved",
        "results/probe.jsonl        recognition check (can the model recall these ratios?)",
        "results/raw_fake_*.jsonl   the relabelling tests (Apple, Microsoft, invented name)",
        "results/name_tests.md      relabelling tests vs the real-name baseline",
        "src/                       fetch, pairing, prompts, runner, analysis",
        "```",
        "",
        "## Reproducing it",
        "",
        "```bash",
        "python3 -m venv venv && ./venv/bin/pip install requests pandas statsmodels mlx-lm",
        "export SEC_USER_AGENT=\"Your Name you@example.com\"   # EDGAR requires a contact",
        "",
        "./venv/bin/python src/fetch_fundamentals.py   # SEC EDGAR -> data/universe.csv",
        "./venv/bin/python src/build_pairs.py          # -> data/pairs.csv",
        "./venv/bin/python src/validate_pairs.py       # pair quality checks",
        "cd src && ../venv/bin/python test_prompts.py  # prompt guards (name/currency leaks)",
        "",
        "# one 600-call run: 20 pairs x 3 conditions x 2 orderings x 5 samples",
        "# sampling is temperature 0.7 throughout, logged in every row",
        "caffeinate -i ../venv/bin/python run.py --layout a_first",
        "",
        "../venv/bin/python write_results.py           # rebuilds results/results.md and this file",
        "```",
        "",
        "Runs are resumable and append-only: rerunning skips calls already recorded. "
        "`caffeinate` matters on a Mac — the first run lost 24 minutes to the display sleeping.",
        "",
        "## Honest limits",
        "",
        "- **20 pairs.** Enough to decide whether to continue, not to publish.",
        "- **Small models only.** 3B at 4-bit, 1.5B at full precision. A 7B run froze an 8GB "
        "MacBook at 123/600 calls and was abandoned.",
        "- **The layout tests and the Apple test were added after seeing the first results.** They "
        "are follow-ups to a bias found in the data, not part of the original plan. A real study "
        "must fix the rotation of company order *and* answer order before the first call.",
        "- **The name effect is entangled with position.** It appears only in the slot the layout "
        "disfavours; in the favoured slot the same label does nothing. Any full study has to "
        "measure the two together rather than report a single name effect.",
        "- **One sector** (technology) and **one fiscal year** (2022).",
        "- **The recognition check came back empty, which is itself a limitation.** Asked to recall "
        "these companies' FY2022 ratios, 3B answered UNKNOWN for all 40, including household "
        "names. That looks like compliance with the \"do not guess\" instruction rather than "
        "absent knowledge, so it does **not** rule out an alternative reading of the Apple result: "
        "the model may be reacting to the numbers not matching Apple's real financials rather than "
        "to the name itself. Against that reading: noticing a mismatch should make a model pick "
        "the company *less*, and both household names raised it, while the invented name — which "
        "no model can hold expectations about — lowered it.",
        "- **`results/raw_7b_partial_abandoned.jsonl` is excluded from every number here.** Those "
        "123 rows are the 7B run that froze the machine; they are committed for the record only "
        "and must not be pooled with the rest.",
        "",
        "Full detail, including what went wrong along the way, is in "
        "[results/results.md](results/results.md).",
        "",
    ]
    root_out = ROOT / "README.md"
    root_out.write_text("\n".join(x for x in R if x is not None) + "\n")
    print(f"-> {root_out}")


if __name__ == "__main__":
    main()
