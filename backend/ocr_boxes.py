"""
Sahayak OCR Engine with Bounding Boxes and Adaptive Preprocessing.

Provides word-level and line-level bounding boxes with confidence scores:
- Uses PyMuPDF text and coordinates when digital text is present.
- High-quality 300 DPI rasterization and adaptive preprocessing for scanned documents.
- Preprocessing: Deskew, Denoise, Otsu adaptive threshold, upscale small images.
- Multi-variant confidence evaluation: selects the variant with highest mean confidence.
- English-only OCR; other script packs are not selected.
- Optional EasyOCR support via OCR_ENGINE=easyocr with graceful fallback to Tesseract.
- Normalized coordinates [x0, y0, x1, y1] in range [0.0, 1.0].
"""

import os
import re
import shutil
import logging
import time
from datetime import datetime
import pytesseract
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import pymupdf as fitz

logger = logging.getLogger(__name__)

# Ensure Tesseract executable path on Windows
if shutil.which("tesseract") is None:
    default_windows_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_windows_path):
        pytesseract.pytesseract.tesseract_cmd = default_windows_path

# --------------------------------------------------------------------------- #
# Language Configuration
# --------------------------------------------------------------------------- #

def get_available_tesseract_languages():
    """Returns set of installed Tesseract language models."""
    try:
        return set(pytesseract.get_languages())
    except Exception:
        return {"eng"}

def check_missing_languages(verbose=False):
    """
    Returns list of desired language files not yet installed.
    Prints location where to place missing traineddata on Windows.
    """
    installed = get_available_tesseract_languages()
    missing = []
    for l in ["hin", "mar"]:
        if l not in installed:
            missing.append(f"{l}.traineddata")
    if missing and verbose:
        import logging
        tessdata_dir = os.environ.get("TESSDATA_PREFIX", r"C:\Program Files\Tesseract-OCR\tessdata")
        msg = f"[OCR WARNING] Missing language packs: {', '.join(missing)}. For Hindi/Marathi OCR, place them in: {tessdata_dir}"
        logging.warning(msg)
        print(msg)
    return missing

def get_ocr_language_string():
    """This deployment recognizes English text only, even if other packs exist."""
    return "eng"

# --------------------------------------------------------------------------- #
# Image Preprocessing & Variant Selection
# --------------------------------------------------------------------------- #

def compute_otsu_threshold(gray_img):
    """Computes global Otsu threshold from grayscale image histogram."""
    hist = gray_img.histogram()
    total = sum(hist)
    if total == 0:
        return 128
    sum_total = sum(i * hist[i] for i in range(256))
    sum_b, w_b, var_max, threshold = 0, 0, 0.0, 128
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f
        var_between = w_b * w_f * ((m_b - m_f) ** 2)
        if var_between > var_max:
            var_max = var_between
            threshold = t
    return threshold

def deskew_image(img):
    """Detects 90/180/270 orientation using Tesseract OSD and rotates upright."""
    try:
        osd = pytesseract.image_to_osd(img, config="--psm 0 -c min_characters_to_try=15", output_type=pytesseract.Output.DICT, timeout=1.5)
        rotate_angle = osd.get("rotate", 0)
        if rotate_angle in (90, 180, 270):
            return img.rotate(360 - rotate_angle, expand=True)
    except Exception:
        pass
    # Optional OpenCV fine deskew, with conservative correction bounds. No dependency
    # download or document network access is performed by the OCR process.
    try:
        import cv2
        import numpy as np
        gray = np.asarray(ImageOps.grayscale(img))
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coordinates = np.column_stack(np.where(binary > 0))[:, ::-1].astype('float32')
        if len(coordinates) > 100:
            angle = cv2.minAreaRect(coordinates)[-1]
            if angle > 45:
                angle -= 90
            if .3 < abs(angle) <= 7:
                return img.rotate(angle, expand=True, fillcolor='white')
    except ImportError:
        pass
    except Exception:
        pass
    return img

