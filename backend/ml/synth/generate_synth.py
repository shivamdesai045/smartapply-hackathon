"""
Synthetic Dataset Generator for Sahayak Document Evaluation Harness.

STRICT COMPLIANCE RULES:
1. "Do NOT generate realistic fake ID card images or replicas of government documents.
    Synthetic data = TEXT + BOUNDING BOXES only."
2. "Synthetic ID numbers must be provably invalid:
    - Aadhaar-like numbers fail Verhoeff checksum.
    - PAN-like strings use an invalid 4th letter ('Z')."
3. "Do not use those checks as ML features."
4. Plain text formatting only; no logos, emblems, holograms, or card designs.
"""

import os
import re
import csv
import json
import random
import pymupdf as fitz

# Verhoeff tables to verify invalidity
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

def fails_verhoeff(num_str):
    clean = re.sub(r"\D", "", str(num_str))
    if len(clean) != 12:
        return True
    c = 0
    for i, item in enumerate(reversed(clean)):
        c = VERHOEFF_D[c][VERHOEFF_P[i % 8][int(item)]]
    return c != 0  # True if it fails Verhoeff

def make_invalid_aadhaar(rng):
    while True:
        digits = [rng.randint(2, 9)] + [rng.randint(0, 9) for _ in range(11)]
        s = "".join(str(d) for d in digits)
        if fails_verhoeff(s) and s not in ("123456789012", "234567890123"):
            return f"{s[:4]} {s[4:8]} {s[8:]}"

def make_invalid_pan(rng, name):
    p1 = "".join(rng.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=3))
    p4 = "Z"  # Strictly invalid entity letter (not A,B,C,F,G,H,L,J,P,T)
    p5 = name.split()[-1][0].upper() if name else "X"
    digits = f"{rng.randint(1000, 9999)}"
    p_last = rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return f"{p1}{p4}{p5}{digits}{p_last}"

FIRST_NAMES = [
    "Aarav", "Pooja", "Rohan", "Neha", "Vikram",
    "Ananya", "Aditya", "Sneha", "Kunal", "Priyanka"
]
MIDDLE_NAMES = [
    "Kumar", "Suresh", "Ramesh", "Dattatray", "Shashikant",
    "Mohan", "Gopal", "Prakash", "Ashok", "Kishore"
]
LAST_NAMES = [
    "Sharma", "Patel", "Kulkarni", "Verma", "Desai",
    "Mehta", "Joshi", "Iyer", "Reddy", "Choudhury"
]
FATHER_FIRSTS = [
    "Suresh", "Dinesh", "Ramesh", "Dattatray", "Shashikant",
    "Mohan", "Gopal", "Prakash", "Ashok", "Kishore"
]
MOTHER_FIRSTS = [
    "Sunita", "Meena", "Sharda", "Laxmi", "Kavita",
    "Geeta", "Rekha", "Usha", "Mangala", "Sangeeta"
]

ADDRESSES = [
    ("House No 42, Sector 15, Gandhinagar, Gujarat 382016", "382016"),
    ("Flat 301, Lake View Apts, MG Road, Pune, Maharashtra 411001", "411001"),
    ("Plot 88, Anna Salai, T Nagar, Chennai, Tamil Nadu 600017", "600017"),
    ("House 12B, Park Street, Kolkata, West Bengal 700016", "700016"),
    ("Flat 104, Green Glen Layout, Bellandur, Bengaluru, Karnataka 560103", "560103"),
    ("B-202, Shanti Vihar, Rohini Sector 9, New Delhi 110085", "110085"),
    ("House 55, Banjara Hills Road No 3, Hyderabad, Telangana 500034", "500034"),
    ("Row House 7, CIDCO Colony, Nashik, Maharashtra 422009", "422009"),
    ("Flat 5A, Civil Lines, Jaipur, Rajasthan 302006", "302006"),
    ("Quarter 412, Sector 4, Bokaro Steel City, Jharkhand 827004", "827004"),
]

DATES_OF_BIRTH = [
    ("1992-05-14", "14/05/1992"),
    ("1988-11-23", "23/11/1988"),
    ("1995-08-19", "19/08/1995"),
    ("2001-03-30", "30/03/2001"),
    ("1997-12-05", "05/12/1997"),
    ("1985-07-10", "10/07/1985"),
    ("2003-01-22", "22/01/2003"),
    ("1990-09-18", "18/09/1990"),
    ("1978-04-12", "12/04/1978"),
    ("1999-06-25", "25/06/1999"),
]

