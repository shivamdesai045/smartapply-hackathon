"""
Unit tests for Phase 4: OCR with Bounding Boxes, Adaptive Preprocessing, and Multi-Engine Adapter.
"""

import os
import unittest
from PIL import Image, ImageDraw

import ocr_boxes
import ocr_extract

class TestPhase4OcrBoxes(unittest.TestCase):

    def test_01_language_discovery(self):
        langs = ocr_boxes.get_available_tesseract_languages()
        self.assertIsInstance(langs, set)
        self.assertIn("eng", langs)

        lang_str = ocr_boxes.get_ocr_language_string()
        self.assertIn("eng", lang_str)

        missing = ocr_boxes.check_missing_languages()
        self.assertIsInstance(missing, list)

    def test_02_preprocessing_pipeline(self):
        # 1. Otsu threshold calculation
        img = Image.new("L", (200, 200), color=240)
        d = ImageDraw.Draw(img)
        d.text((30, 40), "Sample Document Text", fill=20)
        thresh = ocr_boxes.compute_otsu_threshold(img)
        self.assertGreater(thresh, 0)
        self.assertLess(thresh, 255)

        # 2. Small image upscaling
        small_img = Image.new("RGB", (300, 200), color="white")
        upscaled = ocr_boxes.upscale_small_image(small_img, min_dim=1200)
        self.assertGreaterEqual(max(upscaled.size), 1200)

        # 3. Candidate preprocessing variants
        variants = ocr_boxes.generate_preprocessing_variants(img)
        self.assertEqual(len(variants), 4)
        names = [v[0] for v in variants]
        self.assertIn("autocontrast", names)
        self.assertIn("denoised_sharpened", names)
        self.assertIn("otsu_threshold", names)
        self.assertIn("high_contrast", names)

    def test_03_image_bounding_boxes(self):
        img = Image.new("RGB", (600, 200), color="white")
        d = ImageDraw.Draw(img)
        d.text((30, 40), "Government of India\nAadhaar Card 1234", fill="black")
        tmp_img = "test_phase4_box.png"
        img.save(tmp_img)

        try:
            res = ocr_boxes.extract_ocr_with_boxes(tmp_img)
            self.assertIn("words", res)
            self.assertIn("lines", res)
            self.assertGreater(len(res["words"]), 0)
            self.assertGreater(len(res["lines"]), 0)

            # Check normalized coordinates are in [0.0, 1.0]
            for w in res["words"]:
                x0, y0, x1, y1 = w["bbox"]
                self.assertGreaterEqual(x0, 0.0)
                self.assertLessEqual(x0, 1.0)
                self.assertGreaterEqual(y0, 0.0)
                self.assertLessEqual(y0, 1.0)
                self.assertGreaterEqual(w["confidence"], 0.0)
                self.assertLessEqual(w["confidence"], 100.0)
        finally:
            if os.path.exists(tmp_img):
                os.remove(tmp_img)

    def test_04_pdf_text_and_boxes(self):
        pdf_path = os.path.join(os.path.dirname(__file__), "..", "ml", "synth", "data", "aadhaar_card_01.pdf")
        if os.path.exists(pdf_path):
            res = ocr_boxes.extract_ocr_with_boxes(pdf_path)
            self.assertGreater(len(res["words"]), 0)
            self.assertGreater(len(res["lines"]), 0)
            self.assertGreaterEqual(res["mean_confidence"], 80.0)
            self.assertEqual(res["source"], "digital_pdf")

    def test_05_easyocr_fallback(self):
        # Even if easyocr is not installed, it must gracefully return None or fallback
        img = Image.new("RGB", (100, 100), color="white")
        res = ocr_boxes.run_easyocr_on_image(img)
        # In our environment easyocr is not installed, so it should return None without throwing
        self.assertIsNone(res)

    def test_06_extract_fields_additive_keys(self):
        pdf_path = os.path.join(os.path.dirname(__file__), "..", "ml", "synth", "data", "aadhaar_card_01.pdf")
        if os.path.exists(pdf_path):
            fields = ocr_extract.extract_fields(pdf_path, "aadhaar_card_01.pdf")
            self.assertTrue(fields["ocrAttempted"])
            self.assertIn("boxes", fields)
            self.assertIn("lines", fields)
            self.assertIn("ocrConfidence", fields)
            self.assertIn("ocrEngine", fields)
            self.assertEqual(fields["name"], "Aarav Kumar Sharma")
            self.assertEqual(fields["dob"], "1992-05-14")


if __name__ == "__main__":
    unittest.main()
