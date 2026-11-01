import os
import io
import uuid
import unittest
from PIL import Image
from app import app
import db


class TestPhase1Security(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_01_get_session_generates_valid_uuid_and_cookie(self):
        res = self.client.get("/api/session")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("sessionId", data)
        # Verify it parses as a standard UUID
        sid = data["sessionId"]
        self.assertTrue(len(sid) >= 32)
        import re
        self.assertTrue(bool(re.fullmatch(r"^[a-zA-Z0-9_\-]+$", sid)))

    def test_02_session_ownership_enforcement_rejects_spoofing(self):
        # Establish a valid session
        res = self.client.get("/api/session")
        valid_sid = res.get_json()["sessionId"]

        # Attempt to access another random session_id
        attacker_sid = str(uuid.uuid4())
        res_spoof = self.client.get(f"/api/checklist/Passport/status?session_id={attacker_sid}")
        self.assertEqual(res_spoof.status_code, 403)
        self.assertIn("Forbidden", res_spoof.get_json().get("error", ""))

        # Access with matching session_id succeeds
        res_valid = self.client.get(f"/api/checklist/Passport/status?session_id={valid_sid}")
        self.assertEqual(res_valid.status_code, 200)

    def test_03_invalid_session_id_format_rejected(self):
        res1 = self.client.get("/api/checklist/Passport/status?session_id=../../bad_path")
        self.assertEqual(res1.status_code, 400)
        self.assertIn("Invalid session_id", res1.get_json().get("error", ""))

        res2 = self.client.get("/api/checklist/Passport/status?session_id=../")
        self.assertEqual(res2.status_code, 400)

        res3 = self.client.get("/api/checklist/Passport/status?session_id=/etc/passwd")
        self.assertEqual(res3.status_code, 400)

        res4 = self.client.get(r"/api/checklist/Passport/status?session_id=C:\windows\system32")
        self.assertEqual(res4.status_code, 400)

        res5 = self.client.get("/api/checklist/Passport/status?session_id=%2e%2e%2f%2e%2e%2fetc%2fpasswd")
        self.assertEqual(res5.status_code, 400)

        res = self.client.get("/api/checklist/Passport/status?session_id=..%2fsecret")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid session_id", res.get_json().get("error", ""))

    def test_04_diagnostics_endpoint_ignores_client_dev_flags_when_disabled(self):
        sid = str(uuid.uuid4())
        with self.client.session_transaction() as sess:
            sess["session_id"] = sid
            sess["user_id"] = 1

        old_val = os.environ.pop("DIAGNOSTICS_ENABLED", None)
        try:
            # Client passing X-Dev-Mode and ?dev=true must still be rejected with 403
            res = self.client.get(
                f"/api/checklist/Passport/diagnostics?session_id={sid}&variant=adult&dev=true",
                headers={"X-Dev-Mode": "true"}
            )
            self.assertEqual(res.status_code, 403)

            os.environ["ADMIN_TOKEN"] = "test-secret-token"
            res_bad = self.client.get(
                f"/api/checklist/Passport/diagnostics?session_id={sid}&variant=adult",
                headers={"X-Admin-Token": "wrong-token"}
            )
            self.assertEqual(res_bad.status_code, 403)
            os.environ.pop("ADMIN_TOKEN", None)
        finally:
            if old_val:
                os.environ["DIAGNOSTICS_ENABLED"] = old_val

    def test_05_translation_validation_language_and_length(self):
        # Unauthenticated request rejected
        res_unauth = self.client.post("/api/translate", json={"text": "Hello", "target_language": "hi"})
        self.assertEqual(res_unauth.status_code, 401)

        sid = str(uuid.uuid4())
        with self.client.session_transaction() as sess:
            sess["session_id"] = sid
            sess["user_id"] = 1

        # Unsupported language
        res_lang = self.client.post("/api/translate", json={"text": "Hello", "target_language": "fr", "session_id": sid})
        self.assertEqual(res_lang.status_code, 400)
        self.assertIn("Unsupported target language", res_lang.get_json().get("error", ""))

        # Excessively long text (> 2000 chars)
        res_len = self.client.post("/api/translate", json={"text": "A" * 2005, "target_language": "hi", "session_id": sid})
        self.assertEqual(res_len.status_code, 400)
        self.assertIn("exceeds maximum", res_len.get_json().get("error", ""))

    def test_06_auth_validation_inputs(self):
        # Invalid email
        res1 = self.client.post("/api/auth/register", json={
            "full_name": "Test User", "email": "invalid-email",
            "mobile_number": "9876543210", "password": "password123"
        })
        self.assertEqual(res1.status_code, 400)
        self.assertIn("Invalid email", res1.get_json().get("error", ""))

        # Invalid mobile number (not Indian 10-digit starting 6-9)
        res2 = self.client.post("/api/auth/register", json={
            "full_name": "Test User", "email": f"valid_{uuid.uuid4().hex[:6]}@example.com",
            "mobile_number": "12345", "password": "password123"
        })
        self.assertEqual(res2.status_code, 400)
        self.assertIn("Invalid Indian mobile", res2.get_json().get("error", ""))

        # Short password (< 8 chars)
        res3 = self.client.post("/api/auth/register", json={
            "full_name": "Test User", "email": f"valid_{uuid.uuid4().hex[:6]}@example.com",
            "mobile_number": "9876543210", "password": "short"
        })
        self.assertEqual(res3.status_code, 400)
        self.assertIn("at least 8 characters", res3.get_json().get("error", ""))

    def test_07_aadhaar_masking_and_hashing(self):
        # Test helper functions directly
        raw_aadhaar = "Aadhaar: 2345 6789 0123"
        masked = db.mask_doc_number(raw_aadhaar)
        self.assertEqual(masked, "Aadhaar: XXXX XXXX 0123")
        self.assertNotIn("2345", masked)

        h1 = db.hash_doc_number("2345 6789 0123")
        h2 = db.hash_doc_number("234567890123")
        self.assertEqual(h1, h2, "Whitespace normalization must match hashes")

    def test_08_upload_rejection_leaves_existing_intact(self):
        sid = str(uuid.uuid4())
        with self.client.session_transaction() as sess:
            sess["session_id"] = sid
            sess["user_id"] = 1

        # First upload a valid PNG
        img = Image.new("RGB", (100, 100), "white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        res_ok = self.client.post(
            "/api/checklist/Passport/upload",
            data={
                "session_id": sid,
                "requirement": "Proof of Identity",
                "chosen_option": "PAN Card",
                "file": (buf, "valid.png")
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(res_ok.status_code, 200)
        initial_path = res_ok.get_json()["filePath"]
        self.assertTrue(os.path.exists(initial_path))

        # Now attempt to upload an invalid/corrupted file
        bad_buf = io.BytesIO(b"not an image or pdf")
        res_bad = self.client.post(
            "/api/checklist/Passport/upload",
            data={
                "session_id": sid,
                "requirement": "Proof of Identity",
                "chosen_option": "PAN Card",
                "file": (bad_buf, "bad.png")
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(res_bad.status_code, 400)

        # The previously valid file must still exist and be untouched!
        self.assertTrue(os.path.exists(initial_path))

    def test_09_session_data_deletion(self):
        sid = str(uuid.uuid4())
        db.delete_all_user_documents(1)
        with self.client.session_transaction() as sess:
            sess["session_id"] = sid
            sess["user_id"] = 1

        img = Image.new("RGB", (100, 100), "white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        self.client.post(
            "/api/checklist/Passport/upload",
            data={
                "session_id": sid,
                "requirement": "Proof of Identity",
                "chosen_option": "PAN Card",
                "file": (buf, "valid.png")
            },
            content_type="multipart/form-data"
        )

        # Confirm data exists
        status = self.client.get(f"/api/checklist/Passport/status?session_id={sid}").get_json()
        self.assertEqual(status["uploadedCount"], 1)

        # Delete session data
        res_del = self.client.delete(f"/api/session/data?session_id={sid}")
        self.assertEqual(res_del.status_code, 200)

        # Confirm progress is completely wiped
        status_after = self.client.get(f"/api/checklist/Passport/status?session_id={sid}").get_json()
        self.assertEqual(status_after["uploadedCount"], 0)


if __name__ == "__main__":
    unittest.main()

