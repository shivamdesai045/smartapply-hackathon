"""Reconcile Aadhaar fields within page and column boundaries; never guess digits."""
import re
from collections import defaultdict

NAME_LABEL = r"(?:name|नाम|नाव)"
DOB_LABEL = r"(?:D\.?\s*O\.?\s*B\.?|date\s*of\s*birth|जन्म\s*(?:तिथि|तारीख|दिनांक)|जन्मतारीख|year\s*of\s*birth|YOB)"
ADDRESS_LABEL = r"(?:Address|पत्ता|पता)"
NUMBER = r"(?<![\dA-Z])(?:[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}|[Xx*]{4}[ -]?[Xx*]{4}[ -]?\d{4})(?!\d)"
STOP = r"\b(?:VID|UIDAI|www|help|1947|download|issue|DOB|name|Aadhaar|Government|Unique|enrolment|enrollment)\b|" + NUMBER


def _visual_rows(words):
    """Rejoin separate PDF spans on one baseline, preserving visual reading order."""
    rows = []
    for word in sorted(words, key=lambda w: ((w['bbox'][1] + w['bbox'][3]) / 2, w['bbox'][0])):
        box = word['bbox']
        middle, height = (box[1] + box[3]) / 2, box[3] - box[1]
        if rows and abs(middle - rows[-1][0]) <= max(.003, min(height, rows[-1][1]) * .55):
            rows[-1][2].append(word)
        else:
            rows.append((middle, height, [word]))
    return [' '.join(w['text'] for w in sorted(row[2], key=lambda w: w['bbox'][0])) for row in rows]


def _regions(ocr_data):
    """Separate pages and clear gutters that have front/back anchors on each side.

    PSM 6 can join adjacent cards into a single line. Recover columns from word
    coordinates without another OCR pass. Do not split arbitrary address lines.
    """
    from document_fields import normalize_digits
    pages = defaultdict(list)
    for line in ocr_data.get('lines', []):
        if line.get('text', '').strip():
            pages[line.get('page', 1)].append(line)
    if not pages:
        return [[r.strip() for r in normalize_digits(ocr_data.get('text', '')).splitlines() if r.strip()]]
    regions = []
    for lines in pages.values():
        words = [word for line in lines for word in line.get('words', [])
                 if word.get('text') and len(word.get('bbox', [])) == 4]
        if not words:
            regions.append([normalize_digits(line['text']).strip() for line in
                            sorted(lines, key=lambda line: (line.get('bbox', [0, 0])[1], line.get('bbox', [0])[0]))])
            continue
        intervals = sorted((w['bbox'][0], w['bbox'][2]) for w in words)
        gaps, end = [], intervals[0][1]
        for start, stop in intervals[1:]:
            if start - end > .025 and .2 < (start + end) / 2 < .8:
                gaps.append((start - end, (start + end) / 2))
            end = max(end, stop)
        split = None
        for _, cut in sorted(gaps, reverse=True):
            left = [w for w in words if w['bbox'][2] <= cut]
            right = [w for w in words if w['bbox'][0] >= cut]
            texts = [' '.join(w['text'] for w in side) for side in (left, right)]
            anchored = any(re.search(DOB_LABEL, texts[i], re.I) and
                           re.search(ADDRESS_LABEL, texts[1-i], re.I) for i in (0, 1))
            if anchored and min(len(left), len(right)) >= 5:
                split = (left, right)
                break
        for side in split or (words,):
            regions.append([normalize_digits(row).strip() for row in _visual_rows(side)])
    return regions


def _holder(value):
    from document_fields import person
    name = person(re.sub(r'^' + NAME_LABEL + r'(?:\s*[:：]\s*|\s+)', '', value, flags=re.I))
    if name and not re.search(r'\b(?:government|india|authority|identification|aadhaar|uidai|download|enrol|issued|signature|male|female|gender|proof|citizenship|information|verify)\b', name, re.I):
        return name
    return None


def _prefer_latin(options):
    latin = [v for v in options if re.search(r'[A-Za-z]', v) and not re.search(r'[\u0900-\u097f]', v)]
    return latin or options


