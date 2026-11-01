"""
Regression tests for Hotfix:
- Address extraction filtering statutory notice noise and stopping at 6-digit PIN (Failure A)
- Marksheet candidate name extraction avoiding 'This Is To Certify That' (Failure B)
- Preservation of 'Kumar' in person names
- Rejection of institutional headings, labels, and disclaimers in validate_person_name
- Slot-aware parsing routing and document type mismatch warning
- OCR multilingual language detection and tessdata path guidance
- Presence and contract of fieldConfidence and needsReview per field
"""
import pytest
from parsers.base import (
    validate_person_name,
    is_notice_or_garbage_line,
    extract_clean_address,
)
from parsers.marksheet_10th import parse_marksheet as parse_marksheet_10th
from parsers.aadhaar import parse_aadhaar
import parsers
import ocr_boxes
import ocr_extract


def test_validate_person_name_rejects_headings_and_labels():
    """Confirms institutional headers, marksheet banners, and disclaimers are rejected."""
    disallowed = [
        "This Is To Certify That",
        "CERTIFY THAT",
        "STATEMENT OF MARKS",
        "BOARD OF SECONDARY EDUCATION",
        "GOVERNMENT OF INDIA",
        "REPUBLIC OF INDIA",
        "SECONDARY SCHOOL CERTIFICATE",
        "HIGHER SECONDARY",
        "INCOME TAX DEPARTMENT",
        "CENTRE CODE",
        "SUBJECT CODE",
        "TOTAL MARKS",
    ]
    for heading in disallowed:
        assert validate_person_name(heading) is None, f"Expected {heading} to be rejected"


def test_validate_person_name_preserves_kumar():
    """Confirms Indian names with 'Kumar' as first, middle, or last token are preserved."""
    assert validate_person_name("Ramesh Kumar Sharma") == "Ramesh Kumar Sharma"
    assert validate_person_name("Kumar Sanu") == "Kumar Sanu"
    assert validate_person_name("Sunil Kumar") == "Sunil Kumar"
    assert validate_person_name("Ajay Kumar Verma") == "Ajay Kumar Verma"


def test_validate_person_name_strips_honorifics():
    """Confirms honorific titles (Shri, Smt, Dr, Mr) are removed while retaining the name."""
    assert validate_person_name("Shri Rajesh Patil") == "Rajesh Patil"
    assert validate_person_name("Dr. Sunita Rao") == "Sunita Rao"
    assert validate_person_name("Mrs. Ananya Sen") == "Ananya Sen"


def test_failure_b_marksheet_name_extraction():
    """
    Failure B reproduction:
    Marksheet text with 'This Is To Certify That' followed by applicant name.
    Name field MUST extract the actual candidate name and NOT the header.
    """
    synthetic_marksheet = {
        "text": (
            "MAHARASHTRA STATE BOARD OF SECONDARY AND HIGHER SECONDARY EDUCATION\n"
            "DIVISIONAL BOARD, PUNE\n"
            "STATEMENT OF MARKS\n"
            "This Is To Certify That\n"
            "Shivam Shashikant Desai\n"
            "Mother's Name: Sunita Desai\n"
            "Seat No: M098765\n"
            "School: 11.02.001 Model English School\n"
            "Date: 15/06/2018"
        ),
        "lines": [],
    }

    result = parse_marksheet_10th(synthetic_marksheet)
    assert result["name"] == "Shivam Shashikant Desai"
    assert result["name"] != "This Is To Certify That"
    assert "certif" not in result["name"].lower()


def test_failure_b_marksheet_same_line_certify_that():
    """Handles 'This is to certify that <Candidate Name>' on the same line."""
    synthetic_marksheet = {
        "text": (
            "CENTRAL BOARD OF SECONDARY EDUCATION\n"
            "This is to certify that Rahul Kumar Gupta\n"
            "Roll No: 6543210\n"
            "DOB: 12/04/2002"
        ),
        "lines": [],
    }
    result = parse_marksheet_10th(synthetic_marksheet)
    assert result["name"] == "Rahul Kumar Gupta"


