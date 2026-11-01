"""
Feature Extractor for Sahayak ML Document Field Generalizer.

Extracts purely spatial, geometrical, statistical, and context proximity features.
STRICT PRIVACY COMPLIANCE:
- Never memorizes personal text or names.
- Zero raw free-text n-grams.
- Uses only position (x, y, w, h), shape (aspect ratio, length, capitalisation pattern, digit ratio),
  and keyword context distance.
"""

import re

FEATURE_NAMES = [
    "pos_x0", "pos_y0", "pos_x1", "pos_y1",
    "width", "height", "aspect_ratio",
    "char_len", "word_count", "digit_ratio",
    "alpha_ratio", "uppercase_ratio", "whitespace_ratio", "special_ratio",
    "is_all_uppercase", "is_title_case", "has_digits", "has_date_delimiters",
    "has_pin_pattern",
    # Specific anchor flags
    "is_name_anchor", "is_father_anchor", "is_mother_anchor",
    "is_dob_anchor", "is_doc_num_anchor", "is_address_anchor",
    # Context distances and flags
    "dist_anchor_name", "same_line_name",
    "dist_anchor_dob", "same_line_dob",
    "dist_anchor_address", "same_line_address",
    "dist_anchor_doc_number", "same_line_doc_number",
    "dist_anchor_father", "same_line_father",
    "dist_anchor_mother", "same_line_mother",
]

ANCHOR_KEYWORDS = {
    "name": ["name", "candidate", "student", "elector", "given name", "surname"],
    "dob": ["dob", "date of birth", "year of birth", "yob", "birth"],
    "address": ["address", "residence", "flat", "plot", "road", "pin", "post"],
    "doc_number": ["passport no", "epic no", "licence no", "license no", "pan", "permanent account", "aadhaar", "certificate no", "roll no"],
    "father": ["father", "husband", "s/o", "d/o", "w/o", "guardian", "son of", "daughter of"],
    "mother": ["mother", "m/o"],
}

TARGET_LABELS = [
    "other",
    "name",
    "dob",
    "address",
    "doc_number",
    "father_name",
    "mother_name",
]

def extract_line_features(line, all_lines):
    """
    Extracts fixed-length 37-dimensional feature vector for a given OCR line.
    """
    text = line.get("text", "").strip()
    lower_text = text.lower()
    bbox = line.get("bbox", [0.0, 0.0, 1.0, 0.1])
    x0, y0, x1, y1 = bbox
    w = max(0.001, x1 - x0)
    h = max(0.001, y1 - y0)
    aspect_ratio = min(w / h, 50.0) / 50.0

    length = len(text)
    words = text.split()
    word_count = len(words)

    if length > 0:
        digits = sum(1 for c in text if c.isdigit())
        alphas = sum(1 for c in text if c.isalpha())
        uppers = sum(1 for c in text if c.isupper())
        spaces = sum(1 for c in text if c.isspace())
        specials = length - (digits + alphas + spaces)

        digit_ratio = digits / length
        alpha_ratio = alphas / length
        uppercase_ratio = uppers / length
        whitespace_ratio = spaces / length
        special_ratio = specials / length
        is_all_uppercase = 1.0 if (alphas > 0 and uppers == alphas) else 0.0
        is_title_case = 1.0 if (word_count > 0 and all(w[0].isupper() for w in words if w)) else 0.0
        has_digits = 1.0 if digits > 0 else 0.0
    else:
        digit_ratio = alpha_ratio = uppercase_ratio = whitespace_ratio = special_ratio = 0.0
        is_all_uppercase = is_title_case = has_digits = 0.0

    has_date_delimiters = 1.0 if bool(re.search(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}", text)) else 0.0
    has_pin_pattern = 1.0 if bool(re.search(r"\b[1-9]\d{5}\b", text)) else 0.0

    # Specific anchor discriminator
    has_father_word = any(kw in lower_text for kw in ANCHOR_KEYWORDS["father"])
    has_mother_word = any(kw in lower_text for kw in ANCHOR_KEYWORDS["mother"])
    has_name_word = any(kw in lower_text for kw in ANCHOR_KEYWORDS["name"])

    is_name_anchor = 1.0 if (has_name_word and not has_father_word and not has_mother_word) else 0.0
    is_father_anchor = 1.0 if has_father_word else 0.0
    is_mother_anchor = 1.0 if has_mother_word else 0.0
    is_dob_anchor = 1.0 if any(kw in lower_text for kw in ANCHOR_KEYWORDS["dob"]) else 0.0
    is_doc_num_anchor = 1.0 if any(kw in lower_text for kw in ANCHOR_KEYWORDS["doc_number"]) else 0.0
    is_address_anchor = 1.0 if any(kw in lower_text for kw in ANCHOR_KEYWORDS["address"]) else 0.0

    # Keyword context distances
    line_y_center = (y0 + y1) / 2.0
    context_features = []

    for category in ["name", "dob", "address", "doc_number", "father", "mother"]:
        keywords = ANCHOR_KEYWORDS[category]
        min_dist = 1.0
        same_line = 0.0

        for other in all_lines:
            other_text = other.get("text", "").lower()
            if any(kw in other_text for kw in keywords):
                other_y = (other.get("bbox", [0, 0, 0, 0])[1] + other.get("bbox", [0, 0, 0, 0])[3]) / 2.0
                dist = abs(line_y_center - other_y)
                if dist < min_dist:
                    min_dist = dist
                if other == line:
                    same_line = 1.0

        context_features.append(min_dist)
        context_features.append(same_line)

    vec = [
        x0, y0, x1, y1,
        w, h, aspect_ratio,
        min(length, 120) / 120.0,
        min(word_count, 20) / 20.0,
        digit_ratio,
        alpha_ratio,
        uppercase_ratio,
        whitespace_ratio,
        special_ratio,
        is_all_uppercase,
        is_title_case,
        has_digits,
        has_date_delimiters,
        has_pin_pattern,
        is_name_anchor,
        is_father_anchor,
        is_mother_anchor,
        is_dob_anchor,
        is_doc_num_anchor,
        is_address_anchor,
        *context_features,
    ]

    return vec
