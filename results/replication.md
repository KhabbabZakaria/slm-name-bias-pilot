# Replication report — Qwen2.5-3B (4-bit)

Each run: 20 pairs × 3 conditions × 2 orderings × 5 samples = 600 calls. Replicate 1 is the original unseeded run; replicate 2 reruns both layouts with fixed seeds. `a_first` lists Company A first (the frozen template); `b_first` lists Company B first (the position diagnostic).

Brackets are pair-bootstrap 95% intervals, resampling the 20 pairs.

## Run by run

| run | calls | parse fail | chose B | anonymised | identified | swap-following | name effect |
|---|---|---|---|---|---|---|---|
| rep 1 · a_first | 600 | 0 | 73.7% | 54.5% [44–64] | 54.0% [42–66] | 70.6% [64–78] | -0.5 |
| rep 1 · b_first | 600 | 0 | 84.5% | 51.5% [41–62] | 47.5% [43–52] | 50.0% [44–57] | -4.0 |
| rep 2 · a_first | 600 | 0 | 74.2% | 53.5% [43–64] | 59.5% [51–68] | 68.0% [55–80] | +6.0 |
| rep 2 · b_first | 600 | 0 | 82.8% | 46.5% [35–58] | 52.0% [48–57] | 48.8% [45–52] | +5.5 |

## Does each finding replicate?

**a_first** — rep 1 vs rep 2:
- chose B: 73.7% vs 74.2% (Δ +0.5; intervals overlap)
- anonymised: 54.5% vs 53.5% (Δ -1.0; intervals overlap)
- identified: 54.0% vs 59.5% (Δ +5.5; intervals overlap)
- swap-following: 70.6% vs 68.0% (Δ -2.6; intervals overlap)
- name effect: -0.5 vs +6.0 points

**b_first** — rep 1 vs rep 2:
- chose B: 84.5% vs 82.8% (Δ -1.7; intervals overlap)
- anonymised: 51.5% vs 46.5% (Δ -5.0; intervals overlap)
- identified: 47.5% vs 52.0% (Δ +4.5; intervals overlap)
- swap-following: 50.0% vs 48.8% (Δ -1.3; intervals overlap)
- name effect: -4.0 vs +5.5 points

## Position effect by condition

Share choosing B when B is listed first vs second. Positive = the first-listed company is favoured; negative = the second.

| replicate | condition | B first | B second | position effect |
|---|---|---|---|---|
| 1 | identified | 94% | 66% | +28 |
| 1 | anonymised | 66% | 84% | -18 |
| 1 | swapped | 94% | 72% | +23 |
| 2 | identified | 94% | 70% | +24 |
| 2 | anonymised | 58% | 82% | -24 |
| 2 | swapped | 96% | 70% | +26 |

## Order consistency

Same company chosen when the A/B labels are exchanged (50% = random).

| run | identified | anonymised | swapped |
|---|---|---|---|
| rep 1 · a_first | 52% | 31% | 39% |
| rep 1 · b_first | 13% | 47% | 11% |
| rep 2 · a_first | 41% | 33% | 47% |
| rep 2 · b_first | 12% | 53% | 8% |

## Pooled estimates — all four runs (2,400 calls)

Letter and slot are fully counterbalanced, so these are the numbers to quote.

- Chose the letter **B**: 78.8% [73–84]
- Chose the **second-listed** company: 45.1% [41–49]
- Anonymised choice rate (large-cap numbers): 51.5% [45–59]
- Identified choice rate (large-cap name): 53.2% [48–59]
- **Name effect** (identified − anonymised): +1.7 points [-5.1 to +8.3]
- **Swap-following** (numbers over name): 57.6% [53–62]; pairs without a reference: 1/20
- Parse failures: 0/2400

Swap-following by layout, both replicates pooled: A listed first 67.5% [59–76], B listed first 50.5% [48–54].

## Verdict

Across four runs and 2,400 calls, the 3B model shows no detectable name bias: naming the companies moved the large-cap share by +1.7 points (95% -5.1 to +8.3), and single-run estimates ranged from -4.0 to +6.0, which is sampling noise around zero; an effect larger than about 8 points is ruled out. But that null carries little weight, because its choices are driven mainly by the answer label, B in 79% of answers, and the swap measurement depends on layout (68% when A is listed first, 50% when B is), so a model this dominated by the label has little room to show name loyalty, and by this pilot's own rules the task framing is too weak at 3B to answer the research question either way.

## Limitations

- One model: Qwen2.5-3B-Instruct, 4-bit MLX weights. The 7B run could not complete on 8GB and was abandoned.
- The b_first layout and replicate 2 were added after replicate 1 had been read. They are diagnostics of a bias found in the data, not pre-registered conditions.
- Replicate 1 was unseeded and cannot be regenerated exactly; replicate 2 used seeds 2000 (a_first) and 2001 (b_first).
- "Letter B" and "last option in the answer instructions" are not separated: `CHOICE: B` is the last answer line in both layouts.
- Effective sample size is about 20 pairs; intervals resample pairs, not calls.

