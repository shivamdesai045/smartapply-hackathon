import pytest
from document_fields import enrich_fields
from transport_fields import extract_transport

@pytest.mark.parametrize('heading', ['Driving Licence', "Learner's Licence", 'Learning License'])
def test_fields(heading):
    r=extract_transport(heading+"\nName: Aarav Example\nS/W/D of: Suresh Example\nDOB: 19/08/2002\nDL No.: MH1420201234567\nAddress: Flat 12\nTest Nagar Pune 411001\nDate of Issue: 01/01/2025\nValid Till: 01/01/2030\nCOV: LMV MCWG")
    assert r['name']=='Aarav Example'
    assert r['guardian_name']=='Suresh Example'
    assert r['father_name'] is None
    assert r['dob']=='2002-08-19'
    assert r['expiry_date']=='2030-01-01'
    assert r['pincode']=='411001'
    assert r['vehicle_classes']=='LMV MCWG'

def test_date_not_invented_and_conflicts():
    r=extract_transport('Driving Licence\nName: Aarav Example\nName: Amit Example\nDate of Issue: 01/01/2025')
    assert r['name'] is None
    assert r['dob'] is None

def test_learner_not_claimed_checksum_valid():
    r=enrich_fields({}, {'text':"Learner's Licence\nLL No.: MH/00001/2025\nName: Aarav Example",'mean_confidence':95},"Learner Licence")
    assert r['document_type']=='Learner Licence'
    assert r['doc_fields']['doc_number']['needs_review']
