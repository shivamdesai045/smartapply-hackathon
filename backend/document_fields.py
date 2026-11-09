"""Conservative, local-only structured extraction layered over the existing parsers.

Confidence is a heuristic, not a calibrated probability. Missing, conflicting and
invalid candidates require review. Never persist text/boxes through this module.
"""
import re
import unicodedata
from datetime import date, datetime

OCR_VERSION = "5.4-marksheet-fields"
FIELDS = ("name", "father_name", "guardian_name", "mother_name", "spouse_name",
          "dob", "gender", "place_of_birth", "address", "pincode", "mobile_number",
          "doc_number", "issue_date", "expiry_date", "issuing_authority",
          "document_type", "exam_level", "exam_year", "board", "roll_number", "seat_number", "certificate_number", "unique_id", "index_number", "school_name", "vehicle_classes")
LABELS = {
    "name": r"(?:full\s+name|name\s+of\s+(?:child|applicant|candidate|student)|child(?:'s)?\s+name|candidate(?:'s)?\s+name|student(?:'s)?\s+name|name|नाम|नाव)",
    "father_name": r"(?:father(?:['’]s)?(?:\s*/\s*(?:legal\s*)?guardian)?(?:\s+name)?|name\s+of\s+father|s/o|d/o|पिता(?:\s+का\s+नाम)?|वडिलांचे\s+नाव)",
    "guardian_name": r"(?:(?:legal\s+)?guardian(?:'s)?(?:\s+name)?|पालकाचे\s+नाव)",
    "mother_name": r"(?:mother(?:['’]s)?(?:\s+name)?|name\s+of\s+mother|माता(?:\s+का\s+नाम)?|आईचे\s+नाव)",
    "spouse_name": r"(?:(?:spouse|husband|wife)(?:['’]s)?(?:\s+name)?|w/o|पति(?:\s+का\s+नाम)?|पत्नी(?:\s+का\s+नाम)?)",
    "dob": r"(?:date\s+of\s+birth|birth\s+date|d\.?o\.?b\.?|जन्म\s*तिथि|जन्म\s*दिनांक|जन्मतारीख|year\s+of\s+birth|yob)",
    "gender": r"(?:gender|sex|लिंग)",
    "place_of_birth": r"(?:place\s+of\s+birth|birth\s+place|जन्म\s*स्थान|जन्मस्थळ)",
    "address": r"(?:permanent\s+address|residential\s+address|present\s+address|address|पत्ता|पता)",
    "pincode": r"(?:pin\s*(?:code)?|postal\s*code|पिन\s*कोड)",
    "mobile_number": r"(?:(?:registered|linked)?\s*mobile(?:\s+(?:number|no\.?))?|phone(?:\s+(?:number|no\.?))?|मोबाइल|मोबाईल)",
    "issue_date": r"(?:date\s+of\s+issue|issue\s+date|issued\s+on|bill\s+date|agreement\s+date|जारी\s+तिथि)",
    "expiry_date": r"(?:date\s+of\s+expiry|expiry\s+date|valid\s+(?:till|until|upto|up\s+to)|validity(?:\s+date)?|expires\s+on)",
    "issuing_authority": r"(?:issuing\s+authority|issued\s+by|authority)",
    "exam_year": r"(?:examination\s+year|exam\s+year|year\s+of\s+passing|passing\s+year)",
    "exam_level": r"(?:exam\s+level|examination\s+level|class|standard)",
}
TYPE_PATTERNS = (
    ("12th Marksheet", r"12th|class\s*xii\b|higher\s+secondary|\bhsc\b"),
    ("10th Marksheet", r"10th|class\s*x\b|secondary\s+school|\bssc\b|marksheet|icse|cbse"),
    ("Birth Certificate", r"birth\s+certificate|registration\s+of\s+birth|जन्म\s+प्रमाण"),
    ("Aadhaar Card", r"aadhaar|aadhar|uidai|आधार"),
    ("PAN Card", r"pan\s+card|permanent\s+account|income\s+tax\s+department"),
    ("Passport", r"passport|republic\s+of\s+india|P<IND"),
    ("Voter ID Card", r"voter|election\s+commission|\bepic\b"),
    ("Learner Licence", r"learner(?:'s|s)?\s+licen[cs]e|learning\s+licen[cs]e"),
    ("Driving Licence", r"driving\s+licen[cs]e"),
    ("EWS Certificate", r"\bews\b|economically\s+weaker"),
    ("Caste Certificate", r"caste\s+certificate"),
    ("Income Certificate", r"income\s+certificate"),
    ("Ration Card", r"ration\s+card"),
    ("Bank Passbook", r"passbook|bank\s+statement"),
    ("Electricity Bill", r"electricity\s+bill|electric\s+bill"),
    ("Rent Agreement", r"rent(?:al)?\s+agreement|lease\s+agreement"),
)


