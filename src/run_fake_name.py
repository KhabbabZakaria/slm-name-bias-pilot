"""Relabelling diagnostics: can a name pull a choice when the numbers are fixed?

Each test replaces one company's name and ticker while leaving its own real
numbers in place, and is compared against the identical prompts with real names.
See TESTS below for the variants: Apple on the second company (and a second
seeded run of it), Apple on the first company as a mirror, an invented name as
the control that separates "famous" from merely "unfamiliar", and Microsoft as a
second household name.

Original note, for the Apple-on-second case:

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
N_SAMPLES = 5

# tag -> (display name, ticker, which slot carries the label, seed)
TESTS = {
    "apple":       ("Apple Inc.", "AAPL", "second", 7001),
    "apple_rep2":  ("Apple Inc.", "AAPL", "second", 7011),
    "apple_first": ("Apple Inc.", "AAPL", "first", 7021),
    # Control: a plausible but invented name. If this moves the choice as much as
    # Apple does, the effect is "any unfamiliar relabelling", not "famous name".
    "norwell":     ("Norwell Systems", "NWLS", "second", 7031),
    # A second household name, to show the effect is not something about "Apple".
    "microsoft":   ("Microsoft Corporation", "MSFT", "second", 7041),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5-1.5b")
    ap.add_argument("--test", default="apple", choices=list(TESTS))
    args = ap.parse_args()
    name, ticker, slot, seed = TESTS[args.test]
    stem = "raw_fake_apple" if args.test == "apple" else f"raw_fake_{args.test}"
    out = ROOT / "results" / f"{stem}__{args.model}.jsonl"
    if out.exists():
        raise SystemExit(f"{out.name} exists; delete it to rerun")

    mx.random.seed(seed)
    model = Model(args.model)
    df = pd.read_csv(PAIRS)
    n = 0
    for _, pair in df.iterrows():
        for order in ORDERS:
            # In this layout slot A is shown first: role_a is the first company,
            # role_b the second.
            role_a = "large" if order == "large_first" else "small"
            role_b = "small" if order == "large_first" else "large"
            labelled = role_b if slot == "second" else role_a
            fake = pair.copy()
            fake[f"{labelled}_display_name"] = name
            fake[f"{labelled}_ticker"] = ticker
            prompt = build_prompt(fake, "identified", order, LAYOUT)
            for s in range(N_SAMPLES):
                raw = model.complete(prompt)
                row = {"pair_id": pair.pair_id, "order": order, "layout": LAYOUT,
                       "condition": f"identified_fake_{args.test}", "model": args.model,
                       "sample_idx": s, "raw_output": raw,
                       "parsed_choice": parse_choice(raw, LAYOUT),
                       "apple_label_on": labelled,
                       "label_slot": slot, "label_name": name, "label_ticker": ticker,
                       "real_labelled_ticker": pair[f"{labelled}_ticker"],
                       "prompt_sha": hashlib.sha256(prompt.encode()).hexdigest()[:12],
                       "temperature": TEMPERATURE, "seed": seed,
                       "ts": datetime.now(timezone.utc).isoformat()}
                with out.open("a") as f:
                    f.write(json.dumps(row) + "\n")
                n += 1
        print(f"  {pair.pair_id} done ({n} calls)", flush=True)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
