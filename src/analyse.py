"""Step 4: the three numbers, with CIs, from results/raw.jsonl.

Writes results/summary.md.

1. Anonymised choice rate  -- share of choices going to the large-cap's numbers.
2. Identified choice rate  -- share going to the large-cap by name. The gap from
   (1) is the raw name effect.
3. Swap-following rate     -- in the swapped condition, share of choices that
   followed the numbers rather than the name. The headline.

Defining (3) needs a reference. CLAUDE.md: "A model following the numbers flips
its choice." Flips relative to what it chose when name and numbers agreed, so
the reference for each pair is its majority choice in the identified condition.
Under the swap, following the numbers means picking the slot that now carries
the reference company's numbers under the other company's name; following the
name means picking the reference company's name over the other's numbers.
Pairs whose identified choices split exactly 5/5 have no reference and are
excluded from (3), and the count is reported. The same rate with the anonymised
condition as reference is reported as a sensitivity check.

On the intervals: Wilson intervals, as CLAUDE.md specifies, treat every sample
as independent. They are not -- ten samples of the same pair share the pair --
so the effective sample size is nearer the 20 pairs than the 200 choices. A
pair-level bootstrap interval is reported beside each Wilson interval; where the
two disagree, the bootstrap is the honest one.
"""

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from statsmodels.stats.proportion import proportion_confint

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "results" / "raw.jsonl"
PROBE = ROOT / "results" / "probe.jsonl"
OUT = ROOT / "results" / "summary.md"

N_BOOT = 10_000
SEED = 20260918


def wilson(k, n):
    if n == 0:
        return (float("nan"), float("nan"))
    return proportion_confint(k, n, alpha=0.05, method="wilson")


def cluster_bootstrap(outcomes_by_pair):
    """95% percentile interval, resampling pairs rather than samples."""
    pairs = [v for v in outcomes_by_pair.values() if v]
    if not pairs:
        return (float("nan"), float("nan"))
    rng = random.Random(SEED)
    stats = []
    for _ in range(N_BOOT):
        draw = [rng.choice(pairs) for _ in pairs]
        flat = [x for p in draw for x in p]
        stats.append(sum(flat) / len(flat))
    stats.sort()
    return stats[int(0.025 * N_BOOT)], stats[int(0.975 * N_BOOT) - 1]


def rate(outcomes_by_pair):
    flat = [x for v in outcomes_by_pair.values() for x in v]
    k, n = sum(flat), len(flat)
    return {"k": k, "n": n, "p": k / n if n else float("nan"),
            "wilson": wilson(k, n), "boot": cluster_bootstrap(outcomes_by_pair),
            "pairs": sum(1 for v in outcomes_by_pair.values() if v)}


def reference(rows, pair_id, condition):
    """Majority company in a condition for one pair, or None on an exact tie.

    Company is identified by whose numbers were chosen; in the identified and
    anonymised conditions that is also whose name, so the two coincide.
    """
    c = Counter(r["chosen_fundamentals_owner"] for r in rows
                if r["pair_id"] == pair_id and r["condition"] == condition
                and r["parsed_choice"])
    if not c or (len(c) == 2 and c["large"] == c["small"]):
        return None
    return c.most_common(1)[0][0]


def swap_following(rows, ref_condition):
    by_pair, excluded = defaultdict(list), []
    for pid in sorted({r["pair_id"] for r in rows}):
        ref = reference(rows, pid, ref_condition)
        if ref is None:
            excluded.append(pid)
            continue
        for r in rows:
            if r["pair_id"] == pid and r["condition"] == "swapped" and r["parsed_choice"]:
                by_pair[pid].append(int(r["chosen_fundamentals_owner"] == ref))
    out = rate(by_pair)
    out["excluded"] = excluded
    return out


def order_consistency(rows):
    """Same company chosen when A and B are flipped, pairing samples by index.

    Also reports the raw share of 'A' answers: a model that picks whichever
    company sits in one slot is showing position bias, and every rate above is
    uninterpretable until that is ruled out.
    """
    idx = {(r["pair_id"], r["condition"], r["order"], r["sample_idx"]): r
           for r in rows if r["parsed_choice"]}
    per_cond = {}
    for cond in ("identified", "anonymised", "swapped"):
        by_pair = defaultdict(list)
        for (pid, c, order, s), r in idx.items():
            if c != cond or order != "large_first":
                continue
            other = idx.get((pid, c, "small_first", s))
            if other:
                # Name owner: in swapped it is the name that stays with the
                # company across orderings; for the other two it equals the
                # numbers owner anyway.
                by_pair[pid].append(int(r["chosen_name_owner"]
                                        == other["chosen_name_owner"]))
        per_cond[cond] = rate(by_pair)
    parsed = [r for r in rows if r["parsed_choice"]]
    a_share = sum(r["parsed_choice"] == "A" for r in parsed) / len(parsed)
    return per_cond, a_share