def normalize_digits(text):
    return "".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in str(text))


def strict_date(value, allow_year=False):
    """No date swapping or invalid-date-to-year fallback."""
    s = normalize_digits(value).strip()
    s = re.sub(r"(?<=\d)\s*([/.-])\s*(?=\d)", r"\1", s)
    if allow_year and re.fullmatch(r"(?:19|20)\d{2}", s):
        return s if int(s) <= date.today().year else None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%Y.%m.%d", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def mask_aadhaar(value):
    if isinstance(value, dict):
        return {**value, "number": mask_aadhaar(value.get("number"))} if "aadhaar" in str(value.get("type", "")).lower() else value
    if not value:
        return value
    return re.sub(r"(?<!\d)(?:\d{4}[ -]?){2}(\d{4})(?!\d)", r"XXXX XXXX \1", str(value))


def labelled(text, pattern):
    """Read explicit labels only; never take a second label as a value."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for i, line in enumerate(lines):
        match = re.match(r"^\s*" + pattern + r"\s*(?::|[-–])?\s+(.+)$", line, re.I)
        if not match:
            match = re.match(r"^\s*" + pattern + r"\s*[:：]\s*(.*)$", line, re.I)
        if match:
            value = match.group(1).strip()
            if value:
                return value
        if re.fullmatch(pattern + r"\s*[:：]?", line, re.I) and i + 1 < len(lines):
            candidate = lines[i + 1]
            if not any(re.match(p + r"\s*[:：]", candidate, re.I) for p in LABELS.values()):
                return candidate
    return None


def person(value):
    if not value:
        return None
    value = re.sub(r"\s+", " ", str(value)).strip(" :.-")
    if any(c.isdigit() for c in value) or len(value) > 120 or not 1 <= len(value.split()) <= 7:
        return None
    if re.search(r"\b(?:date|gender|address|certificate|department|government|number|name)\b", value, re.I):
        return None
    if re.search(r"\b(?:this is to certify|has passed|board of|school certificate|statement of marks|date of birth)\b", value, re.I):
        return None
    if not all(c.isalpha() or unicodedata.category(c).startswith("M") or c in " .'-’" for c in value):
        return None
    return value


def mrz_check(value, digit):
    if not digit.isdigit():
        return False
    def n(c):
        return 0 if c == "<" else int(c) if c.isdigit() else ord(c) - 55
    return sum(n(c) * (7, 3, 1)[i % 3] for i, c in enumerate(value)) % 10 == int(digit)


def passport_mrz(text):
    """TD3 MRZ: number, birth, expiry, personal and composite check digits."""
    lines = [re.sub(r"\s", "", l).upper() for l in text.splitlines()]
    for i, line in enumerate(lines[:-1]):
        if len(line) != 44 or not line.startswith("P<"):
            continue
        second = lines[i + 1]
        if len(second) != 44 or not re.fullmatch(r"[A-Z0-9<]{44}", second):
            continue
        checks = {"doc_number": mrz_check(second[:9], second[9]),
                  "dob": mrz_check(second[13:19], second[19]),
                  "expiry_date": mrz_check(second[21:27], second[27]),
                  "personal": mrz_check(second[28:42], second[42]) or (second[28:43] == "<" * 15),
                  "composite": mrz_check(second[:10] + second[13:20] + second[21:43], second[43])}
        surname, _, given = line[5:].partition("<<")
        result = {"name": " ".join((given.replace("<", " ") + " " + surname.replace("<", " ")).split()),
                  "doc_number": {"type": "Passport", "number": second[:9].rstrip("<")},
                  "gender": {"M": "Male", "F": "Female"}.get(second[20]), "checks": checks}
        for field, raw in (("dob", second[13:19]), ("expiry_date", second[21:27])):
            if raw.isdigit():
                yy = int(raw[:2]); year = 2000 + yy
                if field == "dob" and year > date.today().year:
                    year -= 100
                result[field] = strict_date(f"{year:04d}-{raw[2:4]}-{raw[4:6]}")
        return result
    return None


def validate_number(value, doc_type, name=None):
    raw = value.get("number") if isinstance(value, dict) else value
    if not raw:
        return False, "missing"
    n = re.sub(r"[\s-]", "", str(raw)).upper()
    t = doc_type.lower()
    if "aadhaar" in t:
        if re.fullmatch(r"[X*]{8}\d{4}", n):
            return True, "masked; checksum unavailable"
        from ocr_extract import validate_verhoeff
        return bool(re.fullmatch(r"[2-9]\d{11}", n) and validate_verhoeff(n)), "Verhoeff"
    if "pan" in t:
        valid = bool(re.fullmatch(r"[A-Z]{3}[ABCFGHJLPT][A-Z]\d{4}[A-Z]", n))
        if valid and n[3] == "P" and name:
            surname = str(name).split()[-1]
            if surname and surname[0].isascii() and surname[0].isalpha() and n[4] != surname[0].upper():
                return False, "surname initial differs; confirm PAN/name order"
        return valid, "PAN layout"
    if "passport" in t:
        return bool(re.fullmatch(r"[A-PR-WYZ]\d{7}", n)), "passport format; MRZ checked separately"
    if "voter" in t:
        return bool(re.fullmatch(r"[A-Z]{3}\d{7}", n)), "EPIC format"
    if "learner" in t:
        return False, "learner licence formats vary by issuer; confirm number"
    if "driving" in t:
        return bool(re.fullmatch(r"[A-Z]{2}\d{2}(?:19|20)\d{2}\d{7}", n)), "DL format"
    return bool(re.fullmatch(r"[A-Z0-9/.-]{3,35}", n)), "format only; issuer verification unavailable"


def enrich_fields(result, ocr_data, chosen_option=None):
    text = normalize_digits((ocr_data or {}).get("text") or result.get("raw_text", ""))
    detected = next((label for label, pat in TYPE_PATTERNS if re.search(pat, text, re.I)), None)
    doc_type = detected or chosen_option or result.get("detectedType") or "Unknown"
    fields = {}
    transport = {}
    if re.search(r"driving|learner|learning", doc_type, re.I):
        from transport_fields import extract_transport
        transport = extract_transport(text)
        result.setdefault("doc_meta", {})["core_field_conflicts"] = transport.pop("_conflicts", [])
        doc_type = transport["document_type"]
    academic = {}
    aadhaar = {}
    if "aadhaar" in doc_type.lower():
        from aadhaar_fields import extract_sides
        aadhaar = extract_sides(ocr_data or {"text": text})
        result.setdefault("doc_meta", {})["aadhaar_review_reasons"] = aadhaar.pop("_review_reasons", [])
    if re.search(r"marksheet|statement\s+of\s+marks|secondary|\b[sh]\.?s\.?c\.?\b|\b(?:cbse|icse|isc|cisce)\b", text + " " + str(chosen_option or ""), re.I):
        from marksheet_fields import extract_marksheet_fields
        academic = extract_marksheet_fields(text, chosen_option, ocr_data)
        result.setdefault("doc_meta", {})["core_field_conflicts"] = academic.pop("_conflicts", [])
        doc_type = academic.get("document_type", doc_type)
    base_conf = result.get("fieldConfidence", {})
    word_conf = max(0.0, min(1.0, float((ocr_data or {}).get("mean_confidence", 0)) / 100))
    for field in FIELDS:
        value = result.get(field)
        confidence = min(float(base_conf.get(field, .55 if value else 0)), word_conf or .55)
        explicit = labelled(text, LABELS[field]) if field in LABELS else None
        if explicit:
            value, confidence = explicit, min(.92, word_conf or .55)
        if field in academic:
            value, confidence = academic[field], min(.90, word_conf or .55)
        if field in transport:
            value, confidence = transport[field], min(.85, word_conf or .55)
        if field in aadhaar:
            value, confidence = aadhaar[field], min(.85, word_conf or .55)
        # An issue/result date must never be guessed to be a student's DOB.
        if academic and field == "dob" and not explicit and "dob" not in academic:
            value, confidence = None, 0
        if field in {"name", "father_name", "mother_name", "guardian_name", "spouse_name"}:
            value = person(value)
        if field in ("dob", "issue_date", "expiry_date"):
            value = strict_date(value, allow_year=field == "dob") if value else None
            if field == "dob" and value and re.fullmatch(r"\d{4}", value):
                confidence = min(confidence, .5)
        if field == "gender" and value:
            value = {"m": "Male", "male": "Male", "पुरुष": "Male", "f": "Female", "female": "Female", "महिला": "Female", "स्त्री": "Female", "transgender": "Transgender", "other": "Other"}.get(str(value).strip().lower())
        if field == "pincode":
            source = str(value or "") if aadhaar else str(value or result.get("address") or labelled(text, LABELS["address"]) or "")
            pins = set(re.findall(r"(?<!\d)[1-9]\d{5}(?!\d)", source))
            value = next(iter(pins)) if len(pins) == 1 else None
            if value:
                confidence = min(.92, word_conf or .55)
        if field == "mobile_number" and value:
            value = re.sub(r"[\s()-]", "", value).upper()
            value = value[3:] if value.startswith("+91") else value
            if not re.fullmatch(r"[6-9]\d{9}|[X*]{2,8}\d{2,8}", value) or len(value) != 10:
                confidence = min(confidence, .4)
        if field == "document_type":
            value, confidence = doc_type, .9 if detected else .5
        if field == "exam_level":
            value = "12th" if doc_type == "12th Marksheet" else "10th" if doc_type == "10th Marksheet" else None
            confidence = min(.9, word_conf or .55) if value else 0
        if field == "exam_year" and value:
            value = str(value) if re.fullmatch(r"(?:19|20)\d{2}", str(value)) else None
        if not value:
            confidence = 0.0
        fields[field] = {"value": value, "confidence": round(confidence, 3), "needs_review": not value or confidence < .8, "user_verified": False}

    # Validated document-number recognition, independent of legacy permissive shortcuts.
    number = fields["doc_number"]["value"]
    if "aadhaar" in doc_type.lower():
        masked = re.search(r"\b[Xx*]{4}\s*[Xx*]{4}\s*\d{4}\b", text)
        if masked and not aadhaar:
            number = {"type": "Aadhaar", "number": re.sub(r"\s+", " ", masked.group()).upper()}
    if not aadhaar and not academic and not transport and (not number or re.search(r"certificate|ration|bank|bill|agreement", doc_type, re.I)):
        label = r"(?:birth\s+registration|registration|certificate|document|account|ration\s+card|consumer)(?:\s+(?:number|no\.?))"
        candidate = labelled(text, label)
        if candidate and re.fullmatch(r"[A-Z0-9/.-]{3,35}", candidate.strip(), re.I):
            number = {"type": doc_type, "number": candidate.strip()}
    if isinstance(number, str):
        number = {"type": doc_type, "number": number} if re.fullmatch(r"[A-Z0-9 /.-]{3,40}", number, re.I) else None
    valid, reason = validate_number(number, doc_type, fields["name"]["value"])
    from identity_store import enabled, identify, seal
    if valid and enabled():
        sensitive=identify(number,doc_type)
        if sensitive:result['_identity_ciphertext']=seal(sensitive,'ocr-internal')
    fields["doc_number"].update(value=mask_aadhaar(number) if "aadhaar" in doc_type.lower() else number, validation=reason)
    if number and valid:
        fields["doc_number"]["confidence"] = min(.92, word_conf or .55)
        fields["doc_number"]["needs_review"] = fields["doc_number"]["confidence"] < .8
    elif number:
        fields["doc_number"].update(confidence=.35, needs_review=True)

    mrz = passport_mrz(text) if "passport" in doc_type.lower() else None
    if mrz:
        all_valid = all(mrz["checks"].values())
        result.setdefault("doc_meta", {})["mrz_checks"] = mrz["checks"]
        for field in ("name", "dob", "gender", "doc_number", "expiry_date"):
            value = mrz.get(field)
            if value and not fields[field]["value"]:
                fields[field].update(value=value, confidence=.94 if all_valid else .4, needs_review=not all_valid)
            elif not all_valid:
                fields[field].update(confidence=min(.4, fields[field]["confidence"]), needs_review=True)

    # Preserve uncertainty when different preprocessing passes disagree on a field.
    passes = (ocr_data or {}).get("passes", [])
    for field, pattern in LABELS.items():
        votes = [labelled(normalize_digits(p.get("text", "")), pattern) for p in passes]
        votes = [v for v in votes if v]
        if len(votes) > 1 and len({v.casefold() for v in votes}) > 1:
            from collections import Counter
            value, count = Counter(votes).most_common(1)[0]
            # Vote only among identically normalized values; no fuzzy confidence inflation.
            if count <= len(votes) / 2:
                fields[field].update(confidence=min(.6, fields[field]["confidence"]), needs_review=True)

    result["doc_fields"] = fields
    result["ocr_version"] = OCR_VERSION
    result["user_verified"] = False
    result["needs_review"] = any(f["needs_review"] for f in fields.values() if f["value"] is not None) or not fields["name"]["value"]
    for field, entry in fields.items():
        result[field] = entry["value"]
        result.setdefault("fieldConfidence", {})[field] = entry["confidence"]
        result.setdefault("needsReview", {})[field] = entry["needs_review"]
    result["fieldConfidences"] = result["fieldConfidence"]
    return result
