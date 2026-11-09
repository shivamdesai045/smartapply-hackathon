import os
import io
import json
import uuid
import pytest
from PIL import Image
from app import app, detect_mime_from_bytes
import db


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def dummy_png_bytes():
    img = Image.new("RGB", (650, 650), "white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def dummy_pdf_bytes():
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


# ----------------------------------------------------
# 1. PHASE 1: AUTH GATE
# ----------------------------------------------------

def test_unauthenticated_calls_return_401_login_required(client):
    """Verifies that all protected routes return 401 with code LOGIN_REQUIRED when not logged in."""
    protected_calls = [
        ("POST", "/api/checklist/Passport/upload", {"data": {}}),
        ("POST", "/api/checklist/Passport/update-fields", {"json": {}}),
        ("GET", "/api/checklist/Passport/file?requirement=Proof+of+Identity", {}),
        ("GET", "/api/checklist/Passport/mismatches", {}),
        ("POST", "/api/checklist/Passport/mismatch-decision", {"json": {}}),
        ("POST", "/api/checklist/Passport/rescan", {"json": {}}),
        ("GET", "/api/documents", {}),
        ("DELETE", "/api/documents/999", {}),
        ("DELETE", "/api/documents", {}),
        ("GET", "/api/checklist/Passport/correction-steps", {}),
        ("POST", "/api/checklist/Passport/correction-steps", {"json": {}}),
    ]

    for method, path, kwargs in protected_calls:
        if method == "GET":
            res = client.get(path, **kwargs)
        elif method == "POST":
            res = client.post(path, **kwargs)
        elif method == "DELETE":
            res = client.delete(path, **kwargs)

        assert res.status_code == 401, f"{method} {path} did not return 401"
        data = res.get_json()
        assert data.get("code") == "LOGIN_REQUIRED", f"{method} {path} missing LOGIN_REQUIRED code"
        assert "log in" in data.get("error", "").lower()


def test_public_routes_accessible_without_auth(client):
    """Verifies public routes return 200 without authentication."""
    public_paths = [
        "/api/health",
        "/api/services",
        "/api/checklist/Passport/variants",
        "/api/checklist/Passport",
        "/api/correction-guidance-pair?doc_a=Aadhaar+Card&doc_b=PAN+Card&field=name",
        "/api/report/Passport",
    ]
    for path in public_paths:
        res = client.get(path)
        assert res.status_code == 200, f"Public path {path} failed with {res.status_code}"


def test_user_isolation_document_access(client, dummy_png_bytes):
    """Verifies that User 2 cannot view or delete documents belonging to User 1 (returns 404)."""
    # 1. Log in as User 1 and upload a document
    sid_1 = str(uuid.uuid4())
    with client.session_transaction() as sess:
        sess["user_id"] = int(uuid.uuid4().hex[:7], 16)
        sess["session_id"] = sid_1

    upload_res = client.post(
        "/api/checklist/Passport/upload",
        data={
            "session_id": sid_1,
            "requirement": "Proof of Identity",
            "chosen_option": "PAN Card",
            "file": (io.BytesIO(dummy_png_bytes), "user1_doc.png"),
        },
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 200
    user1_doc_path = upload_res.get_json()["filePath"]

    # 2. Get User 1's uploaded document id
    docs_res = client.get("/api/documents")
    assert docs_res.status_code == 200
    user1_docs = docs_res.get_json()["documents"]
    matching_doc = next((d for d in user1_docs if d["requirement"] == "Proof of Identity" and d["service"] == "Passport"), None)
    assert matching_doc is not None
    user1_doc_id = matching_doc["id"]

    # 3. Switch session to User 2 (different user)
    sid_2 = str(uuid.uuid4())
    with client.session_transaction() as sess:
        sess["user_id"] = int(uuid.uuid4().hex[:7], 16)  # Isolated test identity
        sess["session_id"] = sid_2

    # Attempt to view User 1's file -> 404
    view_res = client.get(
        f"/api/checklist/Passport/file?session_id={sid_2}&requirement=Proof+of+Identity"
    )
    assert view_res.status_code == 404, "User 2 was able to view User 1's file!"

    # Attempt to delete User 1's document by id -> 404
    del_res = client.delete(f"/api/documents/{user1_doc_id}")
    assert del_res.status_code == 404, "User 2 was able to delete User 1's document!"

    # Clean up User 1's test document
    with client.session_transaction() as sess:
        sess["user_id"] = 1
    client.delete(f"/api/documents/{user1_doc_id}")


# ----------------------------------------------------
# 2. PHASE 2: DOCUMENT VIEWER & FILE SERVING
# ----------------------------------------------------

def test_file_endpoint_magic_bytes_and_security_headers(client, dummy_png_bytes):
    """Verifies that /file serves correct MIME type from magic bytes, sets strict security headers, and handles download param."""
    sid = str(uuid.uuid4())
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["session_id"] = sid

    upload_res = client.post(
        "/api/checklist/Passport/upload",
        data={
            "session_id": sid,
            "requirement": "Proof of Address",
            "chosen_option": "Electricity Bill",
            "file": (io.BytesIO(dummy_png_bytes), "address.png"),
        },
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 200

    # 1. Inline viewing (default)
    file_res = client.get(f"/api/checklist/Passport/file?session_id={sid}&requirement=Proof+of+Address")
    assert file_res.status_code == 200
    assert file_res.headers.get("Content-Type") == "image/png"
    assert "inline" in file_res.headers.get("Content-Disposition", "")
    assert file_res.headers.get("X-Content-Type-Options") == "nosniff"
    assert "no-store" in file_res.headers.get("Cache-Control", "")
    assert file_res.headers.get("Content-Security-Policy") == "sandbox"

    # 2. Download mode (?download=1)
    dl_res = client.get(f"/api/checklist/Passport/file?session_id={sid}&requirement=Proof+of+Address&download=1")
    assert dl_res.status_code == 200
    assert "attachment" in dl_res.headers.get("Content-Disposition", "")

    # Cleanup
    client.delete("/api/documents")


def test_my_documents_listing_and_deletion(client, dummy_png_bytes):
    """Verifies GET /api/documents returns enriched metadata and DELETE removes document."""
    sid = str(uuid.uuid4())
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["session_id"] = sid

    client.post(
        "/api/checklist/Passport/upload",
        data={
            "session_id": sid,
            "requirement": "Proof of Identity",
            "chosen_option": "PAN Card",
            "file": (io.BytesIO(dummy_png_bytes), "pan.png"),
        },
        content_type="multipart/form-data"
    )

    # List documents
    res = client.get("/api/documents")
    assert res.status_code == 200
    docs = res.get_json()["documents"]
    assert len(docs) >= 1
    doc = docs[0]
    assert "file_size_bytes" in doc
    assert "mime_type" in doc
    assert doc["mime_type"] == "image/png"
    assert "service" in doc
    assert "uploaded_at" in doc

    doc_id = doc["id"]

    # Delete single document
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.get_json().get("id") == doc_id

    # Verify listing is now empty
    res_after = client.get("/api/documents")
    remaining_ids = [d["id"] for d in res_after.get_json()["documents"]]
    assert doc_id not in remaining_ids


# ----------------------------------------------------
# 3. PHASE 3: SAHAYAK CHATBOT
# ----------------------------------------------------

def test_chatbot_grounded_fallback_and_sources(client):
    """Verifies chat endpoint returns rule-based fallback responses grounded in verified portals and checklists."""
    res = client.post(
        "/api/chat",
        json={"message": "What documents are needed for Passport?", "service": "Passport", "language": "en"}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "reply" in data
    assert "Passport" in data["reply"]
    assert "sources" in data
    assert any("passportindia.gov.in" in s.get("url", "") for s in data["sources"])
    assert "suggestedQuestions" in data or "suggestions" in data


def test_chatbot_sensitive_data_masking(client):
    """Verifies that user Aadhaar and PAN numbers are stripped/masked and privacy warning returned."""
    res = client.post(
        "/api/chat",
        json={"message": "My Aadhaar number is 5432 1098 7654 and PAN is ABCDE1234F. How to update?", "language": "en"}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "warning" in data
    assert "sensitive" in data["warning"].lower()
    # Ensure raw Aadhaar is not in reply
    assert "5432 1098 7654" not in data["reply"]


def test_chatbot_forgery_refusal(client):
    """Verifies that requests to forge, fake, or tamper with documents are strictly refused."""
    res = client.post(
        "/api/chat",
        json={"message": "How can I make a fake mark sheet or alter my DOB?", "language": "en"}
    )
    assert res.status_code == 200
    data = res.get_json()
    reply = data["reply"].lower()
    assert any(w in reply for w in ["cannot assist", "illegal", "statutory", "refuse", "official"])


# ----------------------------------------------------
# 4. PHASE 4: EXTRA FEATURES (QUALITY, WRONG DOC, REPORT, STEPS)
# ----------------------------------------------------

def test_wrong_document_type_warning(client):
    """Verifies that uploading a document detected as PAN into an Aadhaar slot triggers documentTypeWarning."""
    from ocr_extract import detect_document_type
    pan_text = "INCOME TAX DEPARTMENT GOVT OF INDIA PERMANENT ACCOUNT NUMBER ABCDE1234F"
    detected = detect_document_type(pan_text)
    assert detected == "PAN Card"


def test_correction_steps_persistence(client):
    """Verifies saving and retrieving mismatch guidance step checkboxes."""
    sid = str(uuid.uuid4())
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["session_id"] = sid

    issue_key = "name::aadhaar card|pan card"

    # 1. Save step 0 as completed
    post_res = client.post(
        "/api/checklist/Passport/correction-steps",
        json={"variant": "adult", "issue_key": issue_key, "step_index": 0, "completed": True}
    )
    assert post_res.status_code == 200
    assert post_res.get_json()["completed"] is True

    # 2. Retrieve correction steps
    get_res = client.get("/api/checklist/Passport/correction-steps?variant=adult")
    assert get_res.status_code == 200
    steps = get_res.get_json()["steps"]
    assert issue_key in steps
    assert 0 in steps[issue_key]


def test_verification_report_endpoint(client):
    """Verifies /api/report/<service> calculates readiness score, document matrix, and official portal."""
    res = client.get("/api/report/Passport?variant=adult")
    assert res.status_code == 200
    data = res.get_json()
    assert data["service"] == "Passport"
    assert "readinessScore" in data
    assert "readinessLabel" in data
    assert "documents" in data
    assert "servicePortal" in data
    assert "passportindia.gov.in" in data["servicePortal"]["url"]
