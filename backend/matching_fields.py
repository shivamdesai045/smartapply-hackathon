"""Conservative comparison extensions. No network calls or identity logging.

Metadata is optional for old clients. New OCR callers should always supply it:
unknown confidence in a rich field is reviewed rather than treated as certain.
"""
import re
from datetime import date
from itertools import combinations

import rule_engine as legacy
from correction_guide import get_guidance

NAMES = ('name', 'father_name', 'mother_name', 'guardian_name', 'spouse_name')
EXTRA_FIELDS = NAMES[1:] + ('gender', 'mobile_number', 'pincode', 'place_of_birth')
ADDRESS_TYPES = ('aadhaar', 'passport', 'voter', 'driving', 'domicile',
                 'electricity', 'rent', 'bank', 'ration')
DOB_ORDER = ('birth certificate', '10th marksheet', 'passport', 'pan', 'aadhaar')
STATES = ('andhra pradesh', 'arunachal pradesh', 'assam', 'bihar', 'chhattisgarh',
          'goa', 'gujarat', 'haryana', 'himachal pradesh', 'jharkhand', 'karnataka',
          'kerala', 'madhya pradesh', 'maharashtra', 'manipur', 'meghalaya',
          'mizoram', 'nagaland', 'odisha', 'punjab', 'rajasthan', 'sikkim',
          'tamil nadu', 'telangana', 'tripura', 'uttar pradesh', 'uttarakhand',
          'west bengal', 'delhi', 'jammu and kashmir', 'ladakh', 'puducherry',
          'chandigarh')


def _type(doc, name):
    value = doc.get('document_type') or name
    return str(value).lower().replace('_', ' ')


def _flatten(data):
    doc = dict(data)
    fields = doc.get('doc_fields') or {}
    for field, entry in fields.items():
        doc[field] = entry.get('value') if isinstance(entry, dict) else entry
    return doc


def _uncertain(doc, field, threshold):
    entry = (doc.get('doc_fields') or {}).get(field)
    if isinstance(entry, dict):
        if entry.get('user_verified'):
            return False
        confidence = entry.get('confidence', 0)
        try:
            confidence = float(confidence)
        except (ValueError, TypeError):
            confidence = 0
        return bool(entry.get('needs_review') or confidence < threshold)
    confidence = (doc.get('fieldConfidence') or doc.get('fieldConfidences') or {}).get(field)
    if (doc.get('needsReview') or {}).get(field):
        return True
    return confidence is not None and float(confidence) < threshold


def _review():
    return ('Unable to Compare', 'needs_review', None,
            'Please confirm this value on the original document before comparing it; OCR confidence is low.', 'low')


def _different(message, possible=False):
    return ('Possible Mismatch' if possible else 'Mismatch',
            'possible_mismatch' if possible else 'mismatch', 0.0, message,
            'medium' if possible else 'high')


def _unavailable(message):
    return 'Unable to Compare', 'unable_to_verify', None, message, None


def _match(message='Values match.'):
    return 'Match', 'match', 1.0, message, None


def compare_name(a, b):
    if not a or not b:
        return legacy.compare_names(a, b)
    # Common spelling of the same prefix; this is not a general fuzzy identity merge.
    def normal(value):
        return re.sub(r'\b(?:mohd|mohammed|muhammad|mohammad)\b', 'mohammad',
                      ' '.join(legacy.normalize_name_tokens(value)))
    na, nb = normal(a), normal(b)
    if na.replace(' ', '') == nb.replace(' ', ''):
        return _match('Names match after joined/split-word normalization.')
    result = legacy.compare_names(na, nb)
    ta, tb = na.split(), nb.split()
    # One clearly different word must not disappear in a high whole-name score.
    if len(ta) == len(tb) and len(ta) > 1:
        ua, ub = list(ta), list(tb)
        for token in ta:
            if token in ub:
                ua.remove(token)
                ub.remove(token)
        if len(ua) == len(ub) == 1 and not (
            legacy.is_initial_match(ua[0], ub[0]) or legacy.is_initial_match(ub[0], ua[0])
        ):
            similarity = legacy.char_similarity(ua[0], ub[0])
            if similarity < .80:
                return _different('One name word is clearly different. Confirm the spelling and any documented name change.')
            if ua[0] != ub[0]:
                return _different('A name spelling differs. Confirm it on the original documents, including any documented name change.', True)
    return result