def _owners(condition, order, choice):
    role_a, role_b = (("large", "small") if order == "large_first"
                      else ("small", "large"))
    name = role_a if choice == "A" else role_b
    if condition == "swapped":
        facts = role_b if choice == "A" else role_a
    else:
        facts = name
    return name, facts


def position_null(rows, n_sims=2000):
    """Swap-following for a model that ignores content and only has position bias.

    Each choice is redrawn as B with the observed P(B), independent of what the
    prompt says, and the full metric -- reference selection included -- is
    recomputed. If the observed rate sits inside this distribution, the headline
    is a position artefact rather than evidence about names or numbers.
    """
    p_b = sum(r["parsed_choice"] == "B" for r in rows) / len(rows)
    rng = random.Random(SEED)
    sims = []
    for _ in range(n_sims):
        fake = []
        for r in rows:
            ch = "B" if rng.random() < p_b else "A"
            name, facts = _owners(r["condition"], r["order"], ch)
            fake.append({**r, "parsed_choice": ch, "chosen_name_owner": name,
                         "chosen_fundamentals_owner": facts})
        sims.append(swap_following(fake, "identified")["p"])
    sims.sort()
    return {"p_b": p_b, "mean": sum(sims) / len(sims),
            "lo": sims[int(0.025 * n_sims)], "hi": sims[int(0.975 * n_sims) - 1],
            "sims": sims}


def fmt(r, pct=True):
    s = 100 if pct else 1
    w, b = r["wilson"], r["boot"]
    return (f"{s*r['p']:.1f}%  (k={r['k']}/{r['n']}; Wilson 95% "
            f"{s*w[0]:.1f}–{s*w[1]:.1f}; pair-bootstrap 95% {s*b[0]:.1f}–{s*b[1]:.1f})")


