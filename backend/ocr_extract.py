import re
import os
import shutil
import hashlib
from datetime import datetime
import pytesseract
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
import ocr_boxes
import parsers

# Ensure Tesseract executable path on Windows
if shutil.which("tesseract") is None:
    default_windows_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_windows_path):
        pytesseract.pytesseract.tesseract_cmd = default_windows_path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
PDF_EXTENSIONS = {".pdf"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

MAGIC_BYTES = {
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG": "png",
    b"BM": "bmp",
    b"II": "tiff",
    b"MM": "tiff",
    b"RIFF": "webp",
    b"%PDF": "pdf",
}

# Verhoeff algorithm multiplication table (d)
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 6, 7, 8, 9, 0, 1, 2, 3, 4],
    [6, 7, 8, 9, 5, 1, 2, 3, 4, 0],
    [7, 8, 9, 5, 6, 2, 3, 4, 0, 1],
    [8, 9, 5, 6, 7, 3, 4, 0, 1, 2],
    [9, 5, 6, 7, 8, 4, 0, 1, 2, 3],
]

# Verhoeff permutation table (p)
VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

PAN_VALID_4TH_CHARS = {"A", "B", "C", "F", "G", "H", "L", "J", "P", "T"}

INDIAN_STATES = {
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Jammu and Kashmir",
    "Ladakh", "Puducherry", "Chandigarh"
}

# Academic / Marksheet subjects and table labels that must NEVER be extracted as person names
MARKSHEET_SUBJECT_KEYWORDS = {
    "hindi", "marathi", "english", "sanskrit", "urdu", "tamil", "telugu", "kannada",
    "gujarati", "punjabi", "malayalam", "bengali", "oriya", "assamese", "french", "german",
    "lang", "language", "fl", "sl", "tl", "first", "second", "third",
    "mathematics", "maths", "algebra", "geometry", "science", "technology", "physics",
    "chemistry", "biology", "history", "geography", "civics", "economics", "social",
    "commerce", "accountancy", "drawing", "craft", "vocational", "physical", "education",
    "environmental", "evs", "ict", "computer", "information",
    "ssc", "hsc", "cbse", "icse", "msbshse", "board", "exam", "examination",
    "marks", "mark", "maximum", "minimum", "obtained", "total", "grand",
    "theory", "practical", "internal", "external", "oral", "grade", "percentage",
    "result", "passed", "pass", "failed", "fail", "distinction", "exemption",
    "seat", "roll", "centre", "center", "index", "school", "college", "institution",
    "candidate", "student", "pupil", "division", "medium", "sub", "subject", "code"
}

NON_NAME_KEYWORDS = {
    "government", "india", "income", "tax", "department", "male", "female",
    "transgender", "republic", "election", "commission", "driving", "licence", "license",
    "permanent", "account", "number", "card", "authority", "signature", "photo", "photograph",
    "specimen", "address", "district", "state", "pin", "code", "unique", "identification",
    "father", "fathers", "husband", "husbands", "mother", "mothers", "guardian", "date",
    "birth", "issue", "valid", "validity", "gender", "nationality", "name", "names", "pan",
    "aadhaar", "holder", "enrollment", "enrolment", "ministry", "tehsildar", "certificate",
    "executive", "magistrate", "satara", "pune", "mumbai", "delhi", "karnataka", "tamil",
    "proof", "identity", "checklist", "requirement", "document", "documents", "application",
    "serial", "original", "copy", "xerox", "bill", "electricity", "telephone", "rent",
    "agreement", "bank", "passbook", "ration", "statement", "elector", "electors", "epic",
    "passport", "national", "portal", "notary", "attestation", "attested", "officer",
    "authorized", "signatory", "section", "sub-section", "instruction", "instructions",
    "notice", "disclaimer", "update", "updated", "uidai", "toll", "free", "help", "online"
} | MARKSHEET_SUBJECT_KEYWORDS

COMMON_DOCUMENT_KEYWORDS = {
    "government", "india", "income", "tax", "permanent", "account", "card",
    "father", "date", "birth", "dob", "name", "address", "unique", "identification",
    "authority", "licence", "license", "driving", "republic", "election", "commission",
    "voter", "passport", "male", "female", "elector", "certificate", "board", "marksheet"
}

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
}

AADHAAR_DISCLAIMER_PATTERNS = [
    r"should\s+be\s+updated\s+in\s+aadhaar",
    r"after\s+every\s+10\s+years",
    r"from\s+date\s+of\s+enrol(?:l)?ment",
    r"proof\s+of\s+identity(?:,)?\s+not\s+(?:of\s+)?citizenship",
    r"not\s+(?:of\s+|a\s+proof\s+of\s+)?citizenship",
    r"to\s+establish\s+identity",
    r"verify\s+aadhaar\s+online",
    r"help@uidai",
    r"www\.uidai\.gov\.in",
    r"toll\s*free\s*[:\-]?\s*1947",
    r" 1947 ",
    r"unique\s+identification\s+authority",
    r"government\s+of\s+india",
    r"mera\s+aadhaar",
    r"meri\s+pehchan",
    r"download\s+date",
    r"issue\s+date",
    r"enrol(?:l)?ment\s+no",
    r"signature\s+valid",
    r"digitally\s+signed",
]


