import re

# Domain Allowlist: Data, ML, AI, Analytics, and core engineering
DATA_AI_KEYWORDS = [
    r"\bdata\b",
    r"\bdata\s+analyst\b",
    r"\bdata\s+analytics\b",
    r"\bdata\s+scientist\b",
    r"\bdata\s+science\b",
    r"\bdata\s+engineer\b",
    r"\bmachine\s+learning\b",
    r"\bml\b",
    r"\bai\b",
    r"\bartificial\s+intelligence\b",
    r"\bdeep\s+learning\b",
    r"\bnlp\b",
    r"\bcomputer\s+vision\b",
    r"\bllm\b",
    r"\bgenai\b",
    r"\bgenerative\s+ai\b",
    r"\brag\b",
    r"\bbusiness\s+intelligence\b",
    r"\bbi\s+developer\b",
    r"\bbi\s+analyst\b",
    r"\bquantitative\b",
    r"\banalyst\b",
    r"\banalytics\b",
    r"\bmlops\b",
    r"\bapplied\s+scientist\b",
    r"\bresearch\s+scientist\b",
    r"\bresearch\s+engineer\b",
    r"\bsoftware\s+engineer\b",
    r"\bsoftware\s+developer\b",
    r"\bsde\b",
    r"\bbackend\b",
    r"\bpython\b",
]
DATA_AI_REGEX = re.compile("|".join(DATA_AI_KEYWORDS), re.IGNORECASE)

# Seniority Blocklist
SENIOR_KEYWORDS = [
    r"\bsenior\b",
    r"\bsr\.?\b",
    r"\blead\b",
    r"\bstaff\b",
    r"\bprincipal\b",
    r"\bmanager\b",
    r"\bdirector\b",
    r"\bhead\b",
    r"\bvp\b",
    r"\bpresident\b",
    r"\barchitect\b",
    r"\bexpert\b",
    r"\biii\b",
    r"\biv\b",
    r"\bv\b",
    r"\b3\b",
    r"\b4\b",
    r"\b5\b",
]
SENIOR_REGEX = re.compile("|".join(SENIOR_KEYWORDS), re.IGNORECASE)

# Non-Technical Field Blocklist (Sales, Marketing, HR, Ops, Finance)
NON_DATA_KEYWORDS = [
    r"\bsales\b",
    r"\bmarketing\b",
    r"\baccount\s+executive\b",
    r"\bbusiness\s+development\b",
    r"\bbdr\b",
    r"\bsdr\b",
    r"\brecruiter\b",
    r"\btalent\s+acquisition\b",
    r"\bhuman\s+resources\b",
    r"\bhr\b",
    r"\bfinance\b",
    r"\baccounting\b",
    r"\blegal\b",
    r"\bparalegal\b",
    r"\bcontent\s+writer\b",
    r"\bcopywriter\b",
    r"\bseo\b",
    r"\boperations\s+associate\b",
    r"\bcustomer\s+success\b",
    r"\bcustomer\s+support\b",
    r"\baccount\s+manager\b",
    r"\bunderwriter\b",
]
NON_DATA_REGEX = re.compile("|".join(NON_DATA_KEYWORDS), re.IGNORECASE)

# Early Career Keywords
EARLY_CAREER_KEYWORDS = [
    r"\bintern\b",
    r"\binternship\b",
    r"\bco-op\b",
    r"\bgraduate\b",
    r"\bnew grad\b",
    r"\bentry level\b",
    r"\bjunior\b",
    r"\bjr\.?\b",
    r"\bapprentice\b",
    r"\buniversity\b",
    r"\bassociate\b",
    r"\bi\b",
    r"\b1\b",
]
EARLY_CAREER_REGEX = re.compile("|".join(EARLY_CAREER_KEYWORDS), re.IGNORECASE)

# Location: India cities and variations
INDIA_KEYWORDS = [
    r"\bindia\b",
    r"\bbengaluru\b",
    r"\bbangalore\b",
    r"\bpune\b",
    r"\bmumbai\b",
    r"\bhyderabad\b",
    r"\bdelhi\b",
    r"\bgurugram\b",
    r"\bgurgaon\b",
    r"\bnoida\b",
    r"\bchennai\b",
    r"\bkolkata\b",
    r"\bahmedabad\b",
]
INDIA_REGEX = re.compile("|".join(INDIA_KEYWORDS), re.IGNORECASE)

# Location: True Global Remote terms
GLOBAL_REMOTE_KEYWORDS = [
    r"\bremote\s*-\s*india\b",
    r"\bindia\s*-\s*remote\b",
    r"\banywhere\b",
    r"\bworldwide\b",
    r"\bglobal\b",
    r"^remote$",
]
GLOBAL_REMOTE_REGEX = re.compile("|".join(GLOBAL_REMOTE_KEYWORDS), re.IGNORECASE)

# Foreign Exclusion (reject remote roles explicitly bound to other zones)
FOREIGN_EXCLUSION_KEYWORDS = [
    r"\bus\b",
    r"\busa\b",
    r"\bunited states\b",
    r"\bemea\b",
    r"\blatam\b",
    r"\bapac\b",
    r"\bcanada\b",
    r"\beurope\b",
    r"\buk\b",
    r"\bgermany\b",
]
FOREIGN_EXCLUSION_REGEX = re.compile("|".join(FOREIGN_EXCLUSION_KEYWORDS), re.IGNORECASE)


def is_early_career_job(title: str) -> bool:
    return bool(EARLY_CAREER_REGEX.search(title))


def is_target_domain_job(title: str) -> bool:
    clean_title = title.strip()
    if NON_DATA_REGEX.search(clean_title):
        return False
    if SENIOR_REGEX.search(clean_title):
        return False
    if not DATA_AI_REGEX.search(clean_title):
        return False
    return True


def is_eligible_location(location_str: str, is_remote: bool = False, country_code: str = "") -> bool:
    text = (location_str or "").strip()
    c_code = (country_code or "").strip().upper()

    if c_code in ("IN", "IND"):
        return True

    if INDIA_REGEX.search(text):
        return True

    if FOREIGN_EXCLUSION_REGEX.search(text) and not INDIA_REGEX.search(text):
        return False

    if GLOBAL_REMOTE_REGEX.search(text):
        return True

    if is_remote and (not text or text.lower() == "remote"):
        return True

    return False
