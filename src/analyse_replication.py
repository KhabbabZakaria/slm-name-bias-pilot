"""Replication report: do the findings hold across independent reruns?

One run per layout cannot separate a pattern from sampling noise at 10 samples
per pair. This compares replicate 1 (the original, unseeded runs) with
replicate 2 (seeded reruns of both layouts) on every quantity the pilot reports,
then pools all four runs -- two replicates x two layouts, fully counterbalanced
for letter and slot -- into the estimates that should be quoted.

Writes results/replication.md.
"""

import json
from collections import defaultdict
from pathlib import Path

from analyse import order_consistency, rate, swap_following

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = RES / "replication.md"

RUNS = [  # (replicate, layout, file)
    (1, "a_first", "raw.jsonl"),
    (1, "b_first", "raw_b_first.jsonl"),
    (2, "a_first", "raw_rep2.jsonl"),
    (2, "b_first", "raw_b_first_rep2.jsonl"),
]
CONDS = ("identified", "anonymised", "swapped")


def load():
    out = {}
    for rep, layout, name in RUNS:
        path = RES / name
        if not path.exists():
            continue
        rows = [json.loads(l) for l in path.open()]
        for r in rows:
            r["layout"], r["replicate"] = layout, rep
        out[(rep, layout)] = rows
    return out


def by_pair(rows, pred):
    d = defaultdict(list)
    for r in rows:
        if r["parsed_choice"]:
            d[r["pair_id"]].append(int(pred(r)))
    return rate(d)


def numbers(rows):
    ok = [r for r in rows if r["parsed_choice"]]
    cond = lambda c, f: by_pair([r for r in ok if r["condition"] == c],
                                lambda r: r[f] == "large")
    anon = cond("anonymised", "chosen_fundamentals_owner")
    ident = cond("identified", "chosen_name_owner")
    swap = swap_following(ok, "identified")
    return {
        "anon": anon, "ident": ident, "swap": swap,
        "name_effect": ident["p"] - anon["p"],
        "letter_b": by_pair(ok, lambda r: r["parsed_choice"] == "B"),
        "b_by_cond": {c: sum(r["parsed_choice"] == "B" for r in ok if r["condition"] == c)
                         / max(1, sum(1 for r in ok if r["condition"] == c)) for c in CONDS},
        "fails": sum(1 for r in rows if not r["parsed_choice"]),
        "n": len(rows),
    }


def name_effect_ci(rows, n_boot=10_000, seed=20260918):
    """Pair-bootstrap interval for identified − anonymised large-cap share.

    Resamples pairs and recomputes both rates on the same draw, so the
    correlation between the two conditions within a pair is kept.
    """
    import random
    per = defaultdict(lambda: {"identified": [], "anonymised": []})
    for r in rows:
        if r["parsed_choice"] and r["condition"] == "identified":
            per[r["pair_id"]]["identified"].append(int(r["chosen_name_owner"] == "large"))
        elif r["parsed_choice"] and r["condition"] == "anonymised":
            per[r["pair_id"]]["anonymised"].append(int(r["chosen_fundamentals_owner"] == "large"))
    pairs = list(per.values())
    rng = random.Random(seed)
    diffs = []
    for _ in range(n_boot):
        draw = [rng.choice(pairs) for _ in pairs]
        i = [x for d in draw for x in d["identified"]]
        a = [x for d in draw for x in d["anonymised"]]
        diffs.append(sum(i) / len(i) - sum(a) / len(a))
    diffs.sort()
    return diffs[int(0.025 * n_boot)], diffs[int(0.975 * n_boot) - 1]


def pct(r):
    return f"{100*r['p']:.1f}% [{100*r['boot'][0]:.0f}–{100*r['boot'][1]:.0f}]"


