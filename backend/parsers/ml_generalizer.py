"""
ML Document Field Generalizer for Unusual Layouts and Degraded Scans.

Ensembles with per-type spatial parsers:
- When a per-type parser is unconfident (< 0.70) or returns None,
  the ML model classifies lines/boxes to propose candidates.
- Candidates are validated with format regexes.
- The highest-confidence valid candidate is selected.
"""

import os
import re
import joblib
import numpy as np

from ml.features.feature_extractor import extract_line_features, TARGET_LABELS
from .base import parse_date_to_iso, clean_extracted_name

_MODEL_CACHE = None

def get_classifier():
    """Loads and caches field_classifier.pkl."""
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE

    model_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ml", "models", "field_classifier.pkl"
    )
    if os.path.exists(model_path):
        try:
            _MODEL_CACHE = joblib.load(model_path)
            return _MODEL_CACHE
        except Exception:
            return None
    return None

def clean_field_line(text, field):
    """Strips field labels and anchors from candidate lines."""
    t = str(text).strip()
    if field in ("name", "father_name", "mother_name"):
        t = re.sub(r"^(?:Candidate|Student|Elector|Father['’]?s?|Mother['’]?s?|Given|Surname)?\s*Name(?:\(s\))?\s*[:\-]?\s*", "", t, flags=re.I)
        t = re.sub(r"^(?:Son\s*\/\s*Daughter\s*\/\s*Wife\s*of|S\s*\/\s*W\s*\/\s*D\s*of|Father|Mother)\s*[:\-]?\s*", "", t, flags=re.I)
        return clean_extracted_name(t)
    elif field == "dob":
        m = re.search(r"(?:DOB|Date\s*of\s*Birth|Year\s*of\s*Birth|YOB)\s*[:\-]?\s*([0-9\/\-\.]+)", t, re.I)
        raw_d = m.group(1) if m else t
        return parse_date_to_iso(raw_d)
    elif field == "doc_number":
        t = re.sub(r"^(?:Passport\s*No|EPIC\s*No|Licen[sc]e\s*No|DL\s*No|Certificate\s*No|Roll\s*No|PAN|Permanent\s+Account\s+Number)\s*[:\-]?\s*", "", t, flags=re.I)
        clean_num = t.strip()
        # Clean quotes, colons, extra labels
        clean_num = re.sub(r"^[^\w]+|[^\w]+$", "", clean_num)
        return clean_num if len(clean_num) >= 5 else None
    elif field == "address":
        t = re.sub(r"^Address\s*[:\-]?\s*", "", t, flags=re.I).strip()
        return t if len(t.split()) >= 3 else None
    return t

def predict_field_candidates(ocr_data):
    """
    Classifies all OCR lines using the ML generalizer model.
    Returns: {field: {"value": ..., "confidence": float, "line": ...}}
    """
    pkg = get_classifier()
    if pkg is None:
        return {}

    clf = pkg.get("model")
    id_to_label = pkg.get("id_to_label", {})
    if clf is None:
        return {}

    lines = ocr_data.get("lines", [])
    if not lines:
        return {}

    candidates = {
        "name": [],
        "dob": [],
        "address": [],
        "doc_number": [],
        "father_name": [],
        "mother_name": [],
    }

    for line in lines:
        feat_vec = extract_line_features(line, lines)
        try:
            probs = clf.predict_proba([feat_vec])[0]
            pred_id = int(np.argmax(probs))
            label = id_to_label.get(pred_id, "other")
            conf = float(probs[pred_id])

            if label in candidates and conf >= 0.50:
                raw_text = line.get("text", "")
                cleaned_val = clean_field_line(raw_text, label)
                if cleaned_val:
                    candidates[label].append({
                        "value": cleaned_val,
                        "confidence": round(conf, 2),
                        "line": line,
                    })
        except Exception:
            continue

    best_candidates = {}
    for f, c_list in candidates.items():
        if c_list:
            # Sort by confidence descending
            c_list.sort(key=lambda x: x["confidence"], reverse=True)
            best_candidates[f] = c_list[0]

    return best_candidates
