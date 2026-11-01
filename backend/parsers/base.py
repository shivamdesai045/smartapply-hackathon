"""
Base utilities and spatial helpers for Sahayak Per-Type Parsers.
"""

import re
from datetime import datetime

def calculate_field_confidence(words, anchor_score=1.0, validator_score=1.0):
    """
    Calculates field confidence [0.0, 1.0] based on:
    - mean OCR word confidence (0.5 weight)
    - spatial anchor proximity / fit (0.3 weight)
    - format validator check (0.2 weight)
    """
    if words:
        confs = [w.get("confidence", 80.0) for w in words if isinstance(w, dict)]
        mean_ocr = (sum(confs) / len(confs)) / 100.0 if confs else 0.80
    else:
        mean_ocr = 0.80

    score = 0.5 * mean_ocr + 0.3 * anchor_score + 0.2 * validator_score
    return round(min(1.0, max(0.0, score)), 2)

def find_line_with_keywords(lines, keywords):
    """Finds the first line index and line object matching any keyword."""
    for idx, line in enumerate(lines):
        text = line.get("text", "").lower()
        if any(kw in text for kw in keywords):
            return idx, line
    return None, None

def find_lines_between(lines, start_idx, end_idx):
    """Returns lines strictly between start_idx and end_idx."""
    if start_idx is None or end_idx is None or start_idx >= end_idx:
        return []
    return lines[start_idx + 1:end_idx]

def extract_words_matching_text(words, text_substring):
    """Finds word objects that constitute the text_substring."""
    if not text_substring or not words:
        return []
    sub_tokens = set(re.sub(r"[^\w\s]", "", text_substring.lower()).split())
    matched = []
    for w in words:
        w_clean = re.sub(r"[^\w\s]", "", w.get("text", "").lower())
        if w_clean in sub_tokens:
            matched.append(w)
    return matched

_DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d",
    "%d %b %Y", "%d %B %Y",
    "%b %d %Y", "%B %d %Y",
]

def parse_date_to_iso(date_str):
    """Parses date string into ISO YYYY-MM-DD or 4-digit YYYY."""
    if not date_str:
        return None
    s = str(date_str).strip()
    m_full = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", s)
    if m_full:
        p1, p2, p3 = int(m_full.group(1)), int(m_full.group(2)), int(m_full.group(3))
        # Handle DD/MM/YYYY vs MM/DD/YYYY
        day, month, year = (p1, p2, p3) if p1 <= 31 and p2 <= 12 else (p2, p1, p3)
        try:
            return f"{year:04d}-{month:02d}-{day:02d}"
        except Exception:
            pass

    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    m_year = re.search(r"\b(19\d{2}|20\d{2})\b", s)
    if m_year:
        return m_year.group(1)

    return None

def clean_extracted_name(name_str):
    """Cleans extracted name by stopping at line breaks and stripping delimiter tokens."""
    if not name_str:
        return None
    s = str(name_str).strip()
    # Stop at newline, pipe, tab, or common delimiter
    s = re.split(r"[\n\r|;]", s)[0]
    cleaned = re.sub(r"^[^\w]+|[^\w]+$", "", s).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    tokens = cleaned.split()
    if len(tokens) < 1:
        return None
    return cleaned


# --------------------------------------------------------------------------- #
# Hardened Address & Name Extraction / Validation (Urgent Hotfix)
# --------------------------------------------------------------------------- #

DISALLOWED_NAME_KEYWORDS = {
    "certify", "certified", "that", "this", "board", "statement", "marks",
    "certificate", "government", "school", "examination", "secondary",
    "council", "republic", "india", "name", "candidate", "student",
    "pupil", "examinee", "roll", "seat", "division", "signature",
    "authority", "education", "state", "university", "department",
    "institution", "college", "passing", "higher", "central", "delhi",
    "maharashtra", "cbse", "icse", "ssc", "hsc", "grade", "result",
    "total", "subject", "theory", "practical", "maximum", "obtained",
    "permanent", "account", "income", "tax", "election", "commission",
    "card", "identity", "union", "ministry", "official", "portal",
    "pass", "passed", "fail", "failed", "distinction", "father", "mother",
    "husband", "wife", "address", "gender", "male", "female", "transgender",
    "issued", "date", "year", "session", "centre", "center", "regn", "no", "dob", "birth", "yob"
}

AADHAAR_NOTICE_KEYWORDS = {
    "should be updated",
    "after every 10 years",
    "maadhaar",
    "biometric",
    "biometrics",
    "download",
    "entities",
    "consent",
    "uidai",
    "helpline",
    "toll free",
    "1947",
    "www.",
    "http",
    ".gov.in",
    "proof of identity",
    "not of citizenship",
    "not a proof of citizenship",
    "help@uidai",
    "mera aadhaar",
}

