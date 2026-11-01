"""
Sahayak Per-Type Document Parsers Package with Slot-Aware Priority & ML Ensemble.
Routes OCR data to specialized spatial parsers based on expected slot document type first.
Warns if classifier detects a conflicting document type.
Computes field_confidences and needs_review per field.
"""

import re
from .aadhaar import parse_aadhaar
from .pan import parse_pan
from .marksheet_10th import parse_marksheet
from .passport import parse_passport
from .voter_id import parse_voter_id
from .driving_licence import parse_dl
from .fallback import parse_fallback
from .ml_generalizer import predict_field_candidates
from .base import validate_person_name, extract_clean_address

SLOT_MAP = {
    "passport": "passport",
    "pan": "pan",
    "aadhaar": "aadhaar",
    "10th": "marksheet",
    "marksheet": "marksheet",
    "passing certificate": "marksheet",
    "voter": "voter_id",
    "epic": "voter_id",
    "driving": "driving_licence",
}

def get_parser_key_from_slot(chosen_option):
    if not chosen_option:
        return None
    s = str(chosen_option).lower()
    for k, p in SLOT_MAP.items():
        if k in s:
            return p
    return None

def detect_parser_type(text, chosen_option=None):
    """Detects target parser key from text keywords."""
    combined = f"{chosen_option or ''} {text or ''}".lower()

    if any(k in combined for k in ["passport", "republic of india"]):
        return "passport"
    if any(k in combined for k in ["pan card", "income tax department", "permanent account number"]):
        return "pan"
    if any(k in combined for k in ["aadhaar", "uidai", "unique identification"]):
        return "aadhaar"
    if any(k in combined for k in ["10th", "marksheet", "secondary school", "cbse", "icse", "ssc", "certify that"]):
        return "marksheet"
    if any(k in combined for k in ["voter", "election commission", "epic"]):
        return "voter_id"
    if any(k in combined for k in ["driving", "licence", "license", "transport department"]):
        return "driving_licence"

    return "fallback"

def parse_document(ocr_data, chosen_option=None):
    """
    Main entry point for per-type extraction:
    1. Slot-aware: runs the expected slot document type's parser FIRST.
    2. Warns when classifier/detector suggests the file is a different document type.
    3. Ensembles with ML Generalizer when specialized parser is unconfident (< 0.70) or returns None.
    4. Computes per-field field_confidences and needs_review flags.
    """
    text = ocr_data.get("text", "")
    slot_p_type = get_parser_key_from_slot(chosen_option)
    text_detected_type = detect_parser_type(text, None)

    # 1. Slot-aware priority: Expected slot parser runs FIRST!
    p_type = slot_p_type if slot_p_type else text_detected_type

    if p_type == "passport":
        result = parse_passport(ocr_data, chosen_option)
    elif p_type == "pan":
        result = parse_pan(ocr_data, chosen_option)
    elif p_type == "aadhaar":
        result = parse_aadhaar(ocr_data, chosen_option)
    elif p_type == "marksheet":
        result = parse_marksheet(ocr_data, chosen_option)
    elif p_type == "voter_id":
        result = parse_voter_id(ocr_data, chosen_option)
    elif p_type == "driving_licence":
        result = parse_dl(ocr_data, chosen_option)
    else:
        result = parse_fallback(ocr_data, chosen_option)

    # Warning if content strongly indicates a different document type
    display_names = {
        "pan": "PAN Card",
        "aadhaar": "Aadhaar Card",
        "marksheet": "10th Marksheet",
        "passport": "Passport",
        "voter_id": "Voter ID Card",
        "driving_licence": "Driving Licence",
    }
    if slot_p_type and text_detected_type != "fallback" and text_detected_type != slot_p_type:
        det_disp = display_names.get(text_detected_type, text_detected_type.replace('_', ' ').title())
        result.setdefault("doc_meta", {})["documentTypeWarning"] = (
            f"Uploaded document appears to be a {det_disp} rather than expected {chosen_option}."
        )

    field_confs = result.setdefault("field_confidences", {})
    needs_review = result.setdefault("needs_review", {})

    # Ensemble with ML Generalizer for missing or low-confidence fields
    ml_candidates = predict_field_candidates(ocr_data)
    if ml_candidates:
        for field, cand in ml_candidates.items():
            current_val = result.get(field)
            current_conf = field_confs.get(field, 0.0)

            if not current_val or current_conf < 0.70:
                cand_val = cand["value"]
                cand_conf = cand["confidence"]

                is_valid = True
                if field == "dob" and not re.search(r"\b(19\d{2}|20\d{2})\b", str(cand_val)):
                    is_valid = False
                elif field in ("name", "father_name", "mother_name"):
                    if not validate_person_name(cand_val):
                        is_valid = False
                elif field == "address" and len(str(cand_val).split()) < 3:
                    is_valid = False

                if is_valid and (not current_val or cand_conf > current_conf):
                    result[field] = cand_val
                    field_confs[field] = cand_conf
                    needs_review[field] = False
                    result.setdefault("doc_meta", {})["ml_assisted"] = True

    # Fallback to generic regex for any remaining missing fields to guarantee no regression
    fallback_res = parse_fallback(ocr_data, chosen_option)
    for field in ["name", "dob", "address", "doc_number", "father_name", "mother_name"]:
        if not result.get(field) and fallback_res.get(field):
            f_val = fallback_res[field]
            accept = True
            if field in ("name", "father_name", "mother_name"):
                if not validate_person_name(f_val):
                    accept = False
            if accept:
                result[field] = f_val
                if field in fallback_res.get("field_confidences", {}):
                    field_confs[field] = fallback_res["field_confidences"][field]

    # Enforce needs_review per field
    for field in ["name", "dob", "address", "doc_number"]:
        val = result.get(field)
        conf = field_confs.get(field, 0.0)
        if not val or conf < 0.70 or needs_review.get(field) is True:
            needs_review[field] = True
        else:
            needs_review[field] = False

    result["field_confidences"] = field_confs
    result["needs_review"] = needs_review
    result["parser_used"] = p_type
    return result
