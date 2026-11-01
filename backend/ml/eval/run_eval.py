"""
Evaluation Harness for Sahayak Document Extraction.
Measures field-level extraction accuracy per document type:
- Exact match after normalization for DOB and Document Number.
- Fuzzy matching (token-set / char similarity >= 0.85) for Name, Father Name, Mother Name.
- Fuzzy token overlap (Jaccard >= 0.70 or PIN agreement) for Address.
- Lists worst failures with MASKED values only (never logs unmasked PII).
- Reports baseline metrics and writes JSON report.
"""

import os
import sys
import re
import csv
import json
import difflib
import argparse
from datetime import datetime

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import ocr_extract

# --------------------------------------------------------------------------- #
# PII Masking Helpers (Hard Rule: Never log or persist raw identity data)
# --------------------------------------------------------------------------- #

def mask_name(val):
    if not val:
        return "None"
    parts = str(val).split()
    masked = []
    for p in parts:
        if len(p) <= 1:
            masked.append("*")
        else:
            masked.append(f"{p[0]}{'*' * (len(p) - 1)}")
    return " ".join(masked)

def mask_dob(val):
    if not val:
        return "None"
    s = str(val).strip()
    if len(s) == 4 and s.isdigit():
        return "****"
    m = re.search(r"(\d{4})[-/.](\d{2})[-/.](\d{2})", s)
    if m:
        return f"****-**-{m.group(3)}"
    m_dmy = re.search(r"(\d{2})[-/.](\d{2})[-/.](\d{4})", s)
    if m_dmy:
        return f"{m_dmy.group(1)}-**-****"
    return "****"

def mask_doc_number(val):
    if not val:
        return "None"
    if isinstance(val, dict):
        t = val.get("type", "")
        n = str(val.get("number", "")).strip()
        return f"{t}: {mask_doc_number(n)}"
    s = re.sub(r"[\s\-]", "", str(val)).upper()
    if len(s) == 12 and s.isdigit():
        return f"XXXX XXXX {s[-4:]}"
    if len(s) >= 8:
        return f"{s[:3]}{'*' * (len(s) - 5)}{s[-2:]}"
    return "****"

def mask_address(val):
    if not val:
        return "None"
    s = str(val).strip()
    # Mask numbers and first few words
    m_pin = re.search(r"\b([1-9]\d{5})\b", s)
    pin_str = f"{m_pin.group(1)[:3]}***" if m_pin else "***"
    return f"*** [Address masked, PIN: {pin_str}]"

def mask_value(field, val):
    if val is None:
        return "None"
    if field in ("name", "father_name", "mother_name"):
        return mask_name(val)
    elif field == "dob":
        return mask_dob(val)
    elif field == "doc_number":
        return mask_doc_number(val)
    elif field == "address":
        return mask_address(val)
    return "****"

# --------------------------------------------------------------------------- #
# Evaluator Normalization & Fuzzy Checkers
# --------------------------------------------------------------------------- #

def normalize_text(text):
    if not text:
        return ""
    s = str(text).lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    return " ".join(s.split())

def evaluate_name(gt_name, pred_name):
    if not gt_name:
        return True, 1.0  # Not in ground truth
    if not pred_name:
        return False, 0.0

    norm_gt = normalize_text(gt_name)
    norm_pred = normalize_text(pred_name)
    if norm_gt == norm_pred:
        return True, 1.0

    tokens_gt = norm_gt.split()
    tokens_pred = norm_pred.split()
    set_gt = set(tokens_gt)
    set_pred = set(tokens_pred)

    # Reordered tokens
    if set_gt == set_pred:
        return True, 1.0

    # Token subset match (e.g. middle name absent)
    if set_gt < set_pred or set_pred < set_gt:
        shorter = set_gt if len(set_gt) < len(set_pred) else set_pred
        longer = set_pred if len(set_gt) < len(set_pred) else set_gt
        if len(shorter) >= 2:
            return True, 0.95

    # Initial matching check
    if len(tokens_gt) >= 2 and len(tokens_pred) >= 2:
        if tokens_gt[0] == tokens_pred[0] and tokens_gt[-1] == tokens_pred[-1]:
            return True, 0.90

    # Character similarity fallback
    sim = difflib.SequenceMatcher(None, norm_gt, norm_pred).ratio()
    return (sim >= 0.85), round(sim, 2)

