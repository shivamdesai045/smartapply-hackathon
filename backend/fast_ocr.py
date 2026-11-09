"""Bounded English fast pass. Paddle remains the fallback for incomplete/uncertain reads."""
import os
import re
import time
from PIL import Image, ImageOps


def accept_fast_read(data, chosen_option):
    from document_fields import enrich_fields
    if data.get('mean_confidence',0) < 90:
        return False
    candidate = enrich_fields({}, data, chosen_option)
    if not all(candidate.get(k) for k in ('name','dob','doc_number')):
        return False
    meta=candidate.get('doc_meta',{})
    if meta.get('core_field_conflicts') or meta.get('aadhaar_review_reasons'):
        return False
    # A weak token on an identity-bearing row must go to Paddle, even if the page mean is high.
    anchors = re.compile(r'\b(?:name|certify|birth|dob|roll|seat|unique|uid|index|pan|passport|licen[cs]e)\b',re.I)
    rows=[line for line in data.get('lines',[]) if anchors.search(line.get('text',''))]
    if not rows or any(line.get('mean_confidence',0)<90 or any(w.get('confidence',0)<75 for w in line.get('words',[]) if re.search(r'[A-Za-z0-9]',w.get('text',''))) for line in rows):
        return False
    return True


def fast_image_read(path, chosen_option):
    if os.getenv('OCR_FAST_TEXT_PASS','0') != '1':
        return None
    import pytesseract
    from ocr_boxes import extract_boxes_from_tesseract_data
    started=time.monotonic()
    try:
        if isinstance(path, Image.Image):
            page=ImageOps.exif_transpose(path).convert('RGB')
        else:
            with Image.open(path) as original:
                page=ImageOps.exif_transpose(original).convert('RGB')
        try:
            page.thumbnail((1600,1600))
            raw=pytesseract.image_to_data(page,lang='eng',config='--psm 6 --dpi 300',output_type=pytesseract.Output.DICT,timeout=3)
            result=extract_boxes_from_tesseract_data(raw,*page.size)
            if not accept_fast_read(result,chosen_option):
                return None
            # Two segmentation modes must agree on every core value; never merge disagreements.
            confirmation=pytesseract.image_to_data(page,lang='eng',config='--psm 11 --dpi 300',output_type=pytesseract.Output.DICT,timeout=3)
            second=extract_boxes_from_tesseract_data(confirmation,*page.size)
            if not accept_fast_read(second,chosen_option):
                return None
            from document_fields import enrich_fields
            def signature(reading):
                fields=enrich_fields({},reading,chosen_option)
                number=fields['doc_number']
                if isinstance(number,dict):number=number.get('number','')
                return tuple(re.sub(r'\s+','',str(value)).casefold() for value in (fields['name'],fields['dob'],number))
            if signature(result)!=signature(second):
                return None
        finally:
            page.close()
        if not accept_fast_read(result,chosen_option):
            return None
        result.update(engine='tesseract_fast',source='fast_text_pass',passes=[{'text':result['text']},{'text':second['text']}],timings={'fast_pass_seconds':round(time.monotonic()-started,3)})
        return result
    except (RuntimeError, OSError, ValueError):
        return None