def validate_person_name(candidate_str):
    """
    Validates that a string is a genuine human name:
    - Enforces 2-5 tokens of letters.
    - Each token length between 1 and 25 characters (with initials like 'S.').
    - Rejects headings, board names, labels, and statutory text.
    - Strictly preserves 'Kumar'.
    """
    if not candidate_str:
        return None

    s = str(candidate_str).strip()
    s = re.split(r"[\r\n|;]", s)[0].strip()
    # Strip common leading labels
    s = re.sub(
        r"^(?:Candidate(?:'s)?\s+(?:Full\s+)?Name|Student(?:'s)?\s+Name|Pupil(?:'s)?\s+Name|"
        r"Name\s+of\s+Candidate|Full\s+Name|Elector(?:'s)?\s+Name|Name)\s*[:\-]?\s*",
        "", s, flags=re.I
    )
    # Strip titles except Kumar (preserves Kumar Sanu / Rajesh Kumar)
    s = re.sub(r"^(?:Mr|Mrs|Ms|Shri|Smt|Dr|Prof|Master)\.?\s+", "", s, flags=re.I)
    s = re.sub(r"^Kumari\.?\s+", "", s, flags=re.I)

    # Clean characters except letters, dots for initials, and spaces
    s = re.sub(r"[^A-Za-z\s\.]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    tokens = [t.strip(".") for t in s.split() if t.strip(".")]
    if not (2 <= len(tokens) <= 5):
        return None

    for t in tokens:
        if len(t) < 1 or len(t) > 25:
            return None
        if not t.isalpha():
            return None

    lower_tokens = [t.lower() for t in tokens]
    if any(t in DISALLOWED_NAME_KEYWORDS for t in lower_tokens):
        return None

    return " ".join(t.capitalize() for t in tokens)


def is_notice_or_garbage_line(line_text, min_confidence=None):
    """Checks if a line contains statutory notice text or poor alphanumeric ratio."""
    if not line_text:
        return True
    lt = line_text.lower().strip()
    if any(kw in lt for kw in AADHAAR_NOTICE_KEYWORDS):
        return True

    alnum = re.findall(r"[A-Za-z0-9]", line_text)
    total_len = len(line_text.strip())
    if total_len == 0 or len(alnum) < 3:
        return True
    if len(alnum) / total_len < 0.40:
        return True

    return False


def extract_clean_address(lines, text=None, max_lines=6):
    """
    Extracts an address starting at Address / C/O / S/O / D/O / W/O anchor
    up to the 6-digit PIN code line (inclusive), maximum max_lines lines.
    Drops notice keywords, poor-ratio lines, and low-confidence lines.
    Returns: (cleaned_address_str, confidence, needs_review)
    """
    if not lines and text:
        lines = [{"text": l.strip(), "confidence": 100.0} for l in text.splitlines() if l.strip()]
    elif lines:
        norm_lines = []
        for l in lines:
            if isinstance(l, str):
                norm_lines.append({"text": l.strip(), "confidence": 100.0})
            elif isinstance(l, dict):
                norm_lines.append(l)
        lines = norm_lines

    if not lines:
        return None, 0.0, True

    start_idx = None

    # Find starting anchor
    for idx, line in enumerate(lines):
        lt = line.get("text", "")
        if re.search(r"\b(?:Address|C/O|S/O|D/O|W/O|Care\s+of|Son\s+of|Daughter\s+of|Wife\s+of|पत्ता|पता|निवास)\b", lt, re.I):
            start_idx = idx
            break

    if start_idx is None:
        # Fallback: line containing 6-digit PIN
        for idx, line in enumerate(lines):
            lt = line.get("text", "")
            if re.search(r"\b[1-9]\d{5}\b", lt) and not is_notice_or_garbage_line(lt):
                start_idx = max(0, idx - 2)
                break

    if start_idx is None:
        return None, 0.0, True

    collected_lines = []
    found_pin = False

    for curr_idx in range(start_idx, min(len(lines), start_idx + max_lines)):
        curr_line = lines[curr_idx]
        curr_text = curr_line.get("text", "").strip()

        line_conf = curr_line.get("confidence", 100.0)
        if line_conf < 35.0:
            continue

        if is_notice_or_garbage_line(curr_text):
            continue

        if curr_idx == start_idx:
            cleaned_start = re.sub(r"^(?:Address|पत्ता|पता|निवास)\s*[:\-]?\s*", "", curr_text, flags=re.I).strip()
            if cleaned_start:
                collected_lines.append(cleaned_start)
        else:
            collected_lines.append(curr_text)

        if re.search(r"\b[1-9]\d{5}\b", curr_text):
            found_pin = True
            break

    if not collected_lines:
        return None, 0.0, True

    combined = ", ".join(collected_lines)
    combined = re.sub(r"\s+", " ", combined).strip(" ,/-.:;")

    tokens = combined.split()
    if len(tokens) < 3 or not found_pin:
        return combined if len(tokens) >= 3 else None, 0.50 if len(tokens) >= 3 else 0.0, True

    return combined, 0.95, False
