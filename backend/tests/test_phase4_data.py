import unittest
from services_data import OFFICIAL_PORTALS
from checklist_data import get_checklist
from correction_guide import get_guidance, normalize_doc_key, CORRECTION_GUIDE
from check_links import verify_all_links


class TestPhase4Data(unittest.TestCase):
    def test_01_all_links_verified_official(self):
        results = verify_all_links()
        self.assertEqual(results["invalid"], 0, f"Found invalid domains: {results['errors']}")
        self.assertGreater(results["valid"], 50)

    def test_02_passport_dob_options_exclude_domicile(self):
        reqs = get_checklist("Passport", "adult")
        dob_req = next(r for r in reqs if r["name"] == "Proof of Date of Birth")
        self.assertNotIn("Domicile Certificate", dob_req["options"], "Domicile Certificate must not be in Passport DOB options")
        self.assertIn("Birth Certificate", dob_req["options"])
        self.assertIn("notes", dob_req)
        self.assertIn("1 October 2023", dob_req["notes"])

    def test_03_normalize_doc_key_whole_word_matching(self):
        # Clean exact tokens
        self.assertEqual(normalize_doc_key("Aadhaar Card"), "aadhaar")
        self.assertEqual(normalize_doc_key("PAN Card"), "pan")
        self.assertEqual(normalize_doc_key("Electricity Bill"), "electricity_bill")
        self.assertEqual(normalize_doc_key("Rent Agreement"), "rent_agreement")
        self.assertEqual(normalize_doc_key("Bank Passbook"), "bank_passbook")

        # Must not falsely match substring in unrelated word
        self.assertIsNone(normalize_doc_key("Companion Form"))

    def test_04_marksheet_routing_by_issuer(self):
        # Maharashtra Board
        g_mah = get_guidance("10th Marksheet", "name", doc_meta={"issuer": "maharashtra_board"})
        self.assertEqual(g_mah["portal_url"], "https://boardmarksheet.maharashtra.gov.in/")
        self.assertIn("Maharashtra", g_mah["portal"])

        # CBSE
        g_cbse = get_guidance("10th Marksheet", "name", doc_meta={"issuer": "cbse"})
        self.assertEqual(g_cbse["portal_url"], "https://cbseit.in/cbse/web/dads/")
        self.assertIn("CBSE", g_cbse["portal"])

    def test_05_domicile_routing_by_state(self):
        # Maharashtra
        g_mah = get_guidance("Domicile Certificate", "address", doc_meta={"state": "Maharashtra"})
        self.assertEqual(g_mah["portal_url"], "https://aaplesarkar.mahaonline.gov.in/")

        # Delhi
        g_delhi = get_guidance("Domicile Certificate", "address", doc_meta={"state": "Delhi"})
        self.assertEqual(g_delhi["portal_url"], "https://edistrict.delhigovt.nic.in/")

    def test_06_unverified_items_flagged(self):
        g_elec = get_guidance("Electricity Bill", "name")
        self.assertTrue(g_elec.get("needs_verification"))
        self.assertIsNone(g_elec.get("fee"))

        g_rent = get_guidance("Rent Agreement", "name")
        self.assertTrue(g_rent.get("needs_verification"))
        self.assertIsNone(g_rent.get("fee"))

    def test_07_aadhaar_verified_fee_and_channel(self):
        g_name = get_guidance("Aadhaar Card", "name")
        self.assertEqual(g_name["channel"], "in_person")
        self.assertIn("50", g_name["fee"])

        g_addr = get_guidance("Aadhaar Card", "address")
        self.assertEqual(g_addr["channel"], "online")
        self.assertIn("50", g_addr["fee"])


if __name__ == "__main__":
    unittest.main()

