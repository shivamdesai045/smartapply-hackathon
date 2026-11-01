"""
Unit tests for Phase 5: Per-Type Document Parsers with Spatial Cues and Confidence Scoring.
"""

import unittest
import parsers
import ocr_extract

class TestPhase5Parsers(unittest.TestCase):

    def test_01_passport_split_name_concatenation(self):
        """Passports split Given Name and Surname across lines; parser must combine them."""
        ocr_data = {
            "text": "PASSPORT / REPUBLIC OF INDIA\nGiven Name(s): Shivam Satish\nSurname: Desai\nPassport No: Z1234567\nDate of Birth: 15/08/2003\n",
            "lines": [
                {"text": "PASSPORT / REPUBLIC OF INDIA"},
                {"text": "Given Name(s): Shivam Satish"},
                {"text": "Surname: Desai"},
                {"text": "Passport No: Z1234567"},
                {"text": "Date of Birth: 15/08/2003"},
            ],
            "words": [],
        }
        res = parsers.parse_document(ocr_data, chosen_option="Passport")
        self.assertEqual(res["name"], "Shivam Satish Desai")
        self.assertEqual(res["dob"], "2003-08-15")
        self.assertIsNotNone(res["doc_number"])
        self.assertEqual(res["doc_number"]["number"], "Z1234567")
        self.assertGreaterEqual(res["field_confidences"]["name"], 0.8)

    def test_02_marksheet_candidate_and_parents(self):
        """Marksheet subjects must be rejected, extracting candidate and parents."""
        ocr_data = {
            "text": (
                "CENTRAL BOARD OF SECONDARY EDUCATION\n"
                "SECONDARY SCHOOL EXAMINATION\n"
                "Candidate Name: Aarav Sharma\n"
                "Roll No: 1245781\n"
                "Date of Birth: 14/05/1992\n"
                "Mother's Name: Sunita Sharma\n"
                "Father's Name: Suresh Sharma\n"
                "Subject Codes: 041 Mathematics 086 Science\n"
                "Result: PASSED\n"
                "Certificate No: SYN98765432\n"
            ),
            "lines": [],
            "words": [],
        }
        res = parsers.parse_document(ocr_data, chosen_option="10th Marksheet")
        self.assertEqual(res["name"], "Aarav Sharma")
        self.assertEqual(res["mother_name"], "Sunita Sharma")
        self.assertEqual(res["father_name"], "Suresh Sharma")
        self.assertEqual(res["dob"], "1992-05-14")
        self.assertEqual(res["doc_number"]["number"], "SYN98765432")

    def test_03_pan_father_and_name_separation(self):
        """PAN names must separate applicant name from father's name."""
        ocr_data = {
            "text": (
                "INCOME TAX DEPARTMENT\n"
                "GOVT. OF INDIA\n"
                "Permanent Account Number Card\n"
                "Name: Pooja Patel\n"
                "Father's Name: Dinesh Patel\n"
                "Date of Birth: 23/11/1988\n"
                "Permanent Account Number: ABCZP1234F\n"
            ),
            "lines": [],
            "words": [],
        }
        res = parsers.parse_document(ocr_data, chosen_option="PAN Card")
        self.assertEqual(res["name"], "Pooja Patel")
        self.assertEqual(res["father_name"], "Dinesh Patel")
        self.assertEqual(res["dob"], "1988-11-23")
        self.assertEqual(res["doc_number"]["number"], "ABCZP1234F")

    def test_04_aadhaar_spatial_extraction(self):
        ocr_data = {
            "text": (
                "Government of India\n"
                "Unique Identification Authority of India\n"
                "Name: Rohan Kulkarni\n"
                "DOB: 19/08/1995\n"
                "Gender: Male\n"
                "Address: Flat 301, Lake View, MG Road, Pune 411001\n"
                "2345 6789 0124\n"
            ),
            "lines": [],
            "words": [],
        }
        res = parsers.parse_document(ocr_data, chosen_option="Aadhaar Card")
        self.assertEqual(res["name"], "Rohan Kulkarni")
        self.assertEqual(res["dob"], "1995-08-19")
        self.assertIn("MG Road, Pune 411001", res["address"])
        self.assertEqual(res["doc_number"]["number"], "2345 6789 0124")

    def test_05_driving_licence_and_voter_parsing(self):
        # DL
        dl_data = {
            "text": "UNION OF INDIA\nDRIVING LICENCE\nLicence No: DL-9920201234567\nName: Neha Verma\nSon / Daughter / Wife of: Dattatray Verma\nDOB: 30/03/2001\nAddress: Sector 15 Gandhinagar 382016\n",
            "lines": [], "words": [],
        }
        res_dl = parsers.parse_document(dl_data, chosen_option="Driving Licence")
        self.assertEqual(res_dl["name"], "Neha Verma")
        self.assertEqual(res_dl["father_name"], "Dattatray Verma")
        self.assertEqual(res_dl["dob"], "2001-03-30")
        self.assertEqual(res_dl["doc_number"]["number"], "DL-9920201234567")

        # Voter
        voter_data = {
            "text": "ELECTION COMMISSION OF INDIA\nEPIC No: ZZZ9876543\nElector Name: Vikram Desai\nFather's Name: Shashikant Desai\nDOB: 05/12/1997\nAddress: Green Glen Layout Bengaluru 560103\n",
            "lines": [], "words": [],
        }
        res_voter = parsers.parse_document(voter_data, chosen_option="Voter ID")
        self.assertEqual(res_voter["name"], "Vikram Desai")
        self.assertEqual(res_voter["father_name"], "Shashikant Desai")
        self.assertEqual(res_voter["doc_number"]["number"], "ZZZ9876543")

    def test_06_field_confidence_bounds(self):
        ocr_data = {
            "text": "Name: Shivam Desai\nDOB: 15/08/2003\n",
            "lines": [], "words": [],
        }
        res = parsers.parse_document(ocr_data, chosen_option="PAN Card")
        for f, conf in res["field_confidences"].items():
            self.assertGreaterEqual(conf, 0.0)
            self.assertLessEqual(conf, 1.0)

    def test_07_fallback_preservation_for_unknown_documents(self):
        unknown_data = {
            "text": "Rent Agreement\nName: Shivam Desai\nAddress: Flat 101 Pune 411001\n",
            "lines": [], "words": [],
        }
        res = parsers.parse_document(unknown_data, chosen_option="Rent Agreement")
        self.assertEqual(res["name"], "Shivam Desai")
        self.assertIn("Pune 411001", res["address"])


if __name__ == "__main__":
    unittest.main()
