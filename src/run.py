"""Step 3: run the pilot and write results/raw.jsonl.

20 pairs x 3 conditions x 2 orderings x 5 samples x 2 models = 1,200 calls.

Raw output is written for every call whether or not it parses. Parse failures
are recorded as rows with parsed_choice null and counted at the end; they are
never dropped, because a high failure rate is itself a finding about the task
framing.

The file is append-only and the run is resumable: completed (pair, condition,
order, model, sample) keys are read back on startup and skipped. Each row also
carries a hash of the prompt that produced it, so results gathered under a
changed template can be detected rather than silently pooled.
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from models import DEFAULT_MODELS, MODELS, TEMPERATURE, Model
from prompts import (CONDITIONS, LAYOUTS, ORDERS, answer_labels, build_prompt,
                     fundamentals_owner)

ROOT = Path(__file__).resolve().parent.parent
PAIRS = ROOT / "data" / "pairs.csv"
OUT = ROOT / "results" / "raw.jsonl"

N_SAMPLES = 5
CHOICE_RE = re.compile(r"CHOICE:\s*([AB])")


def parse_choice(raw, layout="a_first"):
    """Strict parse. Returns 'A', 'B', or None.

    Ordinal layouts answer with FIRST/SECOND, mapped onto A/B. Case is ignored
    for those words only, since "CHOICE: First" is unambiguous.

    A second match that disagrees with the first is treated as a failure rather
    than resolved by position: a response saying both is not a choice.
    """
    labels = answer_labels(layout)
    if layout.startswith("ord_"):
        found = [labels[m.upper()] for m in
                 re.findall(r"CHOICE:\s*(FIRST|SECOND)\b", raw, re.IGNORECASE)]
    else:
        found = CHOICE_RE.findall(raw)
    if not found:
        return None
    if len(set(found)) > 1:
        return None
    return found[0]


def done_keys(path):
    if not path.exists():
        return set()
    keys = set()
    with path.open() as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            keys.add((r["pair_id"], r["condition"], r["order"], r["model"],
                      r["sample_idx"]))
    return keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    ap.add_argument("--samples", type=int, default=N_SAMPLES)
    ap.add_argument("--layout", choices=list(LAYOUTS), default="a_first",
                    help="everything except a_first is a diagnostic; each writes to "
                         "its own file and never mixes with raw.jsonl")
    ap.add_argument("--replicate", type=int, default=1,
                    help="1 is the original, unseeded run. 2+ are replications, "
                         "each seeded and written to its own file")
    ap.add_argument("--limit-pairs", type=int, default=None,
                    help="smoke-test on the first N pairs")
    args = ap.parse_args()

    stem = "raw" if args.layout == "a_first" else f"raw_{args.layout}"
    suffix = "" if args.replicate == 1 else f"_rep{args.replicate}"
    # 3B results keep their original file names; any other model gets its own
    # files so models can never be pooled by accident.
    if args.models != DEFAULT_MODELS:
        if len(args.models) != 1:
            raise SystemExit("run one non-default model at a time")
        suffix += f"__{args.models[0]}"
    out_path = OUT.with_name(f"{stem}{suffix}.jsonl")

    # Replicate 1 was run before seeding existed; MLX then draws a fresh random
    # state per process, so those samples are genuine but not reproducible.
    # Replicates 2+ fix the seed so the exact samples can be regenerated.
    # The answer-order layouts are new, so they are seeded from their first run.
    seed = None
    if args.replicate > 1 or args.layout not in ("a_first", "b_first"):
        import mlx.core as mx
        seed = 1000 * args.replicate + list(LAYOUTS).index(args.layout)
        mx.random.seed(seed)

    df = pd.read_csv(PAIRS)
    if args.limit_pairs:
        df = df.head(args.limit_pairs)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    already = done_keys(out_path)
    if already:
        print(f"resuming: {len(already)} calls already in {out_path.name}")

    total = len(df) * len(CONDITIONS) * len(ORDERS) * args.samples * len(args.models)
    done = failures = 0

    for model_name in args.models:
        # One model in memory at a time.
        print(f"\nloading {model_name} ({MODELS[model_name]})", file=sys.stderr)
        model = Model(model_name)
        for _, pair in df.iterrows():
            for condition in CONDITIONS:
                for order in ORDERS:
                    prompt = build_prompt(pair, condition, order, args.layout)
                    phash = hashlib.sha256(prompt.encode()).hexdigest()[:12]
                    for sample_idx in range(args.samples):
                        key = (pair.pair_id, condition, order, model_name, sample_idx)
                        if key in already:
                            done += 1
                            continue
                        raw = model.complete(prompt)
                        choice = parse_choice(raw, args.layout)
                        if choice is None:
                            failures += 1
                        owner = (fundamentals_owner(pair, condition, order, choice)
                                 if choice else {"chosen_name_owner": None,
                                                 "chosen_fundamentals_owner": None,
                                                 "chosen_ticker": None})
                        row = {
                            "pair_id": pair.pair_id,
                            "condition": condition,
                            "order": order,
                            "layout": args.layout,
                            "replicate": args.replicate,
                            "seed": seed,
                            "model": model_name,
                            "sample_idx": sample_idx,
                            "raw_output": raw,
                            "parsed_choice": choice,
                            **owner,
                            "large_ticker": pair.large_ticker,
                            "small_ticker": pair.small_ticker,
                            "prompt_sha": phash,
                            "temperature": TEMPERATURE,
                            "ts": datetime.now(timezone.utc).isoformat(),
                        }
                        with out_path.open("a") as f:
                            f.write(json.dumps(row) + "\n")
                        done += 1
                        if done % 25 == 0:
                            print(f"  {done}/{total}  parse failures {failures}",
                                  file=sys.stderr)
        del model

    print(f"\n{done}/{total} calls, {failures} parse failures "
          f"({100*failures/max(done,1):.1f}%) -> {out_path}")


if __name__ == "__main__":
    main()
