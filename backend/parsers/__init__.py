"""
Sahayak Per-Type Document Parsers Package with ML Generalizer Ensemble.
Routes OCR data to specialized spatial parsers based on chosen option and detected document type.
Ensembles with ML Line/Box Generalizer when per-type parsers are unconfident (< 0.70) or return None.
Falls back to generic regex parser when document type is unknown or confidence is low.
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

def detect_parser_type(text, chosen_option=None):
    """Detects target parser key from chosen option or text keywords."""
    combined = f"{chosen_option or ''} {text or ''}".lower()

    if any(k in combined for k in ["passport", "republic of india"]):
        return "passport"
    if any(k in combined for k in ["pan card", "income tax department", "permanent account number"]):
        return "pan"
    if any(k in combined for k in ["aadhaar", "uidai", "unique identification"]):
        return "aadhaar"
    if any(k in combined for k in ["10th", "marksheet", "secondary school", "cbse", "icse", "ssc"]):
        return "marksheet"
    if any(k in combined for k in ["voter", "election commission", "epic"]):
        return "voter_id"
    if any(k in combined for k in ["driving", "licence", "license", "transport department"]):
        return "driving_licence"

    return "fallback"

def parse_document(ocr_data, chosen_option=None):
    """
    Main entry point for per-type extraction.
    1. Executes specialized parser with spatial cues.
    2. Ensembles with ML Generalizer when specialized parser is unconfident (< 0.70) or returns None.
    3. Falls back to generic regex for any missing fields to guarantee no regression.
    """
    text = ocr_data.get("text", "")
    p_type = detect_parser_type(text, chosen_option)

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

    field_confs = result.setdefault("field_confidences", {})

    # Ensemble with ML Generalizer:
    # When specialized parser returns None or is unconfident (< 0.70),
    # query ML model candidates, validate formats, and pick highest-confidence valid candidate.
    ml_candidates = predict_field_candidates(ocr_data)
    if ml_candidates:
        for field, cand in ml_candidates.items():
            current_val = result.get(field)
            current_conf = field_confs.get(field, 0.0)

            if not current_val or current_conf < 0.70:
                cand_val = cand["value"]
                cand_conf = cand["confidence"]

                # Validate candidate with format checks
                is_valid = True
                if field == "dob" and not re.search(r"\b(19\d{2}|20\d{2})\b", str(cand_val)):
                    is_valid = False
                elif field in ("name", "father_name", "mother_name") and len(str(cand_val).split()) < 1:
                    is_valid = False
                elif field == "address" and len(str(cand_val).split()) < 2:
                    is_valid = False

                if is_valid and (not current_val or cand_conf > current_conf):
                    result[field] = cand_val
                    field_confs[field] = cand_conf
                    result.setdefault("doc_meta", {})["ml_assisted"] = True

    # Fallback to generic regex for any remaining missing fields to guarantee no regression
    fallback_res = parse_fallback(ocr_data, chosen_option)
    for field in ["name", "dob", "address", "doc_number", "father_name", "mother_name"]:
        if not result.get(field) and fallback_res.get(field):
            result[field] = fallback_res[field]
            if field in fallback_res.get("field_confidences", {}):
                field_confs[field] = fallback_res["field_confidences"][field]

    result["parser_used"] = p_type
    return result
