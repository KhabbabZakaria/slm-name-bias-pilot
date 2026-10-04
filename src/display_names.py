"""Company names as they appear in ordinary financial writing.

EDGAR stores registry strings -- "AMPHENOL CORP /DE/", "MKS INC" -- which are
not how these companies are written in filings prose, analyst notes or news.
Two reasons that matters for this experiment:

* Name recognition is the effect being measured. An all-caps registry string is
  a weaker cue than the name the model actually read thousands of times, so
  using it understates whatever bias exists.
* The registry format is inconsistent across companies for reasons having
  nothing to do with the companies. Showing "Motorola Solutions, Inc." against
  "MACOM TECHNOLOGY..." varies presentation style within a pair, laying a
  confound directly on top of the manipulated variable.

Rule applied: the name as the company writes it on its own FY2022 10-K cover.
Hand-checked, not derived -- title-casing turns EPAM into Epam and MKS into Mks.

One substantive correction this catches: EDGAR's current name for MKSI is
"MKS INC", but the company was MKS Instruments, Inc. throughout FY2022 and was
renamed afterwards. EDGAR stores only the present name, so the registry string
is anachronistic for the fiscal year being shown.
"""

DISPLAY_NAMES = {
    "ACIW": "ACI Worldwide, Inc.",
    "ADSK": "Autodesk, Inc.",
    "AEIS": "Advanced Energy Industries, Inc.",
    "AKAM": "Akamai Technologies, Inc.",
    "AMKR": "Amkor Technology, Inc.",
    "APH": "Amphenol Corporation",
    "BAH": "Booz Allen Hamilton Holding Corporation",
    "BDC": "Belden Inc.",
    "BRZE": "Braze, Inc.",
    "BSY": "Bentley Systems, Incorporated",
    "DIOD": "Diodes Incorporated",
    "EPAM": "EPAM Systems, Inc.",
    "FFIV": "F5, Inc.",
    "FROG": "JFrog Ltd.",
    "FTNT": "Fortinet, Inc.",
    "GEN": "Gen Digital Inc.",
    "GTLB": "GitLab Inc.",
    "HCKT": "The Hackett Group, Inc.",
    "IT": "Gartner, Inc.",
    "JKHY": "Jack Henry & Associates, Inc.",
    "LRCX": "Lam Research Corporation",
    "LSCC": "Lattice Semiconductor Corporation",
    "MANH": "Manhattan Associates, Inc.",
    "MDB": "MongoDB, Inc.",
    "MKSI": "MKS Instruments, Inc.",
    "MSI": "Motorola Solutions, Inc.",
    "MTSI": "MACOM Technology Solutions Holdings, Inc.",
    "NCNO": "nCino, Inc.",
    "NSIT": "Insight Enterprises, Inc.",
    "OKTA": "Okta, Inc.",
    "ON": "ON Semiconductor Corporation",
    "ONTO": "Onto Innovation Inc.",
    "PRGS": "Progress Software Corporation",
    "SNOW": "Snowflake Inc.",
    "STX": "Seagate Technology Holdings plc",
    "TDY": "Teledyne Technologies Incorporated",
    "TWLO": "Twilio Inc.",
    "TYL": "Tyler Technologies, Inc.",
    "VSH": "Vishay Intertechnology, Inc.",
    "WDC": "Western Digital Corporation",
}


def display_name(ticker):
    """Fail loudly rather than fall back to the EDGAR string.

    A silent fallback would reintroduce registry formatting for exactly the
    companies a rebuild had just brought into the pair set.
    """
    try:
        return DISPLAY_NAMES[ticker]
    except KeyError:
        raise KeyError(
            f"no display name for {ticker!r}. The pair set changed; add it to "
            f"display_names.py by hand -- do not derive it.") from None
