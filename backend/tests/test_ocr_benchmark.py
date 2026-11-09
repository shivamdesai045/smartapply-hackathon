"""The measurement rules must not give fuzzy matches or omissions a pass."""
import json
from pathlib import Path
from test_ocr_accuracy import normalize, metric, field_result


def test_normalization_does_not_hide_spelling_or_number_errors():
    assert normalize(" AARAV  Example ") == normalize("Aarav Example")
    assert normalize("Aarav Example") != normalize("Aarav Exampel")
    assert normalize("2002-08-19") != normalize("2002-09-18")


def test_missing_fields_and_silent_wrong_have_explicit_denominators():
    report = metric([
        {"exact": True, "silent_wrong": False, "missing": False},
        {"exact": False, "silent_wrong": True, "missing": False},
        {"exact": False, "silent_wrong": False, "missing": True},
    ])
    assert report["expected"] == 3
    assert report["exact_match_pct"] == 33.33
    assert report["silent_wrong_pct"] == 33.33
    assert report["missing"] == 1


def test_new_and_legacy_field_shapes():
    assert field_result({"doc_fields": {"name": {"value": "Aarav", "confidence": .9, "needs_review": False}}}, "name") == ("Aarav", .9, False)
    assert field_result({"doc_number": {"type": "PAN", "number": "ABCZE1234F"}, "fieldConfidence": {"doc_number": .9}, "needsReview": {"doc_number": True}}, "doc_number") == ("ABCZE1234F", .9, True)


def test_all_tier_one_types_have_real_raster_clean_and_phone_fixtures():
    root = Path(__file__).resolve().parents[1] / "ocr_fixtures"
    manifest = json.loads((root / "ground_truth.json").read_text(encoding="utf-8"))
    types = {"Aadhaar Card", "PAN Card", "Passport", "Voter ID Card", "10th Marksheet", "12th Marksheet", "Birth Certificate"}
    assert manifest["synthetic"]
    for kind in types:
        assert {f["quality"] for f in manifest["fixtures"] if f["document_type"] == kind} == {"clean", "phone"}
    for fixture in manifest["fixtures"]:
        assert fixture["synthetic"]
        assert (root / fixture["file"]).read_bytes().startswith(b"\x89PNG")
