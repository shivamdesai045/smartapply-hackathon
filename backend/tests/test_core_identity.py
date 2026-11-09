import copy
import pytest
from document_fields import enrich_fields, strict_date
from marksheet_fields import extract_marksheet_fields
from core_field_retry import recover_core_fields

@pytest.mark.parametrize('heading', ["This is to certify that", "NAME OF CANDIDATE (SURNAME FIRST):", "Candidate Full Name:"])
def test_marksheet_core_labels(heading):
    r=extract_marksheet_fields(f"CBSE Class X\n{heading}\nAarav Example\nDate of Birth (in figures): 19 / 08 / 2002\nRoll No.: 00123456\nCertificate No.: CERT999")
    assert r['name']=='Aarav Example'
    assert r['dob']=='2002-08-19'
    assert r['doc_number']=={'type':'Roll Number','number':'00123456'}


def test_marksheet_split_boxes_join_by_baseline():
    def line(text,box): return {'text':text,'page':1,'words':[{'text':text,'bbox':box}]}
    data={'lines':[line('Candidate Name:',[.1,.2,.3,.24]),line('DOB:',[.1,.3,.2,.34]),
                   line('Aarav Example',[.4,.2,.7,.24]),line('19/08/2002',[.4,.3,.7,.34])]}
    r=extract_marksheet_fields('wrong reading order',ocr_data=data)
    assert r['name']=='Aarav Example' and r['dob']=='2002-08-19'


def test_issue_date_and_headings_are_not_identity():
    r=enrich_fields({'name':'This is to certify that','dob':'2025-01-01'},
                    {'text':'CBSE Class XII\nDate of Issue: 01/01/2025','mean_confidence':95},'12th Marksheet')
    assert r['name'] is None and r['dob'] is None
    assert strict_date('31 / 02 / 2002') is None


def test_crop_retry_only_fills_missing_fields_and_requires_review(monkeypatch):
    import core_field_retry, paddle_engine
    from PIL import Image
    data={'engine':'paddleocr','text':'Aadhaar\nName: Aarav Example\nDOB: unreadable\nXXXX XXXX 1234',
          'mean_confidence':90,'lines':[{'text':'DOB: unreadable','bbox':[.2,.4,.5,.45]}]}
    result=enrich_fields({}, {'text':data['text'],'mean_confidence':90}, 'Aadhaar Card')
    original_name=result['name']; original_number=copy.deepcopy(result['doc_number'])
    monkeypatch.setattr(core_field_retry,'read_crop',lambda *a: Image.new('RGB',(800,250)))
    monkeypatch.setattr(paddle_engine,'recognize_image',lambda image:{'text':'Aadhaar\nName: Another Example\nDOB: 19/08/2002','mean_confidence':97})
    final=recover_core_fields(result,data,'synthetic.png','Aadhaar Card')
    assert final['dob']=='2002-08-19'
    assert final['name']==original_name and final['doc_number']==original_number
    assert final['needsReview']['dob'] and final['fieldConfidence']['dob']<=.79


def test_conflicts_are_never_restored_from_single_crop(monkeypatch):
    import core_field_retry
    result={'name':None,'dob':None,'doc_number':None,'doc_meta':{'core_field_conflicts':['name']}}
    monkeypatch.setattr(core_field_retry,'read_crop',lambda *a:pytest.fail('Must not crop conflicting identities'))
    assert recover_core_fields(result,{'engine':'paddleocr'},'synthetic.png','10th Marksheet')==result


def test_explicit_certificate_id_overrides_label_contaminated_legacy_value():
    result=enrich_fields({'doc_number':'Registration No: TEST/2002/00001'},
                         {'text':'Birth Certificate\nRegistration No: TEST/2002/00001','mean_confidence':95},'Birth Certificate')
    assert result['doc_number']=={'type':'Birth Certificate','number':'TEST/2002/00001'}
