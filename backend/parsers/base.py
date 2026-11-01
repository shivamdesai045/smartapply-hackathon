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
