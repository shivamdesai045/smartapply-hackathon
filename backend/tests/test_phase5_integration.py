import json
import pytest
import uuid
from app import app
import db


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_session_lifecycle(client):
    """Verifies session initialization and session data wipe."""
    res = client.get("/api/session")
    assert res.status_code == 200
    data = res.get_json()
    assert "sessionId" in data
    sid = data["sessionId"]
    assert len(sid) == 36

    # Data wipe
    with client.session_transaction() as sess:
        sess["user_id"] = 1
    del_res = client.delete("/api/session/data", json={"session_id": sid})
    assert del_res.status_code == 200
    assert "wiped successfully" in del_res.get_json().get("message", "").lower()


def test_checklist_status_metadata(client):
    """Verifies that checklist status includes subject, compare, skippable, and comparableCount."""
    sid = str(uuid.uuid4())
    with client.session_transaction() as sess:
        sess["session_id"] = sid

    res = client.get(f"/api/checklist/Passport/status?session_id={sid}&variant=adult")
    assert res.status_code == 200
    data = res.get_json()
    assert "comparableCount" in data
    assert isinstance(data["comparableCount"], int)
    assert "requirements" in data
    reqs = data["requirements"]
    assert len(reqs) > 0

    first_req = reqs[0]
    assert "subject" in first_req
    assert "compare" in first_req
    assert "skippable" in first_req
    assert "skipped" in first_req


def test_skippable_requirement_flow(client):
    """Verifies skipping and un-skipping a skippable requirement."""
    sid = str(uuid.uuid4())
    with client.session_transaction() as sess:
        sess["session_id"] = sid

    # Post-Matric Scholarship has skippable Category Certificate
    service = "Scholarship Schemes"
    req_name = "Category Certificate"

    # 1. Initially not skipped
    status_res = client.get(f"/api/checklist/{service}/status?session_id={sid}&variant=adult")
    assert status_res.status_code == 200
    req_item = next((r for r in status_res.get_json()["requirements"] if r["requirement"] == req_name), None)
    if req_item:
        assert req_item["skippable"] is True
        assert req_item["skipped"] is False

    # 2. Skip requirement
    skip_res = client.post(
        f"/api/checklist/{service}/skip",
        json={"session_id": sid, "variant": "adult", "requirement": req_name, "skipped": True},
    )
    assert skip_res.status_code == 200
    skip_data = skip_res.get_json()
    assert skip_data.get("skipped") is True

    # 3. Status reflects skipped
    status_after = client.get(f"/api/checklist/{service}/status?session_id={sid}&variant=adult")
    assert status_after.status_code == 200
    req_item_after = next((r for r in status_after.get_json()["requirements"] if r["requirement"] == req_name), None)
    if req_item_after:
        assert req_item_after["skipped"] is True
        assert req_item_after["uploaded"] is True

    # 4. Skipped item is NOT counted in comparable documents
    docs_data = db.get_documents_with_data(sid, service, "adult")
    assert req_name not in docs_data

    # 5. Restore (un-skip)
    unskip_res = client.post(
        f"/api/checklist/{service}/skip",
        json={"session_id": sid, "variant": "adult", "requirement": req_name, "skipped": False},
    )
    assert unskip_res.status_code == 200

    status_restored = client.get(f"/api/checklist/{service}/status?session_id={sid}&variant=adult")
    req_item_restored = next((r for r in status_restored.get_json()["requirements"] if r["requirement"] == req_name), None)
    if req_item_restored:
        assert req_item_restored["skipped"] is False
        assert req_item_restored["uploaded"] is False

