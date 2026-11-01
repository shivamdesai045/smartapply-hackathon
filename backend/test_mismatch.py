import requests
import json

url = "http://127.0.0.1:5000/api/check-mismatches"

payload = {
    "documents": {
        "aadhaar": {
            "name": "Pranav Ghatol",
            "dob": "2005-07-15",
            "address": "123 MG Road, Pune, Maharashtra",
        },
        "pan": {
            "name": "Pranav R Ghatol",
            "dob": "2005-07-15",
        },
        "voter_id": {
            "name": "Pranav Ghatol",
            "dob": "2005-07-16",
            "address": "123 MG Road, Pune, Maharashtra",
        },
    }
}

response = requests.post(url, json=payload)

print("Status code:", response.status_code)
print(json.dumps(response.json(), indent=2))
