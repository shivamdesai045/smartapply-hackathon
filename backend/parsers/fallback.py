"""
Fallback Generic Regex Parser.
Used when the document type is unknown or confidence from specialized parsers is low.
"""

import ocr_extract
from .base import calculate_field_confidence

def parse_fallback(ocr_data, chosen_option=None):
    text = ocr_data.get("text", "")
    words = ocr_data.get("words", [])

    name = ocr_extract.guess_name(text, chosen_option=chosen_option)
    dob = ocr_extract.guess_dob(text)
    address = ocr_extract.guess_address(text)
    doc_number = ocr_extract.guess_doc_number(text)
    father_name = ocr_extract.guess_parent_name(text, "father")
    mother_name = ocr_extract.guess_parent_name(text, "mother")

    confidences = {}
    if name:
        confidences["name"] = calculate_field_confidence(words, 0.6, 0.8)
    if dob:
        confidences["dob"] = calculate_field_confidence(words, 0.6, 0.8)
    if address:
        confidences["address"] = calculate_field_confidence(words, 0.6, 0.8)
    if doc_number:
        confidences["doc_number"] = calculate_field_confidence(words, 0.6, 0.8)
    if father_name:
        confidences["father_name"] = calculate_field_confidence(words, 0.6, 0.8)
    if mother_name:
        confidences["mother_name"] = calculate_field_confidence(words, 0.6, 0.8)

    return {
        "name": name,
        "dob": dob,
        "address": address,
        "doc_number": doc_number,
        "father_name": father_name,
        "mother_name": mother_name,
        "field_confidences": confidences,
        "doc_meta": {},
    }
