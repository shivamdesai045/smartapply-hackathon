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


    def test_09_kumar_preservation_and_explicit_honorific(self):
        # Kumar is preserved as an active token in general names
        toks = rule_engine.normalize_name_tokens("Rajesh Kumar")
        self.assertIn("kumar", toks)
        self.assertIn("rajesh", toks)

        toks_lead = rule_engine.normalize_name_tokens("Kumar Sanu")
        self.assertIn("kumar", toks_lead)

        # Kumar is stripped ONLY in explicit certificate phrases
        toks_cert = rule_engine.normalize_name_tokens("certified that, Kumar Rajesh")
        self.assertNotIn("kumar", toks_cert)
        self.assertIn("rajesh", toks_cert)

    def test_10_middle_name_initial_soft_match(self):
        # Middle initial vs full name is a soft match, NOT a mismatch
        res1, verd1, _, exp1, _ = rule_engine.compare_names("Shivam S Desai", "Shivam Satish Desai")
        self.assertEqual(res1, "Match")
        self.assertEqual(verd1, "match")
        self.assertIn("soft match", exp1)

        # Middle initial with period
        res2, verd2, _, _, _ = rule_engine.compare_names("Shivam S. Desai", "Shivam Satish Desai")
        self.assertEqual(res2, "Match")
        self.assertEqual(verd2, "match")

        # Initial absent on one document
        res3, verd3, _, _, _ = rule_engine.compare_names("Shivam S. Desai", "Shivam Desai")
        self.assertEqual(res3, "Match")
        self.assertEqual(verd3, "match")

    def test_11_address_one_word_never_matches(self):
        # One-word addresses never match anything (even identical words)
        res1, verd1, _, exp1, _ = rule_engine.compare_address("Pune", "Pune")
        self.assertEqual(res1, "Unable to Compare")
        self.assertEqual(verd1, "unable_to_verify")
        self.assertIn("One-word address has insufficient detail", exp1)

        res2, verd2, _, exp2, _ = rule_engine.compare_address("Pune", "Flat 402, Shiv Plaza, FC Road, Pune 411005")
        self.assertEqual(res2, "Unable to Compare")
        self.assertEqual(verd2, "unable_to_verify")

    def test_12_address_matching_tokens_and_pin_agreement(self):
        # Minimum matching tokens plus PIN/locality agreement produces match
        addr_a = "Flat 101, Shanti Nagar, FC Road, Pune 411005"
        addr_b = "Shanti Nagar, FC Road, Pune 411005"
        res, verd, _, _, _ = rule_engine.compare_address(addr_a, addr_b)
        self.assertEqual(res, "Match")
        self.assertEqual(verd, "match")

        # Insufficient matching tokens (< 2) produces mismatch
        addr_c = "12 North Block, Sector 4, Chandigarh 160001"
        res_diff, verd_diff, _, _, _ = rule_engine.compare_address(addr_a, addr_c)
        self.assertEqual(res_diff, "Mismatch")
        self.assertEqual(verd_diff, "mismatch")

    def test_13_document_holder_role_exclusion(self):
        # Documents of another person (parent/guardian) get a holder role and are excluded from applicant comparisons
        docs = {
            "Applicant Aadhaar": {"name": "Shivam Desai", "dob": "2003-08-15", "holder": "applicant"},
            "Father's Passport": {"name": "Satish Desai", "dob": "1972-04-10"},
        }
        res = rule_engine.check_mismatches(docs)
        # Father's Passport inferred as holder role and excluded from applicant comparisons
        self.assertEqual(len(res["comparisons"]), 0)

    def test_14_verification_status_all_clear_only_when_every_required_field_verified(self):
        # Case 1: All required fields (Name AND DOB) verified -> "verified" (All clear)
        docs_complete = {
            "PAN Card": {"name": "Shivam Desai", "dob": "2003-08-15"},
            "Aadhaar Card": {"name": "Shivam Satish Desai", "dob": "2003-08-15"},
        }
        res_comp = rule_engine.check_mismatches(docs_complete)
        self.assertEqual(res_comp["verificationStatus"], "verified")

        # Case 2: Name verified but DOB unreadable/missing -> "not_verified" / "partially_verified", NEVER "verified"
        docs_missing_dob = {
            "PAN Card": {"name": "Shivam Desai"},
            "Aadhaar Card": {"name": "Shivam Satish Desai"},
        }
        res_missing = rule_engine.check_mismatches(docs_missing_dob)
        self.assertNotEqual(res_missing["verificationStatus"], "verified")
        self.assertIn(res_missing["verificationStatus"], ("partially_verified", "not_verified"))


if __name__ == "__main__":
    unittest.main()