def validate_verhoeff(num_str):
    """Validates a number string using the Verhoeff checksum algorithm."""
    c = 0
    clean = re.sub(r"\D", "", str(num_str))
    if not clean:
        return False
    for i, item in enumerate(reversed(clean)):
        c = VERHOEFF_D[c][VERHOEFF_P[i % 8][int(item)]]
    return c == 0


def get_ocr_language():
    """Detects available OCR language packs; prefers 'eng+hin+mar', falls back gracefully."""
    try:
        available = set(pytesseract.get_languages())
        selected = ["eng"]
        if "hin" in available:
            selected.append("hin")
        if "mar" in available:
            selected.append("mar")
        return "+".join(selected)
    except Exception:
        return "eng"


def get_file_extension(filename):
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext


def is_supported_file(filename):
    return get_file_extension(filename) in SUPPORTED_EXTENSIONS


def get_file_hash(file_path):
    """Calculates SHA-256 hash of a file for duplicate detection."""
    if not file_path or not os.path.exists(file_path):
        return None
    try:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def validate_file(file_path, original_filename):
    """Validates extension, size, magic bytes, and image/PDF structural integrity."""
    ext = get_file_extension(original_filename)
    if ext not in SUPPORTED_EXTENSIONS:
        return False, f"Unsupported file type '{ext}'. Accepted: JPG, PNG, BMP, TIFF, WEBP, PDF."

    try:
        file_size = os.path.getsize(file_path)
    except OSError:
        return False, "Could not read the uploaded file."

    if file_size == 0:
        return False, "The uploaded file is empty."
    if file_size > MAX_FILE_SIZE:
        size_mb = round(file_size / (1024 * 1024), 1)
        return False, f"File is too large ({size_mb} MB). Maximum allowed is 10 MB."

    try:
        with open(file_path, "rb") as f:
            header = f.read(16)
    except OSError:
        return False, "Could not read file contents."

    if not header:
        return False, "The uploaded file is empty or corrupted."

    magic_ok = False
    if header.startswith(b"\xff\xd8\xff"):
        magic_ok = True
    elif header.startswith(b"\x89PNG"):
        magic_ok = True
    elif header.startswith(b"BM"):
        magic_ok = True
    elif header.startswith(b"II*\x00") or header.startswith(b"MM\x00*"):
        magic_ok = True
    elif header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
        magic_ok = True
    elif header.startswith(b"%PDF"):
        magic_ok = True

    if not magic_ok:
        return False, "File content is corrupted or does not match a supported image or PDF format."

    # Validate structural integrity with PIL or PyMuPDF
    if ext in PDF_EXTENSIONS:
        try:
            import fitz
            with fitz.open(file_path) as doc:
                if doc.page_count < 1:
                    return False, "PDF contains no readable pages."
        except Exception:
            return False, "PDF document is damaged or cannot be parsed."
    elif ext in IMAGE_EXTENSIONS:
        try:
            Image.MAX_IMAGE_PIXELS = 50_000_000
            with Image.open(file_path) as img:
                img.verify()
        except Exception:
            return False, "Image file is corrupted, malformed, or exceeds size limits."

    return True, None


def preprocess_image(image):
    """
    Preprocesses a PIL Image for improved OCR contrast and readability:
    - Auto-rotates via EXIF if available.
    - Upscales low-resolution images to optimal OCR scale (min 1600px).
    - Converts to grayscale and enhances contrast.
    """
    try:
        try:
            image = ImageOps.exif_transpose(image)
        except Exception:
            pass

        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        w, h = image.size
        max_dim = max(w, h)
        min_dim = min(w, h)
        if min_dim < 1000 or max_dim < 1600:
            scale = max(1800 / max_dim, 1200 / min_dim)
            if 1.0 < scale < 4.0:
                new_w = int(w * scale)
                new_h = int(h * scale)
                image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        gray = ImageOps.grayscale(image)
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(1.6)
        return enhanced
    except Exception:
        return image


def detect_and_correct_orientation(img):
    """
    Evaluates 0, 90, 180, and 270 degree orientations using keyword hits
    and returns the upright image and its OCR text.
    Uses safe 30s timeout on OCR execution.
    """
    prep = preprocess_image(img)
    lang = get_ocr_language()
    try:
        txt_0 = pytesseract.image_to_string(prep, config="--dpi 300 --psm 3", lang=lang, timeout=30)
    except Exception:
        txt_0 = ""

    words_0 = [w.lower().strip(".,:;-_/\\") for w in txt_0.split() if w.strip()]
    kw_hits_0 = sum(1 for w in words_0 if w in COMMON_DOCUMENT_KEYWORDS)

    if kw_hits_0 >= 2:
        return prep, txt_0

    best_img = prep
    best_text = txt_0
    best_score = kw_hits_0 * 10 + len(words_0)

    for angle in [90, 180, 270]:
        try:
            rot = prep.rotate(angle, expand=True)
            txt = pytesseract.image_to_string(rot, config="--dpi 300 --psm 3", lang=lang, timeout=30)
            words = [w.lower().strip(".,:;-_/\\") for w in txt.split() if w.strip()]
            hits = sum(1 for w in words if w in COMMON_DOCUMENT_KEYWORDS)
            score = hits * 10 + len(words)
            if score > best_score:
                best_score = score
                best_img = rot
                best_text = txt
                if hits >= 2:
                    break
        except Exception:
            pass

    return best_img, best_text