def extract_sides(ocr_data):
    from document_fields import person, strict_date
    values = dict.fromkeys(('name', 'dob', 'gender', 'address', 'father_name', 'guardian_name', 'pincode', 'doc_number'))
    candidates = {key: [] for key in values}
    numbers, reasons = [], []
    for rows in _regions(ocr_data):
        explicit_names, nearby_names = [], []
        for idx, row in enumerate(rows):
            dob_label = re.search(DOB_LABEL + r'\s*[:：/\-]?\s*(.*)', row, re.I)
            if dob_label:
                # Keep the value after the last label in bilingual DOB headings.
                labels = list(re.finditer(DOB_LABEL, row, re.I))
                date_text = row[labels[-1].end():].lstrip(' :：/-')
                if not date_text and idx+1 < len(rows):
                    date_text = rows[idx+1]
                match = re.match(r'(\d{1,4}\s*[/\.\-]\s*\d{1,2}\s*[/\.\-]\s*\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|(?:19|20)\d{2})\b', date_text)
                date_value = re.sub(r'\s*([/.\-])\s*', r'\1', match[1]) if match else None
                parsed = strict_date(date_value, allow_year=True) if date_value else None
                if parsed:
                    candidates['dob'].append(parsed)
                prior = []
                for before in rows[max(0, idx-3):idx][::-1]:
                    if re.search(ADDRESS_LABEL + r'|[scdw]\s*/\s*o|father|mother|guardian|' + NUMBER, before, re.I):
                        break
                    holder = _holder(before)
                    if holder:
                        prior.append(holder)
                if prior:
                    nearby_names.append(_prefer_latin(prior)[0])
            named = re.match(r'^' + NAME_LABEL + r'\s*[:：]\s*(.*)$', row, re.I)
            if named:
                name_text = named[1] or (rows[idx+1] if idx+1 < len(rows) else '')
                if _holder(name_text):
                    explicit_names.append(_holder(name_text))
            gender = re.search(r'\b(Male|Female|Transgender)\b|पुरुष|महिला|स्त्री', row, re.I)
            if gender:
                candidates['gender'].append({'male':'Male', 'female':'Female', 'transgender':'Transgender', 'पुरुष':'Male', 'महिला':'Female', 'स्त्री':'Female'}[gender[0].lower()])
            relation = re.search(r'\b([SDCW])\s*/\s*O\s*[:：]?\s*([^,\n]+)', row, re.I)
            if relation and relation[1].upper() in {'S', 'D'} and person(relation[2]):
                candidates['father_name'].append(person(relation[2]))
            anchor = re.match(r'^' + ADDRESS_LABEL + r'(?:\s*[:：]\s*(.*)|\s*)$', row, re.I)
            if anchor:
                block = [anchor[1] or '']
                for following in rows[idx+1:idx+11]:
                    if re.search(STOP, following, re.I) or re.match(ADDRESS_LABEL + r'\s*[:：]?$', following, re.I):
                        break
                    if re.search(r'(?<!\d)[1-9]\d{5}(?!\d)', ' '.join(block)):
                        break
                    block.append(following)
                address = ' '.join(filter(None, block))
                pin = re.search(r'(?<!\d)([1-9]\d{5})(?!\d)', address)
                if pin:
                    address = address[:pin.end()]
                    candidates['pincode'].append(pin[1])
                if len(address.split()) >= 3:
                    candidates['address'].append(address)
            if not re.search(r'\bVID\b|enrol', row, re.I):
                numbers.extend(re.sub(r'[ -]', '', match[0]).upper().replace('*', 'X') for match in re.finditer(NUMBER, row))
        candidates['name'].extend(explicit_names or nearby_names)

    unique = set(numbers)
    if len({n[-4:] for n in unique}) > 1 or len({n for n in unique if n.isdigit()}) > 1:
        # Do not produce an apparently complete identity from unrelated cards.
        values['_review_reasons'] = ['Aadhaar numbers differ between sides. Upload both sides of the same card.']
        return values
    if unique:
        value = next((n for n in unique if n.isdigit()), next(iter(unique)))
        values['doc_number'] = {'type': 'Aadhaar', 'number': value}
    for field, options in candidates.items():
        if field in ('name', 'address', 'father_name'):
            options = _prefer_latin(options)
        if field == 'dob' and len({v[:4] for v in options}) == 1:
            options = [v for v in options if len(v) > 4] or options
        distinct = {re.sub(r'\s+', ' ', v).strip().casefold(): v for v in options}
        if len(distinct) == 1:
            values[field] = next(iter(distinct.values()))
        elif len(distinct) > 1:
            reasons.append(f'Conflicting {field.replace("_", " ")} readings; confirm against the document.')
    values['_review_reasons'] = reasons
    return values