def upscale_small_image(img, min_dim=1200):
    """Upscales image if either dimension is below min_dim to bring it to ~300 DPI equivalent."""
    w, h = img.size
    if w < min_dim or h < min_dim:
        scale = max(min_dim / w, min_dim / h)
        scale = min(scale, 4.0)  # Cap at 4x to avoid excessive memory
        new_w = int(w * scale)
        new_h = int(h * scale)
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    return img

def generate_preprocessing_variants(base_img):
    """
    Generates preprocessing candidates:
    1. Grayscale + AutoContrast
    2. Denoised (MedianFilter) + UnsharpMask
    3. Adaptive Otsu Binarization
    4. Contrast-Enhanced Grayscale
    """
    gray = ImageOps.grayscale(base_img)
    var1_autocontrast = ImageOps.autocontrast(gray, cutoff=1)

    var2_denoised = var1_autocontrast.filter(ImageFilter.MedianFilter(size=3)).filter(
        ImageFilter.UnsharpMask(radius=1.5, percent=150, threshold=3)
    )

    t_otsu = compute_otsu_threshold(var1_autocontrast)
    var3_otsu = var1_autocontrast.point(lambda p: 255 if p > t_otsu else 0)

    enhancer = ImageEnhance.Contrast(var1_autocontrast)
    var4_contrast = enhancer.enhance(1.8)

    return [
        ("autocontrast", var1_autocontrast),
        ("denoised_sharpened", var2_denoised),
        ("otsu_threshold", var3_otsu),
        ("high_contrast", var4_contrast),
    ]

# --------------------------------------------------------------------------- #
# Bounding Box Extraction & Line Grouping
# --------------------------------------------------------------------------- #

def extract_boxes_from_tesseract_data(data, width, height):
    """
    Parses pytesseract image_to_data dict into normalized words and grouped lines.
    """
    words = []
    lines_map = {}

    n_boxes = len(data.get("text", []))
    for i in range(n_boxes):
        text = str(data["text"][i]).strip()
        conf = float(data["conf"][i])
        if not text or conf < 0:
            continue

        left = data["left"][i]
        top = data["top"][i]
        w = data["width"][i]
        h = data["height"][i]
        right = left + w
        bottom = top + h

        norm_box = [
            round(left / width, 4),
            round(top / height, 4),
            round(right / width, 4),
            round(bottom / height, 4),
        ]

        block_num = data.get("block_num", [0] * n_boxes)[i]
        line_num = data.get("line_num", [0] * n_boxes)[i]
        word_num = data.get("word_num", [0] * n_boxes)[i]

        word_obj = {
            "text": text,
            "confidence": round(conf, 1),
            "bbox": norm_box,
            "pixel_bbox": [left, top, right, bottom],
            "block_no": block_num,
            "line_no": line_num,
            "word_no": word_num,
        }
        words.append(word_obj)

        # Tesseract restarts line numbers for every paragraph within a block.
        # Omitting paragraph identity interleaves unrelated rows by x coordinate.
        line_key = (block_num, data.get("par_num", [0] * n_boxes)[i], line_num)
        lines_map.setdefault(line_key, []).append(word_obj)

    # Build sorted lines
    lines = []
    for line_key in sorted(lines_map.keys()):
        line_words = sorted(lines_map[line_key], key=lambda w: w["pixel_bbox"][0])
        line_text = " ".join(w["text"] for w in line_words)
        min_x0 = min(w["bbox"][0] for w in line_words)
        min_y0 = min(w["bbox"][1] for w in line_words)
        max_x1 = max(w["bbox"][2] for w in line_words)
        max_y1 = max(w["bbox"][3] for w in line_words)
        p_min_left = min(w["pixel_bbox"][0] for w in line_words)
        p_min_top = min(w["pixel_bbox"][1] for w in line_words)
        p_max_right = max(w["pixel_bbox"][2] for w in line_words)
        p_max_bottom = max(w["pixel_bbox"][3] for w in line_words)

        line_mean_conf = round(sum(w["confidence"] for w in line_words) / len(line_words), 1)

        lines.append({
            "text": line_text,
            "bbox": [min_x0, min_y0, max_x1, max_y1],
            "pixel_bbox": [p_min_left, p_min_top, p_max_right, p_max_bottom],
            "mean_confidence": line_mean_conf,
            "words": line_words,
        })

    full_text = "\n".join(l["text"] for l in lines)
    overall_conf = round(sum(w["confidence"] for w in words) / len(words), 1) if words else 0.0

    return {
        "text": full_text,
        "words": words,
        "lines": lines,
        "mean_confidence": overall_conf,
        "width": width,
        "height": height,
    }

