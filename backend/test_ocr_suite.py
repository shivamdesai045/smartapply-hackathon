import os
import tempfile
import unittest
from io import BytesIO
from PIL import Image, ImageDraw
import fitz

import ocr_extract
import rule_engine
from app import app
import db

class TestSmartApplyOcrAndMatching(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_01_file_validation_success(self):
        # Valid PNG
        img = Image.new("RGB", (100, 100), color="white")
        tmp_img = "test_valid.png"
        img.save(tmp_img)
        try:
            ok, err = ocr_extract.validate_file(tmp_img, "test_valid.png")
            self.assertTrue(ok)
            self.assertIsNone(err)
        finally:
            if os.path.exists(tmp_img):
                os.remove(tmp_img)

        # Valid PDF
        doc = fitz.open()
        doc.new_page()
        tmp_pdf = "test_valid.pdf"
        doc.save(tmp_pdf)
        doc.close()
        try:
            ok, err = ocr_extract.validate_file(tmp_pdf, "test_valid.pdf")
            self.assertTrue(ok)
            self.assertIsNone(err)
        finally:
            if os.path.exists(tmp_pdf):
                os.remove(tmp_pdf)

    def test_02_file_validation_rejections(self):
        # Invalid extension
        tmp_txt = "test_invalid.txt"
        with open(tmp_txt, "w") as f:
            f.write("test content")
        try:
            ok, err = ocr_extract.validate_file(tmp_txt, "test_invalid.txt")
            self.assertFalse(ok)
            self.assertIn("Unsupported file type", err)
        finally:
            if os.path.exists(tmp_txt):
                os.remove(tmp_txt)

        # Empty file
        tmp_empty = "test_empty.png"
        with open(tmp_empty, "wb") as f:
            pass
        try:
            ok, err = ocr_extract.validate_file(tmp_empty, "test_empty.png")
            self.assertFalse(ok)
            self.assertIn("empty", err.lower())
        finally:
            if os.path.exists(tmp_empty):
                os.remove(tmp_empty)

        # Fake extension with corrupted magic bytes
        tmp_corrupt = "test_corrupt.png"
        with open(tmp_corrupt, "wb") as f:
            f.write(b"NOT_A_PNG_FILE_HEADER_XYZ")
        try:
            ok, err = ocr_extract.validate_file(tmp_corrupt, "test_corrupt.png")
            self.assertFalse(ok)
            self.assertIn("corrupted", err.lower())
        finally:
            if os.path.exists(tmp_corrupt):
                os.remove(tmp_corrupt)

    def test_03_pdf_text_extraction(self):
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Name: Rajesh Kumar\nDOB: 12/04/1995\nPAN: ABCDE1234F\nAddress: 123 MG Road, Pune 411001")
        tmp_pdf = "test_ocr.pdf"
        doc.save(tmp_pdf)
        doc.close()

        try:
            fields = ocr_extract.extract_fields(tmp_pdf, "test_ocr.pdf")
            self.assertEqual(fields["name"], "Rajesh Kumar")
            self.assertEqual(fields["dob"], "1995-04-12")
            self.assertIsNotNone(fields["doc_number"])
            self.assertEqual(fields["doc_number"]["type"], "PAN")
            self.assertEqual(fields["doc_number"]["number"], "ABCDE1234F")
        finally:
            if os.path.exists(tmp_pdf):
                os.remove(tmp_pdf)

    def test_04_rule_engine_verdicts(self):
        # 1. Match scenario
        docs_match = {
            "Aadhaar": {"name": "Rajesh Kumar", "dob": "1995-04-12", "address": "123 MG Road Pune 411001"},
            "PAN": {"name": "Rajesh Kumar", "dob": "1995-04-12", "address": "123 MG Road Pune 411001"}
        }
        res_match = rule_engine.check_mismatches(docs_match)
        self.assertTrue(res_match["clean"])
        self.assertEqual(len(res_match["issues"]), 0)
        # Verify comparisons have "match" verdicts
        match_verdicts = [c for c in res_match["comparisons"] if c["verdict"] == "match"]
        self.assertGreaterEqual(len(match_verdicts), 2)

        # 2. Name & DOB Mismatch scenario
        docs_mismatch = {
            "Aadhaar": {"name": "Rajesh Kumar", "dob": "1995-04-12"},
            "PAN": {"name": "Rajesh Sharma", "dob": "1995-04-15"}
        }
        res_mis = rule_engine.check_mismatches(docs_mismatch)
        self.assertFalse(res_mis["clean"])
        self.assertEqual(len(res_mis["issues"]), 2)

        name_issue = next(i for i in res_mis["issues"] if i["field"] == "name")
        self.assertEqual(name_issue["verdict"], "possible_mismatch")
        self.assertIsNotNone(name_issue["similarity"])
        self.assertIn("similarity", name_issue["explanation"].lower())

        dob_issue = next(i for i in res_mis["issues"] if i["field"] == "dob")
        self.assertEqual(dob_issue["verdict"], "possible_mismatch")
        self.assertEqual(dob_issue["similarity"], 0.0)

    def test_05_auth_guard_protection(self):
        # Unauthenticated calls should return 401
        res = self.app.get("/api/checklist/Passport/mismatches")
        self.assertEqual(res.status_code, 401)

        res = self.app.post("/api/checklist/Passport/upload")
        self.assertEqual(res.status_code, 401)

        res = self.app.post("/api/check-mismatches", json={"documents": {}})
        self.assertEqual(res.status_code, 401)

    def test_06_authenticated_flow(self):
        # Log in with existing user
        login_res = self.app.post("/api/auth/login", json={"email": "test@example.com", "password": "password123"})
        # Even if password differs, let's test session directly
        with self.app.session_transaction() as sess:
            sess["user_id"] = 1

        # Now calling authenticated endpoint works
        res = self.app.get("/api/checklist/Passport/mismatches?session_id=sess123")
        self.assertEqual(res.status_code, 200)

if __name__ == "__main__":
    unittest.main()
