import unittest
import uuid
import os
from services_data import OFFICIAL_PORTALS, get_service_portal, categories
from checklist_data import CHECKLISTS, find_service_key, get_variants, get_checklist
from correction_guide import get_guidance, normalize_doc_key
from app import app
import db


class TestServicePortalAndGuidance(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_01_all_services_have_official_portals(self):
        """Verify every single service in categories has official portal metadata with a valid URL."""
        all_service_names = []
        for cat in categories:
            for s in cat["services"]:
                all_service_names.append(s["name"])

        for name in all_service_names:
            portal = get_service_portal(name)
            self.assertIsNotNone(portal, f"Service portal missing for: {name}")
            self.assertTrue(portal["url"].startswith("https://"), f"Invalid portal URL for {name}: {portal.get('url')}")
            self.assertTrue(len(portal["authority"]) > 0, f"Missing authority for {name}")

    def test_02_slug_and_case_insensitive_service_resolution(self):
        """Verify services resolve properly regardless of uppercase, lowercase, or URL slug formatting."""
        test_cases = [
            ("passport", "Passport"),
            ("Passport", "Passport"),
            ("pan-card", "PAN Card"),
            ("PAN Card", "PAN Card"),
            ("driving-licence", "Driving Licence"),
            ("aadhaar-card", "Aadhaar Card"),
            ("pm-kisan", "PM-KISAN"),
            ("upsc", "UPSC"),
            ("neet", "NEET"),
        ]
        for query, expected in test_cases:
            resolved = find_service_key(query)
            self.assertEqual(resolved, expected, f"Failed to resolve {query} to {expected}")

            variants = get_variants(query)
            self.assertIsNotNone(variants, f"get_variants returned None for {query}")

            reqs = get_checklist(query, "adult")
            self.assertIsNotNone(reqs, f"get_checklist returned None for {query}")
            self.assertTrue(len(reqs) > 0, f"Empty requirements for {query}")

    def test_03_correction_guide_urls_and_doc_types(self):
        """Verify correction guidance contains direct URLs for all documents including marksheets and certificates."""
        # 1. Aadhaar
        g_aadhaar_addr = get_guidance("Aadhaar Card", "address")
        self.assertEqual(g_aadhaar_addr["document"], "aadhaar")
        self.assertEqual(g_aadhaar_addr["portal_url"], "https://myaadhaar.uidai.gov.in/")

        g_aadhaar_name = get_guidance("Parent's Aadhaar Card", "name")
        self.assertEqual(g_aadhaar_name["document"], "aadhaar")
        self.assertEqual(g_aadhaar_name["portal_url"], "https://appointments.uidai.gov.in/")

        # 2. PAN Card
        g_pan = get_guidance("PAN Card", "name")
        self.assertEqual(g_pan["document"], "pan")
        self.assertTrue("onlineservices.nsdl.com" in g_pan["portal_url"])

        # 3. 10th Marksheet
        g_marksheet = get_guidance("10th Marksheet", "name")
        self.assertEqual(g_marksheet["document"], "10th_marksheet")
        self.assertTrue("cbse.gov.in" in g_marksheet["portal_url"])

        # 4. Birth Certificate
        g_birth = get_guidance("Birth Certificate", "dob")
        self.assertEqual(g_birth["document"], "birth_certificate")
        self.assertEqual(g_birth["portal_url"], "https://crsorgi.gov.in/")

        # 5. Passport
        g_passport = get_guidance("Passport", "name")
        self.assertEqual(g_passport["document"], "passport")
        self.assertEqual(g_passport["portal_url"], "https://www.passportindia.gov.in/")

        # 6. Driving Licence
        g_dl = get_guidance("Driving Licence", "address")
        self.assertEqual(g_dl["document"], "driving_licence")
        self.assertEqual(g_dl["portal_url"], "https://sarathi.parivahan.gov.in/")

    def test_04_status_endpoint_returns_service_portal(self):
        """Verify /api/checklist/<service>/status returns servicePortal with official link."""
        session_id = f"test_portal_sess_{uuid.uuid4().hex[:8]}"
        res = self.app.get(f"/api/checklist/Passport/status?session_id={session_id}&variant=adult")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("servicePortal", data)
        self.assertIsNotNone(data["servicePortal"])
        self.assertEqual(data["servicePortal"]["url"], "https://www.passportindia.gov.in/")
        self.assertEqual(data["servicePortal"]["name"], "Passport Seva Portal")

    def test_05_diagnostics_endpoint_security_and_format(self):
        """Verify development diagnostics view is protected unless DIAGNOSTICS_ENABLED is true."""
        session_id = str(uuid.uuid4())
        with self.app.session_transaction() as sess:
            sess["session_id"] = session_id

        # Without DIAGNOSTICS_ENABLED set, it is forbidden even with ?dev=true or headers
        os.environ.pop("DIAGNOSTICS_ENABLED", None)
        res_blocked = self.app.get(f"/api/checklist/Passport/diagnostics?session_id={session_id}&variant=adult&dev=true",
                                   headers={"X-Dev-Mode": "true"})
        self.assertEqual(res_blocked.status_code, 403)

        # With DIAGNOSTICS_ENABLED="true" in development
        try:
            os.environ["DIAGNOSTICS_ENABLED"] = "true"
            res = self.app.get(
                f"/api/checklist/Passport/diagnostics?session_id={session_id}&variant=adult",
            )
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data["service"], "Passport")
            self.assertIn("documents", data)
        finally:
            os.environ.pop("DIAGNOSTICS_ENABLED", None)


if __name__ == "__main__":
    unittest.main()
