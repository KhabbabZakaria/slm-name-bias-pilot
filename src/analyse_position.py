"""Position-bias diagnostic: is the preference for B about the letter or the slot?

In the original layout (a_first) Company B is always listed second, so a
preference for B and a preference for the second-listed company are the same
thing. The b_first run lists B first and A second, which separates them:

    bias follows the slot   -> A (now second) wins about as often as B did
    bias follows the letter -> B still wins, though now listed first

With both layouts and both orderings, every company appears in every slot under
every letter, so pooling the two runs counterbalances whichever bias it is. The
pooled three numbers are reported as a secondary result, not a replacement for
summary.md: the b_first run is a diagnostic added after the first run was read.
"""

import json
from collections import defaultdict
from pathlib import Path

from analyse import fmt, order_consistency, rate, swap_following

ROOT = Path(__file__).resolve().parent.parent
A_FIRST = ROOT / "results" / "raw.jsonl"
B_FIRST = ROOT / "results" / "raw_b_first.jsonl"
OUT = ROOT / "results" / "position_diagnostic.md"


def load(path, layout):
    rows = [json.loads(l) for l in path.open()]
    for r in rows:
        r.setdefault("layout", layout)
    return [r for r in rows if r["parsed_choice"]]


def second_listed(r):
    return r["parsed_choice"] == ("B" if r["layout"] == "a_first" else "A")


def by_pair(rows, pred):
    d = defaultdict(list)
    for r in rows:
        d[r["pair_id"]].append(int(pred(r)))
    return rate(d)


def three_numbers(rows):
    def cond(c, field):
        return by_pair([r for r in rows if r["condition"] == c],
                       lambda r: r[field] == "large")
    return (cond("anonymised", "chosen_fundamentals_owner"),
            cond("identified", "chosen_name_owner"),
            swap_following(rows, "identified"))


def main():
    a = load(A_FIRST, "a_first")
    b = load(B_FIRST, "b_first")
    L = ["# Position-bias diagnostic (3B)", "",
         "Diagnostic run added after the main run. Same pairs, conditions, orderings "
         "and samples; the only change is that the Company B block is listed before "
         "Company A.", "",
         "## Letter or slot?", "",
         "| layout | listed first | listed second | chose A | chose B | chose second-listed |",
         "|---|---|---|---|---|---|"]
    for name, rows in (("a_first", a), ("b_first", b)):
        pa = sum(r["parsed_choice"] == "A" for r in rows) / len(rows)
        ps = sum(second_listed(r) for r in rows) / len(rows)
        first, second = ("A", "B") if name == "a_first" else ("B", "A")
        L.append(f"| {name} | {first} | {second} | {100*pa:.1f}% | {100*(1-pa):.1f}% | {100*ps:.1f}% |")

    both = a + b
    slot = by_pair(both, second_listed)
    letter = by_pair(both, lambda r: r["parsed_choice"] == "B")
    L += ["", "Across both layouts, where letter and slot are counterbalanced:", "",
          f"- chose the **second-listed** company: {fmt(slot)}",
          f"- chose the **letter B**: {fmt(letter)}", "",
          "A slot bias shows as the first number far from 50% and the second near it; "
          "a letter bias shows the reverse.", ""]

    L += ["## Order consistency by layout", ""]
    for name, rows in (("a_first", a), ("b_first", b)):
        oc, a_share = order_consistency(rows)
        L.append(f"- {name}: " + "; ".join(f"{c} {100*r['p']:.0f}%" for c, r in oc.items()))

    L += ["", "## The three numbers", "",
          "| | a_first (main run) | b_first | pooled, counterbalanced |", "|---|---|---|---|"]
    ta, tb, tp = three_numbers(a), three_numbers(b), three_numbers(both)
    labels = ["Anonymised (large-cap numbers)", "Identified (large-cap name)",
              "Swap-following (numbers over name)"]
    for i, lab in enumerate(labels):
        cells = [f"{100*t[i]['p']:.1f}% [{100*t[i]['boot'][0]:.0f}–{100*t[i]['boot'][1]:.0f}]"
                 for t in (ta, tb, tp)]
        L.append(f"| {lab} | " + " | ".join(cells) + " |")
    L += ["", "Brackets are pair-bootstrap 95% intervals.", "",
          f"Name effect (identified − anonymised): a_first {100*(ta[1]['p']-ta[0]['p']):+.1f}, "
          f"b_first {100*(tb[1]['p']-tb[0]['p']):+.1f}, pooled {100*(tp[1]['p']-tp[0]['p']):+.1f} points.", ""]

    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