def ocr_image_with_best_variant(img, lang=None):
    """
    Applies deskew and upscale, evaluates candidate preprocessing variants,
    and returns OCR output for the variant with the highest mean confidence.
    """
    started = time.monotonic()
    budget = max(1.0, float(os.getenv("OCR_PAGE_BUDGET_SECONDS", "7.5")))
    if lang is None:
        lang = get_ocr_language_string()

    img = ImageOps.exif_transpose(img).convert("RGB")
    # Bound preprocessing cost for high-resolution scans embedded in PDFs.
    img.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
    upright = deskew_image(img)
    scaled = upscale_small_image(upright)
    w, h = scaled.size

    variants = generate_preprocessing_variants(scaled)
    # Preprocessing must not consume the entire Tesseract execution allowance.
    started = time.monotonic()

    best_result = None
    best_conf = -1.0
    best_variant_name = "default"
    passes = []

    for var_name, var_img in variants:
        remaining = budget - (time.monotonic() - started)
        if remaining <= .2:
            break
        try:
            data = pytesseract.image_to_data(
                var_img,
                output_type=pytesseract.Output.DICT,
                lang=lang,
                config="--dpi 300 --psm 6", timeout=max(.2, remaining)
            )
            res = extract_boxes_from_tesseract_data(data, w, h)
            passes.append({"text": res["text"], "mean_confidence": res["mean_confidence"], "variant": var_name})
            # Require at least 2 words to consider a valid confidence score
            if len(res["words"]) >= 2 and res["mean_confidence"] > best_conf:
                best_conf = res["mean_confidence"]
                best_result = res
                best_variant_name = var_name
            # Retain two independent passes for voting; use more only when uncertain.
            if len(passes) >= 2 and best_conf >= 88 and passes[-1]["text"] == passes[-2]["text"]:
                break
        except Exception:
            continue

    if best_result is None or len(best_result["words"]) == 0:
        # Fallback to standard grayscale without PSM constraint
        gray = ImageOps.grayscale(scaled)
        try:
            data = pytesseract.image_to_data(
                gray, output_type=pytesseract.Output.DICT, lang=lang, config="--dpi 300", timeout=max(.2, budget - (time.monotonic() - started))
            )
            best_result = extract_boxes_from_tesseract_data(data, w, h)
            best_variant_name = "fallback_grayscale"
        except Exception:
            best_result = {
                "text": "", "words": [], "lines": [],
                "mean_confidence": 0.0, "width": w, "height": h
            }

    best_result["selected_preprocessing"] = best_variant_name
    best_result["passes"] = passes
    best_result["budget_exceeded"] = time.monotonic() - started >= budget
    return best_result

# --------------------------------------------------------------------------- #
# PyMuPDF PDF Text & Box Extraction
# --------------------------------------------------------------------------- #

