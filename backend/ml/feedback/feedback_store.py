"""
Feedback Store for Sahayak Continuous Adaptation.

Captures user corrections from the "Wrong? Fix it" interface:
- Stores feedback records in backend/ml/data/feedback_raw/ (git-ignored).
- Extracts and saves 37-dimensional spatial feature vectors for line candidates.
- Strictly adheres to Data Minimization:
  - Masks Aadhaar numbers (XXXX XXXX 1234).
  - Never stores raw OCR page text.
  - Features are purely spatial/geometrical/pattern-density numbers.
"""

import os
import sys
import re
import json
import uuid
import glob
from datetime import datetime

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import ocr_boxes
from ml.features.feature_extractor import extract_line_features, TARGET_LABELS

FEEDBACK_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "feedback_raw"
)


def ensure_feedback_dir():
    """Ensures the feedback storage directory exists."""
    os.makedirs(FEEDBACK_DIR, exist_ok=True)
    return FEEDBACK_DIR


def mask_sensitive_value(field, value):
    """
    Masks sensitive values before storage.
    Never stores unmasked Aadhaar or raw sensitive tokens.
    """
    if value is None:
        return None
    val_str = str(value).strip()
    if not val_str:
        return ""

    # Aadhaar masking
    clean_digits = re.sub(r"\D", "", val_str)
    if len(clean_digits) == 12:
        return f"XXXX XXXX {clean_digits[-4:]}"

    # PAN masking
    pan_match = re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", val_str.upper())
    if pan_match:
        return f"{val_str[:3]}*****{val_str[-1]}"

    if field in ("doc_number", "id_number", "aadhaar", "pan"):
        if len(val_str) > 4:
            return f"***{val_str[-4:]}"
        return "****"

    return val_str


def find_matching_lines(lines, target_value, field_type):
    """
    Finds index of lines in OCR output that best match the target corrected value.
    Returns list of matching line indices.
    """
    if not lines or not target_value:
        return []

    val_str = str(target_value).strip().lower()
    if len(val_str) < 2:
        return []

    matches = []
    val_tokens = set(re.findall(r"\w+", val_str))

    for idx, line in enumerate(lines):
        line_text = line.get("text", "").lower().strip()
        if not line_text:
            continue

        # Exact substring match
        if val_str in line_text:
            matches.append(idx)
            continue

        # Normalized numbers (for document numbers / dates)
        clean_target_num = re.sub(r"[\s\-_/.]", "", val_str)
        clean_line_num = re.sub(r"[\s\-_/.]", "", line_text)
        if len(clean_target_num) >= 4 and clean_target_num in clean_line_num:
            matches.append(idx)
            continue

        # Token set overlap for names and addresses
        line_tokens = set(re.findall(r"\w+", line_text))
        if val_tokens and line_tokens:
            overlap = len(val_tokens & line_tokens)
            if field_type == "name" and overlap >= min(2, len(val_tokens)):
                matches.append(idx)
            elif field_type == "address" and (overlap >= 3 or ("pin" in line_text and overlap >= 2)):
                matches.append(idx)

    return matches


def extract_features_from_file_with_labels(file_path, corrected_fields, original_fields=None):
    """
    Re-scans document lines and bounding boxes to extract 37-dim feature vectors
    labeled with ground-truth correction.
    """
    if not file_path or not os.path.exists(file_path):
        return []

    try:
        ocr_res = ocr_boxes.extract_ocr_with_boxes(file_path)
    except Exception:
        return []

    lines = ocr_res.get("lines", [])
    if not lines:
        return []

    samples = []
    labeled_indices = set()

    for field_name, corr_val in (corrected_fields or {}).items():
        if not corr_val:
            continue
        # Map field name to target label
        target_label = "other"
        if field_name in ("doc_name", "name"):
            target_label = "name"
        elif field_name in ("doc_dob", "dob"):
            target_label = "dob"
        elif field_name in ("doc_address", "address"):
            target_label = "address"
        elif field_name in ("doc_number", "id_number"):
            target_label = "doc_number"
        elif field_name in ("father_name", "father"):
            target_label = "father_name"
        elif field_name in ("mother_name", "mother"):
            target_label = "mother_name"

        if target_label == "other":
            continue

        match_indices = find_matching_lines(lines, corr_val, target_label)
        for m_idx in match_indices:
            line_item = lines[m_idx]
            feats = extract_line_features(line_item, lines)
            samples.append({
                "features": feats,
                "label": target_label,
                "field": field_name,
                "line_index": m_idx,
                "y_mid": line_item.get("y_mid", 0.0),
            })
            labeled_indices.add(m_idx)

    # Optionally add non-target lines as 'other' negative samples
    for idx, line_item in enumerate(lines):
        if idx not in labeled_indices:
            feats = extract_line_features(line_item, lines)
            samples.append({
                "features": feats,
                "label": "other",
                "field": "none",
                "line_index": idx,
                "y_mid": line_item.get("y_mid", 0.0),
            })

    return samples


