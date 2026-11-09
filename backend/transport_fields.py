"""Conservative driving/learner licence labels; no guesses from unrelated dates."""
import re

PATTERNS = {
    "name": r"(?:name(?:\s+of\s+(?:the\s+)?(?:applicant|holder))?|applicant(?:'s)?\s+name)",
    "father_name": r"(?:father(?:'s)?\s+name|s/o|d/o)",
    "guardian_name": r"(?:s\s*/\s*w\s*/\s*d\s*(?:of)?|son\s*/\s*daughter\s*/\s*wife\s+of|guardian(?:'s)?\s+name)",
    "spouse_name": r"(?:w/o|spouse(?:'s)?\s+name)",
    "dob": r"(?:date\s+of\s+birth|d\.?o\.?b\.?)",
    "issue_date": r"(?:date\s+of\s+issue|issue\s+date|issued\s+on|doi)",
    "expiry_date": r"(?:valid\s+(?:till|until|upto|up\s+to)|date\s+of\s+expiry|expiry\s+date)",
    "address": r"(?:(?:permanent|present|residential)\s+address|address)",
    "vehicle_classes": r"(?:class(?:es)?\s+of\s+vehicles?|cov|vehicle\s+class)",
    "issuing_authority": r"(?:licensing\s+authority|issuing\s+authority|issued\s+by)",
    "doc_number": r"(?:(?:learner(?:'s|s)?\s+)?licen[cs]e\s*(?:no\.?|number)|(?:dl|ll|llr)\s*(?:no\.?|number))",
}

def extract_transport(text):
    from document_fields import person, strict_date
    rows = [r.strip() for r in text.splitlines() if r.strip()]
    boundary = re.compile(r"(?:" + "|".join(PATTERNS.values()) + r")\s*[:：]", re.I)
    values = {k:None for k in PATTERNS}
    values["_conflicts"] = []
    for field, pattern in PATTERNS.items():
        candidates = []
        for i,row in enumerate(rows):
            m = re.match(r"^(?:"+pattern+r")\s*[:：\-]?\s*(.*)$", row, re.I)
            if not m:
                continue
            value = m[1].strip()
            if not value and i+1 < len(rows) and not boundary.match(rows[i+1]):
                value = rows[i+1]
            end = boundary.search(value)
            value = value[:end.start()].strip() if end else value
            if field.endswith("name"):
                value = person(value)
            elif field in {"dob","issue_date","expiry_date"}:
                value = strict_date(value)
            elif field == "doc_number":
                value = re.sub(r"\s+", "", value).upper()
                value = value if re.fullmatch(r"[A-Z0-9][A-Z0-9/.-]{5,29}",value) and any(c.isdigit() for c in value) else None
            elif field == "address":
                parts=[value]
                for following in rows[i+1:i+6]:
                    if boundary.match(following) or re.search(r"(?<!\d)[1-9]\d{5}(?!\d)", " ".join(parts)):
                        break
                    parts.append(following)
                value=" ".join(parts)
                pin=re.search(r"(?<!\d)[1-9]\d{5}(?!\d)",value)
                value=value[:pin.end()] if pin else value
            if value:
                candidates.append(value)
        if len(set(candidates))==1:
            values[field]=candidates[0]
        elif len(set(candidates))>1:
            values["_conflicts"].append(field)
    learner=bool(re.search(r"learner(?:'s|s)?\s+licen[cs]e|learning\s+licen[cs]e",text,re.I))
    values['document_type']='Learner Licence' if learner else 'Driving Licence'
    if values['doc_number']:
        values['doc_number']={'type':'LL' if learner else 'DL','number':values['doc_number']}
    if values['address']:
        pins=set(re.findall(r"(?<!\d)[1-9]\d{5}(?!\d)",values['address']))
        values['pincode']=next(iter(pins)) if len(pins)==1 else None
    return values
