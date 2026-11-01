"""
Training Script for Sahayak ML Document Field Generalizer.

Trains a lightweight model (RandomForest/GBDT) on spatial, geometrical, and context features.
Saves model to ml/models/field_classifier.pkl.
Strictly ensures no personal text or PII is memorized.
"""

import os
import sys
import csv
import joblib
from datetime import datetime

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

import ocr_boxes
from ml.features.feature_extractor import extract_line_features, TARGET_LABELS

LABEL_TO_ID = {lbl: i for i, lbl in enumerate(TARGET_LABELS)}
ID_TO_LABEL = {i: lbl for i, lbl in enumerate(TARGET_LABELS)}

def assign_line_label(line_text, row_labels):
    """Assigns ground truth field category based on label matching."""
    text_clean = line_text.lower().strip()
    if not text_clean or len(text_clean) < 2:
        return "other"

    # 1. Date of Birth
    dob = str(row_labels.get("dob", "")).strip()
    if dob:
        y_dob = dob[:4]
        if dob.lower() in text_clean or y_dob in text_clean:
            if any(k in text_clean for k in ["dob", "birth", "yob", "date of birth"]):
                return "dob"

    # 2. Document Number
    doc_num = str(row_labels.get("doc_number", "")).strip().replace(" ", "").upper()
    if doc_num and len(doc_num) >= 6:
        clean_line_upper = line_text.replace(" ", "").upper()
        if doc_num in clean_line_upper or doc_num[-6:] in clean_line_upper:
            return "doc_number"

    # 3. Father / Mother Name
    father = str(row_labels.get("father_name", "")).lower().strip()
    if father and len(father) > 3 and father in text_clean:
        if any(k in text_clean for k in ["father", "guardian", "s/o", "d/o", "w/o", "son", "husband"]):
            return "father_name"

    mother = str(row_labels.get("mother_name", "")).lower().strip()
    if mother and len(mother) > 3 and mother in text_clean:
        if any(k in text_clean for k in ["mother", "m/o"]):
            return "mother_name"

    # 4. Name
    name = str(row_labels.get("name", "")).lower().strip()
    if name and len(name) > 3:
        # Check if first and last name match
        parts = name.split()
        if len(parts) >= 2 and parts[0] in text_clean and parts[-1] in text_clean:
            return "name"

    # 5. Address
    addr = str(row_labels.get("address", "")).lower().strip()
    if addr and len(addr) > 5:
        addr_tokens = set(addr.split())
        line_tokens = set(text_clean.split())
        if len(addr_tokens & line_tokens) >= 3 or ("pin" in text_clean and len(addr_tokens & line_tokens) >= 2):
            return "address"

    return "other"

def train_field_classifier(data_dir=None, labels_file=None, model_out_path=None):
    base_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if data_dir is None:
        data_dir = os.path.join(base_root, "synth", "data")
    if labels_file is None:
        labels_file = os.path.join(data_dir, "labels.csv")
    if model_out_path is None:
        model_out_path = os.path.join(base_root, "models", "field_classifier.pkl")

    if not os.path.exists(labels_file):
        raise FileNotFoundError(f"Labels file not found: {labels_file}")

    print(f"\n[INFO] Loading training dataset from {labels_file}...")
    records = []
    with open(labels_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            records.append(r)

    X = []
    y = []

    for r in records:
        filename = r["file"]
        file_path = os.path.join(data_dir, filename)
        if not os.path.exists(file_path):
            continue

        ocr_res = ocr_boxes.extract_ocr_with_boxes(file_path, filename)
        lines = ocr_res.get("lines", [])

        for line in lines:
            feat_vec = extract_line_features(line, lines)
            label = assign_line_label(line.get("text", ""), r)
            label_id = LABEL_TO_ID.get(label, 0)

            X.append(feat_vec)
            y.append(label_id)

    print(f"[INFO] Extracted {len(X)} line samples across {len(records)} documents.")

    # Train lightweight RandomForest classifier
    clf = RandomForestClassifier(
        n_estimators=60,
        max_depth=10,
        min_samples_split=3,
        random_state=42,
        class_weight="balanced",
    )
    clf.fit(X, y)

    y_pred = clf.predict(X)
    acc = accuracy_score(y, y_pred)
    print(f"[INFO] Training complete. Overall Sample Accuracy: {acc * 100:.2f}%")
    print("\nClassification Report:")
    target_names = [TARGET_LABELS[i] for i in sorted(set(y))]
    print(classification_report(y, y_pred, target_names=target_names))

    # Save model artifact and metadata
    os.makedirs(os.path.dirname(model_out_path), exist_ok=True)
    payload = {
        "model": clf,
        "target_labels": TARGET_LABELS,
        "label_to_id": LABEL_TO_ID,
        "id_to_label": ID_TO_LABEL,
        "trained_at": datetime.now().isoformat(),
        "n_samples": len(X),
        "accuracy": round(acc, 4),
    }
    joblib.dump(payload, model_out_path)
    print(f"[INFO] Model artifact successfully saved to: {model_out_path}\n")
    return model_out_path

if __name__ == "__main__":
    train_field_classifier()
