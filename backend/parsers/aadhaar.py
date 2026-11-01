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

    # 2. DOB / Year of Birth
    dob_m = re.search(r"(?:DOB|Date\s*of\s*Birth|Year\s*of\s*Birth|YOB)\s*[:\-]?\s*([0-9\/\-\.]+)", text, re.I)
    if dob_m:
        iso_dob = parse_date_to_iso(dob_m.group(1))
        if iso_dob:
            extracted["dob"] = iso_dob
            w_matches = extract_words_matching_text(words, dob_m.group(1))
            extracted["field_confidences"]["dob"] = calculate_field_confidence(w_matches, 1.0, 1.0)
    else:
        # Fallback date search
        m_date = re.search(r"\b(\d{2}[-/.]\d{2}[-/.]\d{4})\b", text)
        if m_date:
            iso_dob = parse_date_to_iso(m_date.group(1))
            if iso_dob:
                extracted["dob"] = iso_dob
                w_matches = extract_words_matching_text(words, m_date.group(1))
                extracted["field_confidences"]["dob"] = calculate_field_confidence(w_matches, 0.7, 1.0)

    # 3. Name (Look for explicit 'Name:' or line immediately above DOB/Gender)
    name_m = re.search(r"(?:Name)\s*[:\-]?\s*([A-Za-z\s]{3,40})", text, re.I)
    if name_m:
        cand = clean_extracted_name(name_m.group(1))
        if cand and not any(w in cand.lower().split() for w in AADHAAR_STOPWORDS):
            extracted["name"] = cand
            w_matches = extract_words_matching_text(words, cand)
            extracted["field_confidences"]["name"] = calculate_field_confidence(w_matches, 1.0, 1.0)

    if not extracted["name"] and lines:
        # Spatial search: line directly above DOB line
        for idx, line in enumerate(lines):
            lt = line.get("text", "").lower()
            if any(k in lt for k in ["dob", "year of birth", "yob"]):
                if idx > 0:
                    cand_line = lines[idx - 1].get("text", "").strip()
                    cand = clean_extracted_name(cand_line)
                    if cand and len(cand.split()) >= 2 and not any(w in cand.lower().split() for w in AADHAAR_STOPWORDS):
                        extracted["name"] = cand
                        w_matches = lines[idx - 1].get("words", [])
                        extracted["field_confidences"]["name"] = calculate_field_confidence(w_matches, 0.85, 0.9)
                        break

    # 4. Gender
    gen_m = re.search(r"\b(Male|Female|Transgender)\b", text, re.I)
    if gen_m:
        extracted["gender"] = gen_m.group(1).capitalize()
        extracted["doc_meta"]["gender"] = extracted["gender"]

    # 5. Address (Spatial: lines following 'Address:' up to PIN code)
    addr_m = re.search(r"(?:Address\s*[:\-]?\s*)(.+?)(?:[1-9]\d{5})", text, re.I | re.DOTALL)
    if addr_m:
        full_addr_raw = addr_m.group(0).strip()
        # Clean prefix
        clean_addr = re.sub(r"^Address\s*[:\-]?\s*", "", full_addr_raw, flags=re.I).strip()
        clean_addr = re.sub(r"\s+", " ", clean_addr)
        if len(clean_addr.split()) >= 3:
            extracted["address"] = clean_addr
            w_matches = extract_words_matching_text(words, clean_addr)
            extracted["field_confidences"]["address"] = calculate_field_confidence(w_matches, 1.0, 1.0)
    else:
        # Check if line with Address exists
        for idx, line in enumerate(lines):
            if "address" in line.get("text", "").lower():
                collected = [line.get("text", "")]
                for next_line in lines[idx + 1:idx + 4]:
                    collected.append(next_line.get("text", ""))
                    if re.search(r"\b[1-9]\d{5}\b", next_line.get("text", "")):
                        break
                comb = " ".join(collected)
                comb_clean = re.sub(r"^Address\s*[:\-]?\s*", "", comb, flags=re.I).strip()
                if len(comb_clean.split()) >= 3:
                    extracted["address"] = re.sub(r"\s+", " ", comb_clean)
                    extracted["field_confidences"]["address"] = calculate_field_confidence(line.get("words", []), 0.85, 0.9)
                    break

    return extracted
