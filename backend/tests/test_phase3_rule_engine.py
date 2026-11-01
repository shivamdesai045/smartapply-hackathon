import unittest
import rule_engine


class TestPhase3RuleEngine(unittest.TestCase):
    def test_01_compare_names_token_subset(self):
        # Shorter name with >= 2 tokens that is a subset of longer name
        res, verd, sim, exp, sev = rule_engine.compare_names("Shivam Desai", "Shivam Shashikant Desai")
        self.assertEqual(res, "Match")
        self.assertEqual(verd, "match")
        self.assertIn("additional middle/father's name", exp)

        # Reverse order
        res_rev, _, _, exp_rev, _ = rule_engine.compare_names("Shivam Shashikant Desai", "Shivam Desai")
        self.assertEqual(res_rev, "Match")
        self.assertIn("additional middle/father's name", exp_rev)

    def test_02_compare_names_single_token_possible_mismatch(self):
        # Single token match against full name
        res, verd, sim, exp, sev = rule_engine.compare_names("Shivam", "Shivam Shashikant Desai")
        self.assertEqual(res, "Possible Mismatch")
        self.assertEqual(verd, "possible_mismatch")
        self.assertIn("Single name token match", exp)

    def test_03_compare_names_different(self):
        res, verd, sim, exp, sev = rule_engine.compare_names("Shivam Desai", "Amit Kumar Sharma")
        self.assertEqual(res, "Mismatch")
        self.assertEqual(verd, "mismatch")

    def test_04_compare_dob_year_only_matching(self):
        # Year-only vs Full date with same year
        res, verd, sim, exp, sev = rule_engine.compare_dob("2003", "2003-08-15")
        self.assertEqual(res, "Match")
        self.assertEqual(verd, "match")
        self.assertIn("full date not printed on one document", exp)

        # Full date vs Year-only with same year
        res2, _, _, exp2, _ = rule_engine.compare_dob("2003-08-15", "2003")
        self.assertEqual(res2, "Match")

        # Different years
        res3, verd3, _, _, _ = rule_engine.compare_dob("2003", "2005-08-15")
        self.assertEqual(res3, "Mismatch")
        self.assertEqual(verd3, "mismatch")

    def test_05_compare_address_pin_conflict(self):
        addr1 = "Flat 101, Shanti Nagar, Pune 411001"
        addr2 = "Flat 101, Shanti Nagar, Pune 411038"
        res, verd, sim, exp, sev = rule_engine.compare_address(addr1, addr2)
        self.assertEqual(res, "Mismatch")
        self.assertEqual(verd, "mismatch")
        self.assertIn("PIN codes differ", exp)

    def test_06_compare_address_subset_match(self):
        addr_short = "Shiv Plaza, FC Road, Pune 411005"
        addr_long = "Flat 402, 4th Floor, Shiv Plaza, FC Road, Pune 411005"
        res, verd, sim, exp, sev = rule_engine.compare_address(addr_short, addr_long)
        self.assertEqual(res, "Match")
        self.assertEqual(verd, "match")

    def test_07_verification_status(self):
        # Clean matching documents
        docs_clean = {
            "PAN Card": {"name": "Shivam Desai", "dob": "2003-08-15", "doc_number": "PAN: ABCPE1234F"},
            "Aadhaar Card": {"name": "Shivam Shashikant Desai", "dob": "2003-08-15", "doc_number": "Aadhaar: 2345 6789 0124"},
        }
        res_clean = rule_engine.check_mismatches(docs_clean)
        self.assertEqual(res_clean["verificationStatus"], "verified")
        self.assertTrue(res_clean["clean"])
        self.assertGreaterEqual(res_clean["verifiedFieldCount"], 2)

        # Mismatch documents
        docs_mismatch = {
            "PAN Card": {"name": "Shivam Desai", "dob": "2003-08-15"},
            "Aadhaar Card": {"name": "Rahul Kumar", "dob": "1995-01-01"},
        }
        res_mismatch = rule_engine.check_mismatches(docs_mismatch)
        self.assertEqual(res_mismatch["verificationStatus"], "issues_found")
        self.assertFalse(res_mismatch["clean"])

    def test_08_subject_aware_comparison(self):
        # Document for applicant vs document for deceased parent
        docs = {
            "Applicant Aadhaar": {"name": "Shivam Desai", "dob": "2003-08-15", "subject": "applicant"},
            "Parent Death Certificate": {"name": "Shashikant Desai", "dob": "1965-02-10", "subject": "parent"},
        }
        res = rule_engine.check_mismatches(docs)
        # Should not compare across different subjects
        self.assertEqual(len(res["comparisons"]), 0)


if __name__ == "__main__":
    unittest.main()

