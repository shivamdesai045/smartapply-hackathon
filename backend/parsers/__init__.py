"""
Sahayak Per-Type Document Parsers Package.
Routes OCR data to specialized spatial parsers based on chosen option and detected document type.
Falls back to generic regex parser when document type is unknown or confidence is low.
"""

from .aadhaar import parse_aadhaar
from .pan import parse_pan
from .marksheet_10th import parse_marksheet
from .passport import parse_passport
from .voter_id import parse_voter_id
from .driving_licence import parse_dl
from .fallback import parse_fallback

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
    Executes specialized parser with spatial cues; falls back to generic regex for missing fields.
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

    # Fallback to generic regex for any missing fields to guarantee no regression
    fallback_res = parse_fallback(ocr_data, chosen_option)
    for field in ["name", "dob", "address", "doc_number", "father_name", "mother_name"]:
        if not result.get(field) and fallback_res.get(field):
            result[field] = fallback_res[field]
            if "field_confidences" in result and "field_confidences" in fallback_res:
                if field in fallback_res["field_confidences"]:
                    result["field_confidences"][field] = fallback_res["field_confidences"][field]

    result["parser_used"] = p_type
    return result
