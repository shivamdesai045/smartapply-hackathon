from parsers.pan import parse_pan

def parse(text):
    return parse_pan({"text": text, "lines": [], "words": []})

def test_separate_names_and_dob():
    r = parse("INCOME TAX DEPARTMENT\nName\nAARAV EXAMPLE\nFather's Name\nSURESH EXAMPLE\nDate of Birth\n19/08/2002\nABCPЕ1234F")
    assert r["name"] == "AARAV EXAMPLE"
    assert r["father_name"] == "SURESH EXAMPLE"
    assert r["dob"] == "2002-08-19"

def test_father_label_is_not_holder_label():
    r = parse("Father's Name: SURESH EXAMPLE\nDate of Birth: 19/08/2002")
    assert r["name"] is None
    assert r["father_name"] == "SURESH EXAMPLE"

def test_conflicting_labels_require_review():
    assert parse("Name: AARAV EXAMPLE\nName: AMIT EXAMPLE")["name"] is None
