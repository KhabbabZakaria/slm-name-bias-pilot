# Does the name move the choice? (qwen2.5-3b)

One company's name and ticker are replaced; its numbers are left alone. Compared against the identical prompts with real names (20 pairs × both orderings × 5 samples ≈ 200 answers per cell).

| label | slot | picked with real name | picked with new label | change | pairs up/down |
|---|---|---|---|---|---|
| Apple Inc. (AAPL) | second | 70/197 (35.5%) | 107/194 (55.2%) | **+19.6 pts** [+10.4 to +29.1] | 17/2 |
| Apple Inc. (AAPL), rerun | second | 70/197 (35.5%) | 110/195 (56.4%) | **+20.9 pts** [+13.5 to +29.5] | 18/0 |
| Apple Inc. (AAPL) | first | 127/197 (64.5%) | 125/196 (63.8%) | **-0.7 pts** [-6.1 to +4.5] | 7/7 |
| Norwell Systems (NWLS) — control | second | 70/197 (35.5%) | 45/195 (23.1%) | **-12.5 pts** [-19.5 to -5.3] | 3/14 |
| Microsoft Corporation (MSFT) | second | 70/197 (35.5%) | 105/199 (52.8%) | **+17.2 pts** [+10.1 to +25.3] | 15/2 |

Brackets are pair-bootstrap 95% intervals. A change whose interval excludes zero is a real shift; one that spans zero is not.

## Reading it

- **Famous vs merely unfamiliar.** Apple moved the choice +19.6 points; the invented name Norwell Systems moved it -12.5. The control moves the choice the *other* way, and its interval excludes zero: an unfamiliar name is a penalty. So this is not "any relabelling helps" — it is a familiarity gradient, spanning about 32 points from an invented name to a household one.
- **Replication.** The Apple test rerun with a different seed gave +20.9 points against +19.6 first time — consistent.
- **Mirror.** With the Apple label on the *first* company instead, the shift was -0.7 points [-6.1 to +4.5]. Nothing. The first slot already wins 64% of the time without any relabelling, and the Apple label adds nothing on top. So the name effect shows up only where the layout is working *against* the labelled company: label and position interact, and the headline cannot be stated as a pure name effect.
- **A second household name.** Microsoft moved the choice +17.2 points [+10.1 to +25.3], so the effect is not peculiar to the word "Apple".

