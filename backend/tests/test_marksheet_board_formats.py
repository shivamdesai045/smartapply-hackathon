import pytest
from marksheet_fields import extract_marksheet_fields, marksheet_date
from document_fields import enrich_fields

@pytest.mark.parametrize('text,expected',[
 ('NINETEENTH AUGUST TWO THOUSAND TWO','2002-08-19'),
 ('TWENTY-FIRST JANUARY TWO THOUSAND AND SIX','2006-01-21'),
 ('THIRTY FIRST DECEMBER NINETEEN NINETY NINE','1999-12-31'),
 ('19th August 2002','2002-08-19'),
 ('19 - 08 - 2002 (NINETEENTH AUGUST TWO THOUSAND TWO)','2002-08-19'),
 ('THIRTY FIRST FEBRUARY TWO THOUSAND TWO',None),
 ('TWO THOUSAND TWO',None),
])
def test_written_dob(text,expected):
 assert marksheet_date(text)==expected

@pytest.mark.parametrize('header,level,identifier,expected_id',[
 ('CBSE Secondary School Examination Class X','10th','Roll No. 12345678','12345678'),
 ('CBSE Senior School Certificate Examination Class XII','12th','Roll Number: 23456789','23456789'),
 ('Maharashtra State Board SSC','10th','Seat No. A123456','A123456'),
 ('Maharashtra State Board HSC','12th','Seat Number: B234567','B234567'),
 ('CISCE ICSE','10th','Unique ID: 1234567\nIndex No: 1234567/001','1234567'),
 ('CISCE ISC','12th','UID: 7654321\nIndex Number: 7654321/002','7654321'),
])
def test_board_variations(header,level,identifier,expected_id):
 text=f'{header}\nThis is to certify that\nAARAV EXAMPLE\nMother’s Name: MEERA EXAMPLE\nFather’s Name: SURESH EXAMPLE\nDate of Birth: NINETEENTH AUGUST TWO THOUSAND TWO\n{identifier}\nSchool Code: 12345\nDate of Issue: 15/06/2020'
 result=enrich_fields({}, {'text':text,'mean_confidence':95},level+' Marksheet')
 assert result['name']=='AARAV EXAMPLE'
 assert result['dob']=='2002-08-19'
 assert result['doc_number']['number']==expected_id
 assert result['exam_level']==level

def test_no_school_code_as_roll_number():
 result=extract_marksheet_fields('CBSE Class X\nRoll No.\nSchool Code: 12345\nCandidate Name: AARAV EXAMPLE')
 assert not result.get('roll_number')
 assert not result.get('doc_number')

def test_conflicting_roll_does_not_fallback_to_certificate():
 result=extract_marksheet_fields('Roll No: 1234567\nRoll No: 7654321\nCertificate No: 9876543')
 assert result['doc_number'] is None
 assert 'doc_number' in result['_conflicts']

def test_12th_without_dob_does_not_use_result_date():
 result=enrich_fields({'dob':'2020-06-15'}, {'text':'CISCE ISC\nName: AARAV EXAMPLE\nDate of Issue: 15/06/2020\nUID: 1234567','mean_confidence':95},'12th Marksheet')
 assert result['dob'] is None
