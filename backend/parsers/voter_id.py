"""
Voter ID Card (EPIC) Parser.
Uses spatial anchors (Election Commission of India, EPIC No, Elector Name, Father's Name, DOB, Address).
"""

import re
from .base import (
    calculate_field_confidence,
    parse_date_to_iso,
    clean_extracted_name,
    extract_words_matching_text,
)

VOTER_STOPWORDS = {
    "election", "commission", "india", "elector", "photo", "identity", "card",
    "epic", "gender", "male", "female", "transgender", "assembly", "constituency"
}

def parse_voter_id(ocr_data, chosen_option=None):
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
        "doc_meta": {"detectedType": "Voter ID"},
    }

    # 1. EPIC Number (3 letters + 7 digits)
    epic_m = re.search(r"(?:EPIC\s*No[.\s:]*)\s*([A-Za-z]{3}[0-9]{7})\b", text, re.I)
    if not epic_m:
        epic_m = re.search(r"\b([A-Z]{3}[0-9]{7})\b", text.upper())
    if epic_m:
        epic_num = epic_m.group(1).upper()
        extracted["doc_number"] = {"type": "Voter ID", "number": epic_num}
        w_matches = extract_words_matching_text(words, epic_num)
        extracted["field_confidences"]["doc_number"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    # 2. Name
    name_m = re.search(r"(?:Elector\s*Name|Elector['’]?s?\s*Name|Name)\s*[:\-]?\s*([A-Za-z\s]{3,40})", text, re.I)
    if name_m:
        cand_name = clean_extracted_name(name_m.group(1))
        if cand_name and not any(w in cand_name.lower().split() for w in VOTER_STOPWORDS):
            extracted["name"] = cand_name
            w_matches = extract_words_matching_text(words, cand_name)
            extracted["field_confidences"]["name"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    # 3. Father's / Husband's Name
    rel_m = re.search(r"(?:Father['’]?s?\s*Name|Husband['’]?s?\s*Name|Relation['’]?s?\s*Name)\s*[:\-]?\s*([A-Za-z\s]{3,40})", text, re.I)
    if rel_m:
        cand_rel = clean_extracted_name(rel_m.group(1))
        if cand_rel and not any(w in cand_rel.lower().split() for w in VOTER_STOPWORDS):
            extracted["father_name"] = cand_rel
            w_matches = extract_words_matching_text(words, cand_rel)
            extracted["field_confidences"]["father_name"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    # 4. Date of Birth / Age
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