def extract_pdf_with_boxes(file_path, password=None, chosen_option=None):
    """Read embedded text per page; rasterize only pages without usable text."""
    import time
    started = time.monotonic()
    all_words, all_lines, texts, page_timings = [], [], [], []
    digital_count = scanned_count = 0
    engines = set()
    with fitz.open(file_path) as doc:
        if doc.needs_pass and not doc.authenticate(password or ''):
            return {'text':'', 'words':[], 'lines':[], 'mean_confidence':0,
                    'error_code':'PDF_PASSWORD_REQUIRED', 'password_required':True}
        total_pages = len(doc)
        for page_index in range(min(total_pages, 4)):
            page = doc[page_index]
            started_page = time.monotonic()
            pwords = page.get_text('words')
            # Ignore unusable text layers, but do not OCR good pages just because another page is scanned.
            usable = [w for w in pwords if str(w[4]).strip() and '\ufffd' not in str(w[4])]
            if len(usable) >= 5:
                digital_count += 1
                groups = {}
                for x0,y0,x1,y1,text,block,line,word in usable:
                    obj = {'text':text.strip(), 'confidence':95.0,
                           'bbox':[x0/page.rect.width,y0/page.rect.height,x1/page.rect.width,y1/page.rect.height],
                           'pixel_bbox':[x0,y0,x1,y1], 'page':page_index+1,
                           'block_no':block, 'line_no':line, 'word_no':word}
                    all_words.append(obj)
                    groups.setdefault((block,line),[]).append(obj)
                for key in sorted(groups):
                    words=sorted(groups[key],key=lambda w:w['pixel_bbox'][0])
                    line={'text':' '.join(w['text'] for w in words), 'words':words, 'page':page_index+1,
                          'bbox':[min(w['bbox'][0] for w in words),min(w['bbox'][1] for w in words),max(w['bbox'][2] for w in words),max(w['bbox'][3] for w in words)], 'mean_confidence':95.0}
                    all_lines.append(line);texts.append(line['text'])
                page_timings.append({'page':page_index+1,'source':'embedded_text','total_seconds':round(time.monotonic()-started_page,3)})
            else:
                scanned_count += 1
                limit=int(os.getenv('OCR_MAX_SIDE','1600'))
                scale=min(300/72,limit/max(page.rect.width,page.rect.height))
                pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False)
                image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                del pix
                rendered=time.monotonic()
                try:
                    result=None
                    if chosen_option and os.getenv('OCR_ENGINE','paddleocr').lower() == 'paddleocr':
                        from fast_ocr import fast_image_read
                        result=fast_image_read(image,chosen_option)
                    if result is None: result=run_image_ocr(image)
                    engines.add(result.get('engine',os.getenv('OCR_ENGINE','paddleocr')))
                finally: image.close()
                if result.get('error_code'):
                    return result
                for word in result.get('words',[]):word['page']=page_index+1;all_words.append(word)
                for line in result.get('lines',[]):
                    line['page']=page_index+1
                    for word in line.get('words',[]):word['page']=page_index+1
                    all_lines.append(line)
                texts.append(result.get('text',''))
                page_timings.append({'page':page_index+1,'source':'image_ocr',
                                     'render_seconds':round(rendered-started_page,3),
                                     'total_seconds':round(time.monotonic()-started_page,3),**result.get('timings',{})})
    return {'text':'\n'.join(texts),'words':all_words,'lines':all_lines,
            'mean_confidence':round(sum(w['confidence'] for w in all_words)/len(all_words),2) if all_words else 0,
            'page_count':min(total_pages,4),'total_pages':total_pages,'truncated':total_pages>4,
            'engine':next(iter(engines)) if len(engines)==1 else 'hybrid' if engines else 'pymupdf',
            'source':'digital_pdf' if not scanned_count else 'mixed_pdf' if digital_count else 'scanned_ocr_bounded',
            'timings':{'read_seconds':round(time.monotonic()-started,3),'pages':page_timings}}

# --------------------------------------------------------------------------- #
# Optional EasyOCR Adapter
# --------------------------------------------------------------------------- #

