# Sahayak Ground Truth (Gold) Dataset Instructions

## Strict Security & Privacy Guidelines
1. **Never download or use real people's identity documents from the internet.**
2. Real data must consist **only** of the hackathon team's own consented documents.
3. Keep real documents strictly in `backend/ml/data/gold/` or `backend/ml/data/real/` (both are git-ignored).
4. **Never commit real identity documents or `.env` to Git.**
5. Logs and reports must **never** print or store unmasked PII.

---

## Target Document Portfolio (Target: 10+ per document type)
Collect 10+ consented documents for each of the 6 core document types:
1. **Aadhaar Card** (e-Aadhaar PDF or scanned card; front & back containing address)
2. **PAN Card** (Scanned image or PDF)
3. **10th Marksheet / Passing Certificate** (CBSE, ICSE, or State Boards with candidate, parents' names, and DOB)
4. **Passport** (Personal details page + address page)
5. **Voter ID Card (EPIC)** (Old or new format)
6. **Driving Licence** (Smart card or legacy book format)

### Degraded & Real-World Condition Samples (Include 2-3 per type)
- **Perspective skew / Angle**: Photo captured at a 10°–20° tilt.
- **Low light / Shadows**: Dim ambient lighting or cast shadows across document text.
- **Scanned compression**: PDF/Image compressed below 150 DPI or slightly blurred.
- **Cropping & Borders**: Image with surrounding background or slight margin crop.

---

## Label Formatting (`backend/ml/data/gold/labels.csv`)
Place your annotations in `backend/ml/data/gold/labels.csv` with the following columns:
- `file`: Filename inside `backend/ml/data/gold/` (e.g. `aadhaar_01.pdf`, `pan_02.jpg`).
- `doc_type`: Exact type: `Aadhaar Card`, `PAN Card`, `10th Marksheet`, `Passport`, `Voter ID`, or `Driving Licence`.
- `name`: Full applicant name as printed on the document (e.g. `Shivam Shashikant Desai`).
- `dob`: ISO date `YYYY-MM-DD` or 4-digit year `YYYY` (e.g. `2003-08-15` or `1975`).
- `address`: Complete address string if present on the document, empty otherwise.
- `doc_number`: Document identification number (e.g. masked Aadhaar `XXXX XXXX 1234` or PAN).
- `father_name`: Father's name if printed, empty otherwise.
- `mother_name`: Mother's name if printed, empty otherwise.

Reference example provided at `backend/ml/data/labels.csv.example`.