def generate_dataset(output_dir=None, count_per_type=10):
    """
    Generates synthetic text PDFs and sidecar bounding boxes for evaluation.
    Outputs:
    - 60 plain text PDFs
    - 60 corresponding .boxes.json files
    - labels.csv
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(output_dir, exist_ok=True)
    rng = random.Random(42)  # Deterministic seed for reproducible baseline

    records = []

    doc_types = [
        "Aadhaar Card",
        "PAN Card",
        "10th Marksheet",
        "Passport",
        "Voter ID",
        "Driving Licence",
    ]

    for doc_type in doc_types:
        for idx in range(count_per_type):
            fn = FIRST_NAMES[idx % len(FIRST_NAMES)]
            mn = MIDDLE_NAMES[idx % len(MIDDLE_NAMES)]
            ln = LAST_NAMES[idx % len(LAST_NAMES)]
            full_name = f"{fn} {mn} {ln}"
            father_name = f"{FATHER_FIRSTS[idx % len(FATHER_FIRSTS)]} {ln}"
            mother_name = f"{MOTHER_FIRSTS[idx % len(MOTHER_FIRSTS)]} {ln}"
            dob_iso, dob_str = DATES_OF_BIRTH[idx % len(DATES_OF_BIRTH)]
            addr_str, pin = ADDRESSES[idx % len(ADDRESSES)]

            # Clean file prefix
            type_slug = doc_type.lower().replace(" ", "_").replace("10th_marksheet", "marksheet")
            filename = f"{type_slug}_{idx+1:02d}.pdf"
            file_path = os.path.join(output_dir, filename)

            # Build text lines depending on doc_type
            lines = []
            doc_num = None

            if doc_type == "Aadhaar Card":
                doc_num = make_invalid_aadhaar(rng)
                lines = [
                    ("Government of India", 14, 50, 60),
                    ("Unique Identification Authority of India", 11, 50, 80),
                    (f"Name: {full_name}", 12, 50, 120),
                    (f"DOB: {dob_str}", 11, 50, 145),
                    (f"Gender: {'Male' if idx % 2 == 0 else 'Female'}", 11, 50, 165),
                    (f"Address: {addr_str}", 11, 50, 200),
                    (f"{doc_num}", 14, 50, 250),
                    ("Help: 1947 | help@uidai.gov.in", 9, 50, 290),
                ]
            elif doc_type == "PAN Card":
                doc_num = make_invalid_pan(rng, full_name)
                lines = [
                    ("INCOME TAX DEPARTMENT", 13, 50, 60),
                    ("GOVT. OF INDIA", 11, 50, 80),
                    ("Permanent Account Number Card", 11, 50, 105),
                    (f"Name: {full_name}", 12, 50, 140),
                    (f"Father's Name: {father_name}", 11, 50, 165),
                    (f"Date of Birth: {dob_str}", 11, 50, 190),
                    (f"Permanent Account Number: {doc_num}", 13, 50, 225),
                ]
            elif doc_type == "10th Marksheet":
                doc_num = f"SYN{rng.randint(10000000, 99999999)}"
                lines = [
                    ("CENTRAL BOARD OF SECONDARY EDUCATION", 14, 50, 60),
                    ("SECONDARY SCHOOL EXAMINATION (CLASS X)", 11, 50, 85),
                    (f"Candidate Name: {full_name}", 12, 50, 120),
                    (f"Roll No: {rng.randint(1000000, 9999999)}", 11, 50, 140),
                    (f"Date of Birth: {dob_str}", 11, 50, 160),
                    (f"Mother's Name: {mother_name}", 11, 50, 180),
                    (f"Father's Name: {father_name}", 11, 50, 200),
                    ("Subject Codes and Marks Obtained:", 10, 50, 230),
                    ("101 English: 085 | 002 Hindi: 088 | 041 Mathematics: 092", 10, 50, 250),
                    ("086 Science: 089 | 087 Social Science: 091", 10, 50, 270),
                    ("Result: PASSED", 11, 50, 295),
                    (f"Certificate No: {doc_num}", 10, 50, 320),
                ]
            elif doc_type == "Passport":
                doc_num = f"Z{rng.randint(1000000, 9999999)}"
                lines = [
                    ("PASSPORT / REPUBLIC OF INDIA", 14, 50, 60),
                    (f"Type: P | Country Code: IND | Passport No: {doc_num}", 11, 50, 90),
                    (f"Given Name(s): {fn} {mn}", 12, 50, 120),
                    (f"Surname: {ln}", 12, 50, 140),
                    (f"Nationality: INDIAN | Sex: {'M' if idx % 2 == 0 else 'F'}", 11, 50, 160),
                    (f"Date of Birth: {dob_str}", 11, 50, 180),
                    (f"Father / Legal Guardian: {father_name}", 11, 50, 200),
                    (f"Mother: {mother_name}", 11, 50, 220),
                    (f"Address: {addr_str}", 11, 50, 250),
                ]
            elif doc_type == "Voter ID":
                doc_num = f"ZZZ{rng.randint(1000000, 9999999)}"
                lines = [
                    ("ELECTION COMMISSION OF INDIA", 14, 50, 60),
                    ("ELECTOR PHOTO IDENTITY CARD", 11, 50, 85),
                    (f"EPIC No: {doc_num}", 13, 50, 115),
                    (f"Elector Name: {full_name}", 12, 50, 145),
                    (f"Father's Name: {father_name}", 11, 50, 170),
                    (f"Gender: {'Male' if idx % 2 == 0 else 'Female'}", 11, 50, 195),
                    (f"Date of Birth: {dob_str}", 11, 50, 220),
                    (f"Address: {addr_str}", 11, 50, 250),
                ]
            elif doc_type == "Driving Licence":
                doc_num = f"DL-992020{rng.randint(1000000, 9999999)}"
                lines = [
                    ("UNION OF INDIA / DRIVING LICENCE", 14, 50, 60),
                    ("TRANSPORT DEPARTMENT", 11, 50, 85),
                    (f"Licence No: {doc_num}", 13, 50, 115),
                    (f"Name: {full_name}", 12, 50, 145),
                    (f"Son / Daughter / Wife of: {father_name}", 11, 50, 170),
                    (f"DOB: {dob_str}", 11, 50, 195),
                    (f"Address: {addr_str}", 11, 50, 225),
                    ("Class of Vehicle: LMV, MCWG", 10, 50, 260),
                ]

            # Render text into PDF and extract word bounding boxes
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)  # Standard A4
            for text, size, x, y in lines:
                page.insert_text((x, y), text, fontsize=size)
            doc.save(file_path)

            # Extract word bounding boxes
            words = page.get_text("words")
            doc.close()

            boxes_data = {
                "file": filename,
                "doc_type": doc_type,
                "page_width": 595.0,
                "page_height": 842.0,
                "words": [
                    {
                        "text": w[4],
                        "bbox": [round(w[0], 2), round(w[1], 2), round(w[2], 2), round(w[3], 2)],
                        "block_no": w[5],
                        "line_no": w[6],
                        "word_no": w[7],
                    }
                    for w in words
                ]
            }

            boxes_path = os.path.join(output_dir, f"{filename}.boxes.json")
            with open(boxes_path, "w", encoding="utf-8") as bf:
                json.dump(boxes_data, bf, indent=2)

            records.append({
                "file": filename,
                "doc_type": doc_type,
                "name": full_name,
                "dob": dob_iso,
                "address": addr_str if doc_type in ("Aadhaar Card", "Passport", "Voter ID", "Driving Licence") else "",
                "doc_number": doc_num,
                "father_name": father_name if doc_type in ("PAN Card", "10th Marksheet", "Passport", "Voter ID", "Driving Licence") else "",
                "mother_name": mother_name if doc_type in ("10th Marksheet", "Passport") else "",
            })

    labels_csv_path = os.path.join(output_dir, "labels.csv")
    fieldnames = ["file", "doc_type", "name", "dob", "address", "doc_number", "father_name", "mother_name"]
    with open(labels_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Generated {len(records)} synthetic documents in {output_dir}")
    print(f"Ground truth written to {labels_csv_path}")
    return labels_csv_path

if __name__ == "__main__":
    generate_dataset()
