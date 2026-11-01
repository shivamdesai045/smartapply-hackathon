"""
Sahayak OCR Engine with Bounding Boxes and Adaptive Preprocessing.

Provides word-level and line-level bounding boxes with confidence scores:
- Uses PyMuPDF text and coordinates when digital text is present.
- High-quality 300 DPI rasterization and adaptive preprocessing for scanned documents.
- Preprocessing: Deskew, Denoise, Otsu adaptive threshold, upscale small images.
- Multi-variant confidence evaluation: selects the variant with highest mean confidence.
- Multi-lingual OCR: automatically discovers eng+hin+mar if installed; falls back to eng.
- Optional EasyOCR support via OCR_ENGINE=easyocr with graceful fallback to Tesseract.
- Normalized coordinates [x0, y0, x1, y1] in range [0.0, 1.0].
"""

import os
import re
import shutil
import logging
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

def get_ocr_language_string():
    """
    Returns '+'-separated languages string.
    Uses 'eng+hin+mar' if installed, else available subset, defaulting to 'eng'.
    """
    installed = get_available_tesseract_languages()
    desired = ["eng", "hin", "mar"]
    available = [l for l in desired if l in installed]
    if available:
        return "+".join(available)
    return "eng"

def check_missing_languages():
    """Returns list of desired language files not yet installed."""
    installed = get_available_tesseract_languages()
    missing = []
    for l in ["hin", "mar"]:
        if l not in installed:
            missing.append(f"{l}.traineddata")
    return missing

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
        osd = pytesseract.image_to_osd(img, config="--psm 0 -c min_characters_to_try=15", output_type=pytesseract.Output.DICT)
        rotate_angle = osd.get("rotate", 0)
        if rotate_angle in (90, 180, 270):
            return img.rotate(360 - rotate_angle, expand=True)
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

        line_key = (block_num, line_num)
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
    if lang is None:
        lang = get_ocr_language_string()

    upright = deskew_image(img)
    scaled = upscale_small_image(upright)
    w, h = scaled.size

    variants = generate_preprocessing_variants(scaled)

    best_result = None
    best_conf = -1.0
    best_variant_name = "default"

    for var_name, var_img in variants:
        try:
            data = pytesseract.image_to_data(
                var_img,
                output_type=pytesseract.Output.DICT,
                lang=lang,
                config="--dpi 300 --psm 6"
            )
            res = extract_boxes_from_tesseract_data(data, w, h)
            # Require at least 2 words to consider a valid confidence score
            if len(res["words"]) >= 2 and res["mean_confidence"] > best_conf:
                best_conf = res["mean_confidence"]
                best_result = res
                best_variant_name = var_name
        except Exception:
            continue

    if best_result is None or len(best_result["words"]) == 0:
        # Fallback to standard grayscale without PSM constraint
        gray = ImageOps.grayscale(scaled)
        try:
            data = pytesseract.image_to_data(
                gray, output_type=pytesseract.Output.DICT, lang=lang, config="--dpi 300"
            )
            best_result = extract_boxes_from_tesseract_data(data, w, h)
            best_variant_name = "fallback_grayscale"
        except Exception:
            best_result = {
                "text": "", "words": [], "lines": [],
                "mean_confidence": 0.0, "width": w, "height": h
            }

    best_result["selected_preprocessing"] = best_variant_name
    return best_result

# --------------------------------------------------------------------------- #
# PyMuPDF PDF Text & Box Extraction
# --------------------------------------------------------------------------- #