def main():
    runs = load()
    L = ["# Replication report — Qwen2.5-3B (4-bit)", "",
         "Each run: 20 pairs × 3 conditions × 2 orderings × 5 samples = 600 calls. "
         "Replicate 1 is the original unseeded run; replicate 2 reruns both layouts "
         "with fixed seeds. `a_first` lists Company A first (the frozen template); "
         "`b_first` lists Company B first (the position diagnostic).", "",
         "Brackets are pair-bootstrap 95% intervals, resampling the 20 pairs.", ""]

    res = {k: numbers(v) for k, v in runs.items()}
    keys = sorted(res)

    L += ["## Run by run", "",
          "| run | calls | parse fail | chose B | anonymised | identified | swap-following | name effect |",
          "|---|---|---|---|---|---|---|---|"]
    for k in keys:
        x = res[k]
        L.append(f"| rep {k[0]} · {k[1]} | {x['n']} | {x['fails']} | {100*x['letter_b']['p']:.1f}% | "
                 f"{pct(x['anon'])} | {pct(x['ident'])} | {pct(x['swap'])} | "
                 f"{100*x['name_effect']:+.1f} |")

    L += ["", "## Does each finding replicate?", ""]
    for layout in ("a_first", "b_first"):
        if (1, layout) in res and (2, layout) in res:
            a, b = res[(1, layout)], res[(2, layout)]
            L.append(f"**{layout}** — rep 1 vs rep 2:")
            for label, key in (("chose B", "letter_b"), ("anonymised", "anon"),
                               ("identified", "ident"), ("swap-following", "swap")):
                pa, pb = a[key]["p"], b[key]["p"]
                overlap = a[key]["boot"][0] <= b[key]["boot"][1] and b[key]["boot"][0] <= a[key]["boot"][1]
                L.append(f"- {label}: {100*pa:.1f}% vs {100*pb:.1f}% "
                         f"(Δ {100*(pb-pa):+.1f}; intervals {'overlap' if overlap else 'DO NOT overlap'})")
            L.append(f"- name effect: {100*a['name_effect']:+.1f} vs {100*b['name_effect']:+.1f} points")
            L.append("")

    L += ["## Position effect by condition", "",
          "Share choosing B when B is listed first vs second. Positive = the first-listed "
          "company is favoured; negative = the second.", "",
          "| replicate | condition | B first | B second | position effect |", "|---|---|---|---|---|"]
    for rep in (1, 2):
        if (rep, "a_first") in res and (rep, "b_first") in res:
            for c in CONDS:
                bf = res[(rep, "b_first")]["b_by_cond"][c]
                bs = res[(rep, "a_first")]["b_by_cond"][c]
                L.append(f"| {rep} | {c} | {100*bf:.0f}% | {100*bs:.0f}% | {100*(bf-bs):+.0f} |")

    order_rows = []
    for k in keys:
        oc, _ = order_consistency([r for r in runs[k] if r["parsed_choice"]])
        order_rows.append(f"| rep {k[0]} · {k[1]} | " + " | ".join(f"{100*oc[c]['p']:.0f}%" for c in CONDS) + " |")
    L += ["", "## Order consistency", "",
          "Same company chosen when the A/B labels are exchanged (50% = random).", "",
          "| run | identified | anonymised | swapped |", "|---|---|---|---|"] + order_rows

    all_rows = [r for v in runs.values() for r in v]
    if len(runs) == 4:
        p = numbers(all_rows)
        ne_lo, ne_hi = name_effect_ci(all_rows)
        swap_a = numbers([r for r in all_rows if r["layout"] == "a_first"])["swap"]
        swap_b = numbers([r for r in all_rows if r["layout"] == "b_first"])["swap"]
        slot = by_pair([r for r in all_rows if r["parsed_choice"]],
                       lambda r: r["parsed_choice"] == ("B" if r["layout"] == "a_first" else "A"))
        L += ["", "## Pooled estimates — all four runs (2,400 calls)", "",
              "Letter and slot are fully counterbalanced, so these are the numbers to quote.", "",
              f"- Chose the letter **B**: {pct(p['letter_b'])}",
              f"- Chose the **second-listed** company: {pct(slot)}",
              f"- Anonymised choice rate (large-cap numbers): {pct(p['anon'])}",
              f"- Identified choice rate (large-cap name): {pct(p['ident'])}",
              f"- **Name effect** (identified − anonymised): {100*p['name_effect']:+.1f} points "
              f"[{100*ne_lo:+.1f} to {100*ne_hi:+.1f}]",
              f"- **Swap-following** (numbers over name): {pct(p['swap'])}; pairs without a "
              f"reference: {len(p['swap']['excluded'])}/20",
              f"- Parse failures: {p['fails']}/{p['n']}", "",
              f"Swap-following by layout, both replicates pooled: A listed first {pct(swap_a)}, "
              f"B listed first {pct(swap_b)}.", "",
              "## Verdict", "",
              f"Across four runs and 2,400 calls, the 3B model shows no detectable name bias: naming the "
              f"companies moved the large-cap share by {100*p['name_effect']:+.1f} points "
              f"(95% {100*ne_lo:+.1f} to {100*ne_hi:+.1f}), and single-run estimates ranged from "
              f"{100*min(x['name_effect'] for x in res.values()):+.1f} to "
              f"{100*max(x['name_effect'] for x in res.values()):+.1f}, which is sampling noise around zero; "
              f"an effect larger than about {100*max(abs(ne_lo), abs(ne_hi)):.0f} points is ruled out. "
              f"But that null carries little weight, because its choices are driven mainly by the answer label, B in {100*p['letter_b']['p']:.0f}% "
              f"of answers, and the swap measurement depends on layout "
              f"({100*swap_a['p']:.0f}% when A is listed first, {100*swap_b['p']:.0f}% when B is), "
              f"so a model this dominated by the label has little room to show name loyalty, and by "
              f"this pilot's own rules the task framing is too weak at 3B to answer the research "
              f"question either way.", "",
              "## Limitations", "",
              "- One model: Qwen2.5-3B-Instruct, 4-bit MLX weights. The 7B run could not "
              "complete on 8GB and was abandoned.",
              "- The b_first layout and replicate 2 were added after replicate 1 had been read. "
              "They are diagnostics of a bias found in the data, not pre-registered conditions.",
              "- Replicate 1 was unseeded and cannot be regenerated exactly; replicate 2 used seeds "
              "2000 (a_first) and 2001 (b_first).",
              "- \"Letter B\" and \"last option in the answer instructions\" are not separated: "
              "`CHOICE: B` is the last answer line in both layouts.",
              "- Effective sample size is about 20 pairs; intervals resample pairs, not calls.", ""]

    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
