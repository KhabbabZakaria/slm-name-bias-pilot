"""Step 1a: pull FY2022 fundamentals for the candidate universe from SEC EDGAR.

Writes data/universe.csv -- one row per company that clears the SIC filter and
has complete data. Pairing happens in build_pairs.py; this script only fetches.
Keeping them separate means a bad tag mapping costs a re-parse, not a re-download
(raw companyfacts JSON is cached under data/cache/).

EDGAR requires a descriptive User-Agent with a contact address. Set it yourself:

    export SEC_USER_AGENT="Your Name your.email@example.com"
"""

import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "data" / "universe.csv"

FISCAL_YEAR = 2022
PRIOR_YEAR = FISCAL_YEAR - 1

USER_AGENT = os.environ.get(
    "SEC_USER_AGENT", "rq3-pilot research-contact@example.com"
)
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
RATE_LIMIT_S = 0.12  # SEC asks for <= 10 requests/second

# Technology SIC codes. EDGAR's SIC assignments predate the modern technology
# sector and misfile a lot of it: Lam Research is "special industry machinery",
# KLA is "optical instruments", Corning is "nonferrous wire", Entegris is
# "plastics products". Restricting to the obvious software/semiconductor codes
# silently drops about fourteen large-cap technology companies, which is most of
# the large-cap side of the matching problem.
#
# The curated list in tech_universe.py is what actually defines the sector here;
# this check is a safety net against a ticker misremembered as technology, so it
# is set wide enough to admit the instrument and equipment codes that technology
# hardware really files under.
TECH_SIC_RANGES = [
    (3559, 3559),  # semiconductor capital equipment (LRCX, AMAT)
    (3560, 3560),  # industrial machinery, where ZBRA files
    (3570, 3579),  # computer and office equipment
    (3661, 3661), (3663, 3663), (3669, 3669),  # communications equipment
    (3670, 3679),  # semiconductors and electronic components
    (3812, 3812),  # navigation/detection electronics (GRMN, TDY)
    (3823, 3829),  # measuring and test instruments (KEYS, TER, KLAC, TRMB)
    (3089, 3089),  # ENTG -- semiconductor materials filed as plastics
    (3357, 3357),  # GLW -- optical fibre filed as wire drawing
    (4899, 4899),  # communications services NEC (CALX)
    (5961, 5961),  # IT resellers filed as catalog retail (CDW, NSIT)
    (7370, 7379),  # software, data processing, IT services
    (7389, 7389),  # business services NEC (AKAM)
    (8741, 8742),  # IT research/consulting (IT)
]

# Tag preference order. First tag present wins.
REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
]
COST_TAGS = ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfServices"]



def is_tech(sic):
    if sic is None:
        return False
    return any(lo <= int(sic) <= hi for lo, hi in TECH_SIC_RANGES)


