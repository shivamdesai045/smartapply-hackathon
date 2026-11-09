"""Local advisory thresholds, not official service eligibility requirements.

VERIFICATION_POLICIES_FILE may point to JSON {default:{...}, services:{name:{...}}}.
No network requests are made. Dates are ISO calendar dates.
"""
import json
import os


def get_policy(service=None):
    path = os.getenv("VERIFICATION_POLICIES_FILE")
    if not path:
        return {}
    with open(path, encoding="utf-8") as source:
        config = json.load(source)
    return {**config.get("default", {}), **config.get("services", {}).get(service, {})}