def compare_dob(a, b):
    da, ya = legacy._parse_date(a)
    db, yb = legacy._parse_date(b)
    if da and db and da != db:
        if da.year == db.year and da.day == db.month and da.month == db.day:
            return _different('Day and month appear swapped. Confirm both original dates before choosing a correction.', True)
        digits_a, digits_b = da.strftime('%Y%m%d'), db.strftime('%Y%m%d')
        if sum(x != y for x, y in zip(digits_a, digits_b)) == 1:
            return _different('Dates of birth differ by one digit. Confirm the original documents before correcting either.')
        return _different('Full dates of birth differ. Check the originals and the service requirements.')
    return legacy.compare_dob(a, b)


def compare_address(a, b):
    if not a or not b:
        return legacy.compare_address(a, b)
    def normalize(value):
        # S/O identifies a relationship, not a street component. Remove that line.
        value = re.sub(r'(?im)^\s*[sdwc]/o\s*[:.-]?[^\n,]*(?:[,\n]|$)', '', str(value))
        value = re.sub(r'\b(?:apt|apartment)\b', 'flat', value, flags=re.I)
        return ' '.join(legacy.normalize_address_tokens(value)[0])
    na, nb = normalize(a), normalize(b)
    sa = {s for s in STATES if re.search(r'\b' + re.escape(s) + r'\b', na)}
    sb = {s for s in STATES if re.search(r'\b' + re.escape(s) + r'\b', nb)}
    if sa and sb and sa.isdisjoint(sb):
        return _different('States differ between the two addresses.')
    pa, pb = legacy.PIN_RE.search(str(a)), legacy.PIN_RE.search(str(b))
    if pa and pb and pa.group() != pb.group():
        return _different('Postal PIN codes differ between the two addresses.')
    # A matching locality must not obscure a different house/flat number.
    houses = [re.search(r'\b(?:flat|house|plot|door)\s*(?:number\s*)?(\d+\w*)', x) for x in (na, nb)]
    if all(houses) and houses[0].group(1) != houses[1].group(1):
        return _different('House or flat numbers differ between the two addresses.')
    ta, tb = set(na.split()), set(nb.split())
    if len(ta) > 1 and len(tb) > 1 and (ta < tb or tb < ta):
        return _different('One address is partial. Confirm the missing house/locality details before treating it as the same residence.', True)
    if ta == tb and len(ta) > 1:
        return _match('Addresses match after abbreviation normalization.')
    return legacy.compare_address(a, b)


def _number(raw, doc=''):
    if isinstance(raw, dict):
        typ, val = raw.get('type'), str(raw.get('number') or '')
    elif ':' in str(raw):
        typ, val = str(raw).split(':', 1)
    else:
        typ, val = None, str(raw or '')
    typ = legacy.infer_doc_type('', typ or doc)
    return typ, re.sub(r'[\s-]', '', val).upper()


def compare_numbers(a, b, doc_a, doc_b):
    ta, va = _number(a, doc_a)
    tb, vb = _number(b, doc_b)
    if not ta or not tb or ta != tb:
        return _unavailable('Numbers from different or unidentified document types are not compared.')
    if not va or not vb:
        return _unavailable('Document number was not detected.')
    if ta == 'Aadhaar' and (re.search(r'[X*]', va) or re.search(r'[X*]', vb)):
        if len(va) != 12 or len(vb) != 12:
            return _unavailable('Masked Aadhaar format needs confirmation.')
        known = [(x, y) for x, y in zip(va, vb) if x not in 'X*' and y not in 'X*']
        if any(x != y for x, y in known):
            return _different('Visible Aadhaar digits differ.')
        return ('Unable to Compare', 'partial_match', None,
                'Visible Aadhaar digits agree; hidden digits cannot be verified from a masked copy.', None)
    return legacy.compare_doc_numbers(a, b, doc_a, doc_b)


