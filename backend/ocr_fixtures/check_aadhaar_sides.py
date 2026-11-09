"""End-to-end regression with invented data, never real uploaded documents.

Run from backend: ../.venv/Scripts/python.exe ocr_fixtures/check_aadhaar_sides.py
Results are field exact-match checks on synthetic layouts, not real-world accuracy.
"""
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import pymupdf as fitz
from ocr_extract import extract_fields


def card(back=False):
    image = Image.new("RGB", (1200, 750), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
    rows = (["Unique Identification Authority of India", "Address:",
             "C/O: Meera Example, Flat 12", "Test Nagar, Pune",
             "Maharashtra 411001", "XXXX XXXX 1234", "1947 help@uidai.gov.in"]
            if back else ["Government of India", "Aadhaar", "Aarav Example",
                          "DOB: 19/08/2002", "Male", "XXXX XXXX 1234"])
    for i, row in enumerate(rows):
        draw.text((50, 45 + 86 * i), row, font=font, fill="black")
    return image


def combined(images, horizontal):
    canvas = Image.new("RGB", (2500, 750) if horizontal else (1200, 1600), "white")
    for i, image in enumerate(images):
        canvas.paste(image, (1300 * i, 0) if horizontal else (0, 850 * i))
    return canvas


def main():
    results = []
    expected = {"name": "Aarav Example", "dob": "2002-08-19", "gender": "Male",
                "address": "C/O: Meera Example, Flat 12 Test Nagar, Pune Maharashtra 411001",
                "pincode": "411001", "father_name": None, "guardian_name": None}
    with tempfile.TemporaryDirectory(prefix="synthetic_aadhaar_") as temporary:
        root = Path(temporary)
        front, back = card(), card(True)
        cases = []
        for reverse in (False, True):
            sides = [back, front] if reverse else [front, back]
            suffix = "back_first" if reverse else "front_first"
            pdf = root / f"scanned_{suffix}.pdf"
            # Pillow stores PDF encoder options on images; fresh copies prevent a
            # later reversed save from recursively reusing the earlier page list.
            sides[0].copy().save(pdf, save_all=True, append_images=[sides[1].copy()], resolution=150)
            cases.append(pdf)
            for horizontal in (False, True):
                path = root / f"{'horizontal' if horizontal else 'stacked'}_{suffix}.png"
                combined(sides, horizontal).save(path)
                cases.append(path)
        path = root / "mild_blur.jpg"
        combined([front, back], False).filter(ImageFilter.GaussianBlur(.6)).save(path, quality=70)
        cases.append(path)
        path = root / "digital_two_pages.pdf"
        with fitz.open() as pdf:
            for side in (False, True):
                page = pdf.new_page()
                lines = (["Unique Identification Authority of India", "Address:",
                          "C/O: Meera Example, Flat 12", "Test Nagar, Pune", "Maharashtra 411001", "XXXX XXXX 1234"]
                         if side else ["Government of India", "Aadhaar", "Aarav Example", "DOB: 19/08/2002", "Male", "XXXX XXXX 1234"])
                page.insert_text((50, 70), "\n".join(lines), fontsize=15)
            pdf.save(path)
        cases.append(path)
        for path in cases:
            start = time.monotonic()
            output = extract_fields(str(path), path.name, "Aadhaar Card")
            checks = {field: output.get(field) == value for field, value in expected.items()}
            number = output.get("doc_number") or {}
            checks["masked_number"] = number.get("number", "").replace(" ", "") == "XXXXXXXX1234"
            entry = {"case": path.stem, "checks": checks, "seconds": round(time.monotonic() - start, 2)}
            results.append(entry)
            print(json.dumps(entry), flush=True)
    report = {"scope": "Invented English fixtures only; not a real-document accuracy estimate", "results": results,
              "passed": sum(all(r["checks"].values()) for r in results), "total": len(results)}
    destination = Path(__file__).parent / "reports" / "aadhaar_sides.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "total": report["total"]}))
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
