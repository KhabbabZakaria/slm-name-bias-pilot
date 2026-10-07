# slm-name-bias-pilot

**Does a small language model pick a stock by its name or its numbers?**

A weekend research pilot. Two small open-weight models act as equity analysts and choose between matched pairs of technology companies. The question: do they favour a company because of its **name** rather than its **numbers**?

**Short answer:** not for ordinary large-caps. A household name does move the 3B model — about 20 points — but only when the prompt layout is working against that company. Most of what these small models do is driven by the shape of the prompt rather than by the companies in it.

## Headline numbers

| | Qwen2.5-3B | Qwen2.5-1.5B |
|---|---|---|
| Calls | 7,200 | 2,400 |
| Effect of showing real large-cap names | +1.3 pts [-3.1 to +5.8] | not measurable |
| Relabelling a company "Apple Inc. (AAPL)" — in the slot the layout disfavours | **+20 pts** [+10 to +29], replicated +21 | not interpretable |
| …"Microsoft Corporation (MSFT)" | +17 pts [+10 to +25] | — |
| …an invented name, "Norwell Systems (NWLS)" | -12 pts [-19 to -5] | — |
| …"Apple" in the slot the layout already favours | -0.7 pts [-6.1 to +4.5] | — |
| Followed the numbers when they were swapped | 60% [54–67] (letters), 70% [60–78] (First/Second) | 50% [49–52], not interpretable |
| Picked whichever answer option was listed first | — | 96% of answers |

Brackets are 95% intervals that resample the 20 pairs.

## What the pilot found

1. **Prompt layout decides most answers.** Which letter labels the companies, and which answer option is listed last, move 3B's choices by 20–30 points. The companies' own position matters much less.
2. **1.5B barely chooses at all.** It copies the first answer line it is shown in about 97% of answers, so it cannot be used to study name bias with this prompt.
3. **3B does read the numbers, once layout is balanced.** Pooling all layouts so the position effects cancel, it followed the swapped numbers rather than the name 60% [54–67] of the time.
4. **Ordinary large-cap names have no pull.** Lam Research, Autodesk, Gartner and the rest changed nothing.
5. **Name familiarity has a large pull — but only from behind.** Relabelling one company "Apple Inc. (AAPL)", numbers untouched, raised how often 3B picked it by +20 points (17 of 20 pairs; replicated at +21). Microsoft gave +17. An invented name *cost* -12, so this is a familiarity gradient, not a reaction to any relabelling. The model then justified its choice with the numbers — the same numbers it found less convincing under the real name.
6. **The mirror test fails, and that bounds the claim.** The same Apple label on the company the layout already favours changed nothing (-0.7 pts). The effect shows only where position works against the labelled company, so this is not a pure name effect.

Points 5 and 6 come from five relabelling tests (Apple twice, Microsoft, an invented name, and Apple on the opposite slot), each about 200 answers against a matched real-name baseline. Details and what is still open are in [results/results.md](results/results.md).

## Repository

```
data/pairs.csv             20 matched large/small technology pairs, FY2022
data/universe.csv          all candidate companies pulled from SEC EDGAR
results/results.md         full write-up: every setup, counts and caveats
results/raw*.jsonl         every model call, with raw output preserved
results/probe.jsonl        recognition check (can the model recall these ratios?)
results/raw_fake_*.jsonl   the relabelling tests (Apple, Microsoft, invented name)
results/name_tests.md      relabelling tests vs the real-name baseline
src/                       fetch, pairing, prompts, runner, analysis
```

## Reproducing it

```bash
python3 -m venv venv && ./venv/bin/pip install requests pandas statsmodels mlx-lm
export SEC_USER_AGENT="Your Name you@example.com"   # EDGAR requires a contact

./venv/bin/python src/fetch_fundamentals.py   # SEC EDGAR -> data/universe.csv
./venv/bin/python src/build_pairs.py          # -> data/pairs.csv
./venv/bin/python src/validate_pairs.py       # pair quality checks
cd src && ../venv/bin/python test_prompts.py  # prompt guards (name/currency leaks)

# one 600-call run: 20 pairs x 3 conditions x 2 orderings x 5 samples
# sampling is temperature 0.7 throughout, logged in every row
caffeinate -i ../venv/bin/python run.py --layout a_first

../venv/bin/python write_results.py           # rebuilds results/results.md and this file
```

Runs are resumable and append-only: rerunning skips calls already recorded. `caffeinate` matters on a Mac — the first run lost 24 minutes to the display sleeping.

## Honest limits

- **20 pairs.** Enough to decide whether to continue, not to publish.
- **Small models only.** 3B at 4-bit, 1.5B at full precision. A 7B run froze an 8GB MacBook at 123/600 calls and was abandoned.
- **The layout tests and the Apple test were added after seeing the first results.** They are follow-ups to a bias found in the data, not part of the original plan. A real study must fix the rotation of company order *and* answer order before the first call.
- **The name effect is entangled with position.** It appears only in the slot the layout disfavours; in the favoured slot the same label does nothing. Any full study has to measure the two together rather than report a single name effect.
- **One sector** (technology) and **one fiscal year** (2022).
- **The recognition check came back empty, which is itself a limitation.** Asked to recall these companies' FY2022 ratios, 3B answered UNKNOWN for all 40, including household names. That looks like compliance with the "do not guess" instruction rather than absent knowledge, so it does **not** rule out an alternative reading of the Apple result: the model may be reacting to the numbers not matching Apple's real financials rather than to the name itself. Against that reading: noticing a mismatch should make a model pick the company *less*, and both household names raised it, while the invented name — which no model can hold expectations about — lowered it.
- **`results/raw_7b_partial_abandoned.jsonl` is excluded from every number here.** Those 123 rows are the 7B run that froze the machine; they are committed for the record only and must not be pooled with the rest.

Full detail, including what went wrong along the way, is in [results/results.md](results/results.md).

