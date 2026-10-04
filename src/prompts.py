"""Step 2: the prompt builder.

One public function, build_prompt(pair, condition, order) -> str.

The template is fixed. Only the header block varies across conditions; the
fundamentals block is produced by one function and is byte-identical for a given
company whatever condition it appears under. If the template changes, every
result gathered under the old one is void -- rerun, do not mix.

Two assertions guard the failure modes that are silent and fatal:

* an anonymised prompt containing a ticker or company name
* any prompt containing an absolute currency figure

Both would invalidate the run while leaving output that looks perfectly fine.
They are checked on every prompt as it is built, not sampled.
"""

import re

CONDITIONS = ("identified", "anonymised", "swapped")
ORDERS = ("large_first", "small_first")

# The ratios shown to the model, in display order. Absolute currency figures are
# deliberately absent: revenue scale is an identity cue, not a fundamental, and
# a large-cap's revenue announces which company it is even with the name stripped.
RATIO_FIELDS = [
    ("rev_growth_pct", "Revenue growth (YoY)", "pct"),
    ("gross_margin_pct", "Gross margin", "pct"),
    ("op_margin_pct", "Operating margin", "pct"),
    ("net_margin_pct", "Net margin", "pct"),
    ("debt_to_revenue", "Total debt / revenue", "ratio"),
]

TEMPLATE = """You are an equity analyst. Below are two companies.

Company A: {header_a}
{fundamentals_a}

Company B: {header_b}
{fundamentals_b}

Which would you rather hold for the next 12 months?
Answer with exactly one line:
CHOICE: A
or
CHOICE: B
Then one sentence of reasoning."""

# Diagnostic layout, added after the first run: identical text, but the Company B
# block is listed before the Company A block. In TEMPLATE the label B always sits
# second, so a preference for B cannot be told apart from a preference for the
# second-listed company. Here the two come apart: if the preference follows the
# slot, A wins; if it follows the letter, B still wins. The answer instructions
# are left exactly as in TEMPLATE, so block order is the only thing that moves.
TEMPLATE_B_FIRST = """You are an equity analyst. Below are two companies.

Company B: {header_b}
{fundamentals_b}

Company A: {header_a}
{fundamentals_a}

Which would you rather hold for the next 12 months?
Answer with exactly one line:
CHOICE: A
or
CHOICE: B
Then one sentence of reasoning."""

# Answer-order diagnostic: identical to the two templates above except that
# "CHOICE: B" is listed before "CHOICE: A". In every earlier run CHOICE: B was the
# last answer option, so a preference for B could be a preference for the letter
# or for whichever option is read last. Reversing only these lines separates them.
_ANS_AB = "CHOICE: A\nor\nCHOICE: B"
_ANS_BA = "CHOICE: B\nor\nCHOICE: A"
assert _ANS_AB in TEMPLATE and _ANS_AB in TEMPLATE_B_FIRST

LAYOUTS = {
    "a_first": TEMPLATE,
    "b_first": TEMPLATE_B_FIRST,
    "a_first_ans_ba": TEMPLATE.replace(_ANS_AB, _ANS_BA),
    "b_first_ans_ba": TEMPLATE_B_FIRST.replace(_ANS_AB, _ANS_BA),
}


def _ordinal(template):
    """Same template with ordinal words in place of the letters.

    "First company" takes the role of A and "Second company" the role of B, so
    everything downstream (order, swap, fundamentals_owner) is unchanged; only
    the words the model reads differ. In the b_first variants the block labelled
    "Second company" is listed first -- odd for a real prompt, but it is what
    tests whether the model follows the word or the slot.
    """
    return (template.replace("Company A:", "First company:")
                    .replace("Company B:", "Second company:")
                    .replace("CHOICE: A", "CHOICE: FIRST")
                    .replace("CHOICE: B", "CHOICE: SECOND"))


for _name in list(LAYOUTS):
    LAYOUTS[f"ord_{_name}"] = _ordinal(LAYOUTS[_name])

# Which answer words a layout uses, mapped onto the internal A/B roles.
def answer_labels(layout):
    return {"FIRST": "A", "SECOND": "B"} if layout.startswith("ord_") else {"A": "A", "B": "B"}

# Name fragments too generic to treat as identifying. Without this, the leak
# check trips on the word "Technology" appearing in a label.
_GENERIC = {
    "inc", "corp", "corporation", "co", "company", "ltd", "limited", "plc",
    "llc", "lp", "group", "holdings", "holding", "technologies", "technology",
    "systems", "solutions", "international", "intl", "the", "and", "de", "sa",
    "nv", "software", "digital", "semiconductor", "semiconductors", "associates",
    "enterprises", "industries", "communications", "networks", "labs", "new",
}

_CURRENCY = re.compile(
    r"[$£€¥]"          # any currency symbol
    r"|\b\d{1,3}(?:,\d{3})+\b"        # comma-grouped thousands
    r"|\b\d{4,}\b"                    # any bare four-digit-plus number
    r"|\b(?:million|billion|trillion|thousand|usd|bn|mm)\b",
    re.IGNORECASE,
)


