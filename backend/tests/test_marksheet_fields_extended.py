import pytest
from marksheet_fields import extract_marksheet_fields
from document_fields import enrich_fields

BOARDS = [
    ("Maharashtra State Board Secondary School Certificate SSC", "10th", "Maharashtra State Board"),
    ("Maharashtra State Board Higher Secondary Certificate HSC", "12th", "Maharashtra State Board"),
    ("Central Board of Secondary Education Class X", "10th", "CBSE"),
    ("Central Board of Secondary Education Senior School Certificate Class XII", "12th", "CBSE"),
    ("Council for the Indian School Certificate Examinations ICSE", "10th", "CISCE"),
    ("Council for the Indian School Certificate Examinations ISC", "12th", "CISCE"),
]

@pytest.mark.parametrize("header,level,board", BOARDS)
def test_board_fields(header, level, board):
    text = header + "\nCandidate Name: Aarav Example\nMother's Name: Meera Example  Father's Name: Suresh Example\nDate of Birth: 19/08/2002\nSeat No.: A123456\nExamination March 2020\nSchool Name: Example Public School"
    fields = extract_marksheet_fields(text)
    assert fields["exam_level"] == level
    assert fields["board"] == board
    assert fields["father_name"] == "Suresh Example"
    assert fields["mother_name"] == "Meera Example"
    assert fields["dob"] == "2002-08-19"
    assert fields["seat_number"] == "A123456"
    assert fields["exam_year"] == "2020"
    assert fields["school_name"] == "Example Public School"

def test_next_line_and_hindi_labels():
    r = extract_marksheet_fields("CBSE Class X\nपिता का नाम : Suresh Example\nMother's Name\nMeera Example\nDate of Birth (in figures): 19/08/2002")
    assert r["father_name"] == "Suresh Example"
    assert r["mother_name"] == "Meera Example"
    assert r["dob"] == "2002-08-19"

def test_issue_date_not_dob_and_parents_not_inferred():
    r = enrich_fields({"dob": "2020-05-01", "name": "Aarav Suresh Example"},
                      {"text": "CBSE Class XII\nDate of Issue: 01/05/2020", "mean_confidence": 95}, "12th Marksheet")
    assert r["dob"] is None
    assert r["father_name"] is None

def test_conflicting_parents_do_not_choose_first():
    r = extract_marksheet_fields("Father's Name: Suresh Example\nFather's Name: Ramesh Example")
    assert r["father_name"] is None

def test_invalid_calendar_dob():
    assert "dob" not in extract_marksheet_fields("Date of Birth: 31/02/2002")
