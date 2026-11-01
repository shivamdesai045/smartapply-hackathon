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
    validate_person_name,
)

CERTIFY_ANCHOR_REGEX = re.compile(
    r"(?:this\s+is\s+to\s+)?certif(?:y|ied)\s+that|"
    r"प्रमाणित\s*(?:किया\s*जाता\s*है|करण्यात\s*येते)\s*कि|"
    r"प्रमाणित\s*करण्यात\s*येते\s*की",
    re.I
)

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
        "needs_review": {},
        "doc_meta": {"detectedType": "10th Marksheet"},
    }

    lines_list = []
    if lines:
        for l in lines:
            if isinstance(l, dict):
                lines_list.append(l.get("text", "").strip())
            elif isinstance(l, str):
                lines_list.append(l.strip())
    elif text:
        lines_list = [l.strip() for l in text.splitlines() if l.strip()]

    # 1. Candidate Name
    # Strategy A: 'certify that' anchor (handle same-line and next-line cases)
    if lines_list:
        for idx, line_str in enumerate(lines_list):
            cert_m = CERTIFY_ANCHOR_REGEX.search(line_str)
            if cert_m:
                # Same-line case
                after_text = line_str[cert_m.end():].strip()
                after_text = re.sub(r"^[\s:\-,./]+", "", after_text)
                cand = validate_person_name(after_text)
                if cand:
                    extracted["name"] = cand
                    w_matches = extract_words_matching_text(words, cand)
                    extracted["field_confidences"]["name"] = calculate_field_confidence(w_matches, 1.0, 1.0)
                    extracted["needs_review"]["name"] = False
                    break

                # Next-line case: inspect subsequent lines
                for next_idx in range(idx + 1, min(len(lines_list), idx + 3)):
                    next_str = lines_list[next_idx]
                    cand_next = validate_person_name(next_str)
                    if cand_next:
                        extracted["name"] = cand_next
                        w_matches = extract_words_matching_text(words, cand_next)
                        extracted["field_confidences"]["name"] = calculate_field_confidence(w_matches, 0.95, 1.0)
                        extracted["needs_review"]["name"] = False
                        break
                if extracted["name"]:
                    break

    # Strategy B: Standard Candidate Name label
    if not extracted["name"]:
        cand_m = re.search(
            r"(?:Candidate\s*Name|Student\s*Name|Name\s*of\s*Candidate|Candidate['’]?s?\s*Name)\s*[:\-]?\s*([^\r\n|;]+)",
            text, re.I
        )
        if cand_m:
            cand_name = validate_person_name(cand_m.group(1))
            if cand_name:
                extracted["name"] = cand_name
                w_matches = extract_words_matching_text(words, cand_name)
                extracted["field_confidences"]["name"] = calculate_field_confidence(w_matches, 1.0, 1.0)
                extracted["needs_review"]["name"] = False

    # Strategy C: Spatial search for label 'Name' (non-header)
    if not extracted["name"]:
        cand_m_loose = re.search(r"(?:Name)\s*[:\-]\s*([^\r\n|;]+)", text, re.I)
        if cand_m_loose:
            cand_name = validate_person_name(cand_m_loose.group(1))
            if cand_name:
                extracted["name"] = cand_name
                w_matches = extract_words_matching_text(words, cand_name)
                extracted["field_confidences"]["name"] = calculate_field_confidence(w_matches, 0.85, 1.0)
                extracted["needs_review"]["name"] = False

    if not extracted.get("name"):
        extracted["needs_review"]["name"] = True

    # 2. Mother's Name
    mother_m = re.search(r"(?:Mother['’]?s?\s*Name|Mother)\s*[:\-]?\s*([^\r\n|;]+)", text, re.I)
    if mother_m:
        cand_mother = validate_person_name(mother_m.group(1))
        if cand_mother:
            extracted["mother_name"] = cand_mother
            w_matches = extract_words_matching_text(words, cand_mother)
            extracted["field_confidences"]["mother_name"] = calculate_field_confidence(w_matches, 1.0, 1.0)
            extracted["needs_review"]["mother_name"] = False
        else:
            extracted["needs_review"]["mother_name"] = True
    else:
        extracted["needs_review"]["mother_name"] = True

    # 3. Father's Name
    father_m = re.search(r"(?:Father['’]?s?\s*Name|Father|Father['’]?s?\s*\/\s*Guardian)\s*[:\-]?\s*([^\r\n|;]+)", text, re.I)
    if father_m:
        cand_father = validate_person_name(father_m.group(1))
        if cand_father:
            extracted["father_name"] = cand_father
            w_matches = extract_words_matching_text(words, cand_father)
            extracted["field_confidences"]["father_name"] = calculate_field_confidence(w_matches, 1.0, 1.0)
            extracted["needs_review"]["father_name"] = False
        else:
            extracted["needs_review"]["father_name"] = True
    else:
        extracted["needs_review"]["father_name"] = True

    # 4. Date of Birth
    dob_m = re.search(r"(?:Date\s*of\s*Birth|DOB)\s*[:\-]?\s*([0-9/\-\.]+)", text, re.I)
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

    # 5. Certificate No / Serial No / Roll No
    cert_m = re.search(r"(?:Certificate\s*No|Serial\s*No)\s*[:\-]?\s*([A-Za-z0-9\-]+)", text, re.I)
    if not cert_m:
        cert_m = re.search(r"(?:Roll\s*No)\s*[:\-]?\s*([A-Za-z0-9\-]+)", text, re.I)

    if cert_m:
        cert_num = cert_m.group(1).strip()
        extracted["doc_number"] = {"type": "Certificate No", "number": cert_num}
        w_matches = extract_words_matching_text(words, cert_num)
        extracted["field_confidences"]["doc_number"] = calculate_field_confidence(w_matches, 1.0, 1.0)
        extracted["needs_review"]["doc_number"] = False
    else:
        extracted["needs_review"]["doc_number"] = True

    return extracted
