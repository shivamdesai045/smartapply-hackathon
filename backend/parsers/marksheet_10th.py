"""
10th Marksheet / Passing Certificate Parser.
Uses spatial anchors (Board Header, Candidate Name, Mother's Name, Father's Name, DOB, Roll No, Certificate No).
Rejects marksheet subject names, grade labels, and academic terms from being extracted as names.
"""

import re
from .base import (
    calculate_field_confidence,
    parse_date_to_iso,
    clean_extracted_name,
    extract_words_matching_text,
)

MARKSHEET_EXCLUDED_TOKENS = {
    "hindi", "marathi", "english", "sanskrit", "urdu", "science", "mathematics",
    "maths", "social", "history", "geography", "physics", "chemistry", "biology",
    "fl", "sl", "tl", "first", "second", "third", "language", "sub", "subject",
    "theory", "practical", "internal", "external", "total", "marks", "maximum",
    "minimum", "obtained", "result", "passed", "failed", "distinction", "grade",
    "percentage", "seat", "roll", "centre", "center", "school", "college",
    "board", "cbse", "icse", "ssc", "secondary", "examination", "education",
    "candidate", "student", "mother", "father", "guardian", "date", "birth"
}

def parse_marksheet(ocr_data, chosen_option=None):
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
        "doc_meta": {"detectedType": "10th Marksheet"},
    }

    # 1. Candidate Name
    cand_m = re.search(r"(?:Candidate\s*Name|Student\s*Name|Name\s*of\s*Candidate|Candidate['’]?s?\s*Name|Name)\s*[:\-]?\s*([^\n\r|;]+)", text, re.I)
    if cand_m:
        cand_name = clean_extracted_name(cand_m.group(1))
        if cand_name and not any(w in cand_name.lower().split() for w in MARKSHEET_EXCLUDED_TOKENS):
            extracted["name"] = cand_name
            w_matches = extract_words_matching_text(words, cand_name)
            extracted["field_confidences"]["name"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    # 2. Mother's Name
    mother_m = re.search(r"(?:Mother['’]?s?\s*Name|Mother)\s*[:\-]?\s*([^\n\r|;]+)", text, re.I)
    if mother_m:
        cand_mother = clean_extracted_name(mother_m.group(1))
        if cand_mother and not any(w in cand_mother.lower().split() for w in MARKSHEET_EXCLUDED_TOKENS):
            extracted["mother_name"] = cand_mother
            w_matches = extract_words_matching_text(words, cand_mother)
            extracted["field_confidences"]["mother_name"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    # 3. Father's Name
    father_m = re.search(r"(?:Father['’]?s?\s*Name|Father|Father['’]?s?\s*\/\s*Guardian)\s*[:\-]?\s*([^\n\r|;]+)", text, re.I)
    if father_m:
        cand_father = clean_extracted_name(father_m.group(1))
        if cand_father and not any(w in cand_father.lower().split() for w in MARKSHEET_EXCLUDED_TOKENS):
            extracted["father_name"] = cand_father
            w_matches = extract_words_matching_text(words, cand_father)
            extracted["field_confidences"]["father_name"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    # 4. Date of Birth
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

    # 5. Certificate No / Serial No / Roll No
    cert_m = re.search(r"(?:Certificate\s*No|Serial\s*No)\s*[:\-]?\s*([A-Za-z0-9\-]+)", text, re.I)
    if not cert_m:
        cert_m = re.search(r"(?:Roll\s*No)\s*[:\-]?\s*([A-Za-z0-9\-]+)", text, re.I)

    if cert_m:
        cert_num = cert_m.group(1).strip()
        extracted["doc_number"] = {"type": "Certificate No", "number": cert_num}
        w_matches = extract_words_matching_text(words, cert_num)
        extracted["field_confidences"]["doc_number"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    return extracted
