"""
Driving Licence Parser.
Uses spatial anchors (Driving Licence, Transport Department, Licence No, Name, S/W/D of, DOB, Address).
"""

import re
from .base import (
    calculate_field_confidence,
    parse_date_to_iso,
    clean_extracted_name,
    extract_words_matching_text,
)

DL_STOPWORDS = {
    "union", "india", "driving", "licence", "license", "transport", "department",
    "class", "vehicle", "lmv", "mcwg", "valid", "till", "from", "cov"
}

def parse_dl(ocr_data, chosen_option=None):
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
        "doc_meta": {"detectedType": "Driving Licence"},
    }

    # 1. Licence Number
    dl_m = re.search(r"(?:Licen[sc]e\s*No[.\s:]*|DL\s*No[.\s:]*|DL[\-:\s]+)\s*([A-Za-z0-9\-]{8,20})", text, re.I)
    if not dl_m:
        dl_m = re.search(r"\b([A-Z]{2}[0-9]{2}\s?[0-9]{4,11})\b", text)
    if dl_m:
        dl_num = dl_m.group(1).replace(" ", "")
        extracted["doc_number"] = {"type": "DL", "number": dl_num}
        w_matches = extract_words_matching_text(words, dl_num)
        extracted["field_confidences"]["doc_number"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    # 2. Name
    name_m = re.search(r"(?:Name)\s*[:\-]?\s*([^\n\r|;]+)", text, re.I)
    if name_m:
        cand_name = clean_extracted_name(name_m.group(1))
        if cand_name and not any(w in cand_name.lower().split() for w in DL_STOPWORDS):
            extracted["name"] = cand_name
            w_matches = extract_words_matching_text(words, cand_name)
            extracted["field_confidences"]["name"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    # 3. Father / Relative Name
    rel_m = re.search(r"(?:Son\s*\/\s*Daughter\s*\/\s*Wife\s*of|S\s*\/\s*W\s*\/\s*D\s*of|Father['’]?s?\s*Name)\s*[:\-]?\s*([^\n\r|;]+)", text, re.I)
    if rel_m:
        cand_rel = clean_extracted_name(rel_m.group(1))
        if cand_rel and not any(w in cand_rel.lower().split() for w in DL_STOPWORDS):
            extracted["father_name"] = cand_rel
            w_matches = extract_words_matching_text(words, cand_rel)
            extracted["field_confidences"]["father_name"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    # 4. Date of Birth
    dob_m = re.search(r"(?:DOB|Date\s*of\s*Birth)\s*[:\-]?\s*([0-9\/\-\.]+)", text, re.I)
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

    # 5. Address
    addr_m = re.search(r"(?:Address\s*[:\-]?\s*)(.+?)(?:[1-9]\d{5})", text, re.I | re.DOTALL)
    if addr_m:
        full_addr_raw = addr_m.group(0).strip()
        clean_addr = re.sub(r"^Address\s*[:\-]?\s*", "", full_addr_raw, flags=re.I).strip()
        clean_addr = re.sub(r"\s+", " ", clean_addr)
        if len(clean_addr.split()) >= 3:
            extracted["address"] = clean_addr
            w_matches = extract_words_matching_text(words, clean_addr)
            extracted["field_confidences"]["address"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    return extracted