def run_easyocr_on_image(img, langs=None):
    """
    Runs EasyOCR if installed and requested via OCR_ENGINE=easyocr.
    Gracefully falls back to Tesseract if easyocr is not importable.
    """
    try:
        import easyocr
        import numpy as np
    except ImportError:
        logger.warning("OCR_ENGINE=easyocr specified, but easyocr is not installed. Falling back to Tesseract.")
        return None

    if langs is None:
        langs = ["en"]

    w, h = img.size
    np_img = np.array(img)
    reader = easyocr.Reader(langs, gpu=False)
    results = reader.readtext(np_img)

    words = []
    lines = []
    text_pieces = []

    for idx, (bbox_pts, text_str, conf) in enumerate(results):
        text_str = str(text_str).strip()
        if not text_str:
            continue

        xs = [pt[0] for pt in bbox_pts]
        ys = [pt[1] for pt in bbox_pts]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)

        norm_box = [
            round(x0 / w, 4),
            round(y0 / h, 4),
            round(x1 / w, 4),
            round(y1 / h, 4),
        ]

        word_obj = {
            "text": text_str,
            "confidence": round(float(conf) * 100.0, 1),
            "bbox": norm_box,
            "pixel_bbox": [x0, y0, x1, y1],
            "line_no": idx,
            "word_no": idx,
        }
        words.append(word_obj)
        lines.append({
            "text": text_str,
            "bbox": norm_box,
            "pixel_bbox": [x0, y0, x1, y1],
            "mean_confidence": round(float(conf) * 100.0, 1),
            "words": [word_obj],
        })
        text_pieces.append(text_str)

    mean_conf = round(sum(w["confidence"] for w in words) / len(words), 1) if words else 0.0

    return {
        "text": "\n".join(text_pieces),
        "words": words,
        "lines": lines,
        "mean_confidence": mean_conf,
        "width": w,
        "height": h,
        "engine": "easyocr",
    }

# --------------------------------------------------------------------------- #
# Unified Entrypoint
# --------------------------------------------------------------------------- #

def extract_ocr_with_boxes(file_path, original_filename=None, password=None, chosen_option=None):
    """
    Universal entry point:
    Accepts file_path (image or PDF).
    Returns dict:
      {
        "text": str,
        "words": [{"text": str, "confidence": float, "bbox": [x0, y0, x1, y1], ...}],
        "lines": [{"text": str, "bbox": [x0, y0, x1, y1], "mean_confidence": float, ...}],
        "mean_confidence": float,
        "engine": str,
      }
    """
    ext = os.path.splitext(original_filename or file_path)[1].lower()

    # Check optional EasyOCR
    engine_env = os.getenv("OCR_ENGINE", "paddleocr").lower().strip()
    if engine_env == "easyocr" and ext in {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"}:
        try:
            img = Image.open(file_path)
            easy_res = run_easyocr_on_image(img)
            if easy_res is not None:
                return easy_res
        except Exception as e:
            logger.warning(f"EasyOCR failed: {e}. Falling back to Tesseract.")

    if ext == ".pdf":
        res = extract_pdf_with_boxes(file_path, password=password, chosen_option=chosen_option)
        res["engine"] = "pymupdf" if res.get("source") == "digital_pdf" else res.get("engine",engine_env)
        return res
    else:
        try:
            with Image.open(file_path) as img:
                return run_image_ocr(img)
        except Exception as e:
            logger.error("OCR image failed: %s", getattr(e, "code", type(e).__name__))
            return {
                "text": "", "words": [], "lines": [],
                "mean_confidence": 0.0, "engine": "failed", "error_code": getattr(e, "code", "OCR_ENGINE_FAILED")
            }


def run_image_ocr(img):
    if os.getenv("OCR_ENGINE", "paddleocr").lower() == "tesseract":
        result = ocr_image_with_best_variant(img)
        result["engine"] = "tesseract"
        return result
    from paddle_engine import recognize_image
    return recognize_image(img)
