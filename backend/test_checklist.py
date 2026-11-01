import requests
import json

BASE = "http://127.0.0.1:5000"
SESSION_ID = "test-session-002"
SERVICE = "Aadhaar Card"

print("=== 1. Get available variants for", SERVICE, "===")
r = requests.get(f"{BASE}/api/checklist/{SERVICE}/variants")
print(json.dumps(r.json(), indent=2))
print()

print("=== 2. Get checklist for 'adult' variant ===")
r = requests.get(f"{BASE}/api/checklist/{SERVICE}", params={"variant": "adult"})
print(json.dumps(r.json(), indent=2))
print()

print("=== 3. Get checklist for 'child_under_5' variant (should be much shorter) ===")
r = requests.get(f"{BASE}/api/checklist/{SERVICE}", params={"variant": "child_under_5"})
print(json.dumps(r.json(), indent=2))
print()

print("=== 4. Get status before any uploads (adult variant) ===")
r = requests.get(
    f"{BASE}/api/checklist/{SERVICE}/status",
    params={"session_id": SESSION_ID, "variant": "adult"},
)
print(json.dumps(r.json(), indent=2))
print()

print("=== 5. Upload a file for 'Proof of Identity', choosing 'PAN Card' as the option ===")
with open("dummy_upload.txt", "w") as f:
    f.write("This is a fake test document.")

with open("dummy_upload.txt", "rb") as f:
    files = {"file": ("dummy_upload.txt", f)}
    data = {
        "session_id": SESSION_ID,
        "variant": "adult",
        "requirement": "Proof of Identity",
        "chosen_option": "PAN Card",
    }
    r = requests.post(f"{BASE}/api/checklist/{SERVICE}/upload", data=data, files=files)

print(json.dumps(r.json(), indent=2))
print()

print("=== 6. Get status again - should show 1 item uploaded with chosenOption 'PAN Card' ===")
r = requests.get(
    f"{BASE}/api/checklist/{SERVICE}/status",
    params={"session_id": SESSION_ID, "variant": "adult"},
)
print(json.dumps(r.json(), indent=2))