def record_feedback(
    doc_type,
    original_fields,
    corrected_fields,
    field_confidences=None,
    file_path=None,
    session_id=None,
    service_name=None,
    variant=None,
    requirement=None,
):
    """
    Saves user feedback and extracts training feature vectors without raw text memorization.
    """
    ensure_feedback_dir()

    # Detect what changed
    sanitized_corr = {}
    sanitized_orig = {}
    diffs = {}

    for k, v in (corrected_fields or {}).items():
        orig_v = (original_fields or {}).get(k)
        if str(v or "").strip() != str(orig_v or "").strip():
            diffs[k] = {"from": mask_sensitive_value(k, orig_v), "to": mask_sensitive_value(k, v)}
        sanitized_corr[k] = mask_sensitive_value(k, v)

    for k, v in (original_fields or {}).items():
        sanitized_orig[k] = mask_sensitive_value(k, v)

    # If no changes and no explicit correction recorded, skip unless file has labels
    if not diffs and not corrected_fields:
        return None

    # Extract labeled feature vectors if document file is on disk
    feature_samples = []
    if file_path and os.path.exists(file_path):
        feature_samples = extract_features_from_file_with_labels(
            file_path, corrected_fields, original_fields
        )

    feedback_id = f"fb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    record = {
        "feedback_id": feedback_id,
        "timestamp": datetime.now().isoformat(),
        "service_name": service_name or "unknown",
        "variant": variant or "adult",
        "requirement": requirement or "unknown",
        "doc_type": doc_type or "General",
        "differences": diffs,
        "corrected_fields": sanitized_corr,
        "original_fields": sanitized_orig,
        "field_confidences": field_confidences or {},
        "feature_samples_count": len(feature_samples),
        "feature_samples": feature_samples,
    }

    out_file = os.path.join(FEEDBACK_DIR, f"{feedback_id}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    return record


def get_all_feedback():
    """Loads all feedback records from the feedback directory."""
    ensure_feedback_dir()
    records = []
    files = glob.glob(os.path.join(FEEDBACK_DIR, "*.json"))
    for fpath in sorted(files):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                records.append(json.load(f))
        except Exception:
            continue
    return records


def get_feedback_stats():
    """Returns aggregated summary statistics of user corrections."""
    records = get_all_feedback()
    total = len(records)
    by_doc_type = {}
    by_field_corrected = {}
    total_features = 0

    for r in records:
        dtype = r.get("doc_type") or "Unknown"
        by_doc_type[dtype] = by_doc_type.get(dtype, 0) + 1
        total_features += r.get("feature_samples_count", 0)

        for fld in r.get("differences", {}).keys():
            by_field_corrected[fld] = by_field_corrected.get(fld, 0) + 1

    return {
        "total_feedback_samples": total,
        "total_feature_vectors_captured": total_features,
        "by_document_type": by_doc_type,
        "by_field_corrected": by_field_corrected,
    }


def clear_feedback():
    """Clears all feedback records (for unit test isolation)."""
    ensure_feedback_dir()
    files = glob.glob(os.path.join(FEEDBACK_DIR, "*.json"))
    for f in files:
        try:
            os.remove(f)
        except OSError:
            pass