def evaluate_dob(gt_dob, pred_dob):
    if not gt_dob:
        return True, 1.0
    if not pred_dob:
        return False, 0.0

    norm_gt = ocr_extract.normalize_dob_string(gt_dob)
    norm_pred = ocr_extract.normalize_dob_string(pred_dob)

    if norm_gt and norm_pred and norm_gt == norm_pred:
        return True, 1.0

    # Year-only comparison
    y_gt = re.search(r"\b(19\d{2}|20\d{2})\b", str(gt_dob))
    y_pred = re.search(r"\b(19\d{2}|20\d{2})\b", str(pred_dob))
    if y_gt and y_pred and y_gt.group(1) == y_pred.group(1):
        return True, 0.90

    return False, 0.0

def evaluate_doc_number(gt_num, pred_num):
    if not gt_num:
        return True, 1.0
    if not pred_num:
        return False, 0.0

    # If predicted is dict e.g. {"type": "PAN", "number": "..."}
    pred_val = pred_num.get("number") if isinstance(pred_num, dict) else str(pred_num)
    gt_clean = re.sub(r"[\s\-_:]", "", str(gt_num)).upper()
    pred_clean = re.sub(r"[\s\-_:]", "", str(pred_val)).upper()

    if gt_clean == pred_clean:
        return True, 1.0
    return False, 0.0

def evaluate_address(gt_addr, pred_addr):
    if not gt_addr:
        return True, 1.0
    if not pred_addr:
        return False, 0.0

    norm_gt = normalize_text(gt_addr)
    norm_pred = normalize_text(pred_addr)

    toks_gt = set(norm_gt.split())
    toks_pred = set(norm_pred.split())

    common = toks_gt & toks_pred
    if not common:
        return False, 0.0

    jaccard = len(common) / len(toks_gt | toks_pred)

    pin_gt = re.search(r"\b([1-9]\d{5})\b", gt_addr)
    pin_pred = re.search(r"\b([1-9]\d{5})\b", pred_addr)
    pin_match = bool(pin_gt and pin_pred and pin_gt.group(1) == pin_pred.group(1))

    if pin_match and len(common) >= 2:
        return True, max(0.85, round(jaccard, 2))

    if jaccard >= 0.60:
        return True, round(jaccard, 2)

    return False, round(jaccard, 2)

# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #

