"""Step 1c: checks on data/pairs.csv, to run after any change to the pair set.

Nothing here is a model experiment. These are the checks that decide whether a
result from the real run can be interpreted at all:

* Systematic tilt -- if a prompt-visible ratio favours the same side across
  pairs, the anonymised condition cannot land near 50/50 and a broken control
  is indistinguishable from a real effect.
* Domination -- a pair where one side wins every ratio measures nothing.
* Disjointness -- each company must appear once, or pairs are not independent.
"""

from math import comb
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PAIRS = ROOT / "data" / "pairs.csv"

BETTER_WHEN_HIGHER = {"rev_growth_pct": True, "gross_margin_pct": True,
                      "op_margin_pct": True, "net_margin_pct": True,
                      "debt_to_revenue": False}


def sign_test(k, n):
    """Two-sided exact binomial test against p=0.5."""
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(n + 1)
               if abs(i - n / 2) >= abs(k - n / 2))
    return min(tail / 2 ** n, 1.0)


def large_wins(row, col):
    """1 if the large-cap has the better number, -1 if the small-cap, 0 if tied."""
    b, s = row[f"large_{col}"], row[f"small_{col}"]
    if b == s:
        return 0
    return 1 if (b > s) == BETTER_WHEN_HIGHER[col] else -1


def main():
    df = pd.read_csv(PAIRS)
    failures = []

    print(f"{len(df)} pairs, fiscal year {sorted(df.fiscal_year.unique())}\n")

    print("TILT -- does any prompt-visible ratio favour the same side systematically?")
    for col in BETTER_WHEN_HIGHER:
        w = df.apply(lambda r: large_wins(r, col), axis=1)
        k, n = int((w > 0).sum()), int((w != 0).sum())
        p = sign_test(k, n)
        flag = ""
        if p < 0.05:
            flag = "  <-- TILTED"
            failures.append(f"{col} favours one side systematically (p={p:.3f})")
        print(f"  {col:18s} large better {k:2d}/{n:2d}   p={p:.3f}{flag}")

    print("\nDOMINATION -- pairs where one side wins every ratio:")
    counts = {}
    dominated = []
    for _, r in df.iterrows():
        w = [large_wins(r, c) for c in BETTER_WHEN_HIGHER]
        nL, nS = sum(x > 0 for x in w), sum(x < 0 for x in w)
        counts[nL] = counts.get(nL, 0) + 1
        if nL == 0 or nS == 0:
            dominated.append(f"{r.pair_id} {r.large_ticker}/{r.small_ticker}")
    if dominated:
        failures.append(f"dominated pairs: {', '.join(dominated)}")
        print("  " + "\n  ".join(dominated))
    else:
        print("  none")
    print("  spread of 'large-cap wins k of 5':",
          ", ".join(f"{k}->{counts.get(k,0)}" for k in range(6)))

    print("\nSTRUCTURE")
    tickers = list(df.large_ticker) + list(df.small_ticker)
    if len(set(tickers)) != len(tickers):
        dupes = {t for t in tickers if tickers.count(t) > 1}
        failures.append(f"companies reused across pairs: {sorted(dupes)}")
    print(f"  {len(set(tickers))} distinct companies across {len(df)} pairs "
          f"({'disjoint' if len(set(tickers)) == 2*len(df) else 'REUSED'})")
    if any("public_float" in c for c in df.columns):
        failures.append("public_float leaked into pairs.csv")
    print(f"  public_float absent: {not any('public_float' in c for c in df.columns)}")
    print(f"  float ratio: min {df.float_ratio.min():.1f}x  "
          f"median {df.float_ratio.median():.1f}x  max {df.float_ratio.max():.1f}x")

    print()
    if failures:
        print("FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
