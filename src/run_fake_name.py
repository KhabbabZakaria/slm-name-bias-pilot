"""Fake-mega-cap diagnostic: can a famous name pull a choice against format bias?

1.5B picks FIRST in ~96% of answers in the ord_a_first layout, whatever the
companies are. Here the *second* company in every prompt is relabelled
"Apple Inc. (AAPL)" while keeping its own real numbers; the first company keeps
its real name. If the name carries weight, SECOND should rise above the ~4% it
gets with real names. The real-name baseline is the identified condition of the
existing 1.5B ord_a_first run -- same layout, pairs, orderings and sample count.

Caveat built into the design: the numbers under the Apple label are not Apple's.
A model that knows Apple's FY2022 margins could react to the mismatch.

Writes results/raw_fake_apple__<model>.jsonl.
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import mlx.core as mx
import pandas as pd

from models import TEMPERATURE, Model
from prompts import ORDERS, build_prompt
from run import parse_choice

ROOT = Path(__file__).resolve().parent.parent
PAIRS = ROOT / "data" / "pairs.csv"
LAYOUT = "ord_a_first"
FAKE_NAME, FAKE_TICKER = "Apple Inc.", "AAPL"
N_SAMPLES = 5
SEED = 7001


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5-1.5b")
    args = ap.parse_args()
    out = ROOT / "results" / f"raw_fake_apple__{args.model}.jsonl"
    if out.exists():
        raise SystemExit(f"{out.name} exists; delete it to rerun")

    mx.random.seed(SEED)
    model = Model(args.model)
    df = pd.read_csv(PAIRS)
    n = 0
    for _, pair in df.iterrows():
        for order in ORDERS:
            # In this layout slot A is shown first, so the second company is role_b.
            second = "small" if order == "large_first" else "large"
            fake = pair.copy()
            fake[f"{second}_display_name"] = FAKE_NAME
            fake[f"{second}_ticker"] = FAKE_TICKER
            prompt = build_prompt(fake, "identified", order, LAYOUT)
            for s in range(N_SAMPLES):
                raw = model.complete(prompt)
                row = {"pair_id": pair.pair_id, "order": order, "layout": LAYOUT,
                       "condition": "identified_fake_apple", "model": args.model,
                       "sample_idx": s, "raw_output": raw,
                       "parsed_choice": parse_choice(raw, LAYOUT),
                       "apple_label_on": second,
                       "real_second_ticker": pair[f"{second}_ticker"],
                       "prompt_sha": hashlib.sha256(prompt.encode()).hexdigest()[:12],
                       "temperature": TEMPERATURE, "seed": SEED,
                       "ts": datetime.now(timezone.utc).isoformat()}
                with out.open("a") as f:
                    f.write(json.dumps(row) + "\n")
                n += 1
        print(f"  {pair.pair_id} done ({n} calls)", flush=True)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
