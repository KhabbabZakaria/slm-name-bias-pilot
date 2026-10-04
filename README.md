# slm-name-bias-pilot

Does a small language model pick a stock by its **name** or its **numbers**?

Two small open-weight models (Qwen2.5-3B and Qwen2.5-1.5B) act as equity analysts
and choose between matched pairs of technology companies, with company names
shown, hidden, or swapped onto the other company's fundamentals.

**Start here: [results.md](results.md)** — headline numbers, what the pilot found,
and how to reproduce it. Full detail in [results/results.md](results/results.md),
including every prompt layout, the counts behind each number, and what went wrong
along the way.

Short version: prompt layout drives most of what these models do, ordinary
large-cap names have no pull, and relabelling a company "Apple Inc. (AAPL)" —
numbers untouched — moved the 3B model's choice by about 20 points.
