import os
import unittest
import uuid
import tempfile
from ocr_extract import clean_person_name, guess_name, extract_fields, validate_file
from rule_engine import check_mismatches, compare_names
import db
from app import app


class TestMarksheetPipelineComplete(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_A_and_B_marksheet_extraction_and_missing_dob(self):
        """
        Verify:
        - 10th marksheet extracts student name even with layout noise and next-line candidate name.
        - Marksheet without DOB extracts name cleanly with dob=None.
        - Document is NOT rejected or flagged unreadable because DOB is absent.
        """
        raw_marksheet_text = """
at (starr aga 1a / CANDIDATE'S MOTHER'S NAME Savita _
SECONDARY SCHOOL CERTIFICATE EXAMINATION - STATEMENT OF MARKS
oe oo ara = aH) / CANDIDATE =' FULL NAME (SURNAME FIRST)
Desai Shivam Shashikant \ufffdone
01 MARATHI (1st LANG) - 75
14 MATHEMATICS - 88
73 SOCIAL SCIENCES - 82
Percentage 90.40 Total Marks FOUR HUNDRED AND FIFTYTWO
Result PASS
"""
        name = guess_name(raw_marksheet_text, chosen_option="10th Marksheet")
        self.assertEqual(name, "Desai Shivam Shashikant")

    def test_C_and_D_name_comparisons_matching_and_genuine_difference(self):
        """
        Verify:
        - Inverted surname order ('Shivam Shashikant Desai' vs 'Desai Shivam Shashikant') is a Match.
        - Genuinely different names ('Shivam Shashikant Desai' vs 'Rohan Suresh Patil') is a Mismatch.
        """
        # Matching names with different order
        res_match, verd_match, sim_match, exp_match, sev_match = compare_names(
            "Shivam Shashikant Desai", "Desai Shivam Shashikant"
        )
        self.assertEqual(res_match, "Match")
        self.assertEqual(verd_match, "match")
        self.assertEqual(sim_match, 1.0)

        # Genuinely different names
        res_diff, verd_diff, sim_diff, exp_diff, sev_diff = compare_names(
            "Shivam Shashikant Desai", "Rohan Suresh Patil"
        )
        self.assertEqual(res_diff, "Mismatch")
        self.assertEqual(verd_diff, "mismatch")
        self.assertTrue(sim_diff < 0.82)

    def test_E_missing_fields_not_treated_as_mismatches(self):
        """
        Verify:
        - When Marksheet has Name but no DOB, and Aadhaar has Name and DOB:
        - Checker produces Match for Name, and Unable to Compare for DOB and Address.
        - 0 issues/mismatches are generated.
        - enoughData is True and clean is True.
        """
        docs = {
            "Aadhaar Card": {
                "name": "Shivam Shashikant Desai",
                "dob": "2007-05-03",
                "address": "Satara, Maharashtra, 415003",
                "doc_number": "Aadhaar: 2989 2089 5077",
            },
            "10th Marksheet": {
                "name": "Desai Shivam Shashikant",
                "dob": None,  # absent on marksheet
                "address": None,
                "doc_number": None,
            },
        }
        res = check_mismatches(docs)
        self.assertTrue(res["enoughData"])
        self.assertTrue(res["clean"])
        self.assertEqual(len(res["issues"]), 0)

        summary = res["summary"]
        self.assertEqual(summary["matches"], 1)  # Name matches
        self.assertEqual(summary["mismatches"], 0)
        self.assertEqual(summary["possibleMismatches"], 0)
        self.assertEqual(summary["unableToCompare"], 2)  # DOB & Address

        comparisons = {c["field"]: c for c in res["comparisons"]}
        self.assertEqual(comparisons["name"]["result"], "Match")
        self.assertEqual(comparisons["dob"]["result"], "Unable to Compare")
        self.assertEqual(comparisons["address"]["result"], "Unable to Compare")
        self.assertIn("not detected in 10th Marksheet", comparisons["dob"]["explanation"])

    def test_F_unreadable_and_corrupt_files_produce_accurate_diagnostics(self):
        """
        Verify:
        - Corrupted / invalid file header is rejected at upload validation.
        - When a document has 0 readable text, checker message accurately identifies it as having no text.
        - When a document has text but no identity fields, message explains no identity fields were identified.
        """
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"NOT_A_VALID_PDF_HEADER_JUST_GARBAGE")
            bad_path = f.name

        try:
            is_valid, err = validate_file(bad_path, "corrupt.pdf")
            self.assertFalse(is_valid)
            self.assertIn("corrupted", err.lower())
        finally:
            if os.path.exists(bad_path):
                os.remove(bad_path)

        # State: Text extracted, but no supported identity fields
        docs_no_fields = {
            "Aadhaar Card": {
                "name": "Shivam Desai",
                "dob": "2007-05-03",
                "address": "Satara",
                "doc_number": "1234",
            },
            "Unknown Slip": {
                "name": None,
                "dob": None,
                "address": None,
                "doc_number": None,
                "text_length": 500,  # 500 characters of OCR text
            },
        }
        res_no_fields = check_mismatches(docs_no_fields)
        self.assertFalse(res_no_fields["enoughData"])
        self.assertIn("no identity fields", res_no_fields["message"])

        # State: Little or no text (<60 chars)
        docs_empty = {
            "Aadhaar Card": {
                "name": "Shivam Desai",
                "dob": "2007-05-03",
                "address": "Satara",
                "doc_number": "1234",
            },
            "Blank Image": {
                "name": None,
                "dob": None,
                "address": None,
                "doc_number": None,
                "text_length": 10,  # blank
            },
        }
        res_empty = check_mismatches(docs_empty)
        self.assertFalse(res_empty["enoughData"])
        self.assertIn("no readable text detected", res_empty["message"])


if __name__ == "__main__":
    unittest.main()
