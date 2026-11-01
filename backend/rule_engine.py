"""
SmartApply Rule Engine
Performs field-by-field document comparison across Name, Date of Birth, Address,
and Identification Numbers.

Returns 4 clear comparison result categories:
1. "Match" - Values are identical, reordered, subset with middle name, or semantically equivalent.
2. "Possible Mismatch" - Minor variation, single-token name match, or moderate similarity.
3. "Mismatch" - Clear discrepancy (different dates, different numbers, different names).
4. "Unable to Compare" - Field unreadable, missing, or incompatible document types.
"""

import re
import unicodedata
import difflib
from datetime import datetime
from itertools import combinations
from correction_guide import get_guidance

HONORIFICS = {
    "mr", "mrs", "ms", "miss", "master", "dr", "prof", "shri", "shree",
    "sri", "smt", "kum", "late", "adv"
}
RELATIONAL = {"s/o", "d/o", "w/o", "c/o", "so", "do", "wo", "co"}

# Removed "nag", "up", "st" to prevent false positive abbreviation expansions
ADDRESS_ABBREVIATIONS = {
    "rd": "road", "ln": "lane", "apt": "apartment",
    "bldg": "building", "flr": "floor", "nr": "near", "opp": "opposite",
    "soc": "society", "chs": "society", "sec": "sector",
    "no": "number", "dist": "district", "vill": "village",
    "mah": "maharashtra", "mh": "maharashtra",
    "mp": "madhya pradesh", "tn": "tamil nadu", "wb": "west bengal",
    "guj": "gujarat", "raj": "rajasthan", "kar": "karnataka",
}
ADDRESS_STOPWORDS = {"at", "the", "and", "india", "in", "post"}
PIN_RE = re.compile(r"\b([1-9]\d{5})\b")

CHECKLIST_DESCRIPTIONS = {
    "proof of identity", "proof of address", "proof of date of birth",
    "proof of relationship", "proof of relationship & identity", "photograph",
    "signature", "passport-size photograph", "birth certificate", "pan card",
    "aadhaar card", "voter id card", "driving licence", "electricity bill",
    "rent agreement", "bank passbook", "ration card", "10th marksheet",
    "school id card", "not detected", "none", "null", "undefined",
    "certificate", "application form", "document", "documents"
}

NON_NAME_WORDS = {
    "government", "india", "income", "tax", "department", "male", "female",
    "republic", "election", "commission", "driving", "licence", "license",
    "permanent", "account", "number", "card", "authority", "signature",
    "address", "district", "state", "pin", "code", "unique", "identification",
    "father", "husband", "guardian", "date", "birth", "issue", "valid",
    "proof", "identity", "checklist", "requirement", "document", "documents"
}

DISCLAIMER_WORDS = {
    "should", "updated", "aadhaar", "years", "enrolment", "enrollment",
    "citizenship", "uidai", "toll", "free", "1947", "lang", "ss", "sl", "fl",
    "hindi", "marathi", "sanskrit", "english", "marks", "marksheet", "total",
    "obtained", "theory", "practical", "maximum", "minimum", "passed",
    "distinction", "percentage", "result", "exam", "examination", "subject"
}

# Document field capability map: which fields are realistically expected on each document
DOC_FIELD_MAP = {
    "pan card": {"name", "dob", "doc_number"},
    "aadhaar card": {"name", "dob", "address", "doc_number"},
    "passport": {"name", "dob", "address", "doc_number"},
    "voter id card": {"name", "dob", "address", "doc_number"},
    "driving licence": {"name", "dob", "address", "doc_number"},
    "10th marksheet": {"name", "dob"},
    "birth certificate": {"name", "dob"},
    "domicile certificate": {"name", "address", "dob"},
    "electricity bill": {"name", "address"},
    "rent agreement": {"name", "address"},
    "bank passbook": {"name", "address"},
    "ration card": {"name", "address"},
}


def get_expected_fields(doc_key):
    """Returns the set of fields expected to be present on this document type."""
    k = doc_key.lower().strip()
    for pattern, fields in DOC_FIELD_MAP.items():
        if pattern in k:
            return fields
    return {"name", "dob", "address", "doc_number"}


