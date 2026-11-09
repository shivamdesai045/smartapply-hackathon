"""
PAN Card Parser.
Uses spatial anchors (Income Tax Department, Permanent Account Number, Father's Name, DOB).
"""

import re
from .base import (
    calculate_field_confidence,
    parse_date_to_iso,
    clean_extracted_name,
    extract_words_matching_text,
)

PAN_STOPWORDS = {
    "income", "tax", "department", "govt", "government", "india", "permanent",
    "account", "number", "card", "signature", "photo", "date", "birth", "father"
}

def parse_pan(ocr_data, chosen_option=None):
    text = ocr_data.get("text", "")
    lines = ocr_data.get("lines", [])
    words = ocr_data.get("words", [])

    extracted = {
        "name": None,
        "dob": None,
        "address": None,
        "doc_number": None,
        "father_name": None,
        "mother_name": None,
        "field_confidences": {},
        "doc_meta": {"detectedType": "PAN Card"},
    }

    # 1. Document Number (10 alphanumeric characters)
    # Accept OCR-inserted spaces within a PAN; never replace O/0 or I/1 by guessing.
    pan_m = re.search(r"\b((?:[A-Z][ \t]*){5}(?:[0-9][ \t]*){4}[A-Z])\b", text.upper())
    if pan_m:
        pan_num = re.sub(r"\s", "", pan_m.group(1))
        extracted["doc_number"] = {"type": "PAN", "number": pan_num}
        w_matches = extract_words_matching_text(words, pan_num)
        extracted["field_confidences"]["doc_number"] = calculate_field_confidence(w_matches, 1.0, 1.0)
    else:
        pan_loose = re.search(r"(?:PAN|Permanent\s+Account\s+Number)[^\w\n]*([A-Z0-9]{10})\b", text, re.I)
        if pan_loose:
            pan_num = pan_loose.group(1).upper()
            extracted["doc_number"] = {"type": "PAN", "number": pan_num}
            w_matches = extract_words_matching_text(words, pan_num)
            extracted["field_confidences"]["doc_number"] = calculate_field_confidence(w_matches, 0.85, 0.8)

    # 2. Date of Birth
    dob_m = re.search(r"(?:Date\s*of\s*Birth|DOB)\s*[:\-]?\s*([0-9\/\-\.]+)", text, re.I)
    if dob_m:
        iso_dob = parse_date_to_iso(dob_m.group(1))
        if iso_dob:
            extracted["dob"] = iso_dob
            w_matches = extract_words_matching_text(words, dob_m.group(1))
            extracted["field_confidences"]["dob"] = calculate_field_confidence(w_matches, 1.0, 1.0)
    else:
        m_date = re.search(r"\b(\d{2}[-/.]\d{2}[-/.]\d{4})\b", text)
        if m_date:
            iso_dob = parse_date_to_iso(m_date.group(1))
            if iso_dob:
                extracted["dob"] = iso_dob
                w_matches = extract_words_matching_text(words, m_date.group(1))
                extracted["field_confidences"]["dob"] = calculate_field_confidence(w_matches, 0.7, 1.0)

    # 3. Father's Name
    father_m = re.search(r"(?:Father['’]?s?\s*Name)\s*[:\-]?\s*([A-Za-z\s]{3,40})", text, re.I)
    if father_m:
        cand_father = clean_extracted_name(father_m.group(1))
        if cand_father and not any(w in cand_father.lower().split() for w in PAN_STOPWORDS):
            extracted["father_name"] = cand_father
            w_matches = extract_words_matching_text(words, cand_father)
            extracted["field_confidences"]["father_name"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    # 4. Name
    name_m = re.search(r"(?:Name)\s*[:\-]?\s*([A-Za-z\s]{3,40})", text, re.I)
    if name_m:
        cand_name = clean_extracted_name(name_m.group(1))
        if cand_name and not any(w in cand_name.lower().split() for w in PAN_STOPWORDS):
            extracted["name"] = cand_name
            w_matches = extract_words_matching_text(words, cand_name)
            extracted["field_confidences"]["name"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    # Spatial fallback for name: line between header/Permanent Account Number and Father's Name
    if not extracted["name"] and lines:
        for idx, line in enumerate(lines):
            lt = line.get("text", "").lower()
            if "father" in lt:
                if idx > 0:
                    cand = clean_extracted_name(lines[idx - 1].get("text", ""))
                    if cand and len(cand.split()) >= 2 and not any(w in cand.lower().split() for w in PAN_STOPWORDS):
                        extracted["name"] = cand
                        extracted["field_confidences"]["name"] = calculate_field_confidence(lines[idx - 1].get("words", []), 0.85, 0.9)
                        break

    # Resolve labels by line: \s in the legacy patterns could consume a parent
    # name or the next heading. Holder labels must never match Father's Name.
    from document_fields import person, strict_date
    label_patterns = {
        "name": r"(?:name|नाम)",
        "father_name": r"(?:father['’]?s?\s*name|पिता\s*का\s*नाम)",
        "dob": r"(?:date\s*of\s*birth|d\.?o\.?b\.?|जन्म\s*(?:तिथि|तारीख))",
    }
    rows = [line.strip() for line in text.splitlines() if line.strip()]
    all_labels = "|".join(label_patterns.values())
    for field, pattern in label_patterns.items():
        candidates = []
        for idx, row in enumerate(rows):
            match = re.match(r"^(?:" + pattern + r")\s*[:：/\-]?\s*(.*)$", row, re.I)
            if not match:
                continue
            value = match.group(1).strip()
            # Bilingual name labels can precede a value on the following line.
            value = re.sub(r"^(?:नाम|Name)\s*[:：/]?\s*", "", value, flags=re.I)
            if not value and idx + 1 < len(rows):
                value = rows[idx + 1]
            boundary = re.search(r"(?:" + all_labels + r")\s*[:：]", value, re.I)
            if boundary:
                value = value[:boundary.start()].strip()
            parsed_value = strict_date(value) if field == "dob" else person(value)
            if parsed_value and not any(w in parsed_value.lower().split() for w in PAN_STOPWORDS):
                candidates.append(parsed_value)
        unique = set(candidates)
        if unique:
            extracted[field] = candidates[0] if len(unique) == 1 else None
            matches = extract_words_matching_text(words, candidates[0])
            extracted["field_confidences"][field] = calculate_field_confidence(matches, 1., 1.) if len(unique) == 1 else 0.
    if extracted.get("name") == extracted.get("father_name"):
        extracted["name"] = None
        extracted["field_confidences"]["name"] = 0.
    return extracted