def extract_pdf_with_boxes(file_path):
    """
    Extracts text and word bounding boxes from PDF:
    - Uses digital text if present.
    - If scanned or empty, rasterizes at 300 DPI and runs image OCR with boxes.
    """
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        logger.error(f"Failed to open PDF: {e}")
        return {"text": "", "words": [], "lines": [], "mean_confidence": 0.0, "page_count": 0}

    all_words = []
    all_lines = []
    total_text = []
    is_digital = True

    # 1. Try digital text extraction first
    for page_idx, page in enumerate(doc):
        pw = page.rect.width
        ph = page.rect.height
        pwords = page.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)

        if len(pwords) < 5:
            is_digital = False
            break

        lines_map = {}
        for w_tuple in pwords:
            x0, y0, x1, y1, w_text, block_no, line_no, word_no = w_tuple
            w_text = w_text.strip()
            if not w_text:
                continue

            norm_box = [
                round(x0 / pw, 4),
                round(y0 / ph, 4),
                round(x1 / pw, 4),
                round(y1 / ph, 4),
            ]
            word_obj = {
                "text": w_text,
                "confidence": 95.0,  # Digital text confidence
                "bbox": norm_box,
                "pixel_bbox": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                "page": page_idx + 1,
                "block_no": block_no,
                "line_no": line_no,
                "word_no": word_no,
            }
            all_words.append(word_obj)
            lines_map.setdefault((block_no, line_no), []).append(word_obj)

        for lk in sorted(lines_map.keys()):
            lwords = sorted(lines_map[lk], key=lambda w: w["pixel_bbox"][0])
            ltext = " ".join(w["text"] for w in lwords)
            min_x0 = min(w["bbox"][0] for w in lwords)
            min_y0 = min(w["bbox"][1] for w in lwords)
            max_x1 = max(w["bbox"][2] for w in lwords)
            max_y1 = max(w["bbox"][3] for w in lwords)

            all_lines.append({
                "text": ltext,
                "bbox": [min_x0, min_y0, max_x1, max_y1],
                "page": page_idx + 1,
                "words": lwords,
                "mean_confidence": 95.0,
            })
            total_text.append(ltext)

    # 2. Scanned PDF fallback
    if not is_digital or len(all_words) < 10:
        all_words = []
        all_lines = []
        total_text = []
        confidences = []

        for page_idx in range(min(len(doc), 4)):
            page = doc[page_idx]
            # 300 DPI matrix
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            page_res = ocr_image_with_best_variant(img)
            for w in page_res["words"]:
                w["page"] = page_idx + 1
                all_words.append(w)
            for l in page_res["lines"]:
                l["page"] = page_idx + 1
                all_lines.append(l)
            if page_res["text"]:
                total_text.append(page_res["text"])
            confidences.append(page_res["mean_confidence"])

        num_pages = len(doc)
        doc.close()
        overall_conf = round(sum(confidences) / len(confidences), 1) if confidences else 0.0
        return {
            "text": "\n".join(total_text),
            "words": all_words,
            "lines": all_lines,
            "mean_confidence": overall_conf,
            "page_count": min(num_pages, 4),
            "source": "scanned_ocr_300dpi",
        }

    page_count = len(doc)
    doc.close()
    return {
        "text": "\n".join(total_text),
        "words": all_words,
        "lines": all_lines,
        "mean_confidence": 95.0,
        "page_count": page_count,
        "source": "digital_pdf",
    }

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

def extract_ocr_with_boxes(file_path, original_filename=None):
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
    engine_env = os.getenv("OCR_ENGINE", "tesseract").lower().strip()
    if engine_env == "easyocr" and ext in {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"}:
        try:
            img = Image.open(file_path)
            easy_res = run_easyocr_on_image(img)
            if easy_res is not None:
                return easy_res
        except Exception as e:
            logger.warning(f"EasyOCR failed: {e}. Falling back to Tesseract.")

    if ext == ".pdf":
        res = extract_pdf_with_boxes(file_path)
        res["engine"] = "tesseract_pymupdf"
        return res
    else:
        try:
            img = Image.open(file_path)
            res = ocr_image_with_best_variant(img)
            res["engine"] = "tesseract"
            return res
        except Exception as e:
            logger.error(f"Failed to process image {file_path}: {e}")
            return {
                "text": "", "words": [], "lines": [],
                "mean_confidence": 0.0, "engine": "failed"
            }
