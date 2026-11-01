"""
Passport Parser.
Specialized for Indian Passports:
- Combines 'Given Name(s)' and 'Surname' into full applicant name.
- Extracts Passport Number, DOB, Father / Guardian Name, Mother Name, and Address.
"""

import re
from .base import (
    calculate_field_confidence,
    parse_date_to_iso,
    clean_extracted_name,
    extract_words_matching_text,
)

PASSPORT_STOPWORDS = {
    "passport", "republic", "india", "given", "surname", "nationality",
    "sex", "indian", "place", "birth", "issue", "expiry", "country", "code"
}

def parse_passport(ocr_data, chosen_option=None):
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
        "doc_meta": {"detectedType": "Passport"},
    }

    # 1. Document Number (1 letter + 7 digits, e.g. A1234567 or Z1234567)
    pass_m = re.search(r"(?:Passport\s*No[.\s:]*)\s*([A-Za-z][0-9]{7})\b", text, re.I)
    if not pass_m:
        pass_m = re.search(r"\b([A-PR-WYZ][0-9]{7})\b", text.upper())
    if not pass_m:
        pass_m = re.search(r"\b(Z[0-9]{7})\b", text.upper())

    if pass_m:
        pass_num = pass_m.group(1).upper()
        extracted["doc_number"] = {"type": "Passport", "number": pass_num}
        w_matches = extract_words_matching_text(words, pass_num)
        extracted["field_confidences"]["doc_number"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    # 2. Name Extraction (Given Name(s) + Surname split line handling)
    given_m = re.search(r"(?:Given\s*Name(?:\(s\))?)\s*[:\-]?\s*([^\n\r|;]+)", text, re.I)
    surname_m = re.search(r"(?:Surname)\s*[:\-]?\s*([^\n\r|;]+)", text, re.I)

    if given_m and surname_m:
        given_clean = clean_extracted_name(given_m.group(1))
        surname_clean = clean_extracted_name(surname_m.group(1))
        if given_clean and surname_clean:
            full_name = f"{given_clean} {surname_clean}"
            extracted["name"] = full_name
            w_matches = extract_words_matching_text(words, full_name)
            extracted["field_confidences"]["name"] = calculate_field_confidence(w_matches, 1.0, 1.0)
    elif given_m:
        given_clean = clean_extracted_name(given_m.group(1))
        if given_clean:
            extracted["name"] = given_clean
            w_matches = extract_words_matching_text(words, given_clean)
            extracted["field_confidences"]["name"] = calculate_field_confidence(w_matches, 0.85, 0.9)
    else:
        name_m = re.search(r"(?:Name)\s*[:\-]?\s*([^\n\r|;]+)", text, re.I)
        if name_m:
            cand = clean_extracted_name(name_m.group(1))
            if cand and not any(w in cand.lower().split() for w in PASSPORT_STOPWORDS):
                extracted["name"] = cand
                w_matches = extract_words_matching_text(words, cand)
                extracted["field_confidences"]["name"] = calculate_field_confidence(w_matches, 0.85, 0.9)

    # 3. Date of Birth
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

    # 4. Father / Legal Guardian Name
    father_m = re.search(r"(?:Father\s*\/\s*Legal\s*Guardian|Father['’]?s?\s*Name|Father)\s*[:\-]?\s*([^\n\r|;]+)", text, re.I)
    if father_m:
        cand_father = clean_extracted_name(father_m.group(1))
        if cand_father and not any(w in cand_father.lower().split() for w in PASSPORT_STOPWORDS):
            extracted["father_name"] = cand_father
            w_matches = extract_words_matching_text(words, cand_father)
            extracted["field_confidences"]["father_name"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    # 5. Mother's Name
    mother_m = re.search(r"(?:Mother['’]?s?\s*Name|Mother)\s*[:\-]?\s*([^\n\r|;]+)", text, re.I)
    if mother_m:
        cand_mother = clean_extracted_name(mother_m.group(1))
        if cand_mother and not any(w in cand_mother.lower().split() for w in PASSPORT_STOPWORDS):
            extracted["mother_name"] = cand_mother
            w_matches = extract_words_matching_text(words, cand_mother)
            extracted["field_confidences"]["mother_name"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    # 6. Address
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
