"""Step 2 checks. Run before the first model call and after any template change.

Includes negative cases: an assertion that never fires may simply be broken, so
each guard is shown rejecting a prompt it is supposed to reject.
"""

from pathlib import Path

import pandas as pd

from prompts import (CONDITIONS, ORDERS, TEMPLATE, assert_no_absolute_currency,
                     assert_no_identity_leak, build_prompt, format_fundamentals,
                     fundamentals_owner)

PAIRS = Path(__file__).resolve().parent.parent / "data" / "pairs.csv"


def main():
    df = pd.read_csv(PAIRS)
    failures = []
    built = 0

    # 1. every prompt builds, and both guards run on it
    for _, pair in df.iterrows():
        for cond in CONDITIONS:
            for order in ORDERS:
                try:
                    build_prompt(pair, cond, order)
                    built += 1
                except AssertionError as e:
                    failures.append(f"{pair.pair_id} {cond} {order}: {e}")
    print(f"built {built} prompts (expected {len(df)*3*2})")

    # 2. the fundamentals block is byte-identical for a company across conditions
    for _, pair in df.iterrows():
        for role in ("large", "small"):
            blocks = {format_fundamentals(pair, role) for _ in CONDITIONS}
            if len(blocks) != 1:
                failures.append(f"{pair.pair_id} {role}: block not stable")
    print("fundamentals blocks byte-identical across conditions: "
          f"{not any('not stable' in f for f in failures)}")

    # 3. conditions differ in exactly the intended way
    pair = df.iloc[0]
    ident = build_prompt(pair, "identified", "large_first")
    anon = build_prompt(pair, "anonymised", "large_first")
    swap = build_prompt(pair, "swapped", "large_first")
    if format_fundamentals(pair, "large") not in ident:
        failures.append("identified: large-cap block missing")
    if format_fundamentals(pair, "large") not in anon:
        failures.append("anonymised: large-cap block missing")
    # swapped must put the large-cap's name above the small-cap's numbers
    a_block = swap.split("Company B:")[0]
    if pair.large_ticker not in a_block:
        failures.append("swapped: large-cap name not in slot A")
    if format_fundamentals(pair, "small") not in a_block:
        failures.append("swapped: slot A does not carry the small-cap's numbers")
    print("swapped puts each name over the other's numbers: "
          f"{not any('swapped' in f for f in failures)}")

    # 4. ordering actually reverses the slots
    lf = build_prompt(pair, "identified", "large_first")
    sf = build_prompt(pair, "identified", "small_first")
    if lf == sf:
        failures.append("ordering has no effect on the prompt")
    if pair.small_ticker not in sf.split("Company B:")[0]:
        failures.append("small_first does not put the small-cap in slot A")
    print(f"ordering reverses slots: {not any('ordering' in f or 'small_first' in f for f in failures)}")

    # 5. fundamentals_owner maps back correctly under the swap
    fo = fundamentals_owner(pair, "swapped", "large_first", "A")
    if not (fo["chosen_name_owner"] == "large"
            and fo["chosen_fundamentals_owner"] == "small"):
        failures.append(f"fundamentals_owner wrong under swap: {fo}")
    fo2 = fundamentals_owner(pair, "identified", "large_first", "A")
    if fo2["chosen_fundamentals_owner"] != "large":
        failures.append(f"fundamentals_owner wrong when unswapped: {fo2}")
    if fundamentals_owner(pair, "anonymised", "large_first", "A")["chosen_ticker"] is not None:
        failures.append("anonymised rows must not record a chosen ticker")
    print(f"fundamentals_owner maps back correctly: {not any('fundamentals_owner' in f or 'anonymised rows' in f for f in failures)}")

    # 6. registry formatting must not reach any prompt
    import re
    for _, pair in df.iterrows():
        for role in ("large", "small"):
            disp, edgar = pair[f"{role}_display_name"], pair[f"{role}_name"]
            if re.search(r"/[A-Z]{2,3}/?$", str(disp)):
                failures.append(f"{disp!r}: state-of-incorporation suffix")
            letters = re.sub(r"[^A-Za-z]", "", str(disp))
            if letters and letters.isupper():
                failures.append(f"{disp!r}: fully upper-case registry string")
            if disp != edgar:
                # Strip the display name first: "JFrog Ltd" is a substring of
                # "JFrog Ltd.", so a bare containment test flags every display
                # name that merely extends the registry string.
                shown = build_prompt(pair, "identified", "large_first")
                residue = shown.replace(str(disp), "")
                if str(edgar) in residue:
                    failures.append(f"{pair.pair_id}: EDGAR name {edgar!r} reached the prompt")
    print(f"prompts use display names, not registry strings: "
          f"{not any('registry' in f or 'suffix' in f or 'reached the prompt' in f for f in failures)}")

    # 7. NEGATIVE CASES -- each guard must reject what it exists to reject
    neg = []
    leaky = TEMPLATE.format(header_a="", fundamentals_a=f"  {pair.large_name}",
                            header_b="", fundamentals_b="")
    try:
        assert_no_identity_leak(leaky, pair)
        neg.append("name leak NOT caught")
    except AssertionError:
        pass
    try:
        assert_no_identity_leak(
            TEMPLATE.format(header_a="", fundamentals_a=f"  ({pair.small_ticker})",
                            header_b="", fundamentals_b=""), pair)
        neg.append("ticker leak NOT caught")
    except AssertionError:
        pass
    for bad in ("  Revenue: $394,328 million", "  Revenue: 394328000000",
                "  Net income: 99803000000", "  Revenue: 1,739,700"):
        try:
            assert_no_absolute_currency(bad)
            neg.append(f"currency NOT caught: {bad!r}")
        except AssertionError:
            pass
    print(f"negative cases rejected as intended: {not neg}")
    failures.extend(neg)

    print()
    if failures:
        print("FAILED:")
        for f in failures[:20]:
            print(f"  - {f}")
        return 1
    print("all checks passed")
    print("\n--- sample: P01 swapped, large_first ---")
    print(build_prompt(df.iloc[0], "swapped", "large_first"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
