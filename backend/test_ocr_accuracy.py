"""Exact field benchmark. Run directly; real OCR, no mocks or sidecar boxes.

python test_ocr_accuracy.py --report ocr_fixtures/reports/baseline.json
Only whitespace/case/Unicode normalization is allowed, no fuzzy credit.
Silent wrong = incorrect nonempty value with confidence >= .70 and no review flag,
divided by all expected fields. Missing fields count as exact-match failures.
"""
import argparse
import os
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import re
import time
import unicodedata
import warnings

ROOT = Path(__file__).parent


def normalize(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value))).strip().casefold()


def field_result(result, field):
    entry = (result.get("doc_fields") or {}).get(field)
    if isinstance(entry, dict):
        value = entry.get("value")
        if isinstance(value, dict):
            value = value.get("number", value.get("value"))
        return value, entry.get("confidence", 0), entry.get("needs_review", entry.get("needsReview", True))
    value = result.get(field)
    if field == "document_type":
        value = value or result.get("detectedType") or result.get("doc_meta", {}).get("detectedType")
    if isinstance(value, dict):
        value = value.get("number", value.get("value"))
    confidence = (result.get("fieldConfidence") or result.get("fieldConfidences") or {}).get(field, 0)
    review = result.get("needsReview", {}).get(field, confidence < .70)
    return value, confidence, review


def metric(rows):
    total = len(rows)
    exact = sum(x["exact"] for x in rows)
    silent = sum(x["silent_wrong"] for x in rows)
    return {"expected": total, "exact": exact, "exact_match_pct": round(exact / total * 100, 2) if total else None, "silent_wrong": silent, "silent_wrong_pct": round(silent / total * 100, 2) if total else None, "missing": sum(x["missing"] for x in rows)}


def run(manifest_path, report_path, limit=None):
    # Import once before the run to pin the loaded implementation for this process.
    from ocr_extract import extract_fields
    import pytesseract
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows, samples = [], []
    fixture_list = manifest["fixtures"][:limit] if limit else manifest["fixtures"]
    for fixture in fixture_list:
        path = manifest_path.parent / fixture["file"]
        start = time.perf_counter()
        error_type = None
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = extract_fields(str(path), path.name, fixture["document_type"])
        except Exception as exc:
            result, error_type = {}, type(exc).__name__
        seconds = time.perf_counter() - start
        for field, truth in fixture["expected"].items():
            value, confidence, review = field_result(result, field)
            correct = normalize(value) == normalize(truth)
            rows.append({"fixture_id": fixture["id"], "document_type": fixture["document_type"], "quality": fixture["quality"], "field": field, "exact": correct, "missing": not bool(normalize(value)), "silent_wrong": bool(value) and not correct and confidence >= .70 and not review})
        samples.append({"fixture_id": fixture["id"], "seconds": round(seconds, 3), "seconds_per_page": round(seconds / fixture["pages"], 3), "error_type": error_type})
        print(f"{fixture['id']}: {seconds:.2f}s", flush=True)
    by_type, by_quality, by_field, by_type_field = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for row in rows:
        by_type[row["document_type"]].append(row)
        by_quality[row["quality"]].append(row)
        by_field[row["field"]].append(row)
        by_type_field[(row["document_type"], row["field"])].append(row)
    report = {"generated_utc": datetime.now(timezone.utc).isoformat(), "synthetic": manifest["synthetic"], "fixture_count": len(samples), "limitations": manifest["limitations"], "scoring": __doc__, "runtime": {"ocr_engine": os.getenv("OCR_ENGINE", "paddleocr"), "ocr_max_side": os.getenv("OCR_MAX_SIDE", "3200"), "line_orientation": os.getenv("OCR_LINE_ORIENTATION", "1"), "python": platform.python_version(), "platform": platform.platform(), "tesseract": str(pytesseract.get_tesseract_version()), "languages": pytesseract.get_languages()}, "overall": metric(rows), "by_quality": {k: metric(v) for k,v in by_quality.items()}, "by_document_type": {k: metric(v) for k,v in by_type.items()}, "by_field": {k: metric(v) for k,v in by_field.items()}, "by_document_type_and_field": {f"{k[0]} / {k[1]}": metric(v) for k,v in by_type_field.items()}, "samples": samples, "field_results": rows, "max_seconds_per_page": max(s["seconds_per_page"] for s in samples), "mean_seconds_per_page": round(sum(s["seconds_per_page"] for s in samples)/len(samples), 3)}
    report["targets_met"] = {"clean_exact_95_pct": report["by_quality"].get("clean", {}).get("exact_match_pct", 0) >= 95, "phone_exact_85_pct": report["by_quality"].get("phone", {}).get("exact_match_pct", 0) >= 85, "silent_wrong_at_most_2_pct": report["overall"]["silent_wrong_pct"] <= 2, "all_pages_under_8_seconds": report["max_seconds_per_page"] < 8}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"overall": report["overall"], "by_quality": report["by_quality"], "max_seconds_per_page": report["max_seconds_per_page"], "targets_met": report["targets_met"]}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "ocr_fixtures" / "ground_truth.json")
    parser.add_argument("--report", type=Path, default=ROOT / "ocr_fixtures" / "reports" / "current.json")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    run(args.manifest, args.report, args.limit)
