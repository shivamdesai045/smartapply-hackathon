"""
Phase 8 Comprehensive Test Suite for Sahayak.

Tests covering:
1. Path traversal protection in upload and session paths.
2. Validators (including Verhoeff checksum, PAN structure, DOB normalization).
3. Seeded synthetic generator (numbers provably invalid: Aadhaar fails Verhoeff, PAN uses 4th letter 'Z').
4. Feature extraction (37 dimensions, zero raw text / n-gram memorization).
5. Document extractor on synthetic pages (fields extracted, confidences returned).
6. Model promotion gate (zero-regression thresholding, candidate validation).
7. Feedback storage data minimization (no raw OCR page dump, Aadhaar masked).
8. API keys backward compatibility (all original response keys preserved, new keys additive).
"""

import os
import sys
import re
import json
import pytest
import shutil
import tempfile
import urllib.parse
from datetime import datetime

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import app as flask_app
import db
import ocr_extract
from ocr_extract import validate_verhoeff, is_valid_pan
from app import get_safe_upload_path, is_valid_session_token, UPLOAD_FOLDER
from ml.synth import generate_synth
from ml.features.feature_extractor import extract_line_features, TARGET_LABELS
from ml.feedback.feedback_store import (
    record_feedback,
    get_all_feedback,
    mask_sensitive_value,
    FEEDBACK_DIR,
    clear_feedback,
)
from ml.train.retrain_with_feedback import retrain_model_with_feedback
from parsers import parse_document


@pytest.fixture
def client():
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


# --------------------------------------------------------------------------- #
# 1. Path Traversal Protection
# --------------------------------------------------------------------------- #

class TestPathTraversalProtection:
    def test_rejects_parent_traversal(self):
        """Rejects relative traversal patterns ../ and ..\\."""
        with pytest.raises(ValueError, match="Path traversal"):
            get_safe_upload_path("../../etc/passwd", "Passport", "adult")

        with pytest.raises(ValueError, match="Path traversal"):
            get_safe_upload_path("valid_sid_1234567890123456789012", "../Passport", "adult")

        with pytest.raises(ValueError, match="Path traversal"):
            get_safe_upload_path("valid_sid_1234567890123456789012", "Passport", "..\\adult")

    def test_rejects_url_encoded_traversal(self):
        """Rejects URL-encoded traversal characters (%2e%2e)."""
        with pytest.raises(ValueError, match="Path traversal"):
            get_safe_upload_path("%2e%2e%2froot", "Passport", "adult")

    def test_rejects_absolute_paths(self):
        """Rejects absolute paths trying to break out of upload directory."""
        with pytest.raises(ValueError, match="Path traversal"):
            get_safe_upload_path("C:\\Windows\\System32", "Passport", "adult")

    def test_allows_safe_alphanumeric_paths(self):
        """Allows valid session token, service name, and variant."""
        folder, filepath = get_safe_upload_path(
            "valid_token_32_characters_long_123456",
            "Passport",
            "adult",
            requirement="Proof of Identity",
            ext=".pdf"
        )
        assert folder is not None
        assert filepath is not None
        # Must reside strictly within UPLOAD_FOLDER
        real_upload = os.path.realpath(UPLOAD_FOLDER)
        assert os.path.commonpath([real_upload, filepath]) == real_upload


# --------------------------------------------------------------------------- #
# 2. Validators (Verhoeff, PAN, DOB)
# --------------------------------------------------------------------------- #

class TestValidators:
    def test_verhoeff_checksum_validation(self):
        """Verifies Verhoeff algorithm on valid vs corrupted numbers."""
        # 234567890124 is a mathematically valid Verhoeff number
        assert validate_verhoeff("234567890124") is True
        # Altering single digit must fail checksum
        assert validate_verhoeff("234567890125") is False
        assert validate_verhoeff("234567890123") is False
        assert validate_verhoeff("999999999999") is False
        assert validate_verhoeff("") is False

    def test_pan_structure_and_entity_type(self):
        """Verifies PAN format: 5 letters, 4 digits, 1 letter; 4th char is entity type."""
        # Valid entity types: P (Individual), C (Company), F (Firm), A (AOP), T (Trust), H (HUF)
        assert is_valid_pan("ABCPE1234F") is True
        assert is_valid_pan("XYZCA5678K") is True
        assert is_valid_pan("BLRFA9999M") is True

        # Invalid 4th character (Z, X, numbers)
        assert is_valid_pan("ABCZE1234F") is False
        assert is_valid_pan("ABC1E1234F") is False
        assert is_valid_pan("ABCPE1234") is False
        assert is_valid_pan("ABCPE12345F") is False


