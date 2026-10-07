# Results — Qwen2.5-3B and Qwen2.5-1.5B

**This is a pilot, not a finding.** 20 company pairs, one sector, two small models. Numbers in brackets are 95% intervals that resample the 20 pairs, so they reflect how few pairs there are, not how many calls were made.

Calls: 7,200 on 3B, 2,400 on 1.5B. Unreadable answers: 4 on 3B, 17 on 1.5B.

## The short version

1. **3B showed no bias toward the real large-cap names in our pairs.** Showing the names moved its choice by +1.3 points with letter labels and -1.6 with First/Second labels, both within noise of zero. 1.5B could not be tested for this (see point 3).
2. **Both models were driven mainly by how the question was laid out, not by the companies.** This is the kind of position bias the reference paper reports.
3. **1.5B cannot be used for this question.** It copies whichever answer line is written first, 96% of the time.
4. **3B can be used, if the layout is rotated.** With all layouts combined so the position effects cancel, 3B followed the numbers over the name 60% [54–67] of the time with letters and 70% [60–78] with First/Second labels.
5. **But name familiarity does move 3B — against the layout.** Relabelling one company "Apple Inc. (AAPL)", numbers unchanged, raised how often 3B picked it by +20 points (replicated: +21); Microsoft gave +17; an invented name cost -12. But the same Apple label on the company the layout already favours did nothing (-0.7), so the effect only shows from behind. See Finding 4.

## What we tested

Each prompt showed two technology companies from FY2022 — one large, one small — matched so neither is obviously better on paper. The model had to pick one to hold for 12 months. Only five ratios were shown (growth, gross, operating and net margin, debt to revenue), never dollar amounts.

Every pair was asked three ways:

- **Anonymised** — no names, just the numbers. Should come out about 50/50.
- **Identified** — real names with their real numbers.
- **Swapped** — real names, but each company shown with the *other* company's numbers. If the model follows the numbers, its pick moves with them. If it sticks to the name, that is name bias.

Every pair was also run with the companies in both orders, 5 times each.

**Models:** Qwen2.5-3B-Instruct (4-bit) and Qwen2.5-1.5B-Instruct (full precision, the size used in the reference paper). A 7B run froze this 8GB laptop and was abandoned.

## Finding 1 — the layout decides most answers

An unbiased model should come out near 50/50 in every setup below, because each company sits in each position equally often. Anything outside roughly 45–55% is bias.

### Letter labels — 3B only (each setup run twice, 1,200 answers)

**Setup 1**
```
Company A: ...
Company B: ...
CHOICE: A
or
CHOICE: B
```
3B: A = 313 (26%) · **B = 887 (74%)**

**Setup 2**
```
Company B: ...
Company A: ...
CHOICE: A
or
CHOICE: B
```
3B: A = 196 (16%) · **B = 1004 (84%)**

**Setup 3**
```
Company A: ...
Company B: ...
CHOICE: B
or
CHOICE: A
```
3B: **A = 611 (51%)** · B = 589 (49%)

**Setup 4**
```
Company B: ...
Company A: ...
CHOICE: B
or
CHOICE: A
```
3B: **A = 666 (56%)** · B = 534 (44%)

Across all four letter setups, 3B chose:

- the letter **B**: 63% [59–67]
- the **answer listed last**: 66% [63–69]
- the **company listed at the top**: 51% [48–55]

So with letters, 3B likes B and likes the last answer option. Where the companies sit barely matters. When both pulls point at B (setups 1 and 2), B wins by a lot. When they point in opposite directions (setups 3 and 4), they cancel to about 50/50.

### First/Second labels — 3B and 1.5B (each setup run once, 600 answers)

**Setup 1**
```
First company: ...
Second company: ...
CHOICE: FIRST
or
CHOICE: SECOND
```
3B: **FIRST = 370 (62%)** · SECOND = 226 (38%) · 4 unreadable  
1.5B: **FIRST = 569 (96%)** · SECOND = 23 (4%) · 8 unreadable

**Setup 2**
```
Second company: ...
First company: ...
CHOICE: FIRST
or
CHOICE: SECOND
```
3B: FIRST = 235 (39%) · **SECOND = 365 (61%)**  
1.5B: **FIRST = 542 (91%)** · SECOND = 53 (9%) · 5 unreadable

**Setup 3**
```
First company: ...
Second company: ...
CHOICE: SECOND
or
CHOICE: FIRST
```
3B: **FIRST = 383 (64%)** · SECOND = 217 (36%)  
1.5B: FIRST = 7 (1%) · **SECOND = 589 (99%)** · 4 unreadable

