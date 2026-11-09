from pathlib import Path
from document_fields import enrich_fields
from core_field_retry import recover_core_fields


def test_real_focused_ocr_recovers_split_dob():
    source=Path(__file__).resolve().parents[1]/'ocr_fixtures/core_english/aadhaar_split.png'
    data={'engine':'paddleocr','mean_confidence':90,
          'text':'Aadhaar\nName: Aarav Example\nDate of Birth: unreadable\nXXXX XXXX 1234',
          'lines':[{'text':'Date of Birth: unreadable','bbox':[.035,.26,.22,.30],'page':1}]}
    initial=enrich_fields({}, {'text':data['text'],'mean_confidence':90},'Aadhaar Card')
    assert initial['dob'] is None
    final=recover_core_fields(initial,data,str(source),'Aadhaar Card')
    assert final['name']=='Aarav Example'
    assert final['dob']=='2002-08-19'
    assert final['doc_number']['number']=='XXXXXXXX1234'
    assert final['needsReview']['dob']