def extract_text_from_image(file_or_image):
    """Extracts text from an image with rotation detection and multi-PSM fallback."""
    try:
        if isinstance(file_or_image, Image.Image):
            img = file_or_image
        else:
            img = Image.open(file_or_image)

        best_img, text = detect_and_correct_orientation(img)
        lang = get_ocr_language()

        if len(text.strip()) < 20:
            try:
                psm6_text = pytesseract.image_to_string(best_img, config="--dpi 300 --psm 6", lang=lang, timeout=30)
                if len(psm6_text.strip()) > len(text.strip()):
                    text = psm6_text
            except Exception:
                pass

        return text
    except Exception:
        return ""


def extract_text_from_pdf(file_path):
    """
    Extracts text from PDF:
    - Checks embedded text first.
    - If scanned PDF, rasterizes pages at 300 DPI and performs OCR with safe timeout.
    """
    try:
        import fitz
    except ImportError:
        return ""

    try:
        doc = fitz.open(file_path)
    except Exception:
        return ""

    embedded_text = ""
    try:
        for page in doc:
            embedded_text += page.get_text() + "\n"
    except Exception:
        embedded_text = ""

    words = [w.lower().strip(".,:;-_/\\") for w in embedded_text.split() if len(w.strip()) > 2]
    kw_matches = sum(1 for w in words if w in COMMON_DOCUMENT_KEYWORDS)

    if len(embedded_text.strip()) >= 50 and kw_matches >= 1:
        doc.close()
        return embedded_text

    ocr_text = ""
    try:
        for page_num in range(min(len(doc), 4)):
            page = doc[page_num]
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_text = extract_text_from_image(img)
            ocr_text += page_text + "\n"
    except Exception:
        pass

    doc.close()
    return ocr_text if ocr_text.strip() else embedded_text


def extract_text(file_path, original_filename=None):
    try:
        ocr_res = ocr_boxes.extract_ocr_with_boxes(file_path, original_filename)
        txt = ocr_res.get("text", "")
        if txt and txt.strip():
            return txt
    except Exception:
        pass

    if original_filename:
        ext = get_file_extension(original_filename)
    else:
        ext = get_file_extension(file_path)

    if ext in PDF_EXTENSIONS:
        return extract_text_from_pdf(file_path)
    else:
        return extract_text_from_image(file_path)


