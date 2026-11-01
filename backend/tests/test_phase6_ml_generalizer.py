"""
Unit tests for Phase 6: ML Field Generalizer, Spatial Feature Extractor, and Model Ensemble.
"""

import os
import unittest

from ml.features import feature_extractor
from ml.train import train_classifier
from parsers import ml_generalizer
import parsers

class TestPhase6MLGeneralizer(unittest.TestCase):

    def test_01_feature_extractor_privacy_and_structure(self):
        """Hard rule: Feature extractor must use spatial/geometrical cues only, zero text memorization."""
        line = {"text": "Aarav Sharma", "bbox": [0.08, 0.14, 0.35, 0.18]}
        all_lines = [
            {"text": "Government of India", "bbox": [0.08, 0.05, 0.50, 0.08]},
            line,
            {"text": "DOB: 14/05/1992", "bbox": [0.08, 0.20, 0.30, 0.23]},
        ]
        feats = feature_extractor.extract_line_features(line, all_lines)
        self.assertIsInstance(feats, list)
        self.assertEqual(len(feats), len(feature_extractor.FEATURE_NAMES))
        # Ensure all features are numeric floats
        for f in feats:
            self.assertIsInstance(f, float)
            self.assertFalse(any(isinstance(f, s) for s in (str, bytes)))

    def test_02_model_artifact_integrity(self):
        """Verify field_classifier.pkl loads and has required target classes."""
        pkg = ml_generalizer.get_classifier()
        self.assertIsNotNone(pkg, "field_classifier.pkl could not be loaded!")
        self.assertIn("model", pkg)
        self.assertIn("target_labels", pkg)
        self.assertEqual(pkg["target_labels"], feature_extractor.TARGET_LABELS)

    def test_03_ml_generalizer_candidate_prediction(self):
        """Verify ML generalizer predicts field candidates from OCR lines."""
        pdf_path = os.path.join(os.path.dirname(__file__), "..", "ml", "synth", "data", "pan_card_02.pdf")
        if os.path.exists(pdf_path):
            import ocr_boxes
            ocr_data = ocr_boxes.extract_ocr_with_boxes(pdf_path)
            candidates = ml_generalizer.predict_field_candidates(ocr_data)
            self.assertIsInstance(candidates, dict)
            self.assertIn("name", candidates)
            self.assertEqual(candidates["name"]["value"], "Pooja Suresh Patel")
            self.assertGreaterEqual(candidates["name"]["confidence"], 0.8)
            self.assertIn("father_name", candidates)
            self.assertEqual(candidates["father_name"]["value"], "Dinesh Patel")
            self.assertIn("dob", candidates)
            self.assertEqual(candidates["dob"]["value"], "1988-11-23")

    def test_04_ensemble_assistance_on_unconfident_field(self):
        """When specialized parser leaves field empty, ML model proposes and fills candidate."""
        # Ambiguous document without clear header
        ocr_data = {
            "text": "Name: Shivam Desai\nDOB: 15/08/2003\nABCDE1234F\n",
            "lines": [
                {"text": "Name: Shivam Desai", "bbox": [0.1, 0.20, 0.5, 0.23]},
                {"text": "DOB: 15/08/2003", "bbox": [0.1, 0.25, 0.5, 0.28]},
                {"text": "ABCDE1234F", "bbox": [0.1, 0.32, 0.5, 0.35]},
            ],
            "words": [],
        }
        res = parsers.parse_document(ocr_data, chosen_option="Unknown Certificate")
        self.assertIsNotNone(res["name"])
        self.assertEqual(res["name"], "Shivam Desai")
        self.assertEqual(res["dob"], "2003-08-15")


if __name__ == "__main__":
    unittest.main()