# --------------------------------------------------------------------------- #
# 3. Seeded Synthetic Generator (Provably Invalid Numbers)
# --------------------------------------------------------------------------- #

class TestSeededSyntheticGenerator:
    def test_seeded_generation_reproducibility(self):
        """Verifies seeded generator produces provably invalid numbers deterministically."""
        import random
        rng1 = random.Random(42)
        aadh1 = generate_synth.make_invalid_aadhaar(rng1)
        pan1 = generate_synth.make_invalid_pan(rng1, "Shivam Desai")

        rng2 = random.Random(42)
        aadh2 = generate_synth.make_invalid_aadhaar(rng2)
        pan2 = generate_synth.make_invalid_pan(rng2, "Shivam Desai")

        assert aadh1 == aadh2
        assert pan1 == pan2

    def test_synthetic_ids_are_provably_invalid(self):
        """Verifies all synthetic Aadhaar numbers fail Verhoeff and PAN numbers use invalid 4th letter 'Z'."""
        import random
        rng = random.Random(12345)
        for _ in range(25):
            aadh = generate_synth.make_invalid_aadhaar(rng)
            clean_aadh = re.sub(r"\D", "", aadh)
            assert len(clean_aadh) == 12
            assert generate_synth.fails_verhoeff(clean_aadh) is True
            assert validate_verhoeff(clean_aadh) is False

            pan = generate_synth.make_invalid_pan(rng, "Candidate Name")
            assert len(pan) == 10
            assert pan[3] == "Z"
            assert is_valid_pan(pan) is False


# --------------------------------------------------------------------------- #
# 4. Privacy-Preserving Feature Extraction
# --------------------------------------------------------------------------- #

class TestFeatureExtractionPrivacy:
    def test_feature_vector_dimension_and_types(self):
        """Feature vector must be exactly 37 floats with zero raw text tokens."""
        line = {
            "text": "Shivam Shashikant Desai",
            "x_min": 0.1,
            "y_min": 0.2,
            "x_max": 0.6,
            "y_max": 0.25,
            "confidence": 95.0,
        }
        all_lines = [
            {"text": "Name of Candidate", "x_min": 0.1, "y_min": 0.18, "x_max": 0.4, "y_max": 0.20, "confidence": 98.0},
            line,
            {"text": "Date of Birth: 12/04/1995", "x_min": 0.1, "y_min": 0.28, "x_max": 0.5, "y_max": 0.31, "confidence": 92.0},
        ]
        feats = extract_line_features(line, all_lines)
        assert len(feats) == 37
        assert all(isinstance(v, (float, int)) for v in feats)
        # Verify no string leakage in vector
        for v in feats:
            assert not isinstance(v, str)


# --------------------------------------------------------------------------- #
# 5. Extractor on Synthetic Pages
# --------------------------------------------------------------------------- #

class TestExtractorOnSyntheticPages:
    def test_extractor_reaches_key_fields(self):
        """Extracts fields on benchmark synthetic PDFs with high confidence."""
        synth_dir = os.path.join(backend_dir, "ml", "synth", "data")
        if not os.path.exists(synth_dir):
            pytest.skip("Synthetic dataset directory not found.")

        test_pdf = os.path.join(synth_dir, "passport_01.pdf")
        if not os.path.exists(test_pdf):
            pytest.skip("passport_01.pdf not found.")

        result = ocr_extract.extract_fields(test_pdf, "passport_01.pdf", chosen_option="Passport")
        assert result is not None
        assert result.get("name") is not None
        assert len(result["name"].split()) >= 2
        assert result.get("dob") is not None
        assert result.get("doc_number") is not None
        assert "lines" in result
        assert "boxes" in result
        assert "ocrConfidence" in result


