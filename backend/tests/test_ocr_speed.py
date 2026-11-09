import time
import pytest
from PIL import Image
import pymupdf
import ocr_boxes
from ocr_result_cache import cached_extraction, clear_owner


def test_mixed_pdf_only_recognizes_scanned_page(tmp_path,monkeypatch):
 path=tmp_path/'mixed.pdf'
 with pymupdf.open() as doc:
  page=doc.new_page();page.insert_text((30,40),'Candidate Name Aarav Example Date of Birth 19/08/2002 Roll 12345678')
  doc.new_page();doc.save(path)
 calls=[]
 def fake(image):
  calls.append(image.size)
  return {'text':'scanned text','words':[],'lines':[],'mean_confidence':90}
 monkeypatch.setattr(ocr_boxes,'run_image_ocr',fake)
 result=ocr_boxes.extract_pdf_with_boxes(str(path))
 assert len(calls)==1
 assert 'Aarav Example' in result['text'] and 'scanned text' in result['text']
 assert result['source']=='mixed_pdf'
 assert result['timings']['pages'][0]['source']=='embedded_text'


def test_pdf_page_limit_is_explicit(tmp_path,monkeypatch):
 path=tmp_path/'pages.pdf'
 with pymupdf.open() as doc:
  for _ in range(6):doc.new_page().insert_text((30,40),'One two three four five six seven')
  doc.save(path)
 monkeypatch.setattr(ocr_boxes,'run_image_ocr',lambda image:pytest.fail('Digital PDF must bypass OCR'))
 result=ocr_boxes.extract_pdf_with_boxes(str(path))
 assert result['page_count']==4 and result['total_pages']==6 and result['truncated']


def test_scoped_cache_copy_password_and_delete(tmp_path):
 path=tmp_path/'test.png';path.write_bytes(b'synthetic fixture')
 calls=[]
 def work():
  calls.append(1);return {'ocrAttempted':True,'name':'Synthetic Example','raw_text':'not retained'}
 def run(scope,password=None):return cached_extraction(str(path),path.name,'PAN Card',password,scope,work)
 first=run((9871,'a'));second=run((9871,'a'))
 assert len(calls)==1 and second['timings']['cache_hit']
 assert second['raw_text']==''
 second['name']='Changed';assert run((9871,'a'))['name']=='Synthetic Example'
 run((9872,'a'));run((9871,'b'));run((9871,'a'),'different-password')
 assert len(calls)==4
 clear_owner(9871);run((9871,'a'));assert len(calls)==5
 clear_owner(9871);clear_owner(9872)


def test_failures_not_cached_and_rescan_bypasses(tmp_path):
 path=tmp_path/'test.png';path.write_bytes(b'fixture')
 calls=[]
 def work():calls.append(1);return {'error_code':'OCR_TIMEOUT'}
 for _ in range(2):cached_extraction(str(path),path.name,'PAN Card',None,(9873,'a'),work)
 assert len(calls)==2
 for _ in range(2):cached_extraction(str(path),path.name,'PAN Card',None,None,work)
 assert len(calls)==4


def test_retry_budget_does_not_start_optional_crop(monkeypatch):
 import core_field_retry
 monkeypatch.setattr(core_field_retry,'read_crop',lambda *args:pytest.fail('Expired budget'))
 result={'name':'Synthetic Example','dob':None,'doc_number':None}
 data={'engine':'paddleocr','lines':[{'text':'Date of birth','bbox':[.1,.1,.5,.2]}]}
 core_field_retry.recover_core_fields(result,data,'unused','10th Marksheet',deadline=time.monotonic()-1)
 assert result['dob'] is None and result['doc_meta']['core_retry_deferred']


def test_complete_explicit_fields_skip_second_classifier(tmp_path,monkeypatch):
 import ocr_extract
 path=tmp_path/'document.png';Image.new('RGB',(100,100),'white').save(path)
 text='CBSE Class X\nCandidate Name: AARAV EXAMPLE\nDate of Birth: 19/08/2002\nRoll No: 12345678'
 monkeypatch.setattr(ocr_boxes,'extract_ocr_with_boxes',lambda *a,**kw:{'text':text,'mean_confidence':95})
 monkeypatch.setattr(ocr_extract.parsers,'parse_document',lambda *a,**kw:pytest.fail('Redundant classifier pass'))
 result=ocr_extract.extract_fields(str(path),path.name,'10th Marksheet')
 assert result['name']=='AARAV EXAMPLE' and result['dob']=='2002-08-19'
 assert result['doc_number']['number']=='12345678'
 assert 'field_extraction_seconds' in result['timings']


def test_worker_health_does_not_claim_dead_worker_ready(monkeypatch):
 import paddle_engine
 monkeypatch.setattr(paddle_engine,'_worker',None)
 assert not paddle_engine.worker_status()['ready']