def main():
    rows = [json.loads(l) for l in RAW.open()]
    models = sorted({r["model"] for r in rows})
    lines = ["# RQ3 pilot — summary", "",
             "**Pilot, not a result.** 20 pairs; n is stated with every number.", ""]
    if (ROOT / "results" / "replication.md").exists():
        lines += ["> **Superseded headline.** This file covers only the first run in the "
                  "original layout. Its swap-following figure did not hold when the A/B "
                  "listing order was reversed. For the numbers to quote and the current "
                  "verdict, see [replication.md](replication.md) (four runs, 2,400 calls).", ""]

    for model in models:
        mr = [r for r in rows if r["model"] == model]
        fails = sum(1 for r in mr if r["parsed_choice"] is None)
        shas = len({r["prompt_sha"] for r in mr})

        def cond_rate(cond, owner_field):
            by_pair = defaultdict(list)
            for r in mr:
                if r["condition"] == cond and r["parsed_choice"]:
                    by_pair[r["pair_id"]].append(int(r[owner_field] == "large"))
            return rate(by_pair)

        anon = cond_rate("anonymised", "chosen_fundamentals_owner")
        ident = cond_rate("identified", "chosen_name_owner")
        swap_id = swap_following(mr, "identified")
        swap_an = swap_following(mr, "anonymised")
        # Large-cap name share under the swap: name loyalty stated directly,
        # needing no reference choice.
        swap_name = cond_rate("swapped", "chosen_name_owner")
        oc, a_share = order_consistency(mr)
        null = position_null([r for r in mr if r["parsed_choice"]])
        beats = sum(x < swap_id["p"] for x in null["sims"]) / len(null["sims"])
        # A model choosing by slot alone agrees across orderings only when it
        # happens to pick different slots: 2 * P(A) * P(B).
        consistency_null = 2 * a_share * (1 - a_share)

        L = lines
        L += [f"## {model}", "",
              f"Calls: {len(mr)}. Parse failures: {fails} ({100*fails/len(mr):.1f}%). "
              f"Distinct prompts: {shas} (expected 120).", "",
              "### The three numbers", "",
              f"1. **Anonymised choice rate** (share to the large-cap's numbers): {fmt(anon)}",
              f"2. **Identified choice rate** (share to the large-cap by name): {fmt(ident)}",
              f"   - Raw name effect, (2) − (1): {100*(ident['p']-anon['p']):+.1f} points",
              f"3. **Swap-following rate** (share following the numbers, reference = identified choice): "
              f"{fmt(swap_id)}",
              f"   - Pairs with no reference (identified split 5/5), excluded: "
              f"{len(swap_id['excluded'])} {', '.join(swap_id['excluded'])}",
              f"   - Sensitivity, reference = anonymised choice: {fmt(swap_an)}; "
              f"excluded {len(swap_an['excluded'])}",
              f"   - Large-cap *name* share under the swap (no reference needed): {fmt(swap_name)}",
              "",
              "### Position bias", "",
              f"Share of all answers that were **A**: {100*a_share:.1f}% (50% = no position preference).",
              "",
              f"Swap-following for a model with this position bias and no regard for content "
              f"(simulated, {len(null['sims'])} runs): mean {100*null['mean']:.1f}%, "
              f"95% range {100*null['lo']:.1f}–{100*null['hi']:.1f}%. "
              f"Observed {100*swap_id['p']:.1f}% exceeds {100*beats:.1f}% of runs.",
              "",
              "### Order consistency", "",
              "Same company chosen when A and B are swapped, matched by sample index. "
              f"A model choosing by slot alone would score {100*consistency_null:.1f}%; "
              "one choosing at random, 50%.", ""]
        for cond, r in oc.items():
            L.append(f"- {cond}: {fmt(r)}")

        # CLAUDE.md's "What counts as a result", applied mechanically.
        low_consistency = all(r["p"] < 0.6 for r in oc.values())
        anon_ok = anon["boot"][0] <= 0.5 <= anon["boot"][1]
        swap_above_null = swap_id["boot"][0] > null["hi"]
        swap_below_half = swap_id["boot"][1] < 0.5
        L += ["", "### Decision rules (CLAUDE.md)", "",
              f"- Parse failures high? **{'yes' if fails/len(mr) > 0.05 else 'no'}** ({100*fails/len(mr):.1f}%)",
              f"- Order consistency low? **{'yes' if low_consistency else 'no'}** "
              f"(all conditions below 60%; slot-only baseline {100*consistency_null:.1f}%)",
              f"- Anonymised rate far from 50%? **{'no' if anon_ok else 'yes'}** "
              f"(pair-bootstrap interval {'includes' if anon_ok else 'excludes'} 50%)",
              f"- Swap-following well below 50%? **{'yes' if swap_below_half else 'no'}**",
              f"- Swap-following distinguishable from position bias? "
              f"**{'yes' if swap_above_null else 'no'}** (bootstrap lower bound "
              f"{100*swap_id['boot'][0]:.1f}% vs null ceiling {100*null['hi']:.1f}%)", ""]

        L += ["### Verdict", ""]
        if swap_below_half:
            L.append("Swap-following is below 50% with an interval excluding it: the model "
                     "stays with the name over the numbers, and the full study is worth running.")
        elif swap_above_null and low_consistency:
            L.append(
                f"At this model size there is no sign of name bias: under the swap the model "
                f"followed the numbers in {100*swap_id['p']:.0f}% of choices (pair-bootstrap "
                f"{100*swap_id['boot'][0]:.0f}–{100*swap_id['boot'][1]:.0f}%, clear of the "
                f"{100*null['lo']:.0f}–{100*null['hi']:.0f}% a position-only model would produce), "
                f"and naming the companies moved the large-cap share by {100*(ident["p"]-anon["p"]):+.1f} points. "
                f"But the model picks the second-listed company {100*(1-a_share):.0f}% of the time, "
                f"which pulls order consistency down to the slot-only baseline, so by this pilot's "
                f"own rules the framing is too weak to scale as it stands: fix the position bias "
                f"and rerun at 7B before deciding on the full study.")
        elif swap_above_null:
            L.append("The model follows the numbers under the swap, clear of position bias, "
                     "with no sign of name bias at this size.")
        else:
            L.append("Swap-following cannot be told apart from position bias; the task framing "
                     "needs tightening before any conclusion about names is possible.")
        L.append("")

    if PROBE.exists():
        pr = [json.loads(l) for l in PROBE.open()]
        answered = sum(1 for r in pr for v in r["stated"].values() if v is not None)
        total = sum(len(r["stated"]) for r in pr)
        lines += ["## Recognition probe", "",
                  f"{len(pr)} probe calls ({len({r['ticker'] for r in pr})} companies). "
                  f"Figures stated rather than UNKNOWN: {answered}/{total}.", ""]

    lines += ["## Limitations", "",
              "- **One model.** Qwen2.5-3B-Instruct only. The 7B run was abandoned at "
              "123/600 calls: on this 8GB machine it swapped (~9.6 s/call) and froze the "
              "system. The per-model-size comparison CLAUDE.md asks for is not available.",
              "- **4-bit weights** (MLX), not fp16. Nothing here shows quantisation is "
              "neutral for name bias.",
              "- **Samples are not independent.** Ten samples share each pair, so the "
              "effective n is close to 20. Wilson intervals are reported because CLAUDE.md "
              "asks for them; the pair-bootstrap intervals are the ones to trust.",
              "- **The anonymised control is weaker than designed.** With a strong position "
              "bias and every pair shown in both orders, position alone pushes the "
              "anonymised rate toward 50%. Passing the control here is less evidence of good "
              "matching than it would be for a model without position bias.",
              "- **The probe shows no stated recall, which is not the same as no "
              "recognition.** Every answer was UNKNOWN, identically for every company. "
              "That looks like blanket compliance with the \"do not guess\" instruction; "
              "implicit recognition is not ruled out.", ""]
    OUT.write_text("\n".join(lines) + "\n")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
