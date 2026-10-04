# slm-name-bias-pilot

Does a small language model pick a stock by its **name** or its **numbers**?

A weekend research pilot: Qwen2.5-3B and Qwen2.5-1.5B
act as equity analysts and choose between matched pairs of technology companies,
with names shown, hidden, or swapped onto the other company's fundamentals.

**Start here: [results.md](results.md)** — headline numbers, what the pilot found,
and how to reproduce it. Full detail in [results/results.md](results/results.md),
including every prompt layout, the counts behind each number, and what went wrong.

`CLAUDE.md` is the original brief. The work departed from it in two ways worth
knowing: the 7B model could not run on an 8GB laptop, and the prompt-layout and
Apple-label tests were added after the first results exposed a position bias.
