"""Reproducible, plainly labelled synthetic OCR inputs; no government replicas."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ROOT = Path(__file__).parent
NAME, FATHER, MOTHER = "Aarav Example", "Suresh Example", "Meena Example"
ADDRESS = "Flat 12, Test Nagar, Pune, Maharashtra 411001"


def generate():
    font_path = next((p for p in [Path("C:/Windows/Fonts/arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")] if p.exists()), None)
    font = ImageFont.truetype(str(font_path), 28) if font_path else ImageFont.load_default(size=28)
    common = {"name": NAME, "dob": "2002-08-19"}
    records = [
        ("aadhaar", "Aadhaar Card", ["Unique Identification Authority - Aadhaar", f"Name: {NAME}", f"S/O: {FATHER}", "DOB: 19/08/2002", "Gender: Male", f"Address: {ADDRESS}", "Aadhaar: XXXX XXXX 1234"], {**common, "father_name": FATHER, "gender": "Male", "address": ADDRESS, "pincode": "411001", "doc_number": "XXXX XXXX 1234", "document_type": "Aadhaar Card"}),
        ("pan", "PAN Card", ["Income Tax Department", "Permanent Account Number: ABCZE1234F", f"Name: {NAME}", f"Father's Name: {FATHER}", "Date of Birth: 19/08/2002"], {**common, "father_name": FATHER, "doc_number": "ABCZE1234F", "document_type": "PAN Card"}),
        ("passport", "Passport", ["Passport - Republic of India", "Passport No: Z0000000", "Given Name(s): Aarav", "Surname: Example", f"Father's Name: {FATHER}", f"Mother's Name: {MOTHER}", "Date of Birth: 19/08/2002", "Sex: Male", "Place of Birth: Pune", f"Address: {ADDRESS}", "Date of Issue: 01/06/2024", "Date of Expiry: 31/05/2034"], {**common, "father_name": FATHER, "mother_name": MOTHER, "gender": "Male", "place_of_birth": "Pune", "address": ADDRESS, "pincode": "411001", "doc_number": "Z0000000", "issue_date": "2024-06-01", "expiry_date": "2034-05-31", "document_type": "Passport"}),
        ("voter", "Voter ID Card", ["Election Commission of India", "Elector Photo Identity Card", "EPIC No: TST0000000", f"Name: {NAME}", f"Father's Name: {FATHER}", "Date of Birth: 19/08/2002", "Gender: Male", f"Address: {ADDRESS}"], {**common, "father_name": FATHER, "gender": "Male", "address": ADDRESS, "pincode": "411001", "doc_number": "TST0000000", "document_type": "Voter ID Card"}),
        ("birth", "Birth Certificate", ["Birth Certificate", "Registration of Birth", f"Name: {NAME}", f"Father's Name: {FATHER}", f"Mother's Name: {MOTHER}", "Date of Birth: 19/08/2002", "Gender: Male", "Place of Birth: Pune", "Date of Issue: 01/09/2002", "Issuing Authority: Municipal Registrar"], {**common, "father_name": FATHER, "mother_name": MOTHER, "gender": "Male", "place_of_birth": "Pune", "issue_date": "2002-09-01", "issuing_authority": "Municipal Registrar", "document_type": "Birth Certificate"}),
    ]
    for level in ("10th", "12th"):
        for board in ("Maharashtra Board", "CBSE", "ICSE"):
            label = "ISC" if board == "ICSE" and level == "12th" else board
            year = "2018" if level == "10th" else "2020"
            doc_type = f"{level} Marksheet"
            records.append((f"{level}_{board.lower().replace(' ', '_')}", doc_type, [f"{label} Statement of Marks", f"{level} Marksheet", f"Student Name: {NAME}", f"Father's Name: {FATHER}", f"Mother's Name: {MOTHER}", "Date of Birth: 19/08/2002", f"Exam Level: {level}", f"Exam Year: {year}"], {**common, "father_name": FATHER, "mother_name": MOTHER, "exam_level": level, "exam_year": year, "document_type": doc_type}))
    fixtures = []
    for slug, doc_type, lines, expected in records:
        height = max(650, 150 + len(lines) * 48)
        clean = Image.new("RGB", (1100, height), "white")
        draw = ImageDraw.Draw(clean)
        draw.text((35, 20), "SYNTHETIC TEST ONLY - NOT A VALID DOCUMENT", font=font, fill=(90, 90, 90))
        for i, line in enumerate(lines):
            draw.text((45, 100 + i * 48), line, font=font, fill="black")
        for quality in ("clean", "phone"):
            image = clean
            if quality == "phone":
                image = clean.resize((770, round(height * .7))).filter(ImageFilter.GaussianBlur(.55))
                image = ImageEnhance.Contrast(image).enhance(.66)
                image = ImageEnhance.Brightness(image).enhance(.80).rotate(2.2, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(205,205,205))
            filename = f"{slug}_{quality}.png"
            image.save(ROOT / filename)
            fixtures.append({"id": f"{slug}_{quality}", "file": filename, "document_type": doc_type, "quality": quality, "synthetic": True, "pages": 1, "expected": expected})
    manifest = {"schema_version": 1, "synthetic": True, "description": "Plain labelled synthetic text sheets, not replicas. Phone fixtures simulate downsampling, blur, darkness and skew. No real or consented scans were supplied. PAN deliberately uses invalid entity Z. Masked Aadhaar has no real full number.", "limitations": ["Small deterministic development set; not held out", "English only; not representative of real Hindi/Marathi layouts", "Phone images are simulated, not camera captures", "No MRZ, holograms, seals, complex background, e-Aadhaar encryption or multipage layouts in this extraction accuracy set"], "fixtures": fixtures}
    (ROOT / "ground_truth.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(f"Generated {len(generate()['fixtures'])} labelled synthetic raster fixtures")