def get_json(url, cache_name):
    """Fetch with an on-disk cache so re-parsing costs nothing."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name
    if path.exists():
        return json.loads(path.read_text())
    time.sleep(RATE_LIMIT_S)
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        return None
    path.write_text(resp.text)
    return resp.json()


def fiscal_year_of(end_date):
    """Map a period end date to a fiscal year label.

    A fiscal year ending in Jan-May belongs to the previous fiscal year by the
    usual convention: NVDA's year ending 2023-01-29 is FY2022.
    """
    year, month = int(end_date[:4]), int(end_date[5:7])
    return year if month >= 6 else year - 1


def annual_values(facts, tags, want_year=None, duration=True):
    """Return ({fiscal_year: value}, tag) for the first tag that covers want_year.

    Selecting on "first tag with any data" is wrong: filers migrate tags over
    time. Adobe reported LongTermDebtNoncurrent until 2015 and something else
    afterwards, so a first-match-wins selector returns a tag whose series stops
    seven years before the year we need, and the real value never gets found.
    """
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    fallback = ({}, None)
    for tag in tags:
        units = us_gaap.get(tag, {}).get("units", {}).get("USD")
        if not units:
            continue
        out = {}
        for entry in units:
            if entry.get("form") not in ("10-K", "10-K/A"):
                continue
            end = entry.get("end")
            if duration:
                start = entry.get("start")
                if not start:
                    continue
                span = (pd.Timestamp(end) - pd.Timestamp(start)).days
                if not 340 <= span <= 380:  # annual periods only
                    continue
            # Later entries supersede earlier ones (restatements).
            out[fiscal_year_of(end)] = entry["val"]
        if not out:
            continue
        if want_year is None or want_year in out:
            return out, tag
        if not fallback[0]:
            fallback = (out, tag)
    return fallback


def total_debt(facts, year):
    """Total debt for `year`, preferring tags that are already a total.

    Returns (value, source). Mixing a total tag for one company with a
    noncurrent+current sum for another makes the resulting ratio only loosely
    comparable across a pair, so the source is recorded per company.
    """
    combined, tag = annual_values(
        facts, ["DebtLongtermAndShorttermCombinedAmount",
                "DebtAndCapitalLeaseObligations"], year, duration=False)
    if year in combined:
        return combined[year], tag

    noncur, nc_tag = annual_values(
        facts, ["LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations"],
        year, duration=False)
    cur, c_tag = annual_values(
        facts, ["LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent",
                "DebtCurrent"], year, duration=False)
    # Require the noncurrent leg. Accepting a lone current balance understates
    # total debt badly -- Adobe's FY2022 current portion is $0.5bn against
    # roughly $3.6bn outstanding -- so a partial match falls through instead.
    if year in noncur:
        parts = [(nc_tag, noncur[year]), (c_tag, cur.get(year))]
        present = [(t, v) for t, v in parts if v is not None]
        return sum(v for _, v in present), "+".join(t for t, _ in present)

    single, s_tag = annual_values(
        facts, ["LongTermDebt", "DebtInstrumentCarryingAmount",
                "ConvertibleDebtNoncurrent", "ConvertibleNotesPayable",
                "ConvertibleNotesPayableNoncurrent", "ConvertibleDebt",
                "NotesPayable", "SeniorNotes"], year, duration=False)
    if year in single:
        extra = cur.get(year)
        if extra is not None:
            return single[year] + extra, f"{s_tag}+{c_tag}"
        return single[year], s_tag

    if year in cur:
        return cur[year], c_tag

    # No debt tag at all. Recorded as zero but flagged, so the choice is
    # auditable rather than silent -- see debt_source column.
    return 0.0, "no-debt-tag-assumed-zero"


def public_float(facts, revenue):
    """dei:EntityPublicFloat from the FY2022 10-K cover page."""
    units = (facts.get("facts", {}).get("dei", {})
             .get("EntityPublicFloat", {}).get("units", {}).get("USD"))
    if not units:
        return (None, None)
    candidates = [e for e in units if e.get("form") in ("10-K", "10-K/A")]
    if not candidates:
        return (None, None)
    # The cover-page float is measured mid-fiscal-year; take the measurement
    # sitting inside the FY2022 filing window.
    target = pd.Timestamp(f"{FISCAL_YEAR}-06-30")
    best = min(candidates, key=lambda e: abs(pd.Timestamp(e["end"]) - target))
    if abs((pd.Timestamp(best["end"]) - target).days) > 400:
        return (None, None)
    return scale_correct_float(best["val"], revenue)


def scale_correct_float(value, revenue):
    """Undo filer scale errors in EntityPublicFloat.

    A handful of filers tag this figure in thousands or millions while EDGAR
    treats it as whole dollars: Synaptics' FY2022 10-K reports a $3.26 *quadrillion*
    float and HubSpot's reports $13.7 trillion, both corrected in later filings.
    Left alone these dominate the large/small split. Anything implying a
    price/sales multiple above 100 is rescaled by powers of a thousand until it
    is plausible; if none is, the company is dropped rather than guessed at.
    """
    if revenue is None or revenue <= 0:
        return (value, 1)
    for factor in (1, 1_000, 1_000_000, 1_000_000_000):
        candidate = value / factor
        if 0.05 * revenue <= candidate <= 100 * revenue:
            return (candidate, factor)
    return (None, None)


def main():
    sys.path.insert(0, str(ROOT / "src"))
    from tech_universe import CANDIDATES

    if "example.com" in USER_AGENT:
        print("WARNING: SEC_USER_AGENT is unset; EDGAR may throttle or refuse.",
              file=sys.stderr)

    tickers = get_json("https://www.sec.gov/files/company_tickers.json",
                       "company_tickers.json")
    by_ticker = {v["ticker"]: v for v in tickers.values()}

    rows, skipped = [], []
    for i, ticker in enumerate(CANDIDATES, 1):
        rec = by_ticker.get(ticker)
        if rec is None:
            skipped.append((ticker, "no CIK"))
            continue
        cik = int(rec["cik_str"])
        cik10 = f"{cik:010d}"

        sub = get_json(f"https://data.sec.gov/submissions/CIK{cik10}.json",
                       f"sub_{cik10}.json")
        if sub is None:
            skipped.append((ticker, "submissions fetch failed"))
            continue
        sic = sub.get("sic")
        if not is_tech(sic):
            skipped.append((ticker, f"SIC {sic} not technology"))
            continue

        facts = get_json(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json",
            f"facts_{cik10}.json")
        if facts is None:
            skipped.append((ticker, "companyfacts fetch failed"))
            continue

        revenue, rev_tag = annual_values(facts, REVENUE_TAGS, FISCAL_YEAR)
        if FISCAL_YEAR not in revenue or PRIOR_YEAR not in revenue:
            skipped.append((ticker, "missing FY2021 or FY2022 revenue"))
            continue

        gross, _ = annual_values(facts, ["GrossProfit"], FISCAL_YEAR)
        gp = gross.get(FISCAL_YEAR)
        if gp is None:
            cost, _ = annual_values(facts, COST_TAGS, FISCAL_YEAR)
            if cost.get(FISCAL_YEAR) is not None:
                gp = revenue[FISCAL_YEAR] - cost[FISCAL_YEAR]
        op, _ = annual_values(facts, ["OperatingIncomeLoss"], FISCAL_YEAR)
        ni, _ = annual_values(facts, ["NetIncomeLoss"], FISCAL_YEAR)

        debt, debt_source = total_debt(facts, FISCAL_YEAR)

        flt, float_factor = public_float(facts, revenue[FISCAL_YEAR])
        if flt is None:
            skipped.append((ticker, "no usable EntityPublicFloat"))
            continue
        if gp is None or op.get(FISCAL_YEAR) is None or ni.get(FISCAL_YEAR) is None:
            skipped.append((ticker, "missing gross/operating/net income"))
            continue

        rows.append({
            "ticker": ticker,
            "name": sub.get("name", rec.get("title", "")),
            "cik": cik,
            "sic": sic,
            "fiscal_year": FISCAL_YEAR,
            "revenue": revenue[FISCAL_YEAR],
            "revenue_prior": revenue[PRIOR_YEAR],
            "gross_profit": gp,
            "operating_income": op[FISCAL_YEAR],
            "net_income": ni[FISCAL_YEAR],
            "total_debt": debt,
            "debt_source": debt_source,
            "public_float": flt,
            "float_scale_correction": float_factor,
            "revenue_tag": rev_tag,
        })
        if i % 20 == 0:
            print(f"  {i}/{len(CANDIDATES)} processed, {len(rows)} kept",
                  file=sys.stderr)

    df = pd.DataFrame(rows).sort_values("public_float", ascending=False)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)

    print(f"\nkept {len(df)} companies -> {OUT}")
    print(f"skipped {len(skipped)}")
    reasons = {}
    for _, why in skipped:
        key = why.split(" ")[0] if why.startswith("SIC") else why
        reasons[key] = reasons.get(key, 0) + 1
    for why, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {n:3d}  {why}")


if __name__ == "__main__":
    main()