def is_checklist_description(val):
    """Checks if a value is a checklist description, disclaimer, or subject code rather than valid identity data."""
    if not val or not isinstance(val, str):
        return False
    norm = normalize_text(val)
    if norm in CHECKLIST_DESCRIPTIONS:
        return True
    tokens = norm.split()
    if any(t in DISCLAIMER_WORDS for t in tokens):
        return True
    if len(tokens) >= 2 and all(t in NON_NAME_WORDS or t in CHECKLIST_DESCRIPTIONS for t in tokens):
        return True
    return False


def _fold_diacritics(text):
    decomposed = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_text(value):
    """Lowercase, strip punctuation, collapse whitespace."""
    if not value:
        return ""
    value = _fold_diacritics(value).lower().strip()
    value = re.sub(r"[^\w\s]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value


def normalize_name_tokens(name):
    """Normalize a name and return its lowercase tokens, honorifics and relations stripped."""
    cleaned = normalize_text(name)
    parts = cleaned.split()
    tokens = []
    for tok in parts:
        if tok in RELATIONAL:
            break
        if tok in HONORIFICS:
            continue
        tokens.append(tok)
    return tokens


def normalize_address_tokens(address):
    """Normalize address, expand safe abbreviations, pull out 6-digit PIN."""
    if not address:
        return [], None
    pin_match = PIN_RE.search(address)
    pin = pin_match.group(1) if pin_match else None

    cleaned = normalize_text(address)
    tokens = []
    for tok in cleaned.split():
        if tok in ADDRESS_STOPWORDS or tok == pin:
            continue
        tokens.append(ADDRESS_ABBREVIATIONS.get(tok, tok))
    return tokens, pin


def similarity(s1, s2):
    """Normalized character similarity ratio."""
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return difflib.SequenceMatcher(None, s1, s2).ratio()


def jaro_winkler(s1, s2, prefix_weight=0.1, max_prefix=4):
    """Standard Jaro-Winkler metric."""
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    len1, len2 = len(s1), len(s2)
    match_distance = max(len1, len2) // 2 - 1
    if match_distance < 0:
        match_distance = 0

    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0

    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    k = transpositions = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    transpositions //= 2
    base = (
        (matches / len1) + (matches / len2) + ((matches - transpositions) / matches)
    ) / 3.0

    prefix = 0
    for a, b in zip(s1[:max_prefix], s2[:max_prefix]):
        if a != b:
            break
        prefix += 1
    return base + prefix * prefix_weight * (1.0 - base)


def char_similarity(a, b):
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    return max(jaro_winkler(a, b), similarity(a, b))


def _token_pair_score(a, b):
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if len(a) == 1 or len(b) == 1:
        return 0.9 if a[0] == b[0] else 0.0
    return char_similarity(a, b)


def token_overlap(a_tokens, b_tokens):
    """Scored against shorter token list using greedy best-pairing."""
    if not a_tokens or not b_tokens:
        return 0.0
    if a_tokens == b_tokens:
        return 1.0
    short, long_ = (a_tokens, b_tokens) if len(a_tokens) <= len(b_tokens) else (b_tokens, a_tokens)

    candidates = sorted(
        ((_token_pair_score(a, b), i, j, a, b)
         for i, a in enumerate(short) for j, b in enumerate(long_)),
        key=lambda t: (-t[0], t[1], t[2]),
    )
    used_s, used_l, pairs = set(), set(), []
    for score, i, j, a, b in candidates:
        if i in used_s or j in used_l:
            continue
        used_s.add(i)
        used_l.add(j)
        pairs.append(score)
        if len(used_s) == len(short):
            break
    return sum(pairs) / len(short) if pairs else 0.0


_DATE_FORMATS = [
    "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%d %b %Y", "%d %B %Y", "%d-%b-%Y",
]

def _parse_date(value):
    if not value:
        return None, None
    text = str(value).strip()
    if re.match(r"^(19|20)\d{2}$", text):
        return None, int(text)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date(), None
        except ValueError:
            continue
    return None, None


# --------------------------------------------------------------------------- #
# Field Comparators
# --------------------------------------------------------------------------- #

def compare_names(name_a, name_b):
    """
    Returns (result, verdict, similarity, explanation, severity)
    Result is Match, Possible Mismatch, Mismatch, or Unable to Compare.
    """
    if is_checklist_description(name_a) or is_checklist_description(name_b):
        return "Unable to Compare", "unable_to_verify", None, "Extracted value matched a checklist description or document title instead of a person name.", None

    if not name_a or not name_b:
        missing = "both documents" if (not name_a and not name_b) else ("Document 1" if not name_a else "Document 2")
        return "Unable to Compare", "unable_to_verify", None, f"Name was not detected in {missing}.", None

    norm_a = normalize_text(name_a)
    norm_b = normalize_text(name_b)
    if norm_a == norm_b:
        return "Match", "match", 1.0, "Names match identically.", None

    tokens_a = normalize_name_tokens(name_a)
    tokens_b = normalize_name_tokens(name_b)

    set_a = set(tokens_a)
    set_b = set(tokens_b)

    # Identical token set with different order (e.g. "Desai Shivam" vs "Shivam Desai")
    if set_a == set_b and len(tokens_a) >= 2:
        return "Match", "match", 1.0, f"Names match (different name order: '{name_a}' vs '{name_b}').", None

    # Token subset match: shorter name has >= 2 tokens and is a subset of longer name
    short_tokens, long_tokens = (tokens_a, tokens_b) if len(tokens_a) <= len(tokens_b) else (tokens_b, tokens_a)
    short_name, long_name = (name_a, name_b) if len(tokens_a) <= len(tokens_b) else (name_b, name_a)

    if set(short_tokens) < set(long_tokens):
        if len(short_tokens) >= 2:
            return "Match", "match", 1.0, f"Names match: one document includes an additional middle/father's name ('{short_name}' vs '{long_name}').", None
        elif len(short_tokens) == 1:
            return "Possible Mismatch", "possible_mismatch", 0.70, (
                f"Single name token match ('{short_name}' vs '{long_name}'): only one name part matches. Verify if this represents the same person."
            ), "moderate"

    seq_score = char_similarity(norm_a, norm_b)
    tok_score = token_overlap(tokens_a, tokens_b)
    score = round(max(seq_score, tok_score), 2)

    if score >= 0.82:
        return "Possible Mismatch", "possible_mismatch", score, (
            f"Minor name spelling variation ({int(score * 100)}% similarity): '{name_a}' vs '{name_b}'. "
            "Ensure the spelling matches your application form."
        ), "moderate"
    else:
        return "Mismatch", "mismatch", score, (
            f"Different names detected ({int(score * 100)}% similarity): '{name_a}' vs '{name_b}'. "
            "A name mismatch will likely cause rejection."
        ), "high"


def compare_dob(dob_a, dob_b):
    """
    Returns (result, verdict, similarity, explanation, severity)
    Handles Year-only vs Full DOB gracefully without false mismatch.
    """
    if is_checklist_description(dob_a) or is_checklist_description(dob_b):
        return "Unable to Compare", "unable_to_verify", None, "Extracted value is not a valid date of birth.", None

    if not dob_a or not dob_b:
        missing = "both documents" if (not dob_a and not dob_b) else ("Document 1" if not dob_a else "Document 2")
        return "Unable to Compare", "unable_to_verify", None, f"Date of birth was not detected in {missing}.", None

    date_a, year_a = _parse_date(dob_a)
    date_b, year_b = _parse_date(dob_b)

    if (date_a is None and year_a is None) or (date_b is None and year_b is None):
        return "Unable to Compare", "unable_to_verify", 0.0, f"Could not parse date format: '{dob_a}' or '{dob_b}'.", "error"

    # Both are full dates (day, month, year)
    if date_a and date_b:
        if date_a == date_b:
            return "Match", "match", 1.0, f"Dates of birth match exactly ({dob_a}).", None
        elif date_a.year == date_b.year:
            return "Possible Mismatch", "possible_mismatch", 0.0, (
                f"Birth year matches ({date_a.year}), but dates differ: '{dob_a}' vs '{dob_b}'."
            ), "moderate"
        else:
            return "Mismatch", "mismatch", 0.0, (
                f"Date of birth mismatch: '{dob_a}' vs '{dob_b}'. Mismatched birth dates cause application rejection."
            ), "high"

    # One or both are Year-only
    ya = year_a or (date_a.year if date_a else None)
    yb = year_b or (date_b.year if date_b else None)
    if ya == yb:
        return "Match", "match", 1.0, f"Birth year matches ({ya}); full date not printed on one document.", None
    else:
        return "Mismatch", "mismatch", 0.0, f"Birth years differ: '{dob_a}' vs '{dob_b}'.", "high"


def compare_address(addr_a, addr_b):
    """
    Returns (result, verdict, similarity, explanation, severity)
    PIN code conflict produces Mismatch; subset match requires >= 3 tokens or matching PIN.
    """
    if not addr_a or not addr_b:
        missing = "both documents" if (not addr_a and not addr_b) else ("Document 1" if not addr_a else "Document 2")
        return "Unable to Compare", "unable_to_verify", None, f"Address was not detected in {missing}.", None

    norm_a = normalize_text(addr_a)
    norm_b = normalize_text(addr_b)
    if norm_a == norm_b:
        return "Match", "match", 1.0, "Addresses match identically.", None

    tokens_a, pin_a = normalize_address_tokens(addr_a)
    tokens_b, pin_b = normalize_address_tokens(addr_b)

    pin_conflict = bool(pin_a and pin_b and pin_a != pin_b)
    if pin_conflict:
        return "Mismatch", "mismatch", 0.0, f"Postal PIN codes differ ({pin_a} vs {pin_b}): '{addr_a}' vs '{addr_b}'.", "high"

    set_a = set(tokens_a)
    set_b = set(tokens_b)
    if not set_a or not set_b:
        return "Unable to Compare", "unable_to_verify", None, "Address could not be tokenized.", None

    common = set_a & set_b
    shorter_len = min(len(set_a), len(set_b))
    subset_ratio = len(common) / shorter_len if shorter_len > 0 else 0
    jaccard = len(common) / len(set_a | set_b) if (set_a | set_b) else 0

    score = round(max(jaccard, subset_ratio * 0.8), 2)

    # Shorter address is a complete subset: requires >= 3 tokens or matching PIN
    if (set_a <= set_b or set_b <= set_a):
        if len(common) >= 3 or (pin_a and pin_a == pin_b):
            return "Match", "match", 1.0, f"Addresses match ('{addr_a}' and '{addr_b}').", None

    if subset_ratio >= 0.70 and jaccard >= 0.50:
        return "Match", "match", score, "Addresses match closely.", None
    elif subset_ratio >= 0.25 or jaccard >= 0.20:
        return "Possible Mismatch", "possible_mismatch", score, f"Address differences detected: '{addr_a}' vs '{addr_b}'. Verify if these refer to the same residence.", "moderate"
    else:
        return "Mismatch", "mismatch", score, f"Different addresses detected: '{addr_a}' vs '{addr_b}'.", "high"


def infer_doc_type(val, doc_name=""):
    combined = f"{val} {doc_name}".lower()
    if "aadhaar" in combined:
        return "Aadhaar"
    if "pan" in combined:
        return "PAN"
    if "passport" in combined:
        return "Passport"
    if "voter" in combined or "epic" in combined:
        return "Voter ID"
    if "driving" in combined or "dl" in combined:
        return "Driving Licence"
    if "domicile" in combined or "birth" in combined:
        return "Certificate"
    clean = re.sub(r"[\s\-]", "", str(val)).upper()
    if re.fullmatch(r"\d{12}", clean):
        return "Aadhaar"
    if re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", clean):
        return "PAN"
    return None


def compare_doc_numbers(num_a_raw, num_b_raw, doc_a="", doc_b=""):
    """
    Compares document numbers only when document types match.
    Never compares incompatible document numbers across different document types.
    """
    if not num_a_raw or not num_b_raw:
        missing = "both documents" if (not num_a_raw and not num_b_raw) else ("Document 1" if not num_a_raw else "Document 2")
        return "Unable to Compare", "unable_to_verify", None, f"Document number not detected in {missing}.", None

    def parse_num(raw):
        if isinstance(raw, dict):
            return raw.get("type"), str(raw.get("number", "")).strip()
        s = str(raw).strip()
        if ":" in s:
            t, n = s.split(":", 1)
            return t.strip(), n.strip()
        return None, s

    type_a, n_a = parse_num(num_a_raw)
    type_b, n_b = parse_num(num_b_raw)

    if not type_a:
        type_a = infer_doc_type(num_a_raw, doc_a)
    if not type_b:
        type_b = infer_doc_type(num_b_raw, doc_b)

    clean_a = re.sub(r"[\s\-]", "", n_a).upper()
    clean_b = re.sub(r"[\s\-]", "", n_b).upper()

    if type_a and type_b and type_a.lower() != type_b.lower():
        return "Unable to Compare", "unable_to_verify", None, (
            f"Different document types ({type_a} vs {type_b}); document identification numbers cannot be cross-checked."
        ), None

    if clean_a == clean_b:
        doc_type_str = f"{type_a} " if type_a else "Identification "
        return "Match", "match", 1.0, f"{doc_type_str}numbers match exactly ({n_a}).", None
    else:
        if type_a and type_b and type_a.lower() == type_b.lower():
            return "Mismatch", "mismatch", 0.0, f"{type_a} numbers do not match: '{n_a}' vs '{n_b}'.", "high"
        return "Unable to Compare", "unable_to_verify", None, (
            f"Different document number formats ('{n_a}' vs '{n_b}'); numbers cannot be cross-checked across different document types."
        ), None


def build_correction_options(doc_a, doc_b, field):
    return [get_guidance(doc_a, field), get_guidance(doc_b, field)]


def check_mismatches(documents):
    """
    Compares uploaded documents across Name, Date of Birth, Address, and Document Number.
    Generates a full field-by-field comparison matrix.
    Subject-aware: respects document subjects (applicant vs parent/deceased).
    Outputs verificationStatus, verifiedFieldCount, unverifiedFieldCount.
    """
    doc_names = list(documents.keys())

    # Separate documents with at least one extracted identity field from unreadable ones
    readable_docs = {}
    unreadable_docs = []
    for doc_k, data in documents.items():
        if any([data.get("name"), data.get("dob"), data.get("address"), data.get("doc_number")]):
            readable_docs[doc_k] = data
        else:
            unreadable_docs.append(doc_k)

    readable_keys = list(readable_docs.keys())

    if len(readable_keys) < 2:
        missing_reasons = []
        for doc_k in unreadable_docs:
            doc_data = documents.get(doc_k, {})
            t_len = doc_data.get("text_length") or len(doc_data.get("raw_text") or "")
            if t_len > 60:
                missing_reasons.append(
                    f"{doc_k} (text was extracted, but no identity fields like Name or DOB were identified — use 'Wrong? Fix it' on the checklist to supply them)"
                )
            else:
                missing_reasons.append(
                    f"{doc_k} (no readable text detected — please upload a clearer copy)"
                )

        if missing_reasons:
            msg = (
                f"At least 2 documents with recognized identity fields are required to compare records. "
                f"Could not identify identity details in: {'; '.join(missing_reasons)}."
            )
        else:
            msg = "Upload at least 2 distinct documents to compare their details."

        return {
            "documentsChecked": doc_names,
            "readableDocuments": readable_keys,
            "unreadableDocuments": unreadable_docs,
            "enoughData": False,
            "clean": True,
            "issuesFound": 0,
            "issues": [],
            "comparisons": [],
            "summary": {
                "totalComparisons": 0,
                "matches": 0,
                "possibleMismatches": 0,
                "mismatches": 0,
                "unableToCompare": 0,
            },
            "verificationStatus": "partially_verified",
            "verifiedFieldCount": 0,
            "unverifiedFieldCount": 0,
            "message": msg,
        }

    comparisons = []
    issues = []

    matches_count = 0
    possible_mismatch_count = 0
    mismatch_count = 0
    unable_count = 0

    for doc_a, doc_b in combinations(readable_keys, 2):
        f_a = readable_docs[doc_a]
        f_b = readable_docs[doc_b]

        # Subject-aware check: skip comparing documents intended for different persons
        subj_a = f_a.get("subject") or (f_a.get("doc_meta") or {}).get("subject") or "applicant"
        subj_b = f_b.get("subject") or (f_b.get("doc_meta") or {}).get("subject") or "applicant"
        if subj_a != subj_b:
            continue

        exp_fields_a = get_expected_fields(doc_a)
        exp_fields_b = get_expected_fields(doc_b)

        # Sanitize values to prevent comparing checklist labels on Name and DOB
        raw_name_a = f_a.get("name")
        raw_name_b = f_b.get("name")
        name_a = None if is_checklist_description(raw_name_a) else raw_name_a
        name_b = None if is_checklist_description(raw_name_b) else raw_name_b

        raw_dob_a = f_a.get("dob")
        raw_dob_b = f_b.get("dob")
        dob_a = None if is_checklist_description(raw_dob_a) else raw_dob_a
        dob_b = None if is_checklist_description(raw_dob_b) else raw_dob_b

        # Address is NOT checked with is_checklist_description to prevent false rejections of real addresses
        addr_a = f_a.get("address")
        addr_b = f_b.get("address")

        # 1. Name comparison
        if name_a or name_b:
            if name_a and name_b:
                res, verd, sim, exp, sev = compare_names(name_a, name_b)
            else:
                present_doc = doc_a if name_a else doc_b
                missing_doc = doc_b if name_a else doc_a
                val_present = name_a or name_b
                res = "Unable to Compare"
                verd = "unable_to_verify"
                sim = None
                exp = f"Name was detected in {present_doc} ('{val_present}') but not detected in {missing_doc}."
                sev = None

            comp_name = {
                "field": "name", "fieldName": "Name",
                "docA": doc_a, "docB": doc_b,
                "valA": name_a or "Not detected",
                "valB": name_b or "Not detected",
                "result": res, "verdict": verd,
                "similarity": sim, "explanation": exp,
            }
            comparisons.append(comp_name)
            if res == "Match":
                matches_count += 1
            elif res == "Possible Mismatch":
                possible_mismatch_count += 1
                issues.append({
                    **comp_name, "documents": [doc_a, doc_b], "values": [name_a, name_b],
                    "severity": sev, "message": exp,
                    "correctionOptions": build_correction_options(doc_a, doc_b, "name"),
                })
            elif res == "Mismatch":
                mismatch_count += 1
                issues.append({
                    **comp_name, "documents": [doc_a, doc_b], "values": [name_a, name_b],
                    "severity": sev, "message": exp,
                    "correctionOptions": build_correction_options(doc_a, doc_b, "name"),
                })
            else:
                unable_count += 1

        # 2. Date of Birth comparison
        if dob_a or dob_b:
            if dob_a and dob_b:
                res, verd, sim, exp, sev = compare_dob(dob_a, dob_b)
            else:
                present_doc = doc_a if dob_a else doc_b
                missing_doc = doc_b if dob_a else doc_a
                val_present = dob_a or dob_b
                res = "Unable to Compare"
                verd = "unable_to_verify"
                sim = None
                exp = f"Date of birth was detected in {present_doc} ('{val_present}') but not detected in {missing_doc}."
                sev = None

            comp_dob = {
                "field": "dob", "fieldName": "Date of Birth",
                "docA": doc_a, "docB": doc_b,
                "valA": dob_a or "Not detected",
                "valB": dob_b or "Not detected",
                "result": res, "verdict": verd,
                "similarity": sim, "explanation": exp,
            }
            comparisons.append(comp_dob)
            if res == "Match":
                matches_count += 1
            elif res == "Possible Mismatch":
                possible_mismatch_count += 1
                issues.append({
                    **comp_dob, "documents": [doc_a, doc_b], "values": [dob_a, dob_b],
                    "severity": sev, "message": exp,
                    "correctionOptions": build_correction_options(doc_a, doc_b, "dob"),
                })
            elif res == "Mismatch":
                mismatch_count += 1
                issues.append({
                    **comp_dob, "documents": [doc_a, doc_b], "values": [dob_a, dob_b],
                    "severity": sev, "message": exp,
                    "correctionOptions": build_correction_options(doc_a, doc_b, "dob"),
                })
            else:
                unable_count += 1

        # 3. Address comparison
        if addr_a or addr_b:
            if addr_a and addr_b:
                res, verd, sim, exp, sev = compare_address(addr_a, addr_b)
            else:
                present_doc = doc_a if addr_a else doc_b
                missing_doc = doc_b if addr_a else doc_a
                res = "Unable to Compare"
                verd = "unable_to_verify"
                sim = None
                exp = f"Address was detected in {present_doc} but not detected in {missing_doc}."
                sev = None

            comp_addr = {
                "field": "address", "fieldName": "Address",
                "docA": doc_a, "docB": doc_b,
                "valA": addr_a or "Not detected",
                "valB": addr_b or "Not detected",
                "result": res, "verdict": verd,
                "similarity": sim, "explanation": exp,
            }
            comparisons.append(comp_addr)
            if res == "Match":
                matches_count += 1
            elif res == "Possible Mismatch":
                possible_mismatch_count += 1
                issues.append({
                    **comp_addr, "documents": [doc_a, doc_b], "values": [addr_a, addr_b],
                    "severity": sev, "message": exp,
                    "correctionOptions": build_correction_options(doc_a, doc_b, "address"),
                })
            elif res == "Mismatch":
                mismatch_count += 1
                issues.append({
                    **comp_addr, "documents": [doc_a, doc_b], "values": [addr_a, addr_b],
                    "severity": sev, "message": exp,
                    "correctionOptions": build_correction_options(doc_a, doc_b, "address"),
                })
            else:
                unable_count += 1

        # 4. Document Number comparison: compare only when both documents provide a number
        num_a = f_a.get("doc_number")
        num_b = f_b.get("doc_number")
        if num_a and num_b:
            res, verd, sim, exp, sev = compare_doc_numbers(num_a, num_b, doc_a, doc_b)
            val_a_str = f"{num_a.get('type')}: {num_a.get('number')}" if isinstance(num_a, dict) else str(num_a)
            val_b_str = f"{num_b.get('type')}: {num_b.get('number')}" if isinstance(num_b, dict) else str(num_b)

            comp_num = {
                "field": "doc_number", "fieldName": "Document Number",
                "docA": doc_a, "docB": doc_b,
                "valA": val_a_str, "valB": val_b_str,
                "result": res, "verdict": verd,
                "similarity": sim, "explanation": exp,
            }
            comparisons.append(comp_num)
            if res == "Match":
                matches_count += 1
            elif res == "Possible Mismatch":
                possible_mismatch_count += 1
                issues.append({
                    **comp_num, "documents": [doc_a, doc_b], "values": [val_a_str, val_b_str],
                    "severity": sev or "high", "message": exp,
                    "correctionOptions": build_correction_options(doc_a, doc_b, "doc_number"),
                })
            elif res == "Mismatch":
                mismatch_count += 1
                issues.append({
                    **comp_num, "documents": [doc_a, doc_b], "values": [val_a_str, val_b_str],
                    "severity": sev or "high", "message": exp,
                    "correctionOptions": build_correction_options(doc_a, doc_b, "doc_number"),
                })
            else:
                unable_count += 1

    # Determine top-level verificationStatus
    if len(issues) > 0:
        verification_status = "issues_found"
    elif matches_count >= 1 and len(readable_keys) >= 2:
        verification_status = "verified"
    else:
        verification_status = "partially_verified"

    return {
        "documentsChecked": doc_names,
        "readableDocuments": readable_keys,
        "unreadableDocuments": unreadable_docs,
        "enoughData": len(readable_keys) >= 2,
        "clean": len(issues) == 0,
        "issuesFound": len(issues),
        "issues": issues,
        "comparisons": comparisons,
        "summary": {
            "totalComparisons": len(comparisons),
            "matches": matches_count,
            "possibleMismatches": possible_mismatch_count,
            "mismatches": mismatch_count,
            "unableToCompare": unable_count,
        },
        "verificationStatus": verification_status,
        "verifiedFieldCount": matches_count,
        "unverifiedFieldCount": unable_count + len(issues),
    }