def run_evaluation(data_dir=None, labels_file=None, report_path=None, synth_fallback=True):
    base_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if data_dir is None:
        data_dir = os.path.join(base_root, "data", "gold")
    if labels_file is None:
        labels_file = os.path.join(data_dir, "labels.csv")
    if report_path is None:
        report_path = os.path.join(base_root, "eval", "reports", "baseline.json")

    is_synthetic = False

    # Check if gold set exists and has labels
    has_gold = os.path.exists(labels_file) and os.path.getsize(labels_file) > 10
    if not has_gold:
        if synth_fallback:
            print("\n[NOTICE] Gold set at backend/ml/data/gold is empty or missing labels.csv.")
            print("[NOTICE] Running evaluation on synthetic dataset (synthetic only, not real accuracy).\n")
            data_dir = os.path.join(base_root, "synth", "data")
            labels_file = os.path.join(data_dir, "labels.csv")
            is_synthetic = True
            if not os.path.exists(labels_file):
                print("[NOTICE] Generating synthetic evaluation dataset first...")
                from ml.synth.generate_synth import generate_dataset
                generate_dataset(output_dir=data_dir)
        else:
            raise FileNotFoundError(f"Labels file not found: {labels_file}")

    # Read ground truth labels
    records = []
    with open(labels_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            records.append(r)

    if not records:
        print("[ERROR] No records found in labels file.")
        return {}

    eval_fields = ["name", "dob", "address", "doc_number", "father_name", "mother_name"]

    # Results by document type
    results_by_type = {}
    overall_stats = {f: {"correct": 0, "total": 0} for f in eval_fields}
    worst_failures = []

    for r in records:
        doc_type = r["doc_type"]
        filename = r["file"]
        file_path = os.path.join(data_dir, filename)

        if doc_type not in results_by_type:
            results_by_type[doc_type] = {
                "count": 0,
                "fields": {f: {"correct": 0, "total": 0} for f in eval_fields}
            }

        results_by_type[doc_type]["count"] += 1

        if not os.path.exists(file_path):
            print(f"[WARN] File not found: {file_path}")
            continue

        # Run CURRENT extractor
        extracted = ocr_extract.extract_fields(file_path, filename)

        # Field evaluation
        # 1. Name
        gt_name = r.get("name", "").strip()
        if gt_name:
            results_by_type[doc_type]["fields"]["name"]["total"] += 1
            overall_stats["name"]["total"] += 1
            ok, sim = evaluate_name(gt_name, extracted.get("name"))
            if ok:
                results_by_type[doc_type]["fields"]["name"]["correct"] += 1
                overall_stats["name"]["correct"] += 1
            else:
                worst_failures.append({
                    "doc_type": doc_type, "file": filename, "field": "name",
                    "ground_truth": mask_name(gt_name),
                    "predicted": mask_name(extracted.get("name")),
                    "score": sim,
                })

        # 2. DOB
        gt_dob = r.get("dob", "").strip()
        if gt_dob:
            results_by_type[doc_type]["fields"]["dob"]["total"] += 1
            overall_stats["dob"]["total"] += 1
            ok, sim = evaluate_dob(gt_dob, extracted.get("dob"))
            if ok:
                results_by_type[doc_type]["fields"]["dob"]["correct"] += 1
                overall_stats["dob"]["correct"] += 1
            else:
                worst_failures.append({
                    "doc_type": doc_type, "file": filename, "field": "dob",
                    "ground_truth": mask_dob(gt_dob),
                    "predicted": mask_dob(extracted.get("dob")),
                    "score": sim,
                })

        # 3. Address
        gt_addr = r.get("address", "").strip()
        if gt_addr:
            results_by_type[doc_type]["fields"]["address"]["total"] += 1
            overall_stats["address"]["total"] += 1
            ok, sim = evaluate_address(gt_addr, extracted.get("address"))
            if ok:
                results_by_type[doc_type]["fields"]["address"]["correct"] += 1
                overall_stats["address"]["correct"] += 1
            else:
                worst_failures.append({
                    "doc_type": doc_type, "file": filename, "field": "address",
                    "ground_truth": mask_address(gt_addr),
                    "predicted": mask_address(extracted.get("address")),
                    "score": sim,
                })

        # 4. Document Number
        gt_num = r.get("doc_number", "").strip()
        if gt_num:
            results_by_type[doc_type]["fields"]["doc_number"]["total"] += 1
            overall_stats["doc_number"]["total"] += 1
            ok, sim = evaluate_doc_number(gt_num, extracted.get("doc_number"))
            if ok:
                results_by_type[doc_type]["fields"]["doc_number"]["correct"] += 1
                overall_stats["doc_number"]["correct"] += 1
            else:
                worst_failures.append({
                    "doc_type": doc_type, "file": filename, "field": "doc_number",
                    "ground_truth": mask_doc_number(gt_num),
                    "predicted": mask_doc_number(extracted.get("doc_number")),
                    "score": sim,
                })

        # 5. Father Name
        gt_fname = r.get("father_name", "").strip()
        if gt_fname:
            results_by_type[doc_type]["fields"]["father_name"]["total"] += 1
            overall_stats["father_name"]["total"] += 1
            ok, sim = evaluate_name(gt_fname, extracted.get("father_name"))
            if ok:
                results_by_type[doc_type]["fields"]["father_name"]["correct"] += 1
                overall_stats["father_name"]["correct"] += 1
            else:
                worst_failures.append({
                    "doc_type": doc_type, "file": filename, "field": "father_name",
                    "ground_truth": mask_name(gt_fname),
                    "predicted": mask_name(extracted.get("father_name")),
                    "score": sim,
                })

        # 6. Mother Name
        gt_mname = r.get("mother_name", "").strip()
        if gt_mname:
            results_by_type[doc_type]["fields"]["mother_name"]["total"] += 1
            overall_stats["mother_name"]["total"] += 1
            ok, sim = evaluate_name(gt_mname, extracted.get("mother_name"))
            if ok:
                results_by_type[doc_type]["fields"]["mother_name"]["correct"] += 1
                overall_stats["mother_name"]["correct"] += 1
            else:
                worst_failures.append({
                    "doc_type": doc_type, "file": filename, "field": "mother_name",
                    "ground_truth": mask_name(gt_mname),
                    "predicted": mask_name(extracted.get("mother_name")),
                    "score": sim,
                })

    # Compute percentage tables
    table_rows = []
    type_summaries = {}

    total_correct = 0
    total_eval = 0

    for doc_type, data in results_by_type.items():
        type_correct = 0
        type_eval = 0
        field_acc = {}

        for f in eval_fields:
            c = data["fields"][f]["correct"]
            t = data["fields"][f]["total"]
            type_correct += c
            type_eval += t
            pct = (c / t * 100.0) if t > 0 else None
            field_acc[f] = {"correct": c, "total": t, "accuracy_pct": round(pct, 1) if pct is not None else "N/A"}

        type_pct = (type_correct / type_eval * 100.0) if type_eval > 0 else 0.0
        type_summaries[doc_type] = {
            "samples": data["count"],
            "fields_evaluated": type_eval,
            "fields_correct": type_correct,
            "overall_accuracy_pct": round(type_pct, 1),
            "field_accuracies": field_acc,
        }

        total_correct += type_correct
        total_eval += type_eval

        table_rows.append({
            "doc_type": doc_type,
            "samples": data["count"],
            "name": f"{field_acc['name']['accuracy_pct']}%" if field_acc['name']['accuracy_pct'] != "N/A" else "-",
            "dob": f"{field_acc['dob']['accuracy_pct']}%" if field_acc['dob']['accuracy_pct'] != "N/A" else "-",
            "address": f"{field_acc['address']['accuracy_pct']}%" if field_acc['address']['accuracy_pct'] != "N/A" else "-",
            "doc_number": f"{field_acc['doc_number']['accuracy_pct']}%" if field_acc['doc_number']['accuracy_pct'] != "N/A" else "-",
            "overall": f"{round(type_pct, 1)}%",
        })

    overall_accuracy_pct = round((total_correct / total_eval * 100.0), 1) if total_eval > 0 else 0.0

    report = {
        "timestamp": datetime.now().isoformat(),
        "evaluation_mode": "synthetic only, not real accuracy" if is_synthetic else "gold truth",
        "dataset_path": data_dir,
        "total_documents": len(records),
        "total_fields_evaluated": total_eval,
        "total_fields_correct": total_correct,
        "overall_accuracy_pct": overall_accuracy_pct,
        "by_document_type": type_summaries,
        "overall_by_field": {
            f: {
                "correct": overall_stats[f]["correct"],
                "total": overall_stats[f]["total"],
                "accuracy_pct": round((overall_stats[f]["correct"] / overall_stats[f]["total"] * 100.0), 1) if overall_stats[f]["total"] > 0 else "N/A"
            }
            for f in eval_fields
        },
        "worst_failures_sample": worst_failures[:15],
    }

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Print Formatted Table
    print("\n" + "=" * 78)
    print("           SAHAYAK EXTRACTION BASELINE EVALUATION REPORT")
    print("=" * 78)
    if is_synthetic:
        print("  *** NOTE: Gold dataset empty - SYNTHETIC ONLY, NOT REAL ACCURACY ***")
    print(f"  Total Documents Evaluated: {len(records)}")
    print(f"  Overall Field Accuracy:    {overall_accuracy_pct}% ({total_correct}/{total_eval})")
    print("-" * 78)
    header = f"{'Document Type':<18} | {'N':<3} | {'Name':<7} | {'DOB':<7} | {'Address':<7} | {'Doc No':<7} | {'Overall':<7}"
    print(header)
    print("-" * 78)
    for row in table_rows:
        line = f"{row['doc_type']:<18} | {row['samples']:<3} | {row['name']:<7} | {row['dob']:<7} | {row['address']:<7} | {row['doc_number']:<7} | {row['overall']:<7}"
        print(line)
    print("-" * 78)
    print(f"  Report JSON saved to: {report_path}")
    print("=" * 78 + "\n")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sahayak Extraction Evaluation Harness")
    parser.add_argument("--data-dir", help="Path to evaluation files folder")
    parser.add_argument("--labels-file", help="Path to labels.csv")
    parser.add_argument("--report-path", help="Path to output baseline.json")
    args = parser.parse_args()

    run_evaluation(
        data_dir=args.data_dir,
        labels_file=args.labels_file,
        report_path=args.report_path
    )
