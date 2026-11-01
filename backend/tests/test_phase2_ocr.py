import unittest
import ocr_extract


class TestPhase2OCR(unittest.TestCase):
    def test_01_guess_dob_returns_year_only_for_yob(self):
        text = "GOVERNMENT OF INDIA\nName: Rahul Sharma\nYear of Birth: 1998\nAddress: Delhi"
        dob = ocr_extract.guess_dob(text)
        self.assertEqual(dob, "1998", "Year of birth must return 'YYYY' without inventing '-01-01'")

        text_yob = "YOB: 2002\nUID: 2345 6789 0124"
        dob_yob = ocr_extract.guess_dob(text_yob)
        self.assertEqual(dob_yob, "2002")

        # Full DOB must still return full YYYY-MM-DD
        text_full = "Date of Birth: 15/08/2003"
        self.assertEqual(ocr_extract.guess_dob(text_full), "2003-08-15")

    def test_02_clean_person_name_preserves_kumar(self):
        name1 = ocr_extract.clean_person_name("Kumar Sanu")
        self.assertEqual(name1, "Kumar Sanu")

        name2 = ocr_extract.clean_person_name("Rajesh Kumar")
        self.assertEqual(name2, "Rajesh Kumar")

        # Honorifics stripped
        name3 = ocr_extract.clean_person_name("Shri Rajesh Kumar")
        self.assertEqual(name3, "Rajesh Kumar")

        name4 = ocr_extract.clean_person_name("Dr. Rajesh Kumar")
        self.assertEqual(name4, "Rajesh Kumar")

    def test_03_verhoeff_algorithm(self):
        # 234567890124 is a mathematically valid Verhoeff number
        self.assertTrue(ocr_extract.validate_verhoeff("234567890124"))
        # Tampered digit fails checksum
        self.assertFalse(ocr_extract.validate_verhoeff("234567890125"))

    def test_04_aadhaar_validation(self):
        # Valid Verhoeff Aadhaar starting with 2
        text_valid = "Unique Identification Authority of India\n2345 6789 0124\nName: Shivam"
        doc_num = ocr_extract.guess_doc_number(text_valid)
        self.assertIsNotNone(doc_num)
        self.assertEqual(doc_num["type"], "Aadhaar")
        self.assertEqual(doc_num["number"], "2345 6789 0124")

        # Rejection of placeholder sequence 2020 2021 2022
        text_dummy = "Unique Identification Authority of India\n2020 2021 2022\nName: Fake"
        self.assertIsNone(ocr_extract.guess_doc_number(text_dummy))

    def test_05_pan_validation_4th_char(self):
        # Individual 'P'
        pan_p = ocr_extract.guess_doc_number("INCOME TAX DEPARTMENT\nPAN: ABCPE1234F\nName: Test")
        self.assertIsNotNone(pan_p)
        self.assertEqual(pan_p["type"], "PAN")
        self.assertEqual(pan_p["number"], "ABCPE1234F")

        # Company 'C'
        pan_c = ocr_extract.guess_doc_number("INCOME TAX DEPARTMENT\nPAN: ABCCE1234F\nName: Company")
        self.assertIsNotNone(pan_c)
        self.assertEqual(pan_c["type"], "PAN")

        # Invalid 4th letter (e.g. 'X' is not in PAN holder types)
        pan_invalid = ocr_extract.guess_doc_number("INCOME TAX DEPARTMENT\nPAN: ABCXE1234F\nName: Invalid")
        self.assertIsNone(pan_invalid)

    def test_06_issuer_and_state_detection(self):
        text_msbshse = "Maharashtra State Board of Secondary and Higher Secondary Education, Pune"
        self.assertEqual(ocr_extract.detect_issuer(text_msbshse), "maharashtra_board")
        self.assertEqual(ocr_extract.detect_state(text_msbshse), "Maharashtra")

        text_cbse = "Central Board of Secondary Education, Delhi"
        self.assertEqual(ocr_extract.detect_issuer(text_cbse), "cbse")
        self.assertEqual(ocr_extract.detect_state(text_cbse), "Delhi")

        text_icse = "Council for the Indian School Certificate Examinations, New Delhi"
        self.assertEqual(ocr_extract.detect_issuer(text_icse), "icse")

    def test_07_parent_name_extraction(self):
        text = "Name: Shivam Shashikant Desai\nFather's Name: Shashikant Desai\nMother's Name: Seema Desai\nDOB: 15/08/2003"
        f_name = ocr_extract.guess_parent_name(text, "father")
        m_name = ocr_extract.guess_parent_name(text, "mother")
        self.assertEqual(f_name, "Shashikant Desai")
        self.assertEqual(m_name, "Seema Desai")

    def test_08_get_ocr_language(self):
        lang = ocr_extract.get_ocr_language()
        self.assertIsInstance(lang, str)
        self.assertTrue("eng" in lang)


if __name__ == "__main__":
    unittest.main()

