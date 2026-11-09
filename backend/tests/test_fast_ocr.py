import copy
from PIL import Image
import fast_ocr

def reading(name='AARAV EXAMPLE'):
 texts=['CBSE Class X',f'Candidate Name: {name}','Date of Birth: 19/08/2002','Roll No: 12345678']
 return {'text':'\n'.join(texts),'mean_confidence':95,'lines':[{'text':text,'mean_confidence':95,'words':[{'text':text,'confidence':95}]} for text in texts]}

def test_fast_pass_requires_complete_confident_fields():
 assert fast_ocr.accept_fast_read(reading(),'10th Marksheet')
 weak=reading();weak['lines'][1]['words'][0]['confidence']=40
 assert not fast_ocr.accept_fast_read(weak,'10th Marksheet')
 missing=reading();missing['lines']=missing['lines'][:2]
 assert not fast_ocr.accept_fast_read(missing,'10th Marksheet')
 conflict=reading();conflict['lines'].append({'text':'Roll No: 87654321','mean_confidence':95,'words':[]})
 assert not fast_ocr.accept_fast_read(conflict,'10th Marksheet')

def test_segmentation_disagreement_rejects_fast_pass(tmp_path,monkeypatch):
 import pytesseract,ocr_boxes
 path=tmp_path/'sample.png';Image.new('RGB',(100,100)).save(path)
 monkeypatch.setenv('OCR_FAST_TEXT_PASS','1')
 monkeypatch.setattr(ocr_boxes,'extract_boxes_from_tesseract_data',lambda raw,*a:raw)
 calls=[]
 def fake(*a,**kw):calls.append(kw['config']);return reading() if len(calls)==1 else reading('OTHER EXAMPLE')
 monkeypatch.setattr(pytesseract,'image_to_data',fake)
 assert fast_ocr.fast_image_read(str(path),'10th Marksheet') is None
 assert len(calls)==2

def test_fast_pass_timeout_returns_to_paddle(tmp_path,monkeypatch):
 import pytesseract
 path=tmp_path/'sample.png';Image.new('RGB',(100,100)).save(path)
 monkeypatch.setenv('OCR_FAST_TEXT_PASS','1')
 def timeout(*a,**kw):raise RuntimeError('Tesseract process timeout')
 monkeypatch.setattr(pytesseract,'image_to_data',timeout)
 assert fast_ocr.fast_image_read(str(path),'10th Marksheet') is None

def test_disabled_fast_pass_does_not_run_external_engine(monkeypatch):
 import pytesseract
 monkeypatch.setenv('OCR_FAST_TEXT_PASS','0')
 monkeypatch.setattr(pytesseract,'image_to_data',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('Must not run')))
 assert fast_ocr.fast_image_read('unused','10th Marksheet') is None
