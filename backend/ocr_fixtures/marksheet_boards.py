"""Generate separate synthetic board/level coverage, not official replicas."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).parent
CASES = [
    ("ssc", "Maharashtra State Board Secondary School Certificate SSC", "10th", "Maharashtra State Board"),
    ("hsc", "Maharashtra State Board Higher Secondary Certificate HSC", "12th", "Maharashtra State Board"),
    ("cbse10", "Central Board of Secondary Education Class X", "10th", "CBSE"),
    ("cbse12", "Central Board of Secondary Education Class XII", "12th", "CBSE"),
    ("icse", "Council for the Indian School Certificate Examinations ICSE", "10th", "CISCE"),
    ("isc", "Council for the Indian School Certificate Examinations ISC", "12th", "CISCE"),
]

def generate():
    fixtures = []
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 27)
    for slug, header, level, board in CASES:
        lines = [header, "STATEMENT OF MARKS - SYNTHETIC TEST ONLY", "Candidate Name: Aarav Example",
                 "Mother's Name: Meera Example", "Father's Name: Suresh Example", "Date of Birth: 19/08/2002",
                 "Roll No.: 12345678", "Seat No.: A123456", "Examination March 2020", "School Name: Example Public School",
                 "ENGLISH 080     MATHEMATICS 090     SCIENCE 085", "Date of Issue: 01/06/2020"]
        img = Image.new("RGB", (1500, 800), "white")
        draw = ImageDraw.Draw(img)
        for n, line in enumerate(lines):
            draw.text((40, 30 + n*55), line, fill="black", font=font)
        for quality in ("clean", "phone"):
            out = img if quality == "clean" else img.resize((1200,640)).filter(ImageFilter.GaussianBlur(.4)).rotate(1.5, expand=True, fillcolor="white")
            name = f"board_{slug}_{quality}"
            out.save(ROOT / f"{name}.png")
            fixtures.append({"id": name, "file": name+".png", "document_type": level+" Marksheet", "quality": quality, "pages": 1,
                "expected": {"name": "Aarav Example", "father_name": "Suresh Example", "mother_name": "Meera Example", "dob": "2002-08-19",
                    "exam_year": "2020", "exam_level": level, "board": board, "roll_number": "12345678", "seat_number": "A123456", "school_name": "Example Public School"}})
    (ROOT / "boards.json").write_text(json.dumps({"synthetic": True, "limitations": ["12 synthetic English sheets; no real board accuracy claim", "Simulated phone degradation; no seals or complex table backgrounds"], "fixtures": fixtures}, indent=2))

if __name__ == "__main__":
    generate()
