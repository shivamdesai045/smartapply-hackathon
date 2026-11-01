"""
Unit tests for Phase 3: Evaluation Harness and Synthetic Dataset Generator.
"""

import os
import re
import json
import unittest

from ml.synth import generate_synth
from ml.eval import run_eval

class TestPhase3EvalHarness(unittest.TestCase):

    def test_01_synthetic_id_invalidity_compliance(self):
        """Hard rule: Synthetic ID numbers must be provably invalid."""
        # 1. Aadhaar numbers must fail Verhoeff algorithm
        for _ in range(20):
            aadhaar = generate_synth.make_invalid_aadhaar(generate_synth.random.Random())
            clean = re.sub(r"\D", "", aadhaar)
            self.assertEqual(len(clean), 12)
            self.assertTrue(generate_synth.fails_verhoeff(clean), f"Aadhaar {aadhaar} passed Verhoeff!")

        # 2. PAN numbers must have an invalid 4th letter ('Z')
        for _ in range(20):
            pan = generate_synth.make_invalid_pan(generate_synth.random.Random(), "Aarav Sharma")
            self.assertEqual(len(pan), 10)
            self.assertEqual(pan[3], "Z", f"PAN {pan} has valid entity letter!")

    def test_02_pii_masking_integrity(self):
        """Hard rule: Never log or store raw identity data."""
        # Name masking
        m_name = run_eval.mask_name("Rajesh Kumar Sharma")
        self.assertEqual(m_name, "R***** K**** S*****")
        self.assertNotIn("Rajesh", m_name)

        # DOB masking
        m_dob = run_eval.mask_dob("1995-04-12")
        self.assertEqual(m_dob, "****-**-12")
        self.assertNotIn("1995", m_dob)

        # Aadhaar masking
        m_aadh = run_eval.mask_doc_number("2345 6789 0124")
        self.assertEqual(m_aadh, "XXXX XXXX 0124")
        self.assertNotIn("2345", m_aadh)

        # PAN masking
        m_pan = run_eval.mask_doc_number("ABCPE1234F")
        self.assertEqual(m_pan, "ABC*****4F")
        self.assertNotIn("123", m_pan)

        # Address masking
        m_addr = run_eval.mask_address("Flat 101, MG Road, Pune 411001")
        self.assertIn("PIN: 411***", m_addr)
        self.assertNotIn("Flat 101", m_addr)

    def test_03_evaluator_fuzzy_matching(self):
        # Name matching
        ok1, s1 = run_eval.evaluate_name("Shivam Desai", "Shivam Desai")
        self.assertTrue(ok1)

        # Reordered tokens
        ok2, s2 = run_eval.evaluate_name("Desai Shivam", "Shivam Desai")
        self.assertTrue(ok2)

        # Middle name omission
        ok3, s3 = run_eval.evaluate_name("Shivam Shashikant Desai", "Shivam Desai")
        self.assertTrue(ok3)

        # Mismatch
        ok4, s4 = run_eval.evaluate_name("Shivam Desai", "Rajesh Sharma")
        self.assertFalse(ok4)

        # DOB normalization
        ok_dob1, _ = run_eval.evaluate_dob("1995-04-12", "12/04/1995")
        self.assertTrue(ok_dob1)

        ok_dob2, _ = run_eval.evaluate_dob("1995", "1995-04-12")
        self.assertTrue(ok_dob2)

        # Address matching
        addr_a = "Flat 101, Lake View, FC Road, Pune 411005"
        addr_b = "Lake View, FC Road, Pune 411005"
        ok_addr, _ = run_eval.evaluate_address(addr_a, addr_b)
        self.assertTrue(ok_addr)

    def test_04_run_eval_execution_and_report_output(self):
        """Verify run_eval completes and generates valid report dictionary and JSON."""
        report = run_eval.run_evaluation(synth_fallback=True)
        self.assertIn("total_documents", report)
        self.assertGreaterEqual(report["total_documents"], 60)
        self.assertIn("overall_accuracy_pct", report)
        self.assertIn("by_document_type", report)
        self.assertIn("Aadhaar Card", report["by_document_type"])
        self.assertIn("PAN Card", report["by_document_type"])
        self.assertIn("worst_failures_sample", report)


if __name__ == "__main__":
    unittest.main()

