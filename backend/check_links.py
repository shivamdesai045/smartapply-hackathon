"""
Link and Official Source Verification Tool for SmartApply
Validates that all portal URLs configured across services_data.py and
correction_guide.py belong to official Government of India (.gov.in / .nic.in)
or verified government-authorized agency domains.
"""

from urllib.parse import urlparse
from services_data import OFFICIAL_PORTALS
from correction_guide import CORRECTION_GUIDE

ALLOWED_GOV_SUFFIXES = (".gov.in", ".nic.in", ".mahacet.org", ".mahaonline.gov.in", ".nsdl.com", ".rbi.org.in", ".cisce.org")


def verify_url_domain(url):
    """Checks if a URL has an official government or authorized agency domain."""
    if not url:
        return False, "Missing URL"
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False, f"Invalid URL structure: {url}"

    is_official = any(hostname == s.lstrip(".") or hostname.endswith(s) for s in ALLOWED_GOV_SUFFIXES)
    if not is_official:
        return False, f"Non-official domain '{hostname}'"
    return True, f"Verified official ({hostname})"


def verify_all_links():
    results = {"valid": 0, "invalid": 0, "errors": []}

    print("Verifying services_data.py official portals...")
    for svc_name, meta in OFFICIAL_PORTALS.items():
        url = meta.get("url")
        ok, msg = verify_url_domain(url)
        if ok:
            results["valid"] += 1
        else:
            results["invalid"] += 1
            results["errors"].append(f"Service '{svc_name}': {msg}")

    print("Verifying correction_guide.py portals...")
    for doc_k, fields in CORRECTION_GUIDE.items():
        for field, meta in fields.items():
            if isinstance(meta, dict):
                p_url = meta.get("portal_url")
                ok, msg = verify_url_domain(p_url)
                if ok:
                    results["valid"] += 1
                else:
                    results["invalid"] += 1
                    results["errors"].append(f"Guide '{doc_k}.{field}.portal_url': {msg}")

                s_url = meta.get("source_url")
                if s_url:
                    ok_s, msg_s = verify_url_domain(s_url)
                    if ok_s:
                        results["valid"] += 1
                    else:
                        results["invalid"] += 1
                        results["errors"].append(f"Guide '{doc_k}.{field}.source_url': {msg_s}")

    return results


if __name__ == "__main__":
    res = verify_all_links()
    print(f"\nVerification Results: {res['valid']} verified, {res['invalid']} invalid.")
    if res["errors"]:
        print("Errors detected:")
        for err in res["errors"]:
            print(f"  - {err}")
    else:
        print("ALL URLS VERIFIED ON OFFICIAL DOMAINS SUCCESSFULLY!")