def _identifying_tokens(name, ticker):
    """Distinctive words in a company name, plus the ticker."""
    words = re.split(r"[^A-Za-z0-9]+", str(name))
    tokens = {w for w in words if len(w) >= 3 and w.lower() not in _GENERIC}
    tokens.add(str(ticker))
    return tokens


def format_fundamentals(pair, role):
    """The fundamentals block for one company.

    The single source of the block for every condition. Identical bytes for a
    given company whether it appears identified, anonymised or swapped -- which
    is what makes the conditions differ in exactly one respect.
    """
    lines = []
    width = max(len(label) for _, label, _ in RATIO_FIELDS) + 2
    for field, label, kind in RATIO_FIELDS:
        value = float(pair[f"{role}_{field}"])
        shown = f"{value:.1f}%" if kind == "pct" else f"{value:.2f}x"
        lines.append(f"  {(label + ':').ljust(width)}{shown:>8}")
    return "\n".join(lines)


def _header(pair, role):
    return f"{pair[f'{role}_display_name']} ({pair[f'{role}_ticker']})"


def assert_no_identity_leak(prompt, pair):
    """No ticker or distinctive name fragment may appear. Anonymised only."""
    for role in ("large", "small"):
        # Both name forms: the displayed one and EDGAR's, since either reaching
        # an anonymised prompt is a leak.
        names = f"{pair[f'{role}_display_name']} {pair[f'{role}_name']}"
        for token in _identifying_tokens(names, pair[f"{role}_ticker"]):
            if re.search(rf"\b{re.escape(token)}\b", prompt, re.IGNORECASE):
                raise AssertionError(
                    f"identity leak in anonymised prompt for {pair['pair_id']}: "
                    f"{token!r} ({role}-cap) appears in the prompt")


def assert_no_absolute_currency(prompt):
    """No absolute money figure may appear, in any condition.

    Same class of failure as the ticker leak: silent, and it reintroduces the
    scale cue the ratios-only design exists to remove.
    """
    hit = _CURRENCY.search(prompt)
    if hit:
        raise AssertionError(
            f"absolute currency figure in prompt: {hit.group(0)!r}")


def build_prompt(pair, condition, order, layout="a_first"):
    """Build one prompt.

    pair      -- a row of data/pairs.csv (anything supporting pair["col"])
    condition -- 'identified', 'anonymised' or 'swapped'
    order     -- 'large_first' or 'small_first'; which company is labelled A
    layout    -- 'a_first' (the frozen template), 'b_first' (B block listed
                 first), or either with '_ans_ba' (answer options listed as
                 B then A). All but 'a_first' are diagnostics. Letters keep their meaning either
                 way -- 'order' decides which company carries label A.

    Returns the prompt string. Raises if either assertion fails.
    """
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition!r}")
    if order not in ORDERS:
        raise ValueError(f"unknown order {order!r}")
    if layout not in LAYOUTS:
        raise ValueError(f"unknown layout {layout!r}")

    # Position, not capitalisation, is what the model sees. pairs.csv stores the
    # pair by role, so map role onto slot here and map back when parsing.
    role_a, role_b = (("large", "small") if order == "large_first"
                      else ("small", "large"))

    if condition == "anonymised":
        header_a = header_b = ""
        facts_a, facts_b = role_a, role_b
    elif condition == "identified":
        header_a, header_b = _header(pair, role_a), _header(pair, role_b)
        facts_a, facts_b = role_a, role_b
    else:  # swapped: real name over the other company's numbers
        header_a, header_b = _header(pair, role_a), _header(pair, role_b)
        facts_a, facts_b = role_b, role_a

    prompt = LAYOUTS[layout].format(
        header_a=header_a, fundamentals_a=format_fundamentals(pair, facts_a),
        header_b=header_b, fundamentals_b=format_fundamentals(pair, facts_b))
    # An empty header would otherwise leave "Company A: " with a trailing space
    # before the newline, which some tokenisers treat as its own token. The
    # anonymised label carries no name and no dangling whitespace either.
    prompt = "\n".join(line.rstrip() for line in prompt.split("\n"))

    if condition == "anonymised":
        assert_no_identity_leak(prompt, pair)
    assert_no_absolute_currency(prompt)
    return prompt


def fundamentals_owner(pair, condition, order, choice):
    """Whose numbers the model picked, given its A/B choice.

    In the swapped condition this is the field that separates following the
    numbers from following the name.
    """
    role_a, role_b = (("large", "small") if order == "large_first"
                      else ("small", "large"))
    name_role = role_a if choice == "A" else role_b
    if condition == "swapped":
        facts_role = role_b if choice == "A" else role_a
    else:
        facts_role = name_role
    return {
        "chosen_name_owner": name_role,
        "chosen_fundamentals_owner": facts_role,
        "chosen_ticker": (pair[f"{name_role}_ticker"]
                          if condition != "anonymised" else None),
    }
