import pytest
from document_fields import enrich_fields

FRONT = "Government of India\nName: Aarav Example\nDOB: 19/08/2002\nMale\nXXXX XXXX 1234"
BACK = "Unique Identification Authority of India\nAddress: C/O: Meera Example, Flat 12\nTest Nagar, Pune\nMaharashtra 411001\nXXXX XXXX 1234\n1947 help@uidai.gov.in"

@pytest.mark.parametrize("text", [FRONT+'\n'+BACK, BACK+'\n'+FRONT])
def test_both_sides_in_either_order(text):
    r = enrich_fields({}, {"text":text,"mean_confidence":95}, "Aadhaar Card")
    assert r["name"] == "Aarav Example"
    assert r["dob"] == "2002-08-19"
    assert r["gender"] == "Male"
    assert r["pincode"] == "411001"
    assert r["address"].endswith("411001")
    assert "1947" not in r["address"]
    assert r["father_name"] is None
    assert r["doc_number"]["number"].endswith("1234")

def test_different_cards_not_silently_combined():
    r = enrich_fields({}, {"text":FRONT+'\n'+BACK.replace('1234','5678'),"mean_confidence":95}, "Aadhaar Card")
    assert r["doc_number"] is None
    assert r["needsReview"]["doc_number"]
    assert r['name'] is None and r['address'] is None and r['pincode'] is None
    assert r['doc_meta']['aadhaar_review_reasons']

def test_download_date_not_dob():
    r = enrich_fields({"dob":"2025-01-01"},{"text":"Aadhaar\nDownload Date: 01/01/2025\nAddress: Flat 12, Test Nagar 411001","mean_confidence":95},"Aadhaar Card")
    assert r["dob"] is None


def test_no_name_or_address_continuation_across_pages():
    data = {'text': 'Name: Someone Else\nDOB: 19/08/2002', 'mean_confidence': 95,
            'lines': [{'text': 'Address: C/O: Meera Example', 'page': 1},
                      {'text': 'Test Nagar', 'page': 1},
                      {'text': 'DOB: 19/08/2002', 'page': 2},
                      {'text': 'Male', 'page': 2}]}
    r = enrich_fields({}, data, 'Aadhaar Card')
    assert r['name'] is None
    assert r['address'] == 'C/O: Meera Example Test Nagar'
    assert r['dob'] == '2002-08-19'


def test_bilingual_equivalents_do_not_erase_english_fields():
    text = ('नाम: आरव उदाहरण\nName: Aarav Example\nDOB: 19/08/2002\nपुरुष / Male\n'
            'पता: घर 12, पुणे 411001\n' + BACK)
    r = enrich_fields({}, {'text': text, 'mean_confidence': 95}, 'Aadhaar Card')
    assert r['name'] == 'Aarav Example'
    assert r['address'].startswith('C/O: Meera Example')
    assert r['gender'] == 'Male'


def test_split_labels_and_year_of_birth_do_not_invent_date():
    r = enrich_fields({}, {'text': 'Name:\nNamesh Example\nYOB:\n2002\nAddress\nFlat 12, Test Nagar\nPune 411001',
                           'mean_confidence': 95}, 'Aadhaar Card')
    assert r['name'] == 'Namesh Example'
    assert r['dob'] == '2002'
    assert r['address'] == 'Flat 12, Test Nagar Pune 411001'


def test_vid_is_not_aadhaar_and_invalid_number_stays_unverified():
    r = enrich_fields({}, {'text': FRONT.replace('XXXX XXXX 1234', 'VID: 2345 6789 1234 5678'),
                           'mean_confidence': 95}, 'Aadhaar Card')
    assert r['doc_number'] is None
    r = enrich_fields({}, {'text': FRONT.replace('XXXX XXXX 1234', '2222 2222 2222'),
                           'mean_confidence': 95}, 'Aadhaar Card')
    assert r['needsReview']['doc_number']
    assert '222222222222' not in str(r['doc_fields'])


def test_conflicting_dobs_not_silently_selected():
    r = enrich_fields({}, {'text': FRONT + '\nDOB: 20/08/2002', 'mean_confidence': 95}, 'Aadhaar Card')
    assert r['dob'] is None
    assert r['needsReview']['dob']


def test_legacy_fallback_does_not_restore_conflicting_pin_or_number():
    r = enrich_fields({'address': 'Old address 411001', 'doc_number': {'type': 'Aadhaar', 'number': 'XXXXXXXX1234'}},
                      {'text': FRONT + '\n' + BACK.replace('1234', '5678') + '\nDocument No: 222222222222', 'mean_confidence': 95},
                      'Aadhaar Card')
    assert r['doc_number'] is None and r['pincode'] is None


@pytest.mark.parametrize('label', ['जन्म तारीख / DOB', 'Date of Birth / DOB', 'DOB / जन्म तिथि'])
def test_bilingual_dob_label(label):
    from aadhaar_fields import extract_sides
    assert extract_sides({'text': f'{label}: 19 / 08 / 2002'})['dob'] == '2002-08-19'


def test_bilingual_invalid_dob_is_not_a_year():
    from aadhaar_fields import extract_sides
    assert extract_sides({'text': 'जन्म तारीख / DOB: 31/02/2002'})['dob'] is None


def test_labelled_month_name_dob():
    from aadhaar_fields import extract_sides
    assert extract_sides({'text': 'Date of Birth: 19 August 2002'})['dob'] == '2002-08-19'