# --------------------------------------------------------------------------- #
# 6. Model Promotion Gate
# --------------------------------------------------------------------------- #

class TestModelPromotionGate:
    def test_promotion_gate_threshold_check(self):
        """Retraining pipeline verifies benchmark accuracy meets threshold before updating model."""
        tmp_report = os.path.join(tempfile.gettempdir(), "test_promotion_report.json")
        audit = retrain_model_with_feedback(report_path=tmp_report)
        assert "status" in audit
        assert "benchmark_eval_accuracy_pct" in audit
        # The benchmark accuracy must meet the zero-regression threshold
        assert audit["benchmark_eval_accuracy_pct"] >= 95.0
        assert "SUCCESS" in audit["status"]


# --------------------------------------------------------------------------- #
# 7. Feedback Storage Data Minimization
# --------------------------------------------------------------------------- #

class TestFeedbackStoragePrivacy:
    def test_feedback_has_no_raw_ocr_dump_and_masks_aadhaar(self):
        """Ensures feedback storage contains no raw OCR dumps and strictly masks Aadhaar."""
        clear_feedback()
        try:
            rec = record_feedback(
                doc_type="Aadhaar Card",
                original_fields={"name": "Aarav Sharma", "doc_number": "2345 6789 0124", "raw_text": "DUMP OF FULL PAGE OCR"},
                corrected_fields={"name": "Aarav S Sharma", "doc_number": "2345 6789 0124"},
            )
            assert rec is not None
            fb_id = rec["feedback_id"]
            fb_file = os.path.join(FEEDBACK_DIR, f"{fb_id}.json")
            assert os.path.exists(fb_file)

            with open(fb_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 1. No unmasked 12 digits
            assert "2345 6789 0124" not in content
            assert "234567890124" not in content
            assert "XXXX XXXX 0124" in content

            # 2. Raw OCR page dump key must never be persisted
            assert "DUMP OF FULL PAGE OCR" not in content
        finally:
            clear_feedback()


# --------------------------------------------------------------------------- #
# 8. API Keys Backward Compatibility
# --------------------------------------------------------------------------- #

class TestApiKeysUnchanged:
    def test_services_api_response_keys(self, client):
        """GET /api/services returns structure with original keys (categories, totalCategories, totalServices)."""
        res = client.get("/api/services")
        assert res.status_code == 200
        data = res.get_json()
        assert "categories" in data
        assert "totalCategories" in data
        assert "totalServices" in data
        assert isinstance(data["categories"], list)
        assert len(data["categories"]) > 0
        first_cat = data["categories"][0]
        assert "id" in first_cat
        assert "title" in first_cat
        assert "services" in first_cat
        assert len(first_cat["services"]) > 0
        first_srv = first_cat["services"][0]
        assert "name" in first_srv
        assert "desc" in first_srv

    def test_checklist_status_response_keys(self, client):
        """GET /api/checklist/<service>/status maintains all required keys."""
        import secrets
        sid = secrets.token_urlsafe(32)
        with client.session_transaction() as sess:
            sess["session_id"] = sid

        res = client.get(f"/api/checklist/Passport/status?session_id={sid}&variant=adult")
        assert res.status_code == 200
        data = res.get_json()
        expected_keys = ["service", "variant", "requirements", "comparableCount"]
        for k in expected_keys:
            assert k in data, f"Missing key {k} in status response"

    def test_extraction_result_keys(self):
        """OCR result retains all original fields and adds additive metadata."""
        synth_dir = os.path.join(backend_dir, "ml", "synth", "data")
        test_pdf = os.path.join(synth_dir, "pan_card_01.pdf")
        if not os.path.exists(test_pdf):
            pytest.skip("pan_card_01.pdf not found.")

        res = ocr_extract.extract_fields(test_pdf, "pan_card_01.pdf", chosen_option="PAN Card")
        # Original keys
        assert "name" in res
        assert "dob" in res
        assert "address" in res
        assert "doc_number" in res
        assert "quality" in res
        assert "detectedType" in res

        # Additive Phase 4/5/6 keys
        assert "lines" in res
        assert "boxes" in res
        assert "ocrConfidence" in res
        assert "ocrEngine" in res
