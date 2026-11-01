"""
Aadhaar Card Parser.
Uses spatial anchors (UIDAI header, DOB, Gender, Address, Enrollment) to extract identity fields.
"""

import re
from .base import (
    calculate_field_confidence,
    parse_date_to_iso,
    clean_extracted_name,
    extract_words_matching_text,
    validate_person_name,
    extract_clean_address,
)

AADHAAR_STOPWORDS = {
    "government", "india", "unique", "identification", "authority", "uidai",
    "enrolment", "enrollment", "male", "female", "transgender", "help", "1947",
    "mera", "aadhaar", "pehchan", "vid", "download", "date"
}

def parse_aadhaar(ocr_data, chosen_option=None):
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
        "gender": None,
        "field_confidences": {},
        "needs_review": {},
        "doc_meta": {"detectedType": "Aadhaar Card"},
    }

    # 1. Document Number (12 digits, format 4 4 4 or contiguous)
    num_m = re.search(r"\b([2-9]\d{3}\s\d{4}\s\d{4})\b", text)
    if not num_m:
        num_m = re.search(r"\b([2-9]\d{11})\b", text)
    if num_m:
        raw_num = num_m.group(1)
        formatted_num = raw_num if " " in raw_num else f"{raw_num[:4]} {raw_num[4:8]} {raw_num[8:]}"
        extracted["doc_number"] = {"type": "Aadhaar", "number": formatted_num}
        w_matches = extract_words_matching_text(words, raw_num)
        extracted["field_confidences"]["doc_number"] = calculate_field_confidence(w_matches, 1.0, 1.0)
        extracted["needs_review"]["doc_number"] = False
    else:
        extracted["needs_review"]["doc_number"] = True

    # 2. DOB / Year of Birth
    dob_m = re.search(r"(?:DOB|Date\s*of\s*Birth|Year\s*of\s*Birth|YOB)\s*[:\-]?\s*([0-9/\-\.]+)", text, re.I)
    if dob_m:
        iso_dob = parse_date_to_iso(dob_m.group(1))
        if iso_dob:
            extracted["dob"] = iso_dob
            w_matches = extract_words_matching_text(words, dob_m.group(1))
            extracted["field_confidences"]["dob"] = calculate_field_confidence(w_matches, 1.0, 1.0)
            extracted["needs_review"]["dob"] = False
    else:
        m_date = re.search(r"\b(\d{2}[-/.]\d{2}[-/.]\d{4})\b", text)
        if m_date:
            iso_dob = parse_date_to_iso(m_date.group(1))
            if iso_dob:
                extracted["dob"] = iso_dob
                w_matches = extract_words_matching_text(words, m_date.group(1))
                extracted["field_confidences"]["dob"] = calculate_field_confidence(w_matches, 0.7, 1.0)
                extracted["needs_review"]["dob"] = False

    if not extracted.get("dob"):
        extracted["needs_review"]["dob"] = True

    # 3. Name (Look for explicit 'Name:' or line immediately above DOB/Gender)
    name_m = re.search(r"(?:Name)\s*[:\-]?[^\S\r\n]*([^\r\n|;]+)", text, re.I)
    if name_m:
        cand = validate_person_name(name_m.group(1))
        if cand and not any(w in cand.lower().split() for w in AADHAAR_STOPWORDS):
            extracted["name"] = cand
            w_matches = extract_words_matching_text(words, cand)
            extracted["field_confidences"]["name"] = calculate_field_confidence(w_matches, 1.0, 1.0)
            extracted["needs_review"]["name"] = False

    if not extracted["name"] and lines:
        for idx, line in enumerate(lines):
            lt = line.get("text", "").lower()
            if any(k in lt for k in ["dob", "year of birth", "yob"]):
                if idx > 0:
                    cand_line = lines[idx - 1].get("text", "").strip()
                    cand = validate_person_name(cand_line)
                    if cand and not any(w in cand.lower().split() for w in AADHAAR_STOPWORDS):
                        extracted["name"] = cand
                        w_matches = lines[idx - 1].get("words", [])
                        extracted["field_confidences"]["name"] = calculate_field_confidence(w_matches, 0.85, 0.9)
                        extracted["needs_review"]["name"] = False
                        break

    if not extracted.get("name"):
        extracted["needs_review"]["name"] = True

    # 4. Gender
    gen_m = re.search(r"\b(Male|Female|Transgender)\b", text, re.I)
    if gen_m:
        extracted["gender"] = gen_m.group(1).capitalize()
        extracted["doc_meta"]["gender"] = extracted["gender"]

    # 5. Address (Hardened extraction: anchor up to PIN code, notice text dropped)
    clean_addr, addr_conf, addr_rev = extract_clean_address(lines, text=text, max_lines=6)
    if clean_addr:
        extracted["address"] = clean_addr
        extracted["field_confidences"]["address"] = addr_conf
        extracted["needs_review"]["address"] = addr_rev
    else:
        extracted["needs_review"]["address"] = True

    return extracted