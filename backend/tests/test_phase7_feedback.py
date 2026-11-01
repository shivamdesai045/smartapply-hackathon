"""
Unit tests for Phase 7: Feedback Learning, Continuous Adaptation & Privacy Verification.
"""

import os
import sys
import unittest
import json
import shutil
import tempfile

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ml.feedback import feedback_store
from ml.feedback.feedback_store import (
    record_feedback,
    get_all_feedback,
    get_feedback_stats,
    clear_feedback,
    mask_sensitive_value,
    FEEDBACK_DIR,
)
from ml.train.retrain_with_feedback import retrain_model_with_feedback
import app as flask_app


class TestPhase7FeedbackLearning(unittest.TestCase):
    def setUp(self):
        # Isolate feedback storage for test
        clear_feedback()
        self.app = flask_app.app.test_client()

    def tearDown(self):
        clear_feedback()

    def test_01_privacy_and_data_minimization(self):
        """Verify strict masking: never store unmasked Aadhaar, raw OCR text or raw PII in features."""
        # 1. Aadhaar masking
        masked_aadhaar = mask_sensitive_value("doc_number", "2345 6789 0124")
        self.assertEqual(masked_aadhaar, "XXXX XXXX 0124")
        self.assertNotIn("2345", masked_aadhaar)

        # 2. PAN masking
        masked_pan = mask_sensitive_value("doc_number", "ABCPE1234F")
        self.assertEqual(masked_pan, "ABC*****F")
        self.assertNotIn("1234", masked_pan)

        # 3. Record feedback with Aadhaar and ensure raw digits never exist on disk
        rec = record_feedback(
            doc_type="Aadhaar Card",
            original_fields={"name": "Rajesh Kumar", "doc_number": "234567890124"},
            corrected_fields={"name": "Rajesh Sharma", "doc_number": "234567890124"},
        )
        self.assertIsNotNone(rec)
        fb_id = rec["feedback_id"]
        fb_path = os.path.join(FEEDBACK_DIR, f"{fb_id}.json")
        self.assertTrue(os.path.exists(fb_path))

        with open(fb_path, "r", encoding="utf-8") as f:
            disk_content = f.read()

        # Raw 12-digit number must NOT appear in file
        self.assertNotIn("234567890124", disk_content)
        self.assertIn("XXXX XXXX 0124", disk_content)

    def test_02_feedback_recording_and_stats(self):
        """Verify saving and aggregating feedback samples."""
        record_feedback(
            doc_type="Passport",
            original_fields={"name": "Shivam", "dob": "1995"},
            corrected_fields={"name": "Shivam Desai", "dob": "1995-04-12"},
            field_confidences={"name": 0.65, "dob": 0.80},
        )
        record_feedback(
            doc_type="PAN Card",
            original_fields={"name": "Priya", "doc_number": None},
            corrected_fields={"name": "Priya Sharma", "doc_number": "ABCDE1234F"},
        )

        all_fb = get_all_feedback()
        self.assertEqual(len(all_fb), 2)

        stats = get_feedback_stats()
        self.assertEqual(stats["total_feedback_samples"], 2)
        self.assertIn("Passport", stats["by_document_type"])
        self.assertIn("PAN Card", stats["by_document_type"])
        self.assertIn("name", stats["by_field_corrected"])

    def test_03_feedback_endpoint_post_and_get(self):
        """Verify /api/feedback POST and /api/feedback/stats GET endpoints."""
        import secrets
        valid_sid = secrets.token_urlsafe(32)
        with self.app.session_transaction() as sess:
            sess["session_id"] = valid_sid
            sess["user_id"] = 1

        payload = {
            "session_id": valid_sid,
            "service": "Passport",
            "variant": "adult",
            "requirement": "Proof of Identity",
            "doc_type": "Passport",
            "original": {"name": "Test User"},
            "corrected": {"name": "Test Real User"},
            "field_confidences": {"name": 0.75},
        }

        # Session token query param provides authentication
        res = self.app.post("/api/feedback", json=payload, query_string={"session_id": valid_sid})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("feedback_id", data)

        # Check stats endpoint
        stats_res = self.app.get("/api/feedback/stats", query_string={"session_id": valid_sid})
        self.assertEqual(stats_res.status_code, 200)
        stats_data = stats_res.get_json()
        self.assertGreaterEqual(stats_data["total_feedback_samples"], 1)

    def test_04_continuous_retraining_pipeline(self):
        """Verify feedback ingestion, model retraining, and zero-regression validation."""
        # 1. Create a synthetic feedback record with valid 37-dim feature vectors
        fb_features = [0.5] * 37
        mock_fb_record = {
            "feedback_id": "fb_test_mock_001",
            "timestamp": "2026-11-01T12:00:00",
            "service_name": "Passport",
            "variant": "adult",
            "requirement": "Proof of Identity",
            "doc_type": "Passport",
            "differences": {"name": {"from": "Old", "to": "New"}},
            "corrected_fields": {"name": "New"},
            "original_fields": {"name": "Old"},
            "field_confidences": {"name": 0.60},
            "feature_samples_count": 2,
            "feature_samples": [
                {"features": fb_features, "label": "name", "field": "name", "line_index": 0},
                {"features": [0.1] * 37, "label": "other", "field": "none", "line_index": 1},
            ],
        }
        fb_file = os.path.join(FEEDBACK_DIR, "fb_test_mock_001.json")
        with open(fb_file, "w", encoding="utf-8") as f:
            json.dump(mock_fb_record, f)

        # 2. Run retraining pipeline with temp report
        tmp_report = os.path.join(tempfile.gettempdir(), "test_retrain_report.json")
        audit = retrain_model_with_feedback(report_path=tmp_report)

        self.assertIn("status", audit)
        self.assertIn("SUCCESS", audit["status"])
        self.assertGreaterEqual(audit["benchmark_eval_accuracy_pct"], 95.0)
        self.assertGreaterEqual(audit["feedback_samples"], 2)


if __name__ == "__main__":
    unittest.main()
