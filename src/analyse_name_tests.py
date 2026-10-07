"""Compares every relabelling test against the same prompts with real names.

Each test swaps one company's name and ticker, leaving its numbers untouched, so
any change in how often that company is picked is attributable to the name. The
baseline is the identified condition of the ord_a_first run: same layout, same
pairs, same orderings, same sample count.

What each test is for:

  apple / apple_rep2  does a household name move the choice, and does it replicate
  apple_first         mirror: the same label on the first company instead
  norwell             control: an invented name. If this moves the choice as much
                      as Apple, the effect is unfamiliarity, not fame
  microsoft           a second household name, so the result is not about "Apple"

Writes results/name_tests.md.
"""

import json
import random
from collections import defaultdict
from pathlib import Path

RES = Path(__file__).resolve().parent.parent / "results"
OUT = RES / "name_tests.md"
N_BOOT = 10_000

TESTS = [  # tag, file stem, label, slot
    ("apple", "raw_fake_apple", "Apple Inc. (AAPL)", "second"),
    ("apple_rep2", "raw_fake_apple_rep2", "Apple Inc. (AAPL), rerun", "second"),
    ("apple_first", "raw_fake_apple_first", "Apple Inc. (AAPL)", "first"),
    ("norwell", "raw_fake_norwell", "Norwell Systems (NWLS) — control", "second"),
    ("microsoft", "raw_fake_microsoft", "Microsoft Corporation (MSFT)", "second"),
]


def picked(row, slot):
    """Did the model pick the company in this slot? A is first, B is second."""
    return row["parsed_choice"] == ("B" if slot == "second" else "A")


def rates(base, test, slot):
    """Share picking the labelled slot, before and after, with a pair bootstrap."""
    per = defaultdict(lambda: [[], []])
    for i, rows in enumerate((base, test)):
        for r in rows:
            if r["parsed_choice"]:
                per[r["pair_id"]][i].append(int(picked(r, slot)))
    pairs = [p for p in per.values() if p[0] and p[1]]
    flat = lambda rows, i: [x for p in rows for x in p[i]]
    b, t = flat(pairs, 0), flat(pairs, 1)
    rng, diffs = random.Random(1), []
    for _ in range(N_BOOT):
        draw = [rng.choice(pairs) for _ in pairs]
        db, dt = flat(draw, 0), flat(draw, 1)
        diffs.append(sum(dt) / len(dt) - sum(db) / len(db))
    diffs.sort()
    share = lambda v: sum(v) / len(v)
    return {
        "base": (sum(b), len(b)), "test": (sum(t), len(t)),
        "delta": share(t) - share(b),
        "ci": (diffs[int(0.025 * N_BOOT)], diffs[int(0.975 * N_BOOT) - 1]),
        "up": sum(1 for p in pairs if share(p[1]) > share(p[0])),
        "down": sum(1 for p in pairs if share(p[1]) < share(p[0])),
        "pairs": len(pairs),
    }


def main(model="qwen2.5-3b"):
    base_path = RES / ("raw_ord_a_first.jsonl" if model == "qwen2.5-3b"
                       else f"raw_ord_a_first__{model}.jsonl")
    base = [r for r in map(json.loads, base_path.open())
            if r["condition"] == "identified"]

    L = [f"# Does the name move the choice? ({model})", "",
         "One company's name and ticker are replaced; its numbers are left alone. "
         "Compared against the identical prompts with real names "
         "(20 pairs × both orderings × 5 samples ≈ 200 answers per cell).", "",
         "| label | slot | picked with real name | picked with new label | change | pairs up/down |",
         "|---|---|---|---|---|---|"]
    found = {}
    for tag, stem, label, slot in TESTS:
        path = RES / f"{stem}__{model}.jsonl"
        if not path.exists():
            L.append(f"| {label} | {slot} | — | not run | | |")
            continue
        rows = [json.loads(l) for l in path.open()]
        r = rates(base, rows, slot)
        found[tag] = r
        bk, bn = r["base"]
        tk, tn = r["test"]
        L.append(f"| {label} | {slot} | {bk}/{bn} ({100*bk/bn:.1f}%) | {tk}/{tn} ({100*tk/tn:.1f}%) | "
                 f"**{100*r['delta']:+.1f} pts** [{100*r['ci'][0]:+.1f} to {100*r['ci'][1]:+.1f}] | "
                 f"{r['up']}/{r['down']} |")

    L += ["", "Brackets are pair-bootstrap 95% intervals. A change whose interval excludes "
          "zero is a real shift; one that spans zero is not.", ""]

    if "apple" in found and "norwell" in found:
        a, n = found["apple"], found["norwell"]
        L += ["## Reading it", ""]
        gap = a["delta"] - n["delta"]
        if n["ci"][1] < 0:
            verdict = ("The control moves the choice the *other* way, and its interval "
                       "excludes zero: an unfamiliar name is a penalty. So this is not "
                       "\"any relabelling helps\" — it is a familiarity gradient, "
                       f"spanning about {100*gap:.0f} points from an invented name to a "
                       "household one.")
        elif n["ci"][0] > 0:
            verdict = ("The control moves the choice too, so part of the Apple effect is "
                       "relabelling rather than fame; the gap between them "
                       f"({100*gap:+.1f} points) is what fame adds.")
        else:
            verdict = ("The control's interval spans zero, so the shift is specific to the "
                       "famous name rather than to any relabelling.")
        L.append(
            f"- **Famous vs merely unfamiliar.** Apple moved the choice "
            f"{100*a['delta']:+.1f} points; the invented name Norwell Systems moved it "
            f"{100*n['delta']:+.1f}. " + verdict)
        if "apple_rep2" in found:
            r2 = found["apple_rep2"]
            L.append(f"- **Replication.** The Apple test rerun with a different seed gave "
                     f"{100*r2['delta']:+.1f} points against {100*a['delta']:+.1f} first time"
                     + (" — consistent." if (r2["ci"][0] <= a["delta"] <= r2["ci"][1]) else
                        " — the two runs disagree, so treat the size as unsettled."))
        if "apple_first" in found:
            m = found["apple_first"]
            L.append(f"- **Mirror.** With the Apple label on the *first* company instead, the "
                     f"shift was {100*m['delta']:+.1f} points [{100*m['ci'][0]:+.1f} to "
                     f"{100*m['ci'][1]:+.1f}]"
                     + (". The name pulls the choice in both directions, so it is the label and "
                        "not the position." if m["ci"][0] > 0 else
                        f". Nothing. The first slot already wins {100*m['base'][0]/m['base'][1]:.0f}% "
                        "of the time without any relabelling, and the Apple label adds nothing on "
                        "top. So the name effect shows up only where the layout is working "
                        "*against* the labelled company: label and position interact, and the "
                        "headline cannot be stated as a pure name effect."))
        if "microsoft" in found:
            ms = found["microsoft"]
            L.append(f"- **A second household name.** Microsoft moved the choice "
                     f"{100*ms['delta']:+.1f} points [{100*ms['ci'][0]:+.1f} to "
                     f"{100*ms['ci'][1]:+.1f}]"
                     + (", so the effect is not peculiar to the word \"Apple\"."
                        if ms["ci"][0] > 0 else
                        ", so the effect may be specific to Apple rather than to famous names "
                        "in general."))
        L.append("")

    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
