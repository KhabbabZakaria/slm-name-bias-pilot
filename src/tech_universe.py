"""Candidate technology tickers for the pilot.

This is a hand-assembled candidate list, not a scan of all of EDGAR. Scanning
every filer for its SIC code costs one request per company across ~10k filers;
at pilot scale that is the kind of time sink the brief's two-hour fallback
clause exists to avoid. The SIC code of every candidate below is still verified
against EDGAR in fetch_fundamentals.py, so membership in the technology sector
is checked, not assumed -- this list only decides who gets looked at.

Spread is deliberate: mega-cap through small-cap, so the pairing step has a
populated middle band to draw from.
"""

CANDIDATES = [
    # mega / large cap
    "AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "ADBE", "AMD", "INTC", "CSCO",
    "QCOM", "TXN", "IBM", "NOW", "INTU", "MU", "ADI", "AMAT", "LRCX", "KLAC",
    "SNPS", "CDNS", "PANW", "ANET", "FTNT", "ADSK", "ROP", "APH", "MSI", "HPQ",
    "HPE", "DELL", "WDC", "STX", "NTAP", "JNPR", "ZBRA", "TER", "SWKS", "MCHP",
    "MPWR", "ON", "TYL", "PTC", "ANSS", "AKAM", "EPAM", "CDW", "IT", "GEN",
    "KEYS", "GLW", "GRMN", "FSLR", "ENTG", "TDY", "TRMB", "VRSN", "SSNC", "CTSH",
    # mid cap
    "DDOG", "NET", "SNOW", "TEAM", "MDB", "OKTA", "HUBS", "VEEV", "WDAY", "ZM",
    "DOCU", "TWLO", "ZS", "CRWD", "DBX", "PCTY", "PAYC", "MANH", "AZPN", "FFIV",
    "CIEN", "LSCC", "ONTO", "FORM", "AEIS", "ITRI", "NSIT", "PLXS", "SANM", "VSH",
    "DIOD", "ALGM", "AMKR", "VIAV", "LITE", "CALX", "EXTR", "RMBS", "SMTC", "CRUS",
    "SYNA", "WOLF", "COHR", "NOVT", "MKSI", "QLYS", "TENB", "VRNS", "PRGS", "BOX",
    "APPF", "BL", "SPSC", "WK", "ALRM", "MTSI", "PI", "CEVA", "POWI", "SLAB",
    # small cap
    "SITM", "ACLS", "UCTT", "COHU", "AZTA", "BHE", "CTS", "OSIS", "DGII", "CLFD",
    "ADTN", "HLIT", "VECO", "ICHR", "PLAB", "KLIC", "NVTS", "AOSL", "AVNW", "CSGS",
    "EGHT", "LPSN", "RAMP", "UPLD", "MITK", "YEXT", "BIGC", "AMPL", "ASAN", "BRZE",
    "DOMO", "PD", "FROG", "PATH", "AI", "CXM", "SOUN", "INTT", "KTOS", "NTGR",
    "INFN", "SWI", "NABL", "JAMF", "ENV", "EVCM", "CCCS", "OLO", "DV", "ZUO",
    "AVID", "MODN", "SPT", "NCNO", "EGAN", "GDYN", "GRID", "TTMI", "BELFB", "MEI",
    # second batch -- added after the first pairing run produced only 13 disjoint
    # pairs. The constraint was universe size, not the matching rule, so the
    # tolerance stayed at 20% and the candidate pool grew instead.
    "SMCI", "PSTG", "NTNX", "SPLK", "DT", "ESTC", "GTLB", "S", "CFLT", "MSTR",
    "BSY", "ACIW", "EVTC", "JKHY", "FICO", "CACI", "SAIC", "LDOS", "BAH", "DXC",
    "UIS", "PRFT", "CNXC", "TTEC", "EXLS", "FN", "JBL", "FLEX", "KN", "ROG",
    "LFUS", "XRX", "IDCC", "UI", "NTCT", "DAKT", "VRNT", "CGNT", "SCWX", "OSPN",
    "NSSC", "PAR", "AMBA", "MXL", "NVEC", "PXLW", "LASR", "ASYS", "AEHR", "AXTI",
    "AAOI", "DZSI", "RBBN", "CMBM", "SGH", "ACMR", "CRDO", "ALKT", "ZETA", "IOT",
    "ESMT", "ARLO", "IMMR", "INSG", "SSYS", "DDD", "MCFT", "TDC", "AGYS", "WEAV",
    "MLNK", "CTLP", "GLOB", "DLB", "CMPR", "WIX", "TRUE", "CARS", "YELP", "ZD",
    "TTGT", "QNST", "DJCO", "NEWR", "SPWH", "MGIC", "HCKT", "RCM", "HSTM", "CPSI",
    "OMCL", "EVH", "PINC", "STRL", "VNT", "MTD", "IIVI",
    "BDC", "SILC", "EMKR", "WTT", "CUI", "IEC", "KEQU", "UFPT",
]