def compare_mobile(a, b):
    def normalize(v):
        n = re.sub(r'[\s()+-]', '', str(v))
        return n[2:] if len(n) == 12 and n.startswith('91') else n.upper()
    va, vb = normalize(a), normalize(b)
    valid = lambda n: bool(re.fullmatch(r'[6-9X*][0-9X*]{9}', n))
    if not valid(va) or not valid(vb):
        return _unavailable('Please confirm this value: mobile number must be 10 Indian digits or a masked equivalent.')
    if any(x != y for x, y in zip(va, vb) if x not in 'X*' and y not in 'X*'):
        return _different('Visible mobile digits differ. A printed number does not establish current Aadhaar linkage.')
    if any(c in va + vb for c in 'X*'):
        return ('Unable to Compare', 'partial_match', None,
                'Visible mobile digits agree; masked digits and live Aadhaar linkage cannot be verified.', None)
    return _match('Mobile numbers match; live Aadhaar linkage has not been checked.')


def _extra_compare(field, a, b):
    if field in NAMES:
        return compare_name(a, b)
    if field == 'mobile_number':
        return compare_mobile(a, b)
    if field == 'gender':
        normalize = lambda x: {'m': 'male', 'f': 'female', 'पुरुष': 'male', 'महिला': 'female',
                               'स्त्री': 'female', 't': 'transgender'}.get(str(x).lower(), str(x).lower())
        va, vb = normalize(a), normalize(b)
        if va not in ('male', 'female', 'transgender', 'other') or vb not in ('male', 'female', 'transgender', 'other'):
            return _unavailable('Please confirm this value: gender could not be interpreted.')
    else:
        va, vb = legacy.normalize_text(a), legacy.normalize_text(b)
    if field == 'pincode' and not all(re.fullmatch(r'[1-9]\d{5}', str(v)) for v in (a, b)):
        return _unavailable('Please confirm this value: PIN code must be six digits and cannot start with zero.')
    return _match() if va == vb else _different(f'{field.replace("_", " ").capitalize()} differs between records.')


def _masked(value, field, doc):
    if field == 'doc_number' and _number(value, doc)[0] == 'Aadhaar':
        number = _number(value, doc)[1]
        return 'Aadhaar: XXXX XXXX ' + number[-4:] if len(number) == 12 else 'Aadhaar: [needs review]'
    return value


