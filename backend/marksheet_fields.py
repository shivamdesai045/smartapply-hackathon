"""Label-driven board certificate fields. No inference of parents from student names."""
import re

LABELS = {
    "father_name": r"(?:father(?:['’]?s)?(?:\s*/\s*guardian(?:['’]?s)?)?\s*name|name\s*of\s*father|वडिलांचे\s*नाव|पिता\s*का\s*नाम)",
    "mother_name": r"(?:mother(?:['’]?s)?\s*name|name\s*of\s*mother|आईचे\s*नाव|माता\s*का\s*नाम)",
    "name": r"(?:candidate(?:['’]?s)?\s*(?:full\s*)?name|student(?:['’]?s)?\s*(?:full\s*)?name|name\s*of\s*(?:the\s*)?(?:candidate|student)|full\s+name|this\s+is\s+to\s+certify\s+that|(?m:^\s*name\s*[:：])|उमेदवाराचे\s*(?:पूर्ण\s*)?नाव)",
    "dob": r"(?:date\s*of\s*birth(?:\s*\(in\s*(?:figures|words)\))?|birth\s*date|d\.?\s*o\.?\s*b\.?|जन्म\s*(?:दिनांक|तारीख)|जन्मतिथि)",
    "roll_number": r"(?:roll\s*(?:no\.?|number))",
    "unique_id": r"(?:unique\s*(?:id|identification)(?:\s*(?:no\.?|number))?|\buid\b)",
    "index_number": r"(?:index\s*(?:no\.?|number))",
    "seat_number": r"(?:seat\s*(?:no\.?|number)|आसन\s*क्रमांक)",
    "certificate_number": r"(?:(?:certificate|serial)\s*(?:no\.?|number))",
    "school_name": r"(?:(?:school|college)(?:\s*/\s*college)?\s*name|name\s*of\s*(?:the\s*)?(?:school|college))",
    "exam_year": r"(?:year\s*of\s*passing|(?:exam(?:ination)?|passing)\s*year)",
}
# Non-identity labels terminate values too: never read a school code as a roll number.
STOP_LABELS = r"(?:school\s*(?:code|no\.?|number)|centre\s*(?:code|no\.?|number)|date\s*of\s*issue|result|subject|marks\s*obtained|division|grade|signature|head\s*master)\b"
ALL_LABELS = re.compile("|".join("(?:" + p + ")" for p in LABELS.values()) + "|" + STOP_LABELS, re.I)


def marksheet_date(value):
    """Accept explicit numeric, month-name and English written DOBs, never issue dates."""
    from document_fields import strict_date
    from datetime import date
    numeric = re.search(r"\b(?:\d{4}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*\d{1,2}|\d{1,2}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*\d{4})\b", value)
    if numeric:
        return strict_date(numeric.group())
    month_pattern = r"January|February|March|April|May|June|July|August|September|October|November|December"
    named = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?[\s-]+("+month_pattern+r")[\s,-]+((?:19|20)\d{2})\b", value, re.I)
    if named:
        return strict_date(' '.join(named.groups()))
    direct = strict_date(value)
    if direct:
        return direct
    words = re.sub(r"[-,]", " ", value.lower())
    words = re.sub(r"\s+", " ", words).strip()
    match = re.fullmatch(r"(.+?)\s+("+month_pattern.lower()+r")\s+(.+)", words)
    if not match:
        return None
    days = ['first','second','third','fourth','fifth','sixth','seventh','eighth','ninth','tenth','eleventh','twelfth','thirteenth','fourteenth','fifteenth','sixteenth','seventeenth','eighteenth','nineteenth','twentieth']
    day_map = {word:i+1 for i,word in enumerate(days)}
    day_map.update({'twenty '+word:21+i for i,word in enumerate(days[:9])})
    day_map.update({'thirtieth':30,'thirty first':31})
    units = dict(zip(['one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen'],range(1,20)))
    tens = dict(zip(['twenty','thirty','forty','fifty','sixty','seventy','eighty','ninety'],range(20,100,10)))
    def small(text):
        if not text:return 0
        if text in units:return units[text]
        if text in tens:return tens[text]
        bits=text.split()
        if len(bits)==2 and bits[0] in tens and bits[1] in units and units[bits[1]]<10:return tens[bits[0]]+units[bits[1]]
        return None
    year_text=match[3]
    year=None
    for prefix,base in [('two thousand',2000),('nineteen hundred',1900),('nineteen',1900),('twenty',2000)]:
        if year_text==prefix or year_text.startswith(prefix+' '):
            tail=year_text[len(prefix):].strip()
            if tail.startswith('and '):tail=tail[4:]
            count=small(tail)
            if count is not None:year=base+count
            break
    day=day_map.get(match[1])
    if not day or year is None:return None
    try:
        parsed=date(year,month_pattern.lower().split('|').index(match[2])+1,day)
        return parsed.isoformat() if parsed<=date.today() else None
    except ValueError:
        return None