**Setup 4**
```
Second company: ...
First company: ...
CHOICE: SECOND
or
CHOICE: FIRST
```
3B: **FIRST = 404 (67%)** · SECOND = 196 (33%)  
1.5B: FIRST = 2 (0%) · **SECOND = 598 (100%)**

Across all four First/Second setups:

| chose… | 3B | 1.5B |
|---|---|---|
| the word **SECOND** | 42% [38–45] | 53% [52–54] |
| the **answer listed last** | 58% [55–60] | 4% [3–4] |
| the **company listed at the top** | 55% [50–59] | 51% [51–52] |

- **1.5B** picks the answer listed *first* 96% of the time. It is copying the first line of the answer instructions, not choosing.
- **3B** lands at 61–67% in every setup, so no single layout is clean. It is several small pulls — toward the word FIRST, the last answer option and the top company — that add up differently in each layout. They largely cancel when all four are combined.

## Finding 2 — no bias toward the real large-cap names, once layout is balanced

These numbers combine all four setups for each label type, so the layout effects above cancel out.

| | 3B, letters | 3B, First/Second | 1.5B, First/Second |
|---|---|---|---|
| calls | 4,800 | 2,400 | 2,400 |
| **Anonymised**: large-cap chosen, no names (≈50% expected) | 53% [44–62] | 54% [42–66] | 49% [48–51] |
| **Identified**: large-cap chosen, real names | 54% [46–62] | 52% [43–62] | 51% [49–52] |
| **Name effect**: identified − anonymised | +1.3 pts [-3.1 to +5.8] | -1.6 pts [-8.0 to +4.8] | +1.1 pts [-0.3 to +2.4] |
| **Swap test**: followed the numbers, not the name | 60% [54–67] | 70% [60–78] | 50% [49–52] |
| pairs with no clear choice to compare against | 0/20 | 2/20 | 7/20 |

How to read it:

- **Anonymised is near 50% in every column.** That is consistent with well-matched pairs, but it is weaker evidence than it looks: because every company is shown in every position equally often, position bias alone pushes this number toward 50%. For 1.5B, which barely reads the companies, it says nothing about the pairs at all.
- **The name effect is within noise of zero for both label types on 3B.** For the real large-caps in these pairs, any name bias at 3B is smaller than about 6 points with letters. Finding 4 shows this does not extend to a household name like Apple.
- **On 3B the swap test lands well above 50% for both label types.** When the numbers move, the model's pick moves with them. That is the opposite of name loyalty.
- **The 1.5B column should not be read as a result.** Its answers are almost all format-copying, so there is very little genuine choice left to measure.

## Finding 3 — it replicates (3B, letter labels)

Each letter setup was run twice with different random seeds.

| setup | run | chose B | followed the numbers (swap) | name effect |
|---|---|---|---|---|
| 1 | 1 | 74% | 71% [64–78] | -0.5 |
| 1 | 2 | 74% | 68% [55–80] | +6.0 |
| 2 | 1 | 84% | 50% [44–57] | -4.0 |
| 2 | 2 | 83% | 49% [45–52] | +5.5 |
| 3 | 1 | 48% | 72% [62–82] | +5.0 |
| 3 | 2 | 50% | 69% [54–83] | +1.0 |
| 4 | 1 | 45% | 73% [61–83] | -3.5 |
| 4 | 2 | 44% | 68% [57–78] | +0.5 |

The layout effects and the swap result came out nearly the same both times. The name effect moved around between runs (roughly −4 to +6 points), which is what noise around zero looks like. The First/Second runs have been done once each and have not been replicated yet.

## Finding 4 — name familiarity moves 3B, but only against the layout

The real large-caps in these pairs ($10–150bn: Lam Research, Autodesk, Gartner…) showed no name effect. These tests replace one company's name and ticker while leaving its own real numbers in place, so any change in how often that company is picked is down to the name. The baseline is the identical prompts with real names. Layout is First/Second setup 1 throughout:

```
First company: Amphenol Corporation (APH)     <- real name, real numbers
Second company: Apple Inc. (AAPL)               <- new label over Manhattan Associates' real numbers
CHOICE: FIRST
or
CHOICE: SECOND
```

About 200 answers per cell (20 pairs × both orderings × 5 samples).

