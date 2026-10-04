# RQ3 pilot — summary

**Pilot, not a result.** 20 pairs; n is stated with every number.

> **Superseded headline.** This file covers only the first run in the original layout. Its swap-following figure did not hold when the A/B listing order was reversed. For the numbers to quote and the current verdict, see [replication.md](replication.md) (four runs, 2,400 calls).

## qwen2.5-3b

Calls: 600. Parse failures: 0 (0.0%). Distinct prompts: 120 (expected 120).

### The three numbers

1. **Anonymised choice rate** (share to the large-cap's numbers): 54.5%  (k=109/200; Wilson 95% 47.6–61.3; pair-bootstrap 95% 44.5–64.5)
2. **Identified choice rate** (share to the large-cap by name): 54.0%  (k=108/200; Wilson 95% 47.1–60.8; pair-bootstrap 95% 41.5–66.5)
   - Raw name effect, (2) − (1): -0.5 points
3. **Swap-following rate** (share following the numbers, reference = identified choice): 70.6%  (k=120/170; Wilson 95% 63.3–76.9; pair-bootstrap 95% 63.5–77.6)
   - Pairs with no reference (identified split 5/5), excluded: 3 P02, P11, P20
   - Sensitivity, reference = anonymised choice: 76.7%  (k=92/120; Wilson 95% 68.3–83.3; pair-bootstrap 95% 70.0–83.3); excluded 8
   - Large-cap *name* share under the swap (no reference needed): 45.5%  (k=91/200; Wilson 95% 38.7–52.4; pair-bootstrap 95% 35.0–56.0)

### Position bias

Share of all answers that were **A**: 26.3% (50% = no position preference).

Swap-following for a model with this position bias and no regard for content (simulated, 2000 runs): mean 50.0%, 95% range 42.5–57.5%. Observed 70.6% exceeds 100.0% of runs.

### Order consistency

Same company chosen when A and B are swapped, matched by sample index. A model choosing by slot alone would score 38.8%; one choosing at random, 50%.

- identified: 52.0%  (k=52/100; Wilson 95% 42.3–61.5; pair-bootstrap 95% 39.0–65.0)
- anonymised: 31.0%  (k=31/100; Wilson 95% 22.8–40.6; pair-bootstrap 95% 16.0–48.0)
- swapped: 39.0%  (k=39/100; Wilson 95% 30.0–48.8; pair-bootstrap 95% 27.0–51.0)

### Decision rules (CLAUDE.md)

- Parse failures high? **no** (0.0%)
- Order consistency low? **yes** (all conditions below 60%; slot-only baseline 38.8%)
- Anonymised rate far from 50%? **no** (pair-bootstrap interval includes 50%)
- Swap-following well below 50%? **no**
- Swap-following distinguishable from position bias? **yes** (bootstrap lower bound 63.5% vs null ceiling 57.5%)

### Verdict

At this model size there is no sign of name bias: under the swap the model followed the numbers in 71% of choices (pair-bootstrap 64–78%, clear of the 42–57% a position-only model would produce), and naming the companies moved the large-cap share by -0.5 points. But the model picks the second-listed company 74% of the time, which pulls order consistency down to the slot-only baseline, so by this pilot's own rules the framing is too weak to scale as it stands: fix the position bias and rerun at 7B before deciding on the full study.

## Recognition probe

120 probe calls (40 companies). Figures stated rather than UNKNOWN: 0/600.

## Limitations

- **One model.** Qwen2.5-3B-Instruct only. The 7B run was abandoned at 123/600 calls: on this 8GB machine it swapped (~9.6 s/call) and froze the system. The per-model-size comparison CLAUDE.md asks for is not available.
- **4-bit weights** (MLX), not fp16. Nothing here shows quantisation is neutral for name bias.
- **Samples are not independent.** Ten samples share each pair, so the effective n is close to 20. Wilson intervals are reported because CLAUDE.md asks for them; the pair-bootstrap intervals are the ones to trust.
- **The anonymised control is weaker than designed.** With a strong position bias and every pair shown in both orders, position alone pushes the anonymised rate toward 50%. Passing the control here is less evidence of good matching than it would be for a model without position bias.
- **The probe shows no stated recall, which is not the same as no recognition.** Every answer was UNKNOWN, identically for every company. That looks like blanket compliance with the "do not guess" instruction; implicit recognition is not ruled out.

