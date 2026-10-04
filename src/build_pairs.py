"""Step 1b: match the fetched universe into 20 large/small pairs.

Reads data/universe.csv, writes data/pairs.csv. No network access -- rerun it
freely while tuning the constants below.

Two things this script is careful about:

* public_float decides the large/small split and never leaves this file. It is
  not written into pairs.csv as a prompt-visible field and the prompt builder
  has no business reading it.
* Absolute currency figures are carried into pairs.csv because the ratios are
  derived from them and the full study will want them, but the prompt shows
  ratios only. Scale is not a fundamental; it is an identity cue.
"""

from pathlib import Path

import pandas as pd

from display_names import display_name

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE = ROOT / "data" / "universe.csv"
OUT = ROOT / "data" / "pairs.csv"

N_PAIRS = 20
MATCH_TOL = 0.20          # relative, not percentage points -- see match_distance
SMALL_MIN_FLOAT = 0.3e9
LARGE_MIN_FLOAT = 10e9
FLOAT_RATIO_BAND = (3.0, 60.0)
FLOAT_RATIO_PENALTY = 0.02  # mild tilt toward tighter pairs; see below

# The only fields the prompt is allowed to show. Everything else in pairs.csv
# exists for the full study or for audit.
PROMPT_RATIOS = ["rev_growth_pct", "gross_margin_pct", "op_margin_pct",
                 "net_margin_pct", "debt_to_revenue"]

# Direction that counts as the better number for each prompt-visible ratio.
BETTER_WHEN_HIGHER = {"rev_growth_pct": True, "gross_margin_pct": True,
                      "op_margin_pct": True, "net_margin_pct": True,
                      "debt_to_revenue": False}


def add_ratios(df):
    df = df.copy()
    df["rev_growth_pct"] = (df.revenue - df.revenue_prior) / df.revenue_prior.abs() * 100
    df["gross_margin_pct"] = df.gross_profit / df.revenue * 100
    df["op_margin_pct"] = df.operating_income / df.revenue * 100
    df["net_margin_pct"] = df.net_income / df.revenue * 100
    df["debt_to_revenue"] = df.total_debt / df.revenue
    return df


def relative_diff(a, b):
    """|a-b| / max(|a|,|b|) -- relative, not percentage points.

    Percentage points would call 5% and 24% operating margin a match, which is
    an instant human pick. Relative keeps the pair genuinely hard to choose.
    """
    denom = max(abs(a), abs(b))
    if denom == 0:
        return 0.0 if a == b else float("inf")
    return abs(a - b) / denom


def match_distance(big, small):
    """Distance for a candidate pair, or None if it fails a hard constraint."""
    # Hard constraint 1: opposite signs are never a close match, whatever the
    # ratio test says about magnitude.
    if (big.op_margin_pct > 0) != (small.op_margin_pct > 0):
        return None
    if (big.rev_growth_pct > 0) != (small.rev_growth_pct > 0):
        return None

    # Hard constraint 2: profitable vs loss-making is an instant human pick.
    if (big.net_income > 0) != (small.net_income > 0):
        return None

    d_growth = relative_diff(big.rev_growth_pct, small.rev_growth_pct)
    d_margin = relative_diff(big.op_margin_pct, small.op_margin_pct)
    if d_growth > MATCH_TOL or d_margin > MATCH_TOL:
        return None

    # Hard constraint 3: neither side may win on every prompt-visible ratio.
    #
    # Matching on growth and operating margin alone leaves the other three free,
    # and a pair can be tight on both matched ratios while one company sweeps all
    # five -- Autodesk/Bentley and Fortinet/Synaptics both did. That is CLAUDE.md's
    # own disqualifier: a human picks the winner instantly, so the pair measures
    # nothing.
    #
    # Note this rejects only a clean sweep, not every imbalance. The swapped
    # condition needs each pair to have a discernible better-on-fundamentals side:
    # swap-following asks whether the model follows the numbers when the numbers
    # move, and a pair matched perfectly on all five would leave nothing to follow
    # and put the 100% anchor out of reach. Some per-pair signal is the point.
    big_wins = small_wins = 0
    for col, higher_is_better in BETTER_WHEN_HIGHER.items():
        b_val, s_val = big[col], small[col]
        if b_val == s_val:
            continue
        if (b_val > s_val) == higher_is_better:
            big_wins += 1
        else:
            small_wins += 1
    if big_wins == 0 or small_wins == 0:
        return None

    ratio = big.public_float / small.public_float
    if not FLOAT_RATIO_BAND[0] <= ratio <= FLOAT_RATIO_BAND[1]:
        return None

    # Tilt toward larger small-caps and smaller large-caps. A $600m company and
    # a $390bn company differ in ways no ratio captures -- analyst coverage,
    # index membership, cost of capital -- so a tighter float ratio makes the
    # pair more comparable on its merits. This is a preference, not a filter:
    # the band above already sets the hard limit.
    import math
    return (d_growth + d_margin) / 2 + FLOAT_RATIO_PENALTY * math.log(ratio)


def main():
    df = add_ratios(pd.read_csv(UNIVERSE))
    large = df[df.public_float >= LARGE_MIN_FLOAT]
    small = df[(df.public_float >= SMALL_MIN_FLOAT) &
               (df.public_float < LARGE_MIN_FLOAT)]
    print(f"{len(large)} large-cap and {len(small)} small-cap candidates")

    candidates = []
    for _, b in large.iterrows():
        for _, s in small.iterrows():
            d = match_distance(b, s)
            if d is not None:
                candidates.append((d, b.ticker, s.ticker))
    candidates.sort()
    print(f"{len(candidates)} admissible pairings before disjointness")

    # Greedy on ascending distance. Optimal assignment would be marginally
    # tighter; at 20 pairs the difference is not worth the dependency.
    used, chosen = set(), []
    for d, bt, st in candidates:
        if bt in used or st in used:
            continue
        used.update([bt, st])
        chosen.append((d, bt, st))
        if len(chosen) == N_PAIRS:
            break

    if len(chosen) < N_PAIRS:
        print(f"WARNING: only {len(chosen)} disjoint pairs found "
              f"(wanted {N_PAIRS}). Loosen MATCH_TOL or FLOAT_RATIO_BAND.")

    by_ticker = df.set_index("ticker")
    carry = ["name", "cik", "fiscal_year", "revenue", "revenue_prior",
             "gross_profit", "operating_income", "net_income", "total_debt",
             "debt_source"] + PROMPT_RATIOS

    rows = []
    for i, (d, bt, st) in enumerate(chosen, 1):
        b, s = by_ticker.loc[bt], by_ticker.loc[st]
        row = {"pair_id": f"P{i:02d}", "fiscal_year": int(b.fiscal_year),
               "match_distance": round(d, 4),
               "float_ratio": round(b.public_float / s.public_float, 1)}
        for role, rec, tick in (("large", b, bt), ("small", s, st)):
            row[f"{role}_ticker"] = tick
            # The prompt shows this; row[f"{role}_name"] keeps EDGAR's registry
            # string alongside it for audit.
            row[f"{role}_display_name"] = display_name(tick)
            for c in carry:
                if c == "fiscal_year":
                    continue
                row[f"{role}_{c}"] = rec[c]
        rows.append(row)

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(f"\nwrote {len(out)} pairs -> {OUT}")

    assert not any("public_float" in c for c in out.columns), \
        "public_float must not reach pairs.csv: it is a selection field only"
    return out


if __name__ == "__main__":
    main()