def extract_marksheet_fields(text, chosen_option=None, ocr_data=None):
    from document_fields import strict_date, person
    if ocr_data and ocr_data.get('lines'):
        from aadhaar_fields import _visual_rows
        pages = {}
        for line in ocr_data['lines']:
            pages.setdefault(line.get('page', 1), []).append(line)
        rows = []
        for page in pages.values():
            words = [w for line in page for w in line.get('words', []) if len(w.get('bbox', [])) == 4]
            rows.extend(_visual_rows(words) if words else [line['text'] for line in page])
        text = '\n'.join(rows)
    values = {}
    conflicts = []
    # Inline columns and bilingual labels are common. Stop before the next field.
    for field, pattern in LABELS.items():
        candidates = []
        for match in re.finditer(pattern + r"\s*[:：\-–]?\s*", text, re.I):
            tail = text[match.end():]
            if field == 'name':
                tail = re.sub(r'^\s*\((?:surname\s+first|in\s+block\s+letters|in\s+full)\)\s*[:：]?\s*', '', tail, flags=re.I)
            if ALL_LABELS.match(tail):
                continue
            line = tail.splitlines()[0] if tail else ""
            boundary = ALL_LABELS.search(line)
            value = (line[:boundary.start()] if boundary else line).strip(" :|;-\t")
            if field in {"name", "father_name", "mother_name"}:
                value = person(re.split(r"\b(?:has\s+passed|son\s+of|daughter\s+of)\b", value, flags=re.I)[0].strip())
            elif field == "dob":
                numeric = re.search(r"\b(?:\d{4}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*\d{1,2}|\d{1,2}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*\d{4})\b", value)
                value = marksheet_date(value)
            elif field.endswith("number") or field == "unique_id":
                number = re.match(r"[A-Z0-9][A-Z0-9/.-]{2,30}\b", value, re.I)
                value = number.group().upper() if number and re.search(r"\d", number.group()) else None
            elif field == "exam_year":
                year = re.search(r"\b(?:19|20)\d{2}\b", value)
                value = year.group() if year else None
            if value:
                candidates.append(value)
        unique = {v.casefold(): v for v in candidates}
        # Conflicting repeat labels need human review, not first-match guessing.
        if len(unique) == 1:
            values[field] = next(iter(unique.values()))
        elif unique:
            values[field] = None
            conflicts.append(field)

    if re.search(r"maharashtra|msbshse", text, re.I):
        values["board"] = "Maharashtra State Board"
    elif re.search(r"central\s+board\s+of\s+secondary\s+education|\bcbse\b", text, re.I):
        values["board"] = "CBSE"
    elif re.search(r"council\s+for\s+the\s+indian\s+school|\bcisce\b|\bicse\b|\bisc\b", text, re.I):
        values["board"] = "CISCE"
    if re.search(r"higher\s+secondary|senior\s+school|\bh\.?s\.?c\.?\b|\bisc\b|class\s*(?:xii|12)\b|12th", text, re.I):
        values["exam_level"] = "12th"
    elif re.search(r"secondary\s+school|\bs\.?s\.?c\.?\b|\bicse\b|class\s*(?:x|10)\b|10th", text, re.I):
        values["exam_level"] = "10th"
    if "exam_level" in values:
        values["document_type"] = values["exam_level"] + " Marksheet"
    if "exam_year" not in values:
        years = re.findall(r"(?:examination|exam|march|february|april|may|june)\s*[,/-]?\s*((?:19|20)\d{2})\b", text, re.I)
        if len(set(years)) == 1:
            values["exam_year"] = years[0]
    if values.get("board"):
        values["issuing_authority"] = values["board"]
    for field in ("unique_id", "roll_number", "seat_number", "index_number", "certificate_number"):
        if values.get(field):
            values["doc_number"] = {"type": field.replace("_", " ").title(), "number": values[field]}
            break
    if any(field in conflicts for field in ("unique_id", "roll_number", "seat_number")):
        values["doc_number"] = None
        conflicts.append("doc_number")
    values["_conflicts"] = conflicts
    return values
