# Results — Qwen2.5-3B and Qwen2.5-1.5B

**This is a pilot, not a finding.** 20 company pairs, one sector, two small models. Numbers in brackets are 95% intervals that resample the 20 pairs, so they reflect how few pairs there are, not how many calls were made.

Calls: 7,200 on 3B, 2,400 on 1.5B. Unreadable answers: 4 on 3B, 17 on 1.5B.

## The short version

1. **3B showed no bias toward the real large-cap names in our pairs.** Showing the names moved its choice by +1.3 points with letter labels and -1.6 with First/Second labels, both within noise of zero. 1.5B could not be tested for this (see point 3).
2. **Both models were driven mainly by how the question was laid out, not by the companies.** This is the kind of position bias the reference paper reports.
3. **1.5B cannot be used for this question.** It copies whichever answer line is written first, 96% of the time.
4. **3B can be used, if the layout is rotated.** With all layouts combined so the position effects cancel, 3B followed the numbers over the name 60% [54–67] of the time with letters and 70% [60–78] with First/Second labels.
5. **But a very famous name does move 3B.** Relabelling one company "Apple Inc. (AAPL)" — numbers unchanged — raised how often 3B picked it by +20 points. This is one run and still needs its controls (see Finding 4).

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

## Finding 4 — a famous fake name moves 3B

The real large-caps in our pairs ($10–150bn: Lam Research, Autodesk, Gartner…) showed no name effect. To test a genuinely famous name, the **second** company in every prompt was relabelled **"Apple Inc. (AAPL)"**, keeping its own real numbers. The first company kept its real name. Everything else matched First/Second setup 1:

```
First company: Amphenol Corporation (APH)     <- real name, real numbers
Second company: Apple Inc. (AAPL)               <- fake name over Manhattan Associates' real numbers
CHOICE: FIRST
or
CHOICE: SECOND
```

Compared with the same prompts using the second company's real name (20 pairs × both orders × 5 samples ≈ 200 answers each):

| model | picked the second company — real name | — labelled "Apple" | change |
|---|---|---|---|
| 3B | 70/197 (35.5%) | 107/194 (55.2%) | **+19.6 pts** [+10.4 to +29.1] |
| 1.5B | 5/198 (2.5%) | 5/196 (2.6%) | **+0.0 pts** [-2.0 to +2.1] |

**3B:**

- The Apple label raised picks in **17 of 20 pairs**; 2 went the other way.
- It worked on both sides: Apple label on the real small-cap 28/99 → 46/97; on the real large-cap 42/98 → 61/97.
- In 104 of its 107 "Apple" picks the model named Apple and justified the pick with the numbers ("higher margins", "lower debt"). But the numbers were identical under the real name, where the same company was picked far less often. The name moved the choice; the numbers were the explanation given afterwards.

**1.5B:** no change. It answers FIRST about 97% of the time whatever the names are, so no name could move it. This says nothing about whether 1.5B has name bias.

**Why this matters:** name bias at 3B seems to appear for household names, not for large-caps in general. That fits the idea that what counts is how often the model has seen a name, not the company's size.

**Not yet established.** This is one run. Before relying on it:

1. **Unknown-name control** — relabel the second company with a made-up name (e.g. "Norwell Systems (NWLS)"). If that also raises picks, the effect is "any new name", not "famous name".
2. **Mirror test** — put the Apple label on the *first* company and check it pulls that way too.
3. **Other famous names** — Microsoft, NVIDIA — to show it is not something about the word "Apple".
4. **A second run** of the Apple test itself.
5. **Mismatch caveat** — the numbers under "Apple" are not Apple's. A model that knows Apple's real margins could be reacting to that mismatch as well as to the name.

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