| label | slot | picked with real name | picked with new label | change | pairs up/down |
|---|---|---|---|---|---|
| Apple Inc. (AAPL) | second | 70/197 (35.5%) | 107/194 (55.2%) | **+19.6 pts** [+10.4 to +29.1] | 17/2 |
| Apple Inc. (AAPL), rerun | second | 70/197 (35.5%) | 110/195 (56.4%) | **+20.9 pts** [+13.5 to +29.5] | 18/0 |
| Microsoft Corporation (MSFT) | second | 70/197 (35.5%) | 105/199 (52.8%) | **+17.2 pts** [+10.1 to +25.3] | 15/2 |
| Norwell Systems (NWLS) — control | second | 70/197 (35.5%) | 45/195 (23.1%) | **-12.5 pts** [-19.5 to -5.3] | 3/14 |
| Apple Inc. (AAPL) | first | 127/197 (64.5%) | 125/196 (63.8%) | **-0.7 pts** [-6.1 to +4.5] | 7/7 |

Brackets are pair-bootstrap 95% intervals.

**What holds up:**

- **It is familiarity, not novelty.** The invented name Norwell Systems moved the choice -12.5 points — the *opposite* direction, with an interval excluding zero. An unfamiliar name is a penalty. The gradient from an invented name to a household one spans about 32 points.
- **It replicates.** A rerun with a different seed gave +20.9 points against +19.6, moving 18 of 20 pairs up.
- **It is not about the word "Apple".** Microsoft gave +17.2 points [+10.1 to +25.3].

**What does not hold up — the mirror test:**

- Moving the Apple label to the **first** company changed nothing: -0.7 points [-6.1 to +4.5], 7 pairs up and 7 down. The first slot already wins 64% of the time, and the famous label adds nothing on top.
- So the effect appears **only where the layout is working against the labelled company**. Label and position interact: a familiar name can overcome a position bias pointing the other way, but it buys nothing when position already favours it.
- Consequence for how this is quoted: "+20 points" is the size **in the disfavoured slot**, not a general name effect. A pure name effect has not been demonstrated.

**1.5B:** no change from the Apple label (5/198 → 5/196). It answers FIRST in about 97% of cases whatever the names are, so no label could move it. This says nothing about whether 1.5B has name bias.

**Still open:**

1. **The mirror asymmetry needs explaining.** Is it a ceiling, or does a familiar name genuinely only help from behind? Testing the invented name on the first slot would separate these: if Norwell *lowers* the first slot, the gradient is symmetrical and only the Apple direction is saturated.
2. **The gradient needs more rungs.** Five labels is enough to show a direction, not a dose-response curve.
3. **Larger models.** Everything here is one 3B model.


## What went wrong, and what we learned

- **The first run looked like a clean result and wasn't.** Setup 1 alone gave "follows the numbers 71% of the time". Moving the companies around dropped that to 50% in setup 2. It only held up once the answer order was also rotated.
- **Position bias is bigger than the effect we were trying to measure for ordinary large-caps.** On 3B it moves answers by 20–30 points; bias toward our real large-cap names is under about 8. A household name (Apple) moved answers by about 20.
- **Smaller is worse.** 1.5B is almost pure format-copying; 3B is partly driven by the content.
- **The recognition check told us nothing.** Asked to recall these companies' FY2022 ratios, 3B answered UNKNOWN for all 40 — including very well-known ones — which looks like it just obeyed "do not guess".

## Limitations

- **Only 20 pairs.** Intervals are wide; this is enough to decide whether to continue, not to publish.
- **Small models only.** 3B is 4-bit; 1.5B is full precision. 7B could not run on this machine. Results may not hold for larger models.
- **The layout tests were added after seeing the first results.** They are follow-up checks on a bias we found, not part of the original plan. A full study should fix the rotation of both company order and answer order *before* the first run.
- **Some runs are not exactly reproducible.** The first 3B runs were unseeded, and 3B First/Second setup 3 was paused and resumed.
- **First/Second runs were done once each.** The letter runs were done twice.

## Should the full study go ahead?

Possibly — but not in its current form. Ordinary large-cap names showed no effect, while a household name (Apple) showed a large one on 3B. If that survives its controls, the full study has a real effect to chase, and the question shifts from "large-cap vs small-cap" to "how famous is the name". Any full study needs (a) every layout rotated and pooled from the start, (b) pairs that include genuinely famous names, and (c) models big enough to read the content — 7B and above, on hardware that can hold them.

## Files

- `data/pairs.csv` — the 20 matched pairs
- `results/raw*.jsonl` — every answer, with the raw model output
- `results/probe.jsonl` — the recognition check
- `results/raw_fake_apple__*.jsonl` — the Apple-label test
- `src/write_results.py` — regenerates this file

