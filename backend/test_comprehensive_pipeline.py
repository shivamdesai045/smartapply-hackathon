import uuid
import os
import sys
import unittest
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import fitz

import ocr_extract
import rule_engine
import db
from app import app

class ComprehensivePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()
        cls.client = app.test_client()
        cls.test_files = []

        # Generate test fixtures
        cls.pan_img = cls._create_pan_fixture("comp_pan.png")
        cls.aadhaar_img = cls._create_aadhaar_fixture("comp_aadhaar.png")
        cls.mismatch_pan_img = cls._create_mismatch_pan_fixture("comp_mismatch_pan.png")
        cls.rot90_img = cls._create_rot90_fixture("comp_rot90_pan.png")
        cls.scanned_pdf = cls._create_scanned_pdf_fixture("comp_scanned_pan.pdf")
        cls.blank_img = cls._create_blank_fixture("comp_blank.png")

    @classmethod
    def tearDownClass(cls):
        for f in cls.test_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass

    @classmethod
    def _create_pan_fixture(cls, filename):
        img = Image.new("RGB", (1800, 1200), "white")
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
            font_bold = ImageFont.truetype("arialbd.ttf", 44)
        except Exception:
            font = font_bold = ImageFont.load_default()
        d.text((100, 80), "INCOME TAX DEPARTMENT", fill="black", font=font_bold)
        d.text((100, 150), "GOVT. OF INDIA", fill="black", font=font_bold)
        d.text((100, 240), "Permanent Account Number Card", fill="black", font=font)
        d.text((100, 340), "Name: SHIVAM SHASHIKANT DESAI", fill="black", font=font)
        d.text((100, 420), "Father's Name: SHASHIKANT DESAI", fill="black", font=font)
        d.text((100, 500), "Date of Birth: 15/08/2003", fill="black", font=font)
        d.text((100, 600), "PAN: ABCDE1234F", fill="black", font=font_bold)
        img.save(filename, dpi=(300, 300))
        cls.test_files.append(filename)
        return filename

    @classmethod
    def _create_aadhaar_fixture(cls, filename):
        img = Image.new("RGB", (1800, 1200), "white")
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
            font_bold = ImageFont.truetype("arialbd.ttf", 44)
        except Exception:
            font = font_bold = ImageFont.load_default()
        d.text((100, 80), "GOVERNMENT OF INDIA", fill="black", font=font_bold)
        d.text((100, 150), "UNIQUE IDENTIFICATION AUTHORITY OF INDIA", fill="black", font=font_bold)
        d.text((100, 260), "Shivam Shashikant Desai", fill="black", font=font_bold)
        d.text((100, 340), "DOB: 15/08/2003", fill="black", font=font)
        d.text((100, 420), "Gender: Male", fill="black", font=font)
        d.text((100, 520), "Address: Flat 402, Shiv Plaza, FC Road, Pune 411005", fill="black", font=font)
        d.text((100, 620), "1234 5678 9012", fill="black", font=font_bold)
        img.save(filename, dpi=(300, 300))
        cls.test_files.append(filename)
        return filename

    @classmethod
    def _create_mismatch_pan_fixture(cls, filename):
        img = Image.new("RGB", (1800, 1200), "white")
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
            font_bold = ImageFont.truetype("arialbd.ttf", 44)
        except Exception:
            font = font_bold = ImageFont.load_default()
        d.text((100, 80), "INCOME TAX DEPARTMENT", fill="black", font=font_bold)
        d.text((100, 150), "GOVT. OF INDIA", fill="black", font=font_bold)
        d.text((100, 240), "Permanent Account Number Card", fill="black", font=font)
        d.text((100, 340), "Name: RAHUL RAMESH SHARMA", fill="black", font=font)
        d.text((100, 420), "Father's Name: RAMESH SHARMA", fill="black", font=font)
        d.text((100, 500), "Date of Birth: 20/11/1998", fill="black", font=font)
        d.text((100, 600), "PAN: WXYZP9876Q", fill="black", font=font_bold)
        img.save(filename, dpi=(300, 300))
        cls.test_files.append(filename)
        return filename

    @classmethod
    def _create_rot90_fixture(cls, filename):
        img = Image.new("RGB", (1800, 1200), "white")
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
            font_bold = ImageFont.truetype("arialbd.ttf", 44)
        except Exception:
            font = font_bold = ImageFont.load_default()
        d.text((100, 80), "INCOME TAX DEPARTMENT", fill="black", font=font_bold)
        d.text((100, 150), "GOVT. OF INDIA", fill="black", font=font_bold)
        d.text((100, 240), "Permanent Account Number Card", fill="black", font=font)
        d.text((100, 340), "Name: SHIVAM SHASHIKANT DESAI", fill="black", font=font)
        d.text((100, 420), "Father's Name: SHASHIKANT DESAI", fill="black", font=font)
        d.text((100, 500), "Date of Birth: 15/08/2003", fill="black", font=font)
        d.text((100, 600), "PAN: ABCDE1234F", fill="black", font=font_bold)
        rot = img.rotate(90, expand=True)
        rot.save(filename, dpi=(300, 300))
        cls.test_files.append(filename)
        return filename

    @classmethod
    def _create_scanned_pdf_fixture(cls, filename):
        doc = fitz.open()
        page = doc.new_page(width=1800, height=1200)
        page.insert_image(fitz.Rect(0, 0, 1800, 1200), filename=cls.pan_img)
        doc.save(filename)
        doc.close()
        cls.test_files.append(filename)
        return filename

    @classmethod
    def _create_blank_fixture(cls, filename):
        img = Image.new("RGB", (600, 600), "white")
        img.save(filename)
        cls.test_files.append(filename)
        return filename

    # =========================================================================
    # Test 1: Upright Documents OCR Accuracy
    # =========================================================================
    def test_01_upright_ocr_accuracy(self):
        pan_fields = ocr_extract.extract_fields(self.pan_img, self.pan_img)
        self.assertEqual(pan_fields["name"], "Shivam Shashikant Desai")
        self.assertEqual(pan_fields["dob"], "2003-08-15")
        self.assertIsNotNone(pan_fields["doc_number"])
        self.assertEqual(pan_fields["doc_number"]["type"], "PAN")
        self.assertEqual(pan_fields["doc_number"]["number"], "ABCDE1234F")
        self.assertTrue(len(pan_fields["raw_text"]) > 50)

        aadhaar_fields = ocr_extract.extract_fields(self.aadhaar_img, self.aadhaar_img)
        self.assertEqual(aadhaar_fields["name"], "Shivam Shashikant Desai")
        self.assertEqual(aadhaar_fields["dob"], "2003-08-15")
        self.assertIn("FC Road, Pune", aadhaar_fields["address"])
        self.assertEqual(aadhaar_fields["doc_number"]["type"], "Aadhaar")
        self.assertEqual(aadhaar_fields["doc_number"]["number"], "1234 5678 9012")

    # =========================================================================
    # Test 2: Rotated 90-degree Image Handling
    # =========================================================================
    def test_02_rotated_image_handling(self):
        rot_fields = ocr_extract.extract_fields(self.rot90_img, self.rot90_img)
        self.assertEqual(rot_fields["name"], "Shivam Shashikant Desai")
        self.assertEqual(rot_fields["dob"], "2003-08-15")
        self.assertIsNotNone(rot_fields["doc_number"])
        self.assertEqual(rot_fields["doc_number"]["number"], "ABCDE1234F")

    # =========================================================================
    # Test 3: Pure Scanned PDF Rasterization at 300 DPI
    # =========================================================================
    def test_03_scanned_pdf_handling(self):
        # Confirm no embedded text
        doc = fitz.open(self.scanned_pdf)
        self.assertEqual(len(doc[0].get_text().strip()), 0)
        doc.close()

        pdf_fields = ocr_extract.extract_fields(self.scanned_pdf, self.scanned_pdf)
        self.assertEqual(pdf_fields["name"], "Shivam Shashikant Desai")
        self.assertEqual(pdf_fields["dob"], "2003-08-15")
        self.assertEqual(pdf_fields["doc_number"]["type"], "PAN")
        self.assertEqual(pdf_fields["doc_number"]["number"], "ABCDE1234F")

    # =========================================================================
    # Test 4: Unreadable / Blank Image
    # =========================================================================
    def test_04_unreadable_image(self):
        blank_fields = ocr_extract.extract_fields(self.blank_img, self.blank_img)
        self.assertIsNone(blank_fields["name"])
        self.assertIsNone(blank_fields["dob"])
        self.assertIsNone(blank_fields["address"])
        self.assertIsNone(blank_fields["doc_number"])
        self.assertEqual(blank_fields["raw_text"], "")
        self.assertTrue(blank_fields["ocrAttempted"])

    # =========================================================================
    # Test 5: Matching Documents Comparison
    # =========================================================================
    def test_05_matching_documents(self):
        pan_fields = ocr_extract.extract_fields(self.pan_img, self.pan_img)
        aadhaar_fields = ocr_extract.extract_fields(self.aadhaar_img, self.aadhaar_img)

        docs = {
            "PAN Card": pan_fields,
            "Aadhaar Card": aadhaar_fields
        }
        res = rule_engine.check_mismatches(docs)

        # Name and DOB should match
        name_comp = next(c for c in res["comparisons"] if c["field"] == "name")
        self.assertEqual(name_comp["result"], "Match")
        self.assertEqual(name_comp["verdict"], "match")

        dob_comp = next(c for c in res["comparisons"] if c["field"] == "dob")
        self.assertEqual(dob_comp["result"], "Match")
        self.assertEqual(dob_comp["verdict"], "match")

        # Address: PAN does not have address, so address is Unable to Compare (not mismatch!)
        addr_comp = next(c for c in res["comparisons"] if c["field"] == "address")
        self.assertEqual(addr_comp["result"], "Unable to Compare")

        # Doc Number: Incompatible document types (PAN vs Aadhaar) is Unable to Compare (not mismatch!)
        doc_num_comp = next(c for c in res["comparisons"] if c["field"] == "doc_number")
        self.assertEqual(doc_num_comp["result"], "Unable to Compare")

        # No blocking issues!
        self.assertEqual(len(res["issues"]), 0)
        self.assertTrue(res["clean"])

    # =========================================================================
    # Test 6: Deliberate Mismatch Detection
    # =========================================================================
    def test_06_deliberate_mismatches(self):
        pan_fields = ocr_extract.extract_fields(self.pan_img, self.pan_img)
        mismatch_fields = ocr_extract.extract_fields(self.mismatch_pan_img, self.mismatch_pan_img)

        docs = {
            "Primary PAN": pan_fields,
            "Secondary PAN": mismatch_fields
        }
        res = rule_engine.check_mismatches(docs)
        self.assertFalse(res["clean"])
        self.assertGreaterEqual(len(res["issues"]), 2)

        name_issue = next(i for i in res["issues"] if i["field"] == "name")
        self.assertEqual(name_issue["result"], "Mismatch")

        dob_issue = next(i for i in res["issues"] if i["field"] == "dob")
        self.assertEqual(dob_issue["result"], "Mismatch")

    # =========================================================================
    # Test 7: Checklist Descriptions Never Compared as Identity Data
    # =========================================================================
    def test_07_checklist_description_protection(self):
        docs = {
            "Doc A": {"name": "Proof of Identity", "dob": "2003-08-15"},
            "Doc B": {"name": "Shivam Shashikant Desai", "dob": "2003-08-15"}
        }
        res = rule_engine.check_mismatches(docs)
        name_comp = next(c for c in res["comparisons"] if c["field"] == "name")
        self.assertEqual(name_comp["result"], "Unable to Compare")
        # Ensure it is NOT treated as a Mismatch issue
        self.assertEqual(len([i for i in res["issues"] if i["field"] == "name"]), 0)

    # =========================================================================
    # Test 8: Dev Diagnostic View Access Control & Payload
    # =========================================================================
    def test_08_diagnostic_view_endpoint(self):
        session_id = str(uuid.uuid4())
        service = "Passport"
        variant = "adult"

        with self.client.session_transaction() as sess:
            sess["session_id"] = session_id

        # 1. Blocked when DIAGNOSTICS_ENABLED is not set even with dev flag & header
        os.environ.pop("DIAGNOSTICS_ENABLED", None)
        res_blocked = self.client.get(
            f"/api/checklist/{service}/diagnostics?session_id={session_id}&variant={variant}&dev=true",
            headers={"X-Dev-Mode": "true"}
        )
        self.assertEqual(res_blocked.status_code, 403)

        # 2. Allowed when DIAGNOSTICS_ENABLED="true" in dev
        try:
            os.environ["DIAGNOSTICS_ENABLED"] = "true"
            db.mark_uploaded(
                session_id, service, variant, "Proof of Identity", "PAN Card",
                self.pan_img, doc_name="Shivam Desai", doc_dob="2003-08-15",
                doc_address=None, doc_number="PAN: ABCDE1234F",
                raw_text="INCOME TAX DEPARTMENT\nGOVT. OF INDIA\nPAN: ABCDE1234F"
            )

            res = self.client.get(
                f"/api/checklist/{service}/diagnostics?session_id={session_id}&variant={variant}"
            )
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data["isDev"])
            self.assertEqual(len(data["documents"]), 1)
            doc_entry = data["documents"][0]
            self.assertIn("INCOME TAX DEPARTMENT", doc_entry["rawOcrText"])
            self.assertEqual(doc_entry["extractedFields"]["name"], "Shivam Desai")
            self.assertEqual(doc_entry["extractedFields"]["dob"], "2003-08-15")

            # 3. Production simulation check: disabled in production even with DIAGNOSTICS_ENABLED="true"
            old_env = os.environ.get("FLASK_ENV")
            try:
                os.environ["FLASK_ENV"] = "production"
                app.debug = False
                res_prod = self.client.get(
                    f"/api/checklist/{service}/diagnostics?session_id={session_id}&variant={variant}"
                )
                self.assertEqual(res_prod.status_code, 403)
                self.assertIn("restricted", res_prod.get_json().get("error", "").lower())
            finally:
                if old_env is not None:
                    os.environ["FLASK_ENV"] = old_env
                else:
                    os.environ.pop("FLASK_ENV", None)
                app.debug = True
        finally:
            os.environ.pop("DIAGNOSTICS_ENABLED", None)

    # =========================================================================
    # Test 9: Navigation & Database Persistence
    # =========================================================================
    def test_09_database_persistence(self):
        sess = str(uuid.uuid4())
        service = "Aadhaar Card"
        variant = "adult"

        os.environ["DIAGNOSTICS_ENABLED"] = "true"
        try:
            db.mark_uploaded(
                sess, service, variant, "Proof of Identity", "PAN Card",
                self.pan_img, doc_name="Shivam Desai", doc_dob="2003-08-15",
                doc_address=None, doc_number="PAN: ABCDE1234F",
                raw_text="PAN Raw OCR Data"
            )

            progress = db.get_progress(sess, service, variant)
            self.assertIn("Proof of Identity", progress)
            self.assertEqual(progress["Proof of Identity"]["docName"], "Shivam Desai")
            self.assertEqual(progress["Proof of Identity"]["rawText"], "PAN Raw OCR Data")

            docs = db.get_documents_with_data(sess, service, variant)
            self.assertIn("PAN Card", docs)
            self.assertEqual(docs["PAN Card"]["name"], "Shivam Desai")
        finally:
            os.environ.pop("DIAGNOSTICS_ENABLED", None)


    # =========================================================================
    # Test 10: Aadhaar Update Disclaimer Never Included in Address
    # =========================================================================
    def test_10_aadhaar_disclaimer_not_in_address(self):
        img = Image.new("RGB", (1800, 1200), "white")
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
            font_bold = ImageFont.truetype("arialbd.ttf", 44)
        except Exception:
            font = font_bold = ImageFont.load_default()
        d.text((100, 80), "GOVERNMENT OF INDIA", fill="black", font=font_bold)
        d.text((100, 160), "UNIQUE IDENTIFICATION AUTHORITY OF INDIA", fill="black", font=font_bold)
        d.text((100, 260), "Address: Flat 402, Shiv Plaza, FC Road, Pune 411005", fill="black", font=font)
        d.text((100, 360), "should be updated in Aadhaar after every 10 years from date of enrolment for Aadhaar.", fill="black", font=font)
        d.text((100, 440), "Toll free: 1947, help@uidai.gov.in, www.uidai.gov.in", fill="black", font=font)
        d.text((100, 540), "1234 5678 9012", fill="black", font=font_bold)
        fname = "comp_aadhaar_disclaimer.png"
        img.save(fname, dpi=(300, 300))
        self.test_files.append(fname)

        fields = ocr_extract.extract_fields(fname, fname)
        addr = fields.get("address")
        self.assertIsNotNone(addr)
        self.assertIn("FC Road, Pune", addr)
        # Verify disclaimers are completely stripped
        self.assertNotIn("10 years", addr.lower())
        self.assertNotIn("updated", addr.lower())
        self.assertNotIn("enrolment", addr.lower())
        self.assertNotIn("1947", addr)
        self.assertNotIn("uidai", addr.lower())

    # =========================================================================
    # Test 11: Marksheet Subject Never Classified as Person Name
    # =========================================================================
    def test_11_marksheet_subject_not_in_name(self):
        img = Image.new("RGB", (1800, 1200), "white")
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
            font_bold = ImageFont.truetype("arialbd.ttf", 44)
        except Exception:
            font = font_bold = ImageFont.load_default()
        d.text((100, 80), "MAHARASHTRA STATE BOARD OF SECONDARY EDUCATION", fill="black", font=font_bold)
        d.text((100, 160), "SECONDARY SCHOOL CERTIFICATE EXAMINATION - MARCH 2019", fill="black", font=font_bold)
        d.text((100, 260), "01 MARATHI 100 035 088", fill="black", font=font)
        d.text((100, 340), "02 HINDI LANG SS 100 035 085", fill="black", font=font)
        d.text((100, 420), "03 ENGLISH 100 035 079", fill="black", font=font)
        d.text((100, 500), "MATHEMATICS 100 035 092", fill="black", font=font)
        d.text((100, 580), "TOTAL MARKS: 514", fill="black", font=font_bold)
        fname = "comp_marksheet_no_name.png"
        img.save(fname, dpi=(300, 300))
        self.test_files.append(fname)

        fields = ocr_extract.extract_fields(fname, fname)
        # Name must be None, NOT "Hindi Lang Ss"
        self.assertIsNone(fields.get("name"))

    # =========================================================================
    # Test 12: Marksheet Candidate Name Accurately Extracted
    # =========================================================================
    def test_12_marksheet_candidate_name_extracted(self):
        img = Image.new("RGB", (1800, 1200), "white")
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
            font_bold = ImageFont.truetype("arialbd.ttf", 44)
        except Exception:
            font = font_bold = ImageFont.load_default()
        d.text((100, 80), "MAHARASHTRA STATE BOARD OF SECONDARY EDUCATION", fill="black", font=font_bold)
        d.text((100, 160), "SECONDARY SCHOOL CERTIFICATE EXAMINATION", fill="black", font=font_bold)
        d.text((100, 260), "Candidate's Full Name: DESAI SHIVAM SHASHIKANT", fill="black", font=font)
        d.text((100, 340), "Mother's Name: SEEMA", fill="black", font=font)
        d.text((100, 420), "02 HINDI LANG SS 100 035 085", fill="black", font=font)
        d.text((100, 500), "Date of Birth: 15/08/2003", fill="black", font=font)
        fname = "comp_marksheet_valid.png"
        img.save(fname, dpi=(300, 300))
        self.test_files.append(fname)

        fields = ocr_extract.extract_fields(fname, fname)
        self.assertEqual(fields.get("name"), "Desai Shivam Shashikant")
        self.assertEqual(fields.get("dob"), "2003-08-15")

    # =========================================================================
    # Test 13: Reusing Same Document Across Slots Avoids Duplicate Comparisons
    # =========================================================================
    def test_13_duplicate_document_reuse_deduplication(self):
        sess = str(uuid.uuid4())
        service = "Aadhaar Card"
        variant = "adult"

        with self.client.session_transaction() as sc:
            sc["session_id"] = sess

        # Upload Aadhaar for Proof of Identity and Proof of Address
        db.mark_uploaded(
            sess, service, variant, "Proof of Identity", "Aadhaar Card",
            self.aadhaar_img, doc_name="Shivam Desai", doc_dob="2003-08-15",
            doc_address=None, doc_number="Aadhaar: 1234 5678 9012",
            raw_text="Aadhaar Front"
        )
        db.mark_uploaded(
            sess, service, variant, "Proof of Address", "Aadhaar Card",
            self.aadhaar_img, doc_name=None, doc_dob=None,
            doc_address="Flat 402, Shiv Plaza, FC Road, Pune 411005", doc_number="Aadhaar: 1234 5678 9012",
            raw_text="Aadhaar Back"
        )

        res = self.client.get(f"/api/checklist/{service}/mismatches?session_id={sess}")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["enoughData"])
        self.assertEqual(len(data["comparisons"]), 0)
        self.assertEqual(len(data["issues"]), 0)
        self.assertIn("cannot be cross-compared against itself", data["message"])

        # Now add PAN Card (a 2nd distinct document)
        db.mark_uploaded(
            sess, service, variant, "Proof of Date of Birth", "PAN Card",
            self.pan_img, doc_name="Shivam Desai", doc_dob="2003-08-15",
            doc_address=None, doc_number="PAN: ABCDE1234F",
            raw_text="PAN Card Front"
        )

        res2 = self.client.get(f"/api/checklist/{service}/mismatches?session_id={sess}")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertTrue(data2["enoughData"])
        # Exactly ONE pair of distinct documents compared: Aadhaar vs PAN
        self.assertEqual(set(data2["documentsWithData"]), {"Aadhaar Card", "PAN Card"})
        # 0 issues between matching records
        self.assertEqual(len(data2["issues"]), 0)

    # =========================================================================
    # Test 14: Missing or Unreliable Fields Yield 'Unable to Compare' Without False Mismatch
    # =========================================================================
    def test_14_missing_or_unreliable_fields_no_false_mismatch(self):
        docs = {
            "PAN Card": {"name": "Shivam Desai", "dob": "2003-08-15", "address": None, "doc_number": "PAN: ABCDE1234F"},
            "10th Marksheet": {"name": None, "dob": "2003-08-15", "address": None, "doc_number": None}
        }
        res = rule_engine.check_mismatches(docs)

        # Name is reported as Unable to Compare
        name_comp = next(c for c in res["comparisons"] if c["field"] == "name")
        self.assertEqual(name_comp["result"], "Unable to Compare")
        self.assertIn("not detected in 10th Marksheet", name_comp["explanation"])

        # DOB is Match
        dob_comp = next(c for c in res["comparisons"] if c["field"] == "dob")
        self.assertEqual(dob_comp["result"], "Match")

        # Zero false mismatch issues!
        self.assertEqual(len(res["issues"]), 0)

if __name__ == "__main__":
    unittest.main()