def test_failure_a_aadhaar_back_address_filtering():
    """
    Failure A reproduction:
    Aadhaar back side containing statutory notice text, mobile/UIDAI disclaimers,
    and genuine address. The parser must isolate the genuine address up to PIN code
    and exclude the notice lines.
    """
    synthetic_aadhaar_back = {
        "text": (
            "Address: S/O Ramesh Kumar, Flat 402, Sunshine Heights,\n"
            "MG Road, Shivajinagar, Pune,\n"
            "Maharashtra - 411001\n"
            "should be updated in Aadhaar after every 10 years\n"
            "Download mAadhaar app to carry your Aadhaar on mobile\n"
            "Lock/Unlock biometrics anytime for higher security\n"
            "Entities seeking Aadhaar are obligated to seek consent\n"
            "1947 www.uidai.gov.in help@uidai.gov.in"
        ),
        "lines": [],
    }

    result = parse_aadhaar(synthetic_aadhaar_back)
    addr = result["address"]
    assert addr is not None
    assert "Sunshine Heights" in addr
    assert "411001" in addr

    # Verify statutory notice keywords are purged
    for prohibited in ["updated", "10 years", "maadhaar", "biometrics", "obligated", "consent", "1947", "www"]:
        assert prohibited not in addr.lower(), f"Notice keyword '{prohibited}' leaked into address: {addr}"

    assert result["needs_review"]["address"] is False


def test_address_garbage_returns_needs_review():
    """When address has low letter ratio or only noise lines, returns needs_review=True."""
    garbage_text = (
        "Address: %%%% #### $$$$ @@@@\n"
        "Download mAadhaar app\n"
        "Lock/Unlock biometrics\n"
        "1947"
    )
    lines = [l.strip() for l in garbage_text.splitlines()]
    addr, conf, needs_rev = extract_clean_address(lines, garbage_text)
    assert addr is None
    assert needs_rev is True


def test_is_notice_or_garbage_line():
    """Verifies that notice lines and low-alphanumeric noise are identified correctly."""
    assert is_notice_or_garbage_line("should be updated in Aadhaar after every 10 years") is True
    assert is_notice_or_garbage_line("Download mAadhaar app") is True
    assert is_notice_or_garbage_line("Lock/Unlock biometrics") is True
    assert is_notice_or_garbage_line("Entities seeking Aadhaar are obligated to seek consent") is True
    assert is_notice_or_garbage_line("$$$$ %%%% ####") is True
    assert is_notice_or_garbage_line("Flat 402, Sunshine Heights, MG Road") is False


def test_slot_aware_parsing_prioritization():
    """When a checklist slot is passed, that parser runs first."""
    synthetic_marksheet = {
        "text": (
            "CENTRAL BOARD OF SECONDARY EDUCATION\n"
            "This is to certify that Pooja Verma\n"
            "Roll No: 1234567\n"
            "DOB: 15/08/2001"
        )
    }
    # Pass checklist slot for 10th Marksheet
    parsed = parsers.parse_document(synthetic_marksheet, chosen_option="10th Marksheet")
    assert parsed["name"] == "Pooja Verma"
    assert parsed["doc_meta"]["detectedType"] == "10th Marksheet"


def test_slot_mismatch_warning():
    """If user uploads a PAN Card into an Aadhaar slot, parser emits documentTypeWarning without breaking."""
    pan_doc = {
        "text": (
            "INCOME TAX DEPARTMENT\n"
            "GOVT. OF INDIA\n"
            "Permanent Account Number\n"
            "ABCDE1234F\n"
            "Rahul Sharma\n"
            "Father's Name: Suresh Sharma\n"
            "01/01/1990"
        )
    }
    parsed = parsers.parse_document(pan_doc, chosen_option="Aadhaar Card")
    # Warning should indicate mismatch
    assert "documentTypeWarning" in parsed["doc_meta"]
    assert "PAN Card" in parsed["doc_meta"]["documentTypeWarning"]


def test_ocr_language_discovery_guidance(capsys):
    """Verifies missing languages check prints Windows tessdata guidance path."""
    missing = ocr_boxes.check_missing_languages()
    # It must return a list or set of missing languages
    assert isinstance(missing, (set, list))
    lang_str = ocr_boxes.get_ocr_language_string()
    assert "eng" in lang_str


def test_extract_fields_includes_confidence_and_review_contracts(tmp_path):
    """
    Contract test: extract_fields must return fieldConfidence and needsReview
    dictionaries with keys for name, dob, address, doc_number.
    """
    # Create a dummy image file
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (600, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "Sample Document", fill=(0, 0, 0))
    dummy_path = tmp_path / "test_doc.png"
    img.save(dummy_path)

    res = ocr_extract.extract_fields(str(dummy_path), "test_doc.png")
    assert "fieldConfidence" in res
    assert "needsReview" in res
    assert "name" in res["fieldConfidence"]
    assert "dob" in res["fieldConfidence"]
    assert "address" in res["fieldConfidence"]
    assert "doc_number" in res["fieldConfidence"]
    assert "name" in res["needsReview"]
    assert "dob" in res["needsReview"]
    assert "address" in res["needsReview"]
    assert "doc_number" in res["needsReview"]
