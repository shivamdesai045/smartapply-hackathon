CHECKLISTS = {
    "Aadhaar Card": {
        "variants": {
            "adult": {
                "label": "Adult (18 years or older)",
                "requirements": [
                    {
                        "name": "Proof of Identity",
                        "options": ["PAN Card", "Passport", "Voter ID Card", "Driving Licence"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                    },
                    {
                        "name": "Proof of Address",
                        "options": ["Electricity Bill", "Rent Agreement", "Bank Passbook", "Ration Card"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                    },
                    {
                        "name": "Proof of Date of Birth",
                        "options": ["Birth Certificate", "10th Marksheet", "Passport"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                        "notes": "Birth Certificate is mandatory for individuals born on or after 1 Oct 2023.",
                    },
                    {
                        "name": "Photograph",
                        "options": ["Passport-size Photograph"],
                        "subject": "applicant",
                        "compare": False,
                        "skippable": False,
                    },
                ],
            },
            "child_under_5": {
                "label": "Child under 5 years",
                "requirements": [
                    {
                        "name": "Proof of Relationship & Identity",
                        "options": ["Birth Certificate", "Parent's or Guardian's Aadhaar Card"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                    },
                ],
            },
            "child_5_to_18": {
                "label": "Child 5 to 18 years",
                "requirements": [
                    {
                        "name": "Proof of Identity",
                        "options": ["School ID Card", "Birth Certificate", "Parent's or Guardian's Aadhaar Card"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                    },
                ],
            },
        }
    },
    "PAN Card": {
        "variants": {
            "adult": {
                "label": "Applicant",
                "requirements": [
                    {
                        "name": "Proof of Identity",
                        "options": ["Aadhaar Card", "Passport", "Voter ID Card", "Driving Licence"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                    },
                    {
                        "name": "Proof of Address",
                        "options": ["Aadhaar Card", "Passport", "Electricity Bill", "Bank Passbook"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                    },
                    {
                        "name": "Proof of Date of Birth",
                        "options": ["Birth Certificate", "10th Marksheet", "Passport"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                    },
                    {
                        "name": "Photograph",
                        "options": ["Passport-size Photograph"],
                        "subject": "applicant",
                        "compare": False,
                        "skippable": False,
                    },
                ],
            }
        }
    },
    "Voter ID": {
        "variants": {
            "adult": {
                "label": "Applicant",
                "requirements": [
                    {
                        "name": "Proof of Age",
                        "options": ["Birth Certificate", "10th Marksheet", "PAN Card", "Passport"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                    },
                    {
                        "name": "Proof of Residence",
                        "options": ["Aadhaar Card", "Electricity Bill", "Rent Agreement", "Bank Passbook"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                    },
                    {
                        "name": "Photograph",
                        "options": ["Passport-size Photograph"],
                        "subject": "applicant",
                        "compare": False,
                        "skippable": False,
                    },
                ],
            }
        }
    },
    "Driving Licence": {
        "variants": {
            "adult": {
                "label": "Applicant",
                "requirements": [
                    {
                        "name": "Proof of Age",
                        "options": ["Birth Certificate", "10th Marksheet", "PAN Card", "Passport"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                    },
                    {
                        "name": "Proof of Address",
                        "options": ["Aadhaar Card", "Electricity Bill", "Rent Agreement", "Bank Passbook"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                    },
                    {
                        "name": "Learner's Licence",
                        "options": ["Learner's Licence (for new DL only)", "Not Applicable (for renewal or duplicate)"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": True,
                    },
                    {
                        "name": "Photograph",
                        "options": ["Passport-size Photograph"],
                        "subject": "applicant",
                        "compare": False,
                        "skippable": False,
                    },
                    {
                        "name": "Medical Certificate",
                        "options": ["Form 1A (required for transport/commercial vehicles or applicants above 40)", "Not Applicable (non-transport under 40)"],
                        "subject": "applicant",
                        "compare": False,
                        "skippable": True,
                    },
                ],
            }
        }
    },
    "Passport": {
        "variants": {
            "adult": {
                "label": "Adult (18 years or older)",
                "requirements": [
                    {
                        "name": "Proof of Identity",
                        "options": ["Aadhaar Card", "Voter ID Card", "PAN Card"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                    },
                    {
                        "name": "Proof of Address",
                        "options": ["Aadhaar Card", "Electricity Bill", "Rent Agreement", "Bank Passbook"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                    },
                    {
                        "name": "Proof of Date of Birth",
                        "options": ["Birth Certificate", "10th Marksheet", "Aadhaar Card", "PAN Card"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                        "notes": "Domicile Certificate is NOT an accepted proof of date of birth per MEA Passport rules. Per RBD Amendment Act 2023, Birth Certificate is the single mandatory proof of DOB for individuals born on or after 1 October 2023.",
                    },
                    {
                        "name": "Photograph",
                        "options": ["Passport-size Photograph (as per Passport Seva specification)"],
                        "subject": "applicant",
                        "compare": False,
                        "skippable": False,
                    },
                ],
            },
            "minor": {
                "label": "Minor (under 18 years)",
                "requirements": [
                    {
                        "name": "Proof of Date of Birth",
                        "options": ["Birth Certificate"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                        "notes": "Mandatory Birth Certificate for minors.",
                    },
                    {
                        "name": "Parent/Guardian Proof of Identity",
                        "options": ["Parent's Aadhaar Card", "Parent's Passport"],
                        "subject": "parent",
                        "compare": False,
                        "skippable": False,
                    },
                    {
                        "name": "Annexure (Parental Consent)",
                        "options": ["Annexure D (both parents/guardians, standard case)", "Annexure C / G / H (special cases: single parent, divorced, or adoption)"],
                        "subject": "parent",
                        "compare": False,
                        "skippable": False,
                    },
                    {
                        "name": "Photograph",
                        "options": ["Passport-size Photograph (as per Passport Seva specification)"],
                        "subject": "applicant",
                        "compare": False,
                        "skippable": False,
                    },
                ],
            },
        }
    },
    "UPSC": {
        "variants": {
            "adult": {
                "label": "Applicant",
                "requirements": [
                    {
                        "name": "Proof of Date of Birth",
                        "options": ["10th Certificate / Marksheet"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                    },
                    {
                        "name": "Educational Qualification",
                        "options": ["Graduation Certificate", "Final Year Marksheet (if awaiting result)"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": False,
                    },
                    {
                        "name": "Category Certificate",
                        "options": ["Caste Certificate", "EWS Certificate", "Not Applicable (General category)"],
                        "subject": "applicant",
                        "compare": True,
                        "skippable": True,
                    },
                    {
                        "name": "Photograph",
                        "options": ["Passport-size Photograph"],
                        "subject": "applicant",
                        "compare": False,
                        "skippable": False,
                    },
                    {
                        "name": "Signature",
                        "options": ["Scanned Signature"],
                        "subject": "applicant",
                        "compare": False,
                        "skippable": False,
                    },
                ],
            }
        }
    },
    "Birth Certificate": {
        "variants": {
            "adult": {
                "label": "Applicant",
                "requirements": [
                    {"name": "Proof of Identity", "options": ["Aadhaar Card", "Voter ID Card", "Passport"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Hospital/Institution Letter", "options": ["Hospital Discharge Summary", "Birth Registration Form"], "subject": "applicant", "compare": False, "skippable": False},
                    {"name": "Parents' Identity Proof", "options": ["Father's Aadhaar Card", "Mother's Aadhaar Card"], "subject": "parent", "compare": False, "skippable": False}
                ]
            }
        }
    },
    "Ration Card": {
        "variants": {
            "adult": {
                "label": "Head of Family",
                "requirements": [
                    {"name": "Proof of Identity", "options": ["Aadhaar Card", "Voter ID Card"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Proof of Address", "options": ["Electricity Bill", "Water Bill", "Rent Agreement"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Family Member Details", "options": ["Family Aadhaar Cards", "Birth Certificates for Minors"], "subject": "family", "compare": False, "skippable": False},
                    {"name": "Income Certificate", "options": ["Revenue Department Income Certificate", "Salary Slip"], "subject": "applicant", "compare": False, "skippable": False},
                    {"name": "Photograph", "options": ["Passport-size Family Photograph"], "subject": "applicant", "compare": False, "skippable": False}
                ]
            }
        }
    },
    "Death Certificate": {
        "variants": {
            "adult": {
                "label": "Applicant (Relative/Next of Kin)",
                "requirements": [
                    {"name": "Deceased Identity Proof", "options": ["Deceased's Aadhaar Card", "Deceased's Voter ID"], "subject": "deceased", "compare": False, "skippable": False},
                    {"name": "Applicant Identity Proof", "options": ["Aadhaar Card", "Voter ID Card"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Hospital/Doctor Certificate", "options": ["Medical Cause of Death Certificate", "Hospital Record"], "subject": "deceased", "compare": False, "skippable": False}
                ]
            }
        }
    },
    "Vehicle Registration (RC)": {
        "variants": {
            "adult": {
                "label": "Vehicle Owner",
                "requirements": [
                    {"name": "Proof of Identity", "options": ["Aadhaar Card", "PAN Card", "Passport"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Proof of Address", "options": ["Aadhaar Card", "Electricity Bill", "Rent Agreement"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Sales Invoice / Certificate", "options": ["Form 21 (Sale Certificate)", "Form 22 (Roadworthiness)"], "subject": "applicant", "compare": False, "skippable": False},
                    {"name": "Insurance", "options": ["Valid Vehicle Insurance Policy"], "subject": "applicant", "compare": False, "skippable": False}
                ]
            }
        }
    },
    "Vehicle Transfer / NOC": {
        "variants": {
            "adult": {
                "label": "Applicant (Buyer/Seller)",
                "requirements": [
                    {"name": "Original RC", "options": ["Registration Certificate (RC)"], "subject": "applicant", "compare": False, "skippable": False},
                    {"name": "Transfer Forms", "options": ["Form 29", "Form 30"], "subject": "applicant", "compare": False, "skippable": False},
                    {"name": "Proof of Identity (Buyer)", "options": ["Aadhaar Card", "PAN Card"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Proof of Address (Buyer)", "options": ["Aadhaar Card", "Electricity Bill"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Insurance", "options": ["Valid Vehicle Insurance Policy"], "subject": "applicant", "compare": False, "skippable": False}
                ]
            }
        }
    },
    "MHT-CET": {
        "variants": {
            "adult": {
                "label": "Student/Applicant",
                "requirements": [
                    {"name": "Proof of Identity", "options": ["Aadhaar Card", "School/College ID"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Educational Qualification", "options": ["10th Marksheet", "12th Marksheet (or equivalent)"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Domicile / Category", "options": ["Maharashtra Domicile Certificate", "Caste Certificate", "Not Applicable (General)"], "subject": "applicant", "compare": True, "skippable": True},
                    {"name": "Photograph", "options": ["Passport-size Photograph"], "subject": "applicant", "compare": False, "skippable": False},
                    {"name": "Signature", "options": ["Scanned Signature"], "subject": "applicant", "compare": False, "skippable": False}
                ]
            }
        }
    },
    "JEE": {
        "variants": {
            "adult": {
                "label": "Student/Applicant",
                "requirements": [
                    {"name": "Proof of Identity", "options": ["Aadhaar Card", "Passport", "School/College ID"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Educational Qualification", "options": ["10th Marksheet", "12th Marksheet (or equivalent)"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Category Certificate", "options": ["Caste Certificate", "EWS Certificate", "Not Applicable (General)"], "subject": "applicant", "compare": True, "skippable": True},
                    {"name": "Photograph", "options": ["Passport-size Photograph"], "subject": "applicant", "compare": False, "skippable": False},
                    {"name": "Signature", "options": ["Scanned Signature"], "subject": "applicant", "compare": False, "skippable": False}
                ]
            }
        }
    },
    "NEET": {
        "variants": {
            "adult": {
                "label": "Student/Applicant",
                "requirements": [
                    {"name": "Proof of Identity", "options": ["Aadhaar Card", "Passport", "Voter ID Card"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Educational Qualification", "options": ["10th Certificate", "12th Marksheet (or equivalent)"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Category Certificate", "options": ["Caste Certificate", "EWS Certificate", "Not Applicable (General)"], "subject": "applicant", "compare": True, "skippable": True},
                    {"name": "Photograph", "options": ["Passport-size Photograph", "Postcard-size Photograph"], "subject": "applicant", "compare": False, "skippable": False},
                    {"name": "Signature", "options": ["Scanned Signature"], "subject": "applicant", "compare": False, "skippable": False},
                    {"name": "Thumb Impression", "options": ["Left-hand Thumb Impression"], "subject": "applicant", "compare": False, "skippable": False}
                ]
            }
        }
    },
    "PM-KISAN": {
        "variants": {
            "adult": {
                "label": "Farmer/Applicant",
                "requirements": [
                    {"name": "Proof of Identity", "options": ["Aadhaar Card"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Land Ownership Proof", "options": ["7/12 Extract", "Land Record / Khasra Khatauni"], "subject": "applicant", "compare": False, "skippable": False},
                    {"name": "Bank Details", "options": ["Bank Passbook (Aadhaar Seeded)", "Cancelled Cheque"], "subject": "applicant", "compare": True, "skippable": False}
                ]
            }
        }
    },
    "Ayushman Bharat": {
        "variants": {
            "adult": {
                "label": "Applicant",
                "requirements": [
                    {"name": "Proof of Identity", "options": ["Aadhaar Card", "Voter ID Card", "Ration Card"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Family Proof", "options": ["Ration Card", "PM Letter (Golden Card)"], "subject": "family", "compare": False, "skippable": False},
                    {"name": "Income/Category Proof", "options": ["Income Certificate", "Caste Certificate"], "subject": "applicant", "compare": False, "skippable": False}
                ]
            }
        }
    },
    "PM Awas Yojana": {
        "variants": {
            "adult": {
                "label": "Applicant",
                "requirements": [
                    {"name": "Proof of Identity", "options": ["Aadhaar Card", "Voter ID Card"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Proof of Address", "options": ["Aadhaar Card", "Electricity Bill", "Rent Agreement"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Income Proof", "options": ["Income Certificate", "Salary Slip", "ITR"], "subject": "applicant", "compare": False, "skippable": False},
                    {"name": "Property Details", "options": ["Property Agreement", "Builder Allotment Letter"], "subject": "applicant", "compare": False, "skippable": False},
                    {"name": "Bank Details", "options": ["Bank Passbook"], "subject": "applicant", "compare": True, "skippable": False}
                ]
            }
        }
    },
    "PM Ujjwala Yojana": {
        "variants": {
            "adult": {
                "label": "Applicant (Adult Woman of BPL Family)",
                "requirements": [
                    {"name": "Proof of Identity", "options": ["Aadhaar Card", "Voter ID Card"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Family Proof", "options": ["Ration Card (BPL)", "SECC 2011 Data Document"], "subject": "family", "compare": False, "skippable": False},
                    {"name": "Bank Details", "options": ["Bank Passbook (Aadhaar Seeded)", "Cancelled Cheque"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Photograph", "options": ["Passport-size Photograph"], "subject": "applicant", "compare": False, "skippable": False}
                ]
            }
        }
    },
    "Scholarship Schemes": {
        "variants": {
            "adult": {
                "label": "Student/Applicant",
                "requirements": [
                    {"name": "Proof of Identity", "options": ["Aadhaar Card", "School/College ID"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Educational Qualification", "options": ["Previous Year Marksheet", "Admission Receipt"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Income Certificate", "options": ["Revenue Department Income Certificate"], "subject": "applicant", "compare": False, "skippable": False},
                    {"name": "Category Certificate", "options": ["Caste Certificate", "EWS Certificate", "Not Applicable (General)"], "subject": "applicant", "compare": True, "skippable": True},
                    {"name": "Bank Details", "options": ["Bank Passbook (Aadhaar Seeded)", "Cancelled Cheque"], "subject": "applicant", "compare": True, "skippable": False},
                    {"name": "Domicile", "options": ["State Domicile Certificate"], "subject": "applicant", "compare": True, "skippable": False}
                ]
            }
        }
    },
}


def find_service_key(service_name):
    """Finds the canonical service name key in CHECKLISTS regardless of casing or slug formatting."""
    if not service_name:
        return None
    if service_name in CHECKLISTS:
        return service_name
    cleaned = service_name.strip().lower().replace("-", " ")
    for k in CHECKLISTS:
        if k.lower() == cleaned or k.lower().replace("-", " ") == cleaned:
            return k
    for k in CHECKLISTS:
        if cleaned in k.lower() or k.lower() in cleaned:
            return k
    return None


def get_variants(service_name):
    """Returns {variant_key: label} for a service, or None if service not found."""
    canonical = find_service_key(service_name)
    if not canonical:
        return None
    service = CHECKLISTS[canonical]
    return {key: v["label"] for key, v in service["variants"].items()}


def get_checklist(service_name, variant="adult"):
    """Returns the requirements list for a service+variant, or None if not found."""
    canonical = find_service_key(service_name)
    if not canonical:
        return None
    service = CHECKLISTS[canonical]
    variant_data = service["variants"].get(variant)
    if variant_data is None:
        return None
    return variant_data["requirements"]
