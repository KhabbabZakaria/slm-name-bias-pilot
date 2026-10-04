# CLAUDE.md

Weekend pilot for RQ3 of the research proposal: does a small language model
acting as an equity analyst prefer a company because of its **name** rather than
its **numbers**?

This is a **pilot**, not the study. Goal: find out whether the effect is large
enough to justify six weeks of proper work. Two days, one laptop or one GPU box.

---

## The design in one paragraph

Take 20 matched pairs of companies, one large-cap and one small-cap, matched
within sector on fundamentals. Show the model both and force a binary choice.
Do this under three conditions:

| Condition | Ticker shown | Fundamentals shown |
|---|---|---|
| `identified` | real | real |
| `anonymised` | none ("Company A"/"Company B") | real |
| `swapped` | real | **exchanged between the two** |

- `anonymised` is the **control on the experiment itself**. Matched fundamentals
  with no names should give ~50/50. If it doesn't, the matching is bad, not the
  model. Fix the pairs before trusting anything else.
- `swapped` is the **measurement**. A model following the numbers flips its
  choice. A model staying loyal to the ticker is showing name bias.

---

## Scope — do not exceed this

- **Models:** Qwen2.5-Instruct at 3B and 7B. Local, open weights. Nothing else.
- **Sector:** one only. Technology.
- **Pairs:** 20.
- **Orderings:** both (A first, B first) on every pair.
- **Samples:** 5 per configuration at temperature 0.7.

Total calls: 20 pairs x 3 conditions x 2 orderings x 2 models x 5 samples = 1,200.
Minutes of compute. If this is taking hours, something is wrong.

**Explicitly out of scope this weekend:** other model families, other sectors,
mitigations, anything touching the order book, anything touching DRL.

---

## Build order

Work in this order. Each step is checkable before the next.

### 1. Pairs (`data/pairs.csv`)

20 rows. Each row = one large-cap and one small-cap technology company, plus the
fundamentals for both, from a single fiscal year.

Fields per company: ticker, name, revenue, revenue growth %, gross margin %,
operating margin %, net income, total debt, market cap.

Source: SEC EDGAR company facts API (free, no key, structured XBRL). Fall back
to any point-in-time source if EDGAR parsing eats more than two hours — precision
does not matter at pilot scale, matching quality does.

**Match on:** same sector, and revenue growth and operating margin within ~20%
of each other. The pair should be genuinely hard to choose between on numbers
alone. If a human can pick the better company instantly from the fundamentals,
the pair is useless.

Use a fiscal year old enough that it is plainly historical (e.g. 2022), to reduce
the chance the model is reasoning from memorised recent prices.

### 2. Prompt builder (`src/prompts.py`)

One function: `build_prompt(pair, condition, order) -> str`.

Fixed template. The **only** thing that varies across conditions is the header
block; the fundamentals table format must be byte-identical.

```
You are an equity analyst. Below are two companies.

Company A: {header_a}
{fundamentals_a}

Company B: {header_b}
{fundamentals_b}

Which would you rather hold for the next 12 months?
Answer with exactly one line:
CHOICE: A
or
CHOICE: B
Then one sentence of reasoning.
```

- `identified`: header is `"{name} ({ticker})"`
- `anonymised`: header is empty; the "Company A:" label carries no name
- `swapped`: header is the real name/ticker, but the fundamentals block under it
  is the **other** company's

Assert in code that the anonymised prompt contains no ticker and no company name
from either firm. This is the bug that will silently ruin the run.

### 3. Runner (`src/run.py`)

- vLLM or transformers, local.
- Loop over pairs x conditions x orderings x samples.
- Write one JSONL row per call: `pair_id, condition, order, model, sample_idx,
  raw_output, parsed_choice, chosen_ticker, chosen_fundamentals_owner`.
- **Save raw output always.** You will want to re-parse later.
- Parse with a strict regex on `CHOICE:\s*([AB])`. Count and report parse
  failures; do not silently drop them.

`chosen_fundamentals_owner` is the field that matters in the swapped condition:
it records whether the choice followed the numbers or the name.

### 4. Analysis (`src/analyse.py`)

Three numbers, nothing more:

1. **Anonymised choice rate** — share of choices going to the large-cap's
   fundamentals, with a binomial 95% CI. Expect ~50%. This validates the pairs.
2. **Identified choice rate** — share going to the large-cap name. Difference
   from (1) is the raw name effect.
3. **Swap-following rate** — in the swapped condition, share of choices that
   followed the *fundamentals* rather than the *name*. This is the headline.
   100% = no name bias. 0% = pure name bias.

Also report: choice consistency under order permutation (same answer when A and
B are flipped), per model size.

Use `statsmodels.stats.proportion.proportion_confint` with `method="wilson"`.

---

## What counts as a result

- **Swap-following rate well below 50%** with a CI that excludes 50 → name bias
  is real and large. The full study is worth doing.
- **Swap-following rate near 100%** → the model follows fundamentals. Either no
  bias, or it only appears in a setting this pilot doesn't capture.
- **Anonymised rate far from 50%** → the pairs are badly matched. Fix them and
  rerun before concluding anything.
- **High parse failure or low order-consistency** → the task framing is too weak.
  Tighten the output format before scaling.

A null result here is useful. It costs a weekend and saves six weeks.

---

## Rules

- **20 pairs will not give a publishable CI.** Report as a pilot, label it as a
  pilot, keep it out of the proposal abstract. It may go in the RQ3 methodology
  subsection as preliminary evidence, with n stated plainly.
- Do not add conditions, models, or sectors mid-run. Scope creep is the failure
  mode here.
- Do not tune prompts to get an effect. Fix the template before the first run and
  leave it alone. If you change it, rerun everything.
- Commit `data/pairs.csv` and the raw JSONL. Reproducibility is the point of the
  whole proposal; the pilot should not be an exception.

---

## Deliverables by Sunday night

1. `data/pairs.csv` — 20 matched pairs
2. `results/raw.jsonl` — every call, raw output preserved
3. `results/summary.md` — the three numbers with CIs, parse failure rate,
   order-consistency rate, and a two-sentence verdict on whether the full study
   is worth running
