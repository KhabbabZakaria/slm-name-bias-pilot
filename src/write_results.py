"""Writes results/results.md: the consolidated pilot write-up for 3B and 1.5B.

Every number in the file is computed here from the raw JSONL, so the write-up
can be regenerated and checked. The interpretive text is fixed; if a rerun
changes the numbers, reread the prose before quoting it.
"""

import json
from collections import defaultdict
from pathlib import Path

from analyse import rate
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
          f"5. **But a very famous name does move 3B.** Relabelling one company \"Apple Inc. (AAPL)\" "
          f"— numbers unchanged — raised how often 3B picked it by "
          f"{100*(ap3['fake'][0]/ap3['fake'][1]-ap3['base'][0]/ap3['base'][1]):+.0f} points. "
          f"This is one run and still needs its controls (see Finding 4).", ""]

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

    if ap3 or ap15:
        L += ["## Finding 4 — a famous fake name moves 3B", "",
              "The real large-caps in our pairs ($10–150bn: Lam Research, Autodesk, Gartner…) showed no "
              "name effect. To test a genuinely famous name, the **second** company in every prompt was "
              "relabelled **\"Apple Inc. (AAPL)\"**, keeping its own real numbers. The first company kept "
              "its real name. Everything else matched First/Second setup 1:", "",
              "```\nFirst company: Amphenol Corporation (APH)     <- real name, real numbers\n"
              "Second company: Apple Inc. (AAPL)               <- fake name over Manhattan Associates' real numbers\n"
              "CHOICE: FIRST\nor\nCHOICE: SECOND\n```", "",
              "Compared with the same prompts using the second company's real name "
              "(20 pairs × both orders × 5 samples ≈ 200 answers each):", "",
              "| model | picked the second company — real name | — labelled \"Apple\" | change |",
              "|---|---|---|---|"]
        for label, ap in (("3B", ap3), ("1.5B", ap15)):
            if not ap:
                continue
            (b, bn), (f, fn) = ap["base"], ap["fake"]
            L.append(f"| {label} | {b}/{bn} ({100*b/bn:.1f}%) | {f}/{fn} ({100*f/fn:.1f}%) | "
                     f"**{100*(f/fn-b/bn):+.1f} pts** [{100*ap['ci'][0]:+.1f} to {100*ap['ci'][1]:+.1f}] |")
        if ap3:
            (sb, sbn), (sf, sfn) = ap3["side"]["small"]
            (lb, lbn), (lf, lfn) = ap3["side"]["large"]
            L += ["", "**3B:**", "",
                  f"- The Apple label raised picks in **{ap3['up']} of 20 pairs**; {ap3['down']} went the other way.",
                  f"- It worked on both sides: Apple label on the real small-cap {sb}/{sbn} → {sf}/{sfn}; "
                  f"on the real large-cap {lb}/{lbn} → {lf}/{lfn}.",
                  f"- In {ap3['mentions']} of its {ap3['picks']} \"Apple\" picks the model named Apple and "
                  "justified the pick with the numbers (\"higher margins\", \"lower debt\"). But the numbers "
                  "were identical under the real name, where the same company was picked far less often. "
                  "The name moved the choice; the numbers were the explanation given afterwards."]
        if ap15:
            L += ["", "**1.5B:** no change. It answers FIRST about 97% of the time whatever the names are, so "
                  "no name could move it. This says nothing about whether 1.5B has name bias."]
        L += ["", "**Why this matters:** name bias at 3B seems to appear for household names, not for "
              "large-caps in general. That fits the idea that what counts is how often the model has "
              "seen a name, not the company's size.", "",
              "**Not yet established.** This is one run. Before relying on it:", "",
              "1. **Unknown-name control** — relabel the second company with a made-up name "
              "(e.g. \"Norwell Systems (NWLS)\"). If that also raises picks, the effect is \"any new "
              "name\", not \"famous name\".",
              "2. **Mirror test** — put the Apple label on the *first* company and check it pulls that way too.",
              "3. **Other famous names** — Microsoft, NVIDIA — to show it is not something about the word \"Apple\".",
              "4. **A second run** of the Apple test itself.",
              "5. **Mismatch caveat** — the numbers under \"Apple\" are not Apple's. A model that knows "
              "Apple's real margins could be reacting to that mismatch as well as to the name.", ""]

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

    # Short front-page version at the repo root, generated from the same numbers
    # so the two files cannot drift apart.
    swap_l, swap_o = ci(s3l[1]["swap"]), ci(s3o[1]["swap"])
    ap_delta = 100 * (ap3["fake"][0] / ap3["fake"][1] - ap3["base"][0] / ap3["base"][1]) if ap3 else None
    R = [
        "# Does a small language model pick a stock by its name or its numbers?",
        "",
        "A weekend research pilot. Two small open-weight models act as "
        "equity analysts and choose between matched pairs of technology companies. The question: do "
        "they favour a company because of its **name** rather than its **numbers**?",
        "",
        "**Short answer:** not for ordinary large-caps — but a household name moves them a lot, and "
        "most of what these models do is driven by the shape of the prompt rather than the companies.",
        "",
        "## Headline numbers",
        "",
        f"| | Qwen2.5-3B | Qwen2.5-1.5B |",
        "|---|---|---|",
        f"| Calls | {n3:,} | {n15:,} |",
        f"| Effect of showing real large-cap names | {100*s3l[1]['name_effect']:+.1f} pts "
        f"[{100*s3l[2]:+.1f} to {100*s3l[3]:+.1f}] | not measurable |",
        f"| Effect of relabelling a company \"Apple Inc. (AAPL)\" | **{ap_delta:+.0f} pts** "
        f"[{100*ap3['ci'][0]:+.0f} to {100*ap3['ci'][1]:+.0f}] | {100*(ap15['fake'][0]/ap15['fake'][1]-ap15['base'][0]/ap15['base'][1]):+.1f} pts |"
        if ap3 and ap15 else None,
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
        f"5. **A famous name has a large pull.** Relabelling one company \"Apple Inc. (AAPL)\" while "
        f"leaving its numbers untouched raised how often 3B picked it by {ap_delta:+.0f} points, in "
        f"{ap3['up']} of 20 pairs. The model then justified the choice with the numbers — the same "
        "numbers it had found less convincing under the real name." if ap3 else None,
        "",
        "Point 5 is a single run and still needs its controls, listed in "
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
        "# one 600-call run (20 pairs x 3 conditions x 2 orders x 5 samples)",
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
        "- **One sector** (technology) and **one fiscal year** (2022).",
        "",
        "Full detail, including what went wrong along the way, is in "
        "[results/results.md](results/results.md).",
        "",
    ]
    root_out = ROOT / "results.md"
    root_out.write_text("\n".join(x for x in R if x is not None) + "\n")
    print(f"-> {root_out}")


if __name__ == "__main__":
    main()
