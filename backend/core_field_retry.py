"""Re-read up to two labelled regions for missing identity fields; never guess."""
import copy
import json
import re
from pathlib import Path
from PIL import Image, ImageOps

CORE = ('name', 'dob', 'doc_number')
ANCHORS = {
    'name': r"\b(?:name|this\s+is\s+to\s+certify\s+that)\b",
    'dob': r"\b(?:d\.?\s*o\.?\s*b\.?|date\s+of\s+birth|birth\s+date)\b",
    'doc_number': r"\b(?:roll|seat|index|unique|certificate|passport|licen[cs]e|permanent\s+account)\s*(?:no\.?|number)|\b(?:PAN|UID|unique\s+id)\b",
}


def regions(data, missing, aadhaar=False):
    found = []
    for line in data.get('lines', []):
        text, box = line.get('text', ''), line.get('bbox', [])
        if len(box) != 4: continue
        matches = any(re.search(ANCHORS[field], text, re.I) for field in missing)
        if aadhaar and 'name' in missing:
            matches |= bool(re.search(ANCHORS['dob'], text, re.I))
        if not matches: continue
        x0, y0, x1, y1 = box
        rect = (max(0, x0-.04), max(0, y0-(.16 if aadhaar else .025)),
                min(1, max(x1+.3, x0+.65)), min(1, y1+.12))
        page = line.get('page', 1)
        if any(page == p and abs(rect[1]-r[1]) < .08 for p,r in found): continue
        found.append((page, rect))
        if len(found) == 2: break
    return found


def read_crop(path, page_number, rect, password):
    if Path(path).suffix.lower() == '.pdf':
        import pymupdf
        with pymupdf.open(path) as pdf:
            if pdf.needs_pass and not pdf.authenticate(password or ''): return None
            if not 1 <= page_number <= len(pdf): return None
            page = pdf[page_number-1]
            w,h = page.rect.width,page.rect.height
            clip=pymupdf.Rect(rect[0]*w,rect[1]*h,rect[2]*w,rect[3]*h)
            scale=min(300/72,1600/max(clip.width,clip.height))
            pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),clip=clip,colorspace=pymupdf.csRGB,alpha=False)
            return Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
    with Image.open(path) as source:
        image=ImageOps.exif_transpose(source).convert('RGB')
        w,h=image.size
        crop=image.crop((int(rect[0]*w),int(rect[1]*h),int(rect[2]*w),int(rect[3]*h)))
        image.close()
        crop.thumbnail((1600,1600))
        return crop


def recover_core_fields(result, data, path, chosen_option, password=None, deadline=None):
    import time
    from document_fields import enrich_fields
    from paddle_engine import recognize_image
    if data.get('engine') != 'paddleocr': return result
    meta=result.get('doc_meta', {})
    if meta.get('aadhaar_review_reasons') or meta.get('core_field_conflicts'): return result
    missing=[field for field in CORE if not result.get(field)]
    if not missing: return result
    crops=regions(data,missing,'aadhaar' in str(chosen_option).lower())
    candidates={field:[] for field in missing}
    attempts=0
    for page,rect in crops:
        # Budget applies to optional recovery, never fabricate a value to meet a timer.
        if deadline is not None and (time.monotonic()+2 >= deadline or attempts >= 1):
            result.setdefault('doc_meta', {})['core_retry_deferred'] = True
            break
        crop=None
        try:
            crop=read_crop(path,page,rect,password)
            if crop is None: continue
            attempts+=1
            reading=recognize_image(crop)
            candidate=enrich_fields({},reading,chosen_option)
            if candidate.get('doc_meta',{}).get('aadhaar_review_reasons') or candidate.get('doc_meta',{}).get('core_field_conflicts'): continue
            for field in missing:
                if candidate.get(field): candidates[field].append(candidate['doc_fields'][field])
        except Exception:
            # A timed-out/broken worker must not trigger another expensive restart.
            break
        finally:
            if crop is not None: crop.close()
    recovered=[]
    for field,options in candidates.items():
        distinct={json.dumps(item['value'],sort_keys=True).casefold():item for item in options}
        if len(distinct)!=1: continue
        entry=copy.deepcopy(next(iter(distinct.values())))
        entry.update(confidence=min(.79,entry.get('confidence',0)),needs_review=True,user_verified=False)
        result['doc_fields'][field]=entry
        result[field]=entry['value']
        result.setdefault('fieldConfidence',{})[field]=entry['confidence']
        result.setdefault('fieldConfidences',{})[field]=entry['confidence']
        result.setdefault('needsReview',{})[field]=True
        recovered.append(field)
    if attempts:
        result.setdefault('doc_meta',{})['core_field_retry']={'attempts':attempts,'recovered':recovered}
    return result