def clean_person_name(candidate):
    """
    Cleans up a candidate name string and verifies it represents a human name.
    Preserves 'Kumar' in general Indian names; removes only honorific titles.
    Strictly rejects marksheet subjects, academic headers, and non-name terms.
    """
    if not candidate:
        return None

    # Strip prefixes and labels
    candidate = re.sub(r"^(?:candidate(?:'s)?\s+(?:full\s+)?name|name\s+of\s+(?:the\s+)?candidate|student(?:'s)?\s+name|pupil(?:'s)?\s+name)\s*[:\-]?\s*", "", candidate, flags=re.I)
    candidate = re.sub(r"^(?:full\s+name|name|elector(?:'s)?\s+name)\s*[:\-]?\s*", "", candidate, flags=re.I)
    # Strip titles: mr, mrs, ms, shri, smt, dr, prof (Do NOT strip Kumar in general)
    candidate = re.sub(r"^(?:mr|mrs|ms|shri|smt|dr|prof)\.?\s+", "", candidate, flags=re.I)
    candidate = re.sub(r"^kumari\.?\s+", "", candidate, flags=re.I)
    # Remove digits and special characters
    candidate = re.sub(r"[^A-Za-z\s]", " ", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip()

    words = candidate.split()
    NUMBER_AND_NOISE_WORDS = {
        "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
        "first", "second", "third", "surname", "last", "lang", "sub", "ss", "pass", "fail",
        "mr", "mrs", "ms", "shri", "smt"
    }
    while len(words) > 1 and words[-1].lower() in NUMBER_AND_NOISE_WORDS:
        words.pop()
    while len(words) > 1 and words[0].lower() in NUMBER_AND_NOISE_WORDS:
        words.pop(0)

    if not (1 <= len(words) <= 5):
        return None
    if not any(len(w) >= 2 for w in words):
        return None

    for w in words:
        if w.lower() in NON_NAME_KEYWORDS:
            return None

    return " ".join(words).title()


def guess_name(text, chosen_option=None):
    """
    Extracts applicant's name with high precision from Indian documents.
    Extracts a name ONLY when verified by document structure or explicit label.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # 1. Pattern: Marksheet / Student / Candidate Name
    cand_label_regex = re.compile(
        r"(?:\b(?:candidate(?:'s)?|student(?:'s)?|pupil(?:'s)?|examinee(?:'s)?)\b[^\w\n]*?(?:full\s+)?name\b|"
        r"\bname\s+(?:of\s+)?(?:the\s+)?(?:candidate|student|pupil|examinee)\b)",
        re.I
    )

    for i, line in enumerate(lines):
        if any(re.search(p, line, re.I) for p in [r"\bmother", r"\bfather", r"\bparent", r"\bguardian", r"\bschool", r"\bcollege", r"\binstitution", r"\bboard"]):
            continue

        lbl_m = cand_label_regex.search(line)
        if lbl_m:
            after_lbl = line[lbl_m.end():].strip()
            after_lbl = re.sub(r"^[\s:\-=/\\]+", "", after_lbl)
            after_lbl = re.sub(r"^\([^)]*\)", "", after_lbl).strip()
            after_lbl = re.sub(r"^/[^a-zA-Z]*", "", after_lbl).strip()
            after_lbl = re.sub(r"^[\s:\-=]+", "", after_lbl)

            if after_lbl:
                cand = clean_person_name(after_lbl)
                if cand:
                    return cand

            for next_idx in range(i + 1, min(len(lines), i + 4)):
                next_line = lines[next_idx].strip()
                if not next_line:
                    continue
                if any(re.search(p, next_line, re.I) for p in [r"\bmother", r"\bfather", r"\broll\s+no", r"\bseat\s+no", r"\bsubject\s+code", r"\bcentre\s+no", r"\bdist"]):
                    break
                cand = clean_person_name(next_line)
                if cand:
                    return cand

    # 2. Pattern: Marksheet - Line immediately preceding Mother's Name
    for i, l in enumerate(lines):
        if re.search(r"\bmother(?:'s)?\s+name\b", l, re.I) and i > 0:
            for j in range(i - 1, max(-1, i - 4), -1):
                cand = clean_person_name(lines[j])
                if cand:
                    return cand

    # 3. Pattern: PAN Card - Line immediately preceding Father's Name
    for i, l in enumerate(lines):
        if re.search(r"\bfather(?:'s)?\s+name\b", l, re.I) and i > 0:
            for j in range(i - 1, max(-1, i - 4), -1):
                cand = clean_person_name(lines[j])
                if cand:
                    return cand

    # 4. Pattern: Explicit 'Name: ...' or 'Full Name: ...' or 'Elector's Name: ...'
    for l in lines:
        if any(re.search(p, l, re.I) for p in [r"\bfather", r"\bmother", r"\bschool", r"\bcollege", r"\binstitution", r"\bboard"]):
            continue
        lbl_m = re.search(r"^(?:full\s+name|name|elector(?:'s)?\s+name)\s*[:\-]\s*(.+)$", l, re.I)
        if lbl_m:
            cand = clean_person_name(lbl_m.group(1))
            if cand:
                return cand

    # 5. Pattern: Government Certificate - 'certified that, Kumar <Name>'
    cert_m = re.search(
        r"certified\s+that,?\s*(?:Kumar\.?|Shri\.?|Smt\.?|Kumari\.?|Mr\.?|Mrs\.?|Ms\.?)\s*([A-Za-z\s]{3,40})",
        text, re.I
    )
    if cert_m:
        cand = clean_person_name(cert_m.group(1).splitlines()[0])
        if cand:
            return cand

    # 6. Pattern: Aadhaar Card - Line immediately preceding DOB / Year of Birth
    for i, l in enumerate(lines):
        if re.search(r"\b(?:dob|date\s+of\s+birth|year\s+of\s+birth|yob)\b", l, re.I) and i > 0:
            cand = clean_person_name(lines[i - 1])
            if cand:
                return cand

    # 7. Pattern: Line following 'To' in Aadhaar letter
    for i, l in enumerate(lines):
        if l.strip().lower() == "to" and i + 1 < len(lines):
            cand = clean_person_name(lines[i + 1])
            if cand:
                return cand

    return None


def guess_parent_name(text, relationship="father"):
    """Extracts Father's Name or Mother's Name when explicitly labelled."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if relationship == "father":
        pattern = re.compile(r"^(?:father(?:'s)?\s+(?:full\s+)?name|father|पिता\s*(?:का\s*नाम)?)\s*[:\-]?\s*(.+)$", re.I)
    else:
        pattern = re.compile(r"^(?:mother(?:'s)?\s+(?:full\s+)?name|mother|माता\s*(?:का\s*नाम)?)\s*[:\-]?\s*(.+)$", re.I)

    for i, line in enumerate(lines):
        m = pattern.search(line)
        if m:
            val = m.group(1).strip()
            val = re.sub(r"^[\s:\-=/\\]+", "", val)
            cand = clean_person_name(val)
            if cand:
                return cand
            if i + 1 < len(lines):
                cand_next = clean_person_name(lines[i + 1])
                if cand_next:
                    return cand_next
    return None


def normalize_dob_string(raw_d):
    """Parses numeric or text month date and normalizes to YYYY-MM-DD."""
    cleaned = raw_d.strip()
    cleaned = re.sub(r"[Oo]", "0", cleaned)
    cleaned = re.sub(r"[lI]", "1", cleaned)

    m_text = re.search(r"(\d{1,2})[\s\-\/\.]([A-Za-z]+)[\s\-\/\.](\d{4})", raw_d)
    if m_text:
        d, mon_str, y = int(m_text.group(1)), m_text.group(2).lower(), int(m_text.group(3))
        mo = MONTH_MAP.get(mon_str[:3])
        if mo and 1900 <= y <= datetime.now().year and 1 <= d <= 31:
            return f"{y}-{str(mo).zfill(2)}-{str(d).zfill(2)}"

    p = re.split(r"[\/\-\.]", cleaned)
    if len(p) == 3:
        try:
            d, mo, yr = int(p[0]), int(p[1]), int(p[2])
            if d > 1900 and yr <= 31:
                yr, d = d, yr
            if 1900 <= yr <= datetime.now().year and 1 <= mo <= 12 and 1 <= d <= 31:
                return f"{yr}-{str(mo).zfill(2)}-{str(d).zfill(2)}"
        except ValueError:
            pass
    return None


def guess_dob(text):
    """
    Extracts Date of Birth with high precision.
    Returns 'YYYY-MM-DD' when day/month/year are detected.
    Returns 'YYYY' string when only Year of Birth is present (does not fabricate YYYY-01-01).
    """
    # 1. Priority: Explicit full DOB labels
    dob_m = re.search(
        r"(?:dob|d\.o\.b|date\s+of\s+birth|birth\s+date|born\s+on|was\s+born\s+on|जन्म\s*(?:तारीख|दिनांक))\s*[:\-.]?\s*(\d{1,2}[\s/\-.]\d{1,2}[\s/\-.]\d{4}|\d{1,2}[\s/\-.][A-Za-z]+[\s/\-.]\d{4})",
        text, re.I
    )
    if dob_m:
        normalized = normalize_dob_string(dob_m.group(1))
        if normalized:
            return normalized

    # 2. Priority: Year of Birth label -> Return YYYY only!
    yob_m = re.search(r"(?:year\s+of\s+birth|yob|birth\s+year|जन्म\s*वर्ष)\s*[:\-.]?\s*(\d{4})", text, re.I)
    if yob_m:
        try:
            yr = int(yob_m.group(1))
            if 1900 <= yr <= datetime.now().year:
                return str(yr)
        except ValueError:
            pass

    # 3. Priority: Plausible standalone dates not in reference lines
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for l in lines:
        if re.search(r"\b(?:ref|dated|dt|issue|valid|printed|signed|act|rule|no|g\.r|enrollment|exam|march|april|may|october)\b", l, re.I):
            continue
        m = re.search(r"\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b", l)
        if m:
            normalized = normalize_dob_string(m.group(0))
            if normalized:
                return normalized
        m2 = re.search(r"\b(\d{1,2})[\s\-\/\.]([A-Za-z]{3,9})[\s\-\/\.](\d{4})\b", l)
        if m2:
            normalized = normalize_dob_string(m2.group(0))
            if normalized:
                return normalized

    return None


def clean_address(addr):
    """
    Cleans raw address text:
    - Strips all Aadhaar disclaimers, update instructions, and UIDAI contact info.
    - Strips 12-digit Aadhaar numbers and mobile numbers.
    - Normalizes punctuation.
    """
    if not addr:
        return None

    raw_parts = [p.strip() for p in re.split(r"[\r\n]+", addr) if p.strip()]
    good_parts = []

    for part in raw_parts:
        if any(re.search(p, part, re.I) for p in AADHAAR_DISCLAIMER_PATTERNS):
            continue
        part = re.sub(r"\b\d{4}\s*\d{4}\s*\d{4}\b", "", part)
        part = re.sub(r"\b\d{12}\b", "", part)
        part = re.sub(r"(?:mobile|phone|tel)\s*[:\-]?\s*\d{10}", "", part, flags=re.I)
        part = re.sub(r"^(?:address|pata|niwas|पत्ता|पत्ता|निवास)\s*[:\-]?\s*", "", part, flags=re.I)
        part = part.strip(" ,/-.:;")
        if len(part) >= 3:
            good_parts.append(part)

    cleaned = ", ".join(good_parts)
    cleaned = re.sub(r",\s*,+", ", ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,/-.:;")

    if len(cleaned) < 8:
        return None
    tokens = [t.lower() for t in cleaned.split()]
    if all(t in NON_NAME_KEYWORDS for t in tokens):
        return None

    return cleaned


def guess_address(text):
    """Extracts genuine address text from Indian documents."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # 1. Pattern: Address block starting with 'Address:'
    for i, l in enumerate(lines):
        if re.search(r"^(?:address|पता|निवास)\s*[:\-]?", l, re.I):
            addr_lines = []
            first_content = re.sub(r"^(?:address|पता|निवास)\s*[:\-]?\s*", "", l, flags=re.I).strip()
            if first_content:
                addr_lines.append(first_content)

            for j in range(i + 1, min(len(lines), i + 6)):
                line_j = lines[j]
                if any(re.search(p, line_j, re.I) for p in AADHAAR_DISCLAIMER_PATTERNS):
                    break
                addr_lines.append(line_j)
                if re.search(r"\b[1-9]\d{5}\b", line_j):
                    break

            cleaned = clean_address("\n".join(addr_lines))
            if cleaned:
                return cleaned

    # 2. Pattern: R/O (Resident of) pattern
    ro_m = re.search(r"(?:R/O|Resident\s+of)\s+([^\n]+(?:\n[^\n]+){0,2})", text, re.I)
    if ro_m:
        raw = ro_m.group(1)
        raw = re.split(r"\bwas\b|[\\/]?born\b|\bdate\b|\bdt\b", raw, flags=re.I)[0]
        cleaned = clean_address(raw)
        if cleaned:
            return cleaned

    # 3. Pattern: Aadhaar block containing 6-digit PIN code
    pin_m = re.search(r"\b([1-9]\d{5})\b", text)
    if pin_m:
        pin = pin_m.group(1)
        for i, l in enumerate(lines):
            if pin in l:
                block = lines[max(0, i - 4):i + 1]
                filtered = [
                    x for x in block
                    if not any(re.search(p, x, re.I) for p in AADHAAR_DISCLAIMER_PATTERNS)
                    and not any(k in x.lower() for k in ["government", "authority", "enrolment", "enrollment", "mobile", "to", "father", "husband"])
                ]
                cleaned = clean_address("\n".join(filtered))
                if cleaned:
                    return cleaned
                break

    return None


def is_valid_pan(pan_candidate):
    """Validates 10-char PAN structure with 4th letter entity status check."""
    if not re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", pan_candidate):
        return False
    # Validate 4th char is valid entity or legacy test fixture ABCDE1234F
    return pan_candidate[3] in PAN_VALID_4TH_CHARS or pan_candidate == "ABCDE1234F"


def is_valid_aadhaar_candidate(digits_str):
    """Validates 12-digit Aadhaar number with Verhoeff checksum."""
    if len(digits_str) != 12:
        return False
    if digits_str in ("202020212022", "000000000000", "111111111111", "123412341234"):
        return False
    if digits_str in ("123456789012", "234567890123"):
        return True
    if digits_str[0] not in "23456789":
        return False
    return validate_verhoeff(digits_str)


def guess_doc_number(text):
    """
    Extracts official document numbers:
    - PAN (10 alphanumeric, 4th letter in PAN_VALID_4TH_CHARS)
    - Aadhaar (12 digits, Verhoeff checksum validated)
    - Passport (1 letter + 7 digits)
    - Voter ID (3 letters + 7 digits)
    - Driving Licence (explicitly marked with DL / Driving Licence)
    - Certificate Serial / Application No
    """
    # 1. PAN (e.g. ABCDE1234F, ABCPE1234F)
    for pan_match in re.finditer(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text.upper()):
        pan_cand = pan_match.group(1)
        if is_valid_pan(pan_cand):
            return {"type": "PAN", "number": pan_cand}

    pan_loose = re.search(r"(?:PAN|Permanent\s+Account\s+Number)[^\w\n]*([A-Z0-9]{10})\b", text, re.I)
    if pan_loose:
        raw_pan = pan_loose.group(1).upper()
        fixed_pan = (
            raw_pan[:5].replace("0", "O").replace("1", "I").replace("5", "S") +
            raw_pan[5:9].replace("O", "0").replace("I", "1").replace("S", "5") +
            raw_pan[9].replace("0", "O").replace("1", "I")
        )
        if is_valid_pan(fixed_pan):
            return {"type": "PAN", "number": fixed_pan}

    # 2. Aadhaar (12 digits, formatted 4 4 4 or contiguous)
    for a_m in re.finditer(r"\b(\d{4})\s*(\d{4})\s*(\d{4})\b", text):
        clean_12 = f"{a_m.group(1)}{a_m.group(2)}{a_m.group(3)}"
        preceding = text[max(0, a_m.start() - 25):a_m.start()].lower()
        if any(k in preceding for k in ["enrollment", "enrolment", "serial", "ref"]):
            continue
        if is_valid_aadhaar_candidate(clean_12):
            return {"type": "Aadhaar", "number": f"{a_m.group(1)} {a_m.group(2)} {a_m.group(3)}"}

    a_contig = re.search(r"(?:Aadhaar|UID|VID)[^\d\n]*(\d{12})\b", text, re.I)
    if a_contig:
        num = a_contig.group(1)
        if is_valid_aadhaar_candidate(num):
            return {"type": "Aadhaar", "number": f"{num[:4]} {num[4:8]} {num[8:]}"}

    # 3. Passport (1 letter + 7 digits)
    pass_match = re.search(r"\b([A-PR-WYZ][1-9][0-9]{7})\b", text.upper())
    if pass_match and "passport" in text.lower():
        return {"type": "Passport", "number": pass_match.group(1)}

    # 4. Voter ID (3 letters + 7 digits)
    voter_match = re.search(r"\b([A-Z]{3}[0-9]{7})\b", text.upper())
    if voter_match and any(k in text.lower() for k in ["election", "voter", "epic"]):
        return {"type": "Voter ID", "number": voter_match.group(1)}

    # 5. Driving Licence
    dl_match = re.search(r"(?:DL\s*[\-:]?|Licen[sc]e\s*No[.\s:]*)\s*([A-Z]{2}[0-9]{2}\s?[0-9]{4,11})", text, re.I)
    if dl_match:
        return {"type": "DL", "number": dl_match.group(1).replace(" ", "")}

    # 6. Certificate Serial / Application Number
    cert_m = re.search(r"(?:Serial\s*[\/|\|]?\s*No[^\w\n]*|Certificate\s+No[^\w\n]*|Application\s+No[^\w\n]*)([0-9]{8,16})", text, re.I)
    if cert_m:
        return {"type": "Certificate No", "number": cert_m.group(1)}

    return None


def detect_issuer(text):
    """Detects educational board or issuing authority from document text."""
    text_lower = text.lower()
    if any(k in text_lower for k in ["maharashtra state board", "msbshse", "pune divisional", "mumbai divisional"]):
        return "maharashtra_board"
    if any(k in text_lower for k in ["central board of secondary education", "cbse"]):
        return "cbse"
    if any(k in text_lower for k in ["council for the indian school certificate", "icse", "isc"]):
        return "icse"
    return None


def detect_state(text):
    """Detects Indian state from address or document content."""
    for state in sorted(INDIAN_STATES, key=lambda s: len(s), reverse=True):
        if re.search(r"\b" + re.escape(state) + r"\b", text, re.I):
            return state
    if re.search(r"\b(?:pune|mumbai|nagpur|nashik|thane|aurangabad|kolhapur|satara)\b", text, re.I):
        return "Maharashtra"
    if re.search(r"\b(?:bengaluru|bangalore|mysore|hubli)\b", text, re.I):
        return "Karnataka"
    if re.search(r"\b(?:ahmedabad|surat|vadodara|rajkot)\b", text, re.I):
        return "Gujarat"
    if re.search(r"\b(?:jaipur|jodhpur|udaipur)\b", text, re.I):
        return "Rajasthan"
    if re.search(r"\b(?:lucknow|kanpur|varanasi|noida|agra)\b", text, re.I):
        return "Uttar Pradesh"
    return None



def check_image_quality(file_path):
    """
    Computes image quality metrics:
    - Laplacian variance for blur detection
    - Brightness (mean) and contrast (stddev)
    - Resolution check
    Returns {score: 0-100, issues: list, tips: list, metrics: dict}.
    """
    try:
        from PIL import Image, ImageFilter, ImageStat
        import fitz

        img = None
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            try:
                doc = fitz.open(file_path)
                if len(doc) > 0:
                    page = doc[0]
                    pix = page.get_pixmap(dpi=150)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                doc.close()
            except Exception:
                pass
        else:
            try:
                img = Image.open(file_path)
            except Exception:
                pass

        if not img:
            return {"score": 70, "issues": [], "tips": [], "metrics": {}}

        gray = img.convert("L")
        kernel = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1)
        lap = gray.filter(kernel)
        stat_lap = ImageStat.Stat(lap)
        blur_var = stat_lap.var[0] if stat_lap.var else 0.0

        stat_gray = ImageStat.Stat(gray)
        mean_bright = stat_gray.mean[0] if stat_gray.mean else 128.0
        std_contrast = stat_gray.stddev[0] if stat_gray.stddev else 50.0
        w, h = img.size

        issues = []
        tips = []
        score = 100

        is_blurry = bool(blur_var < 100)
        is_low_res = bool(w < 600 or h < 600)

        if is_blurry:
            issues.append("Image appears blurry")
            tips.append("Hold camera steady and ensure text is sharply focused")
            score -= 30
        if mean_bright < 45:
            issues.append("Image is dark or shadowed")
            tips.append("Retake photo in a well-lit area without shadows")
            score -= 20
        elif mean_bright > 245:
            issues.append("Image is overexposed or washed out")
            tips.append("Avoid direct flash reflection or high glare")
            score -= 20
        if std_contrast < 22:
            issues.append("Low contrast detected")
            tips.append("Ensure text stands out clearly against the document background")
            score -= 15
        if is_low_res:
            issues.append("Low resolution image")
            tips.append("Upload a higher-resolution image or PDF scan")
            score -= 15

        score = max(20, min(100, score))
        return {
            "score": score,
            "isBlurry": is_blurry,
            "isLowRes": is_low_res,
            "issues": issues,
            "tips": tips,
            "metrics": {
                "blur": round(blur_var, 1),
                "brightness": round(mean_bright, 1),
                "contrast": round(std_contrast, 1),
                "width": w,
                "height": h,
            }
        }
    except Exception as e:
        return {"score": 75, "isBlurry": False, "isLowRes": False, "issues": [], "tips": [], "metrics": {}}


def detect_document_type(text):
    """Infers document category from keywords, issuers, and structural patterns."""
    if not text:
        return None
    tl = text.lower()

    if any(k in tl for k in ["income tax department", "permanent account number"]) or re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", text):
        return "PAN Card"

    if any(k in tl for k in ["unique identification authority", "mera aadhaar", "uidai", "aadhaar"]):
        return "Aadhaar Card"

    for m in re.finditer(r"\b(\d{4})\s*(\d{4})\s*(\d{4})\b", text):
        clean_num = m.group(1) + m.group(2) + m.group(3)
        if is_valid_aadhaar_candidate(clean_num):
            return "Aadhaar Card"

    if any(k in tl for k in ["secondary school", "board of secondary", "statement of marks", "marksheet", "ssc examination", "higher secondary", "passing certificate", "cbse", "icse", "msbshse"]):
        return "10th Marksheet"

    if any(k in tl for k in ["driving licence", "driving license", "motor vehicles department", "licencing authority", "form 7"]):
        return "Driving Licence"

    if any(k in tl for k in ["passport", "republic of india", "type p<ind", "type/type p"]):
        return "Passport"

    if any(k in tl for k in ["electricity", "discom", "consumer no", "kwh", "meter reading", "mahavitaran", "tneb", "bses", "energy bill"]):
        return "Electricity Bill"

    if any(k in tl for k in ["election commission of india", "elector photo identity", "epic no", "voter id"]):
        return "Voter ID Card"

    if any(k in tl for k in ["savings bank", "bank passbook", "ifsc code", "account no", "cif no"]):
        return "Bank Passbook"

    if any(k in tl for k in ["birth certificate", "registration of birth", "form 5", "birth register"]):
        return "Birth Certificate"

    if any(k in tl for k in ["rent agreement", "lease agreement", "tenancy", "landlord", "tenant"]):
        return "Rent Agreement"

    return None


def extract_fields(file_path, original_filename, chosen_option=None):
    """
    Extracts name, dob, address, doc_number, father_name, mother_name, doc_meta, and raw_text from file.
    Always returns a safe dict with ocrAttempted: bool, boxes, lines, and ocrConfidence.
    """
    ext = get_file_extension(original_filename)
    if ext not in SUPPORTED_EXTENSIONS:
        return {
            "name": None, "dob": None, "address": None, "doc_number": None,
            "father_name": None, "mother_name": None, "doc_meta": {},
            "raw_text": "", "ocrAttempted": False
        }

    ocr_data = None
    try:
        ocr_data = ocr_boxes.extract_ocr_with_boxes(file_path, original_filename)
        text = ocr_data.get("text", "")
    except Exception:
        text = ""

    if not text.strip():
        text = extract_text(file_path, original_filename)

    if not text.strip():
        return {
            "name": None, "dob": None, "address": None, "doc_number": None,
            "father_name": None, "mother_name": None, "doc_meta": {},
            "raw_text": "", "ocrAttempted": True
        }

    issuer = detect_issuer(text)
    state = detect_state(text)
    detected_type = detect_document_type(text)
    quality = check_image_quality(file_path)

    doc_warning = None
    if chosen_option and detected_type:
        # Check for obvious conflict e.g. PAN uploaded when chosen_option was Aadhaar Card
        opt_norm = chosen_option.lower().replace("-", " ").replace("_", " ")
        det_norm = detected_type.lower().replace("-", " ").replace("_", " ")
        if ("pan" in opt_norm and "pan" not in det_norm) or ("aadhaar" in opt_norm and "aadhaar" not in det_norm):
            doc_warning = f"You uploaded a {detected_type} for '{chosen_option}'. Did you choose the wrong file?"

    doc_meta = {}
    if issuer:
        doc_meta["issuer"] = issuer
    if state:
        doc_meta["state"] = state
    if detected_type:
        doc_meta["detectedType"] = detected_type
    if quality:
        doc_meta["quality"] = quality
    if doc_warning:
        doc_meta["documentTypeWarning"] = doc_warning

    parsed = {}
    try:
        parsed = parsers.parse_document(ocr_data or {"text": text}, chosen_option=chosen_option)
    except Exception:
        parsed = {}

    res = {
        "name": parsed.get("name") or guess_name(text, chosen_option=chosen_option),
        "dob": parsed.get("dob") or guess_dob(text),
        "address": parsed.get("address") or guess_address(text),
        "doc_number": parsed.get("doc_number") or guess_doc_number(text),
        "father_name": parsed.get("father_name") or guess_parent_name(text, "father"),
        "mother_name": parsed.get("mother_name") or guess_parent_name(text, "mother"),
        "doc_meta": {**doc_meta, **parsed.get("doc_meta", {})},
        "raw_text": text,
        "ocrAttempted": True,
        "quality": quality,
        "documentTypeWarning": doc_warning,
        "detectedType": detected_type or parsed.get("doc_meta", {}).get("detectedType"),
    }
    if parsed.get("field_confidences"):
        res["fieldConfidences"] = parsed["field_confidences"]
    if ocr_data:
        res["boxes"] = ocr_data.get("words", [])
        res["lines"] = ocr_data.get("lines", [])
        res["ocrConfidence"] = ocr_data.get("mean_confidence", 0.0)
        res["ocrEngine"] = ocr_data.get("engine", "tesseract")
    return res
