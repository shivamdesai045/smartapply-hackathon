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
    pan_m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text.upper())
    if pan_m:
        pan_num = pan_m.group(1)
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

    return extracted
