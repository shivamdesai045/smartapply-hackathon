"""Shared persistence boundary for OCR and user-corrected fields. No PII logging."""
import json
import re

FIELD_NAMES = frozenset("name father_name guardian_name mother_name spouse_name dob gender place_of_birth address pincode mobile_number doc_number issue_date expiry_date issuing_authority document_type exam_level exam_year board roll_number seat_number certificate_number unique_id index_number school_name vehicle_classes".split())
LEGACY = {"name": "doc_name", "dob": "doc_dob", "address": "doc_address", "doc_number": "doc_number"}


def json_object(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return {}
    return value if isinstance(value, dict) else {}


def sanitize(value):
    """Mask all 12 digit Aadhaar-shaped values including nested metadata."""
    if isinstance(value, dict):
        return {k: v if k == "_identity_ciphertext" else "" if k in {"raw_text", "rawText", "raw_ocr"} else sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        if __import__('os').getenv('IDENTITY_ENCRYPTION_KEY'):
            value=re.sub(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b',lambda m:'XXXXXX'+m[0][-4:].upper(),value,flags=re.I)
        return re.sub(r"(?<!\d)(\d{4})[ -]?(\d{4})[ -]?(\d{4})(?!\d)", lambda m: "XXXX XXXX " + m[3], value)
    return value


def merge_fields(existing, incoming, verified=False):
    fields = dict(json_object(existing))
    for name, entry in json_object(incoming).items():
        if name not in FIELD_NAMES:
            continue
        previous = fields.get(name, {})
        if previous.get("user_verified") and not verified:
            continue
        item = dict(entry) if isinstance(entry, dict) else {"value": entry}
        value = item.get("value")
        if value is not None and not isinstance(value, (str, int, float)):
            # Legacy document numbers may be {type, number}.
            if name == "doc_number" and isinstance(value, dict):
                value = value.get("number")
            else:
                raise ValueError("Field values must be text or null")
        if value is not None and len(str(value)) > 4000:
            raise ValueError("Field value exceeds 4000 characters")
        confidence = 1.0 if verified else max(0.0, min(1.0, float(item.get("confidence", 0) or 0)))
        fields[name] = {"value": sanitize(value), "confidence": confidence,
                        "needs_review": False if verified else bool(item.get("needs_review", confidence < .8)),
                        "user_verified": bool(verified)}
    return sanitize(fields)


def flags(fields):
    populated = [e for e in fields.values() if e.get("value") not in (None, "")]
    return (any(e.get("needs_review", True) for e in fields.values()) if fields else True,
            bool(populated) and all(e.get("user_verified", False) for e in populated))