def check_extended_mismatches(documents, profile=None, policy=None, today=None):
    docs = {name: _flatten(data) for name, data in documents.items()}
    policy = policy or {}
    threshold = float(policy.get('min_confidence', .80))
    result = legacy._check_legacy_mismatches(docs)
    comparisons = []
    issues = []

    def add(field, name_a, name_b, outcome=None):
        da, db = docs[name_a], docs[name_b]
        a, b = da.get(field), db.get(field)
        if _uncertain(da, field, threshold) or _uncertain(db, field, threshold):
            outcome = _review()
        elif outcome is None:
            if field == 'name': outcome = compare_name(a, b)
            elif field == 'dob': outcome = compare_dob(a, b)
            elif field == 'address': outcome = compare_address(a, b)
            elif field == 'doc_number': outcome = compare_numbers(a, b, _type(da, name_a), _type(db, name_b))
            else: outcome = _extra_compare(field, a, b)
        res, verdict, similarity, explanation, severity = outcome
        # Legacy comparators include raw numbers in text; use a value-free message.
        if field == 'doc_number':
            explanation = {'Match': 'Document numbers match.', 'Mismatch': 'Visible document numbers differ.'}.get(res, explanation)
        comp = {'field': field, 'fieldName': field.replace('_', ' ').title(),
                'docA': name_a, 'docB': name_b, 'valA': _masked(a, field, name_a) if a else 'Not detected',
                'valB': _masked(b, field, name_b) if b else 'Not detected',
                'result': res, 'verdict': verdict, 'similarity': similarity, 'explanation': explanation}
        comparisons.append(comp)
        if res in ('Mismatch', 'Possible Mismatch') or verdict == 'needs_review':
            risk = {'moderate': 'medium', 'error': 'low'}.get(severity, severity) or 'low'
            issue = {**comp, 'documents': [name_a, name_b], 'values': [comp['valA'], comp['valB']],
                     'severity': risk, 'riskLevel': risk, 'message': explanation,
                     'correctionOptions': [get_guidance(name_a, field), get_guidance(name_b, field)]}
            if field == 'dob' and verdict != 'needs_review':
                def rank(name):
                    typ = _type(docs[name], name)
                    return next((i for i, pattern in enumerate(policy.get('dob_authority_order', DOB_ORDER)) if pattern in typ), 99)
                if rank(name_a) != rank(name_b):
                    reference, correction = sorted((name_a, name_b), key=rank)
                    issue.update(referenceDocument=reference, suggestedCorrectionDocument=correction,
                                 recommendationBasis='Configured document preference; confirm the originals and service rules before making a correction.')
            issues.append(issue)

    for comp in result['comparisons']:
        a, b, field = comp['docA'], comp['docB'], comp['field']
        if field == 'address' and not all(any(t in _type(docs[n], n) for t in ADDRESS_TYPES) for n in (a, b)):
            continue
        add(field, a, b)
    for a, b in combinations(docs, 2):
        if legacy.get_document_holder(a, docs[a]) != legacy.get_document_holder(b, docs[b]):
            continue
        for field in EXTRA_FIELDS:
            if docs[a].get(field) and docs[b].get(field):
                add(field, a, b)
    if profile:
        key = 'Registered profile'
        while key in docs: key += ' (profile)'
        docs[key] = {'name': profile.get('full_name'), 'mobile_number': profile.get('mobile_number')}
        for a in documents:
            if legacy.get_document_holder(a, docs[a]) != 'applicant': continue
            for field in ('name', 'mobile_number'):
                if docs[a].get(field) and docs[key].get(field): add(field, a, key)

    current_date = today or date.today()
    if isinstance(current_date, str): current_date = date.fromisoformat(current_date)
    for name in documents:
        data = docs[name]
        typ = _type(data, name)
        # Expiry is only inferred from an explicit printed date, never invented.
        if data.get('expiry_date') and any(t in typ for t in ('passport', 'driving', 'certificate', 'ews', 'caste', 'income')):
            expires, _ = legacy._parse_date(data['expiry_date'])
            if not expires:
                add('expiry_date', name, name, _review())
            else:
                remaining = (expires - current_date).days
                limit = int(policy.get('expiry_warning_days', 90))
                if remaining < 0:
                    add('expiry_date', name, name, _different('The printed validity date has passed. Check renewal requirements.'))
                elif remaining <= limit:
                    add('expiry_date', name, name, _different(f'The document expires within the configured {limit}-day warning window. Check service validity requirements.', True))
        if 'electricity' in typ and 'recent_bill_days' in policy and data.get('issue_date'):
            issued, _ = legacy._parse_date(data['issue_date'])
            if not issued or issued > current_date:
                add('issue_date', name, name, _review())
            elif (current_date - issued).days > int(policy['recent_bill_days']):
                add('issue_date', name, name, _different('The bill is older than the configured service age limit.', True))

    counts = {v: sum(c['result'] == v for c in comparisons) for v in ('Match', 'Possible Mismatch', 'Mismatch', 'Unable to Compare')}
    result.update(comparisons=comparisons, issues=issues, issuesFound=len(issues),
                  summary={'totalComparisons': len(comparisons), 'matches': counts['Match'],
                           'possibleMismatches': counts['Possible Mismatch'], 'mismatches': counts['Mismatch'],
                           'unableToCompare': counts['Unable to Compare']},
                  verifiedFieldCount=counts['Match'], unverifiedFieldCount=sum(c['result'] != 'Match' for c in comparisons))
    if issues:
        result['verificationStatus'] = 'issues_found'
    elif any(c['verdict'] in ('needs_review', 'partial_match') for c in comparisons):
        result['verificationStatus'] = 'partially_verified'
    result['clean'] = not issues and result['verificationStatus'] == 'verified'
    return result
