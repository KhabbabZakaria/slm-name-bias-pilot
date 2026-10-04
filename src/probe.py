"""Recognition probe: can the model recall these companies' FY2022 ratios?

Not a fourth condition. The factorial stays at 1,200 calls; this is a separate
diagnostic run against tickers alone, which is what keeps it inside CLAUDE.md's
rule against adding conditions mid-run.

Why it is needed: under the swap, a model shown "Amphenol Corporation" over
another company's numbers may react to the numbers being *wrong for that name*
rather than to the name itself. Recognition and name loyalty are different
mechanisms producing similar-looking results, and the swap alone cannot separate
them. This probes the exact five ratios the prompt displays -- if the model can
recall Autodesk's FY2022 operating margin, that is the number the swap perturbs,
and that is the contamination that matters.

It asks for recall with an explicit UNKNOWN option, so declining to answer is
distinguishable from guessing.

The naive baseline matters as much as the model's error. Technology companies
cluster: predicting the universe median for every company already scores
reasonably. Recall is only evidence of company-specific memorisation if it beats
that baseline, so analyse_probe.py reports both.
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from models import DEFAULT_MODELS, MODELS, TEMPERATURE, Model

ROOT = Path(__file__).resolve().parent.parent
PAIRS = ROOT / "data" / "pairs.csv"
OUT = ROOT / "results" / "probe.jsonl"

N_SAMPLES = 3

# Keyed to the ratios the prompt actually shows.
FIELDS = [
    ("REVENUE_GROWTH", "rev_growth_pct", "%"),
    ("GROSS_MARGIN", "gross_margin_pct", "%"),
    ("OPERATING_MARGIN", "op_margin_pct", "%"),
    ("NET_MARGIN", "net_margin_pct", "%"),
    ("DEBT_TO_REVENUE", "debt_to_revenue", "x"),
]

PROBE_TEMPLATE = """It is early 2023. State the fiscal year 2022 figures for the company below, as best you can recall.

Company: {name} ({ticker})

Answer with exactly these five lines and nothing else:
REVENUE_GROWTH: <number>%
GROSS_MARGIN: <number>%
OPERATING_MARGIN: <number>%
NET_MARGIN: <number>%
DEBT_TO_REVENUE: <number>x

Write UNKNOWN instead of a number for any figure you do not recall. Do not guess."""


def parse_probe(raw):
    """Return {field: float | None}. None means UNKNOWN or unparseable."""
    out = {}
    for label, field, _ in FIELDS:
        m = re.search(rf"{label}\s*:\s*(UNKNOWN|-?\d+(?:\.\d+)?)", raw, re.IGNORECASE)
        if not m or m.group(1).upper() == "UNKNOWN":
            out[field] = None
        else:
            out[field] = float(m.group(1))
    return out


def companies(df):
    """The 40 companies of the pair set, each once, with their true ratios."""
    seen = {}
    for _, r in df.iterrows():
        for role in ("large", "small"):
            t = r[f"{role}_ticker"]
            if t in seen:
                continue
            seen[t] = {
                "ticker": t,
                "display_name": r[f"{role}_display_name"],
                "role": role,
                "pair_id": r.pair_id,
                "actual": {f: float(r[f"{role}_{f}"]) for _, f, _ in FIELDS},
            }
    return list(seen.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    ap.add_argument("--samples", type=int, default=N_SAMPLES)
    args = ap.parse_args()

    df = pd.read_csv(PAIRS)
    firms = companies(df)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print(f"probing {len(firms)} companies x {args.samples} samples "
          f"x {len(args.models)} models = "
          f"{len(firms)*args.samples*len(args.models)} calls")

    for model_name in args.models:
        model = Model(model_name)
        for i, firm in enumerate(firms, 1):
            prompt = PROBE_TEMPLATE.format(name=firm["display_name"],
                                           ticker=firm["ticker"])
            for sample_idx in range(args.samples):
                raw = model.complete(prompt)
                row = {
                    "ticker": firm["ticker"],
                    "display_name": firm["display_name"],
                    "role": firm["role"],
                    "pair_id": firm["pair_id"],
                    "model": model_name,
                    "sample_idx": sample_idx,
                    "raw_output": raw,
                    "stated": parse_probe(raw),
                    "actual": firm["actual"],
                    "temperature": TEMPERATURE,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
                with OUT.open("a") as f:
                    f.write(json.dumps(row) + "\n")
            if i % 10 == 0:
                print(f"  {model_name}: {i}/{len(firms)} companies")
        del model

    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
