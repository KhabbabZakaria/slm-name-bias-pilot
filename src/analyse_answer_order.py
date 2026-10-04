"""Answer-order diagnostic: does the model like the letter B, or the last option?

Four setups, crossing which company block is listed first with which answer
option is listed last. Each company is A in half the samples and B in the
other half, so a choice made on merit splits evenly between the letters.

Writes results/answer_order.md.
"""

import json
from collections import defaultdict
from pathlib import Path

from analyse import rate
from analyse_replication import numbers

RES = Path(__file__).resolve().parent.parent / "results"
OUT = RES / "answer_order.md"

SETUPS = [  # layout, file, block listed first, answer listed last
    ("a_first", "raw.jsonl", "A", "B"),
    ("b_first", "raw_b_first.jsonl", "B", "B"),
    ("a_first_ans_ba", "raw_a_first_ans_ba.jsonl", "A", "A"),
    ("b_first_ans_ba", "raw_b_first_ans_ba.jsonl", "B", "A"),
]


def by_pair(rows, pred):
    d = defaultdict(list)
    for r in rows:
        d[r["pair_id"]].append(int(pred(r)))
    return rate(d)


def main():
    L = ["# Letter B or last answer option? (3B)", "",
         "| setup | company listed first | answer listed last | chose A | chose B |",
         "|---|---|---|---|---|"]
    pooled = []
    for layout, name, first, last in SETUPS:
        path = RES / name
        if not path.exists():
            L.append(f"| {layout} | {first} | {last} | not run | |")
            continue
        rows = [json.loads(l) for l in path.open()]
        rows = [r for r in rows if r["parsed_choice"]]
        for r in rows:
            r["_first"], r["_last"] = first, last
        pooled += rows
        pa = sum(r["parsed_choice"] == "A" for r in rows) / len(rows)
        L.append(f"| {layout} | {first} | {last} | {100*pa:.1f}% | {100*(1-pa):.1f}% |")

    if len({r["_last"] for r in pooled}) == 2:
        fmt = lambda x: f"{100*x['p']:.1f}% [{100*x['boot'][0]:.0f}–{100*x['boot'][1]:.0f}]"
        letter = by_pair(pooled, lambda r: r["parsed_choice"] == "B")
        last = by_pair(pooled, lambda r: r["parsed_choice"] == r["_last"])
        second = by_pair(pooled, lambda r: r["parsed_choice"] != r["_first"])
        L += ["", "All four setups together (50% = no preference):", "",
              f"- chose the **letter B**: {fmt(letter)}",
              f"- chose the **answer option listed last**: {fmt(last)}",
              f"- chose the **company listed second**: {fmt(second)}", "",
              "Brackets are pair-bootstrap 95% intervals. Whichever is far from 50% "
              "is what drives the choice.", ""]

    # Replication of the two answer-reversed setups.
    L += ["## Second run of the answer-reversed setups", "",
          "| setup | run | chose B | followed the numbers (swap) | name effect |",
          "|---|---|---|---|---|"]
    for layout in ("a_first_ans_ba", "b_first_ans_ba"):
        for rep, name in ((1, f"raw_{layout}.jsonl"), (2, f"raw_{layout}_rep2.jsonl")):
            path = RES / name
            if not path.exists():
                L.append(f"| {layout} | {rep} | not run | | |")
                continue
            x = numbers([json.loads(l) for l in path.open()])
            sw = x["swap"]
            L.append(f"| {layout} | {rep} | {100*x['letter_b']['p']:.1f}% | "
                     f"{100*sw['p']:.1f}% [{100*sw['boot'][0]:.0f}–{100*sw['boot'][1]:.0f}] | "
                     f"{100*x['name_effect']:+.1f} |")
    L.append("")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
