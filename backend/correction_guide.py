import re

CORRECTION_GUIDE = {
    "aadhaar": {
        "name": {
            "channel": "in_person",
            "portal": "Aadhaar Seva Kendra / Enrolment Centre",
            "portal_url": "https://appointments.uidai.gov.in/",
            "source_url": "https://uidai.gov.in/",
            "form": "Aadhaar Enrolment / Correction Form",
            "notes": (
                "Name, date of birth, gender, and biometric details cannot be updated online per UIDAI regulations. "
                "Visit an authorized Aadhaar Seva Kendra with valid supporting proof (e.g. Passport, PAN Card, or Gazette notification)."
            ),
            "fee": "₹50 (inclusive of GST)",
            "turnaround": "Typically 15 to 30 days for update reflection",
            "last_verified": "2025-01",
        },
        "dob": {
            "channel": "in_person",
            "portal": "Aadhaar Seva Kendra / Enrolment Centre",
            "portal_url": "https://appointments.uidai.gov.in/",
            "source_url": "https://uidai.gov.in/",
            "form": "Aadhaar Enrolment / Correction Form",
            "notes": (
                "Date of birth corrections require an in-person visit with an approved Birth Certificate or 10th Marksheet. "
                "UIDAI permits DOB correction only once in a lifetime."
            ),
            "fee": "₹50 (inclusive of GST)",
            "turnaround": "Typically 15 to 30 days",
            "last_verified": "2025-01",
        },
        "address": {
            "channel": "online",
            "portal": "myAadhaar portal (myaadhaar.uidai.gov.in)",
            "portal_url": "https://myaadhaar.uidai.gov.in/",
            "source_url": "https://uidai.gov.in/",
            "form": "Online Address Update Service",
            "notes": "Address updates can be submitted online using valid address proof (Electricity bill, Rent agreement, Bank passbook) or Head of Family (HoF) consent with OTP.",
            "fee": "₹50 (online update fee)",
            "turnaround": "Typically 3 to 14 business days",
            "last_verified": "2025-01",
        },
    },
    "pan": {
        "name": {
            "channel": "online",
            "portal": "Protean (NSDL) / UTIITSL PAN Portal",
            "portal_url": "https://www.onlineservices.nsdl.com/paam/endUserRegisterContact.html",
            "source_url": "https://www.incometax.gov.in/",
            "form": "PAN Correction Request (Changes or Correction in existing PAN Data)",
            "notes": "Paperless online application via Aadhaar e-KYC or digital e-Sign. Attach proof of identity matching the corrected name.",
            "fee": "₹72 (e-PAN only) / ₹107 (Physical card delivered in India)",
            "turnaround": "e-PAN issued in 2–4 days; physical card delivered by post in 10–15 days",
            "last_verified": "2025-01",
        },
        "dob": {
            "channel": "online",
            "portal": "Protean (NSDL) / UTIITSL PAN Portal",
            "portal_url": "https://www.onlineservices.nsdl.com/paam/endUserRegisterContact.html",
            "source_url": "https://www.incometax.gov.in/",
            "form": "PAN Correction Request (Changes or Correction in existing PAN Data)",
            "notes": "Upload valid Birth Certificate, 10th Marksheet, or Aadhaar Card as proof of date of birth.",
            "fee": "₹72 (e-PAN) / ₹107 (Physical card)",
            "turnaround": "e-PAN in 2–4 days; physical card follows by post",
            "last_verified": "2025-01",
        },
        "address": {
            "channel": "online",
            "portal": "Protean (NSDL) / UTIITSL PAN Portal",
            "portal_url": "https://www.onlineservices.nsdl.com/paam/endUserRegisterContact.html",
            "source_url": "https://www.incometax.gov.in/",
            "form": "Online PAN Address Update through Aadhaar",
            "notes": "Paperless address update using Aadhaar e-KYC authentication.",
            "fee": "₹50 for reprint / Free online e-KYC sync",
            "turnaround": "e-KYC verified in minutes",
            "last_verified": "2025-01",
        },
    },
    "voter_id": {
        "name": {
            "channel": "online",
            "portal": "ECI Voters' Service Portal (voters.eci.gov.in)",
            "portal_url": "https://voters.eci.gov.in/",
            "source_url": "https://eci.gov.in/",
            "form": "Form 8 (Correction of Entries in Existing Electoral Roll)",
            "notes": "Submit Form 8 on the official ECI portal. Attach supporting identity proof reflecting your correct name.",
            "fee": "Free",
            "turnaround": "15 to 30 days following Booth Level Officer (BLO) verification",
            "last_verified": "2025-01",
        },
        "dob": {
            "channel": "online",
            "portal": "ECI Voters' Service Portal (voters.eci.gov.in)",
            "portal_url": "https://voters.eci.gov.in/",
            "source_url": "https://eci.gov.in/",
            "form": "Form 8 (Correction of Entries in Existing Electoral Roll)",
            "notes": "Submit Form 8 with an attached Birth Certificate, 10th Marksheet, or Aadhaar Card.",
            "fee": "Free",
            "turnaround": "15 to 30 days",
            "last_verified": "2025-01",
        },
        "address": {
            "channel": "online",
            "portal": "ECI Voters' Service Portal (voters.eci.gov.in)",
            "portal_url": "https://voters.eci.gov.in/",
            "source_url": "https://eci.gov.in/",
            "form": "Form 8 (Shifting of Residence / Correction)",
            "notes": "Use Form 8 for shifting of residence within or outside assembly constituency. Attach current electricity bill or rent agreement.",
            "fee": "Free",
            "turnaround": "15 to 30 days",
            "last_verified": "2025-01",
        },
    },
    "driving_licence": {
        "name": {
            "channel": "online_then_appointment",
            "portal": "Sarathi Parivahan (MoRTH)",
            "portal_url": "https://sarathi.parivahan.gov.in/",
            "source_url": "https://parivahan.gov.in/",
            "form": "Application for Change of Name in DL",
            "notes": "Select state on Sarathi Parivahan, choose 'Services on Driving Licence', enter DL number and DOB. Many states now offer Aadhaar-authenticated paperless processing.",
            "fee": "Approx. ₹200–₹350 (varies by state Motor Vehicles Department)",
            "turnaround": "Updated licence dispatched within 30 days",
            "last_verified": "2025-01",
        },
        "address": {
            "channel": "online_then_appointment",
            "portal": "Sarathi Parivahan (MoRTH)",
            "portal_url": "https://sarathi.parivahan.gov.in/",
            "source_url": "https://parivahan.gov.in/",
            "form": "Application for Change of Address in DL",
            "notes": "Submit change of address on Sarathi Parivahan with valid residential address proof.",
            "fee": "Approx. ₹200–₹350 (varies by state)",
            "turnaround": "Typically within 30 days",
            "last_verified": "2025-01",
        },
        "dob": {
            "channel": "online_then_appointment",
            "portal": "Sarathi Parivahan (MoRTH)",
            "portal_url": "https://sarathi.parivahan.gov.in/",
            "source_url": "https://parivahan.gov.in/",
            "form": "Application for Correction in DL Particulars",
            "notes": "Requires uploading an authentic Birth Certificate or 10th Marksheet and in-person verification at the issuing RTO.",
            "fee": "Approx. ₹200–₹350",
            "turnaround": "Typically within 30 days",
            "last_verified": "2025-01",
        },
    },
    "passport": {
        "name": {
            "channel": "online_then_appointment",
            "portal": "Passport Seva Portal (Ministry of External Affairs)",
            "portal_url": "https://www.passportindia.gov.in/",
            "source_url": "https://www.passportindia.gov.in/",
            "form": "Application for Re-issue of Passport (Change in Personal Particulars)",
            "notes": (
                "Fill the Re-issue form online, pay fee, and book an appointment at the nearest Passport Seva Kendra (PSK/POPSK). "
                "Document verification and biometric capture are mandatory in person."
            ),
            "fee": "₹1,500 (Standard 36 pages) / ₹3,500 (Tatkal)",
            "turnaround": "7 to 20 business days (Normal) or 1 to 3 days (Tatkal)",
            "last_verified": "2025-01",
        },
        "dob": {
            "channel": "online_then_appointment",
            "portal": "Passport Seva Portal (Ministry of External Affairs)",
            "portal_url": "https://www.passportindia.gov.in/",
            "source_url": "https://www.passportindia.gov.in/",
            "form": "Application for Re-issue of Passport (Change in Personal Particulars)",
            "notes": (
                "Apply for Re-issue on Passport Seva. Attach authenticated Birth Certificate. "
                "Note: Domicile Certificate is not an accepted proof of date of birth per MEA regulations."
            ),
            "fee": "₹1,500 standard re-issue fee",
            "turnaround": "1 to 3 weeks",
            "last_verified": "2025-01",
        },
        "address": {
            "channel": "online_then_appointment",
            "portal": "Passport Seva Portal (Ministry of External Affairs)",
            "portal_url": "https://www.passportindia.gov.in/",
            "source_url": "https://www.passportindia.gov.in/",
            "form": "Application for Re-issue of Passport (Change of Address)",
            "notes": "Apply online and present current address proof (updated Aadhaar, electricity bill, or bank passbook) at PSK.",
            "fee": "₹1,500 standard re-issue fee",
            "turnaround": "7 to 20 business days",
            "last_verified": "2025-01",
        },
    },
    "10th_marksheet": {
        "name": {
            "channel": "in_person",
            "portal": "Respective State Education Board / CBSE",
            "portal_url": "https://cbse.gov.in/",
            "source_url": "https://www.cbse.gov.in/",
            "form": "Application for Name Correction in Matriculation / Secondary Certificate",
            "notes": (
                "Corrections in school certificates must be forwarded by the head of the institution where you studied, "
                "supported by the school admission register extract."
            ),
            "fee": "₹500–₹1,000 depending on the education board",
            "turnaround": "30 to 60 days following board committee review",
            "last_verified": "2025-01",
        },
        "dob": {
            "channel": "in_person",
            "portal": "Respective State Education Board / CBSE",
            "portal_url": "https://cbse.gov.in/",
            "source_url": "https://www.cbse.gov.in/",
            "form": "Application for Date of Birth Correction in Secondary Examination Record",
            "notes": "Must be routed through the school principal with verified municipal birth registration record.",
            "fee": "₹500–₹1,000",
            "turnaround": "30 to 60 days",
            "last_verified": "2025-01",
        },
    },
    "birth_certificate": {
        "name": {
            "channel": "in_person",
            "portal": "Civil Registration System (CRS) / Municipal Corporation",
            "portal_url": "https://crsorgi.gov.in/",
            "source_url": "https://crsorgi.gov.in/",
            "form": "Application for Correction in Birth Record under Section 15 of RBD Act, 1969",
            "notes": (
                "Contact the local Registrar of Births and Deaths (Municipal Corporation, Nagar Palika, or Gram Panchayat) "
                "where the birth occurred. Submit an affidavit and school/hospital records."
            ),
            "fee": "₹10–₹50 search and correction fee",
            "turnaround": "15 to 30 days",
            "last_verified": "2025-01",
        },
        "dob": {
            "channel": "in_person",
            "portal": "Civil Registration System (CRS) / Municipal Corporation",
            "portal_url": "https://crsorgi.gov.in/",
            "source_url": "https://crsorgi.gov.in/",
            "form": "Application for Date of Birth Rectification under Section 15 of RBD Act",
            "notes": "Requires hospital discharge summary, vaccination card, or magistrate order if delayed registration.",
            "fee": "₹10–₹50",
            "turnaround": "15 to 30 days",
            "last_verified": "2025-01",
        },
    },
    "domicile": {
        "name": {
            "channel": "online",
            "portal": "State e-District / Citizen Portal",
            "portal_url": "https://services.india.gov.in/",
            "source_url": "https://services.india.gov.in/",
            "form": "Correction in Domicile / Residence Certificate",
            "notes": "Apply through your respective State citizen portal (e.g. Aaple Sarkar in Maharashtra) or Tehsil office.",
            "fee": "₹20–₹50",
            "turnaround": "15 to 21 days",
            "last_verified": "2025-01",
        },
        "address": {
            "channel": "online",
            "portal": "State e-District / Citizen Portal",
            "portal_url": "https://services.india.gov.in/",
            "source_url": "https://services.india.gov.in/",
            "form": "Correction / Re-issuance of Domicile Certificate",
            "notes": "Submit updated residential proof through the district revenue authority portal.",
            "fee": "₹20–₹50",
            "turnaround": "15 to 21 days",
            "last_verified": "2025-01",
        },
    },
    "electricity_bill": {
        "name": {
            "channel": "online_or_in_person",
            "portal": "State Electricity Distribution Company (DISCOM)",
            "portal_url": "https://services.india.gov.in/",
            "source_url": "https://services.india.gov.in/",
            "form": "Application for Name Change / Transfer of Connection",
            "notes": "Submit ownership document (Registered Sale Deed or Rent Agreement), NOC from previous owner, and latest paid bill to local DISCOM office or portal.",
            "fee": None,
            "needs_verification": True,
            "turnaround": "7 to 30 days",
            "last_verified": "2025-01",
        },
        "address": {
            "channel": "online_or_in_person",
            "portal": "State Electricity Distribution Company (DISCOM)",
            "portal_url": "https://services.india.gov.in/",
            "source_url": "https://services.india.gov.in/",
            "form": "Application for Premises / Billing Address Correction",
            "notes": "Submit municipal property tax receipt or registered address proof to your electricity supply subdivision.",
            "fee": None,
            "needs_verification": True,
            "turnaround": "7 to 15 days",
            "last_verified": "2025-01",
        },
    },
    "rent_agreement": {
        "name": {
            "channel": "in_person",
            "portal": "Sub-Registrar Office / Department of Registration & Stamps",
            "portal_url": "https://services.india.gov.in/",
            "source_url": "https://services.india.gov.in/",
            "form": "Fresh Rent Agreement / Supplementary Agreement (Addendum)",
            "notes": "Execute a fresh registered agreement or notarized addendum on stamp paper signed by both tenant and landlord.",
            "fee": None,
            "needs_verification": True,
            "turnaround": "1 to 3 days",
            "last_verified": "2025-01",
        },
        "address": {
            "channel": "in_person",
            "portal": "Sub-Registrar Office / Department of Registration & Stamps",
            "portal_url": "https://services.india.gov.in/",
            "source_url": "https://services.india.gov.in/",
            "form": "Rectification Deed / Fresh Registered Tenancy Agreement",
            "notes": "Execute a rectification deed or fresh agreement clearly stating correct premises address with survey/flat number.",
            "fee": None,
            "needs_verification": True,
            "turnaround": "1 to 3 days",
            "last_verified": "2025-01",
        },
    },
    "bank_passbook": {
        "name": {
            "channel": "in_person",
            "portal": "Home Bank Branch",
            "portal_url": "https://services.india.gov.in/",
            "source_url": "https://rbi.org.in/",
            "form": "Customer Information Updation Form (KYC Updation)",
            "notes": "Visit your bank branch with proof of identity (Aadhaar/PAN/Passport) and residential proof to update records and get an updated passbook.",
            "fee": "Free / Nominal charge for duplicate passbook (₹50–₹100)",
            "turnaround": "Immediate across counter or 1–3 working days",
            "last_verified": "2025-01",
        },
        "address": {
            "channel": "online_or_in_person",
            "portal": "Bank NetBanking Portal / Home Branch",
            "portal_url": "https://services.india.gov.in/",
            "source_url": "https://rbi.org.in/",
            "form": "Customer Address Updation Request",
            "notes": "Many banks allow Aadhaar OTP-based online address update via NetBanking/Mobile App, or submit an address proof at the branch.",
            "fee": "Free",
            "turnaround": "1 to 3 business days",
            "last_verified": "2025-01",
        },
    },
    "ration_card": {
        "name": {
            "channel": "online_or_in_person",
            "portal": "National Food Security Portal (NFSA) / State PDS",
            "portal_url": "https://nfsa.gov.in/",
            "source_url": "https://nfsa.gov.in/",
            "form": "Ration Card Member Modification Form",
            "notes": "Submit correction request via the State Food & Civil Supplies portal or local Tehsil / Rationing office with Aadhaar cards.",
            "fee": None,
            "needs_verification": True,
            "turnaround": "15 to 30 days",
            "last_verified": "2025-01",
        },
        "address": {
            "channel": "online_or_in_person",
            "portal": "National Food Security Portal (NFSA) / State PDS",
            "portal_url": "https://nfsa.gov.in/",
            "source_url": "https://nfsa.gov.in/",
            "form": "Ration Card Address Shifting / Modification Form",
            "notes": "Apply for fair price shop transfer or address change through your state PDS portal with residential proof.",
            "fee": None,
            "needs_verification": True,
            "turnaround": "15 to 30 days",
            "last_verified": "2025-01",
        },
    },
}

ALIASES = {
    "aadhaar": "aadhaar",
    "aadhar": "aadhaar",
    "aadhaar_card": "aadhaar",
    "uidai": "aadhaar",
    "parents_aadhaar_card": "aadhaar",
    "parent_aadhaar": "aadhaar",
    "pan": "pan",
    "pan_card": "pan",
    "voter_id": "voter_id",
    "voter_id_card": "voter_id",
    "voterid": "voter_id",
    "voter": "voter_id",
    "driving_licence": "driving_licence",
    "driving_license": "driving_licence",
    "dl": "driving_licence",
    "passport": "passport",
    "10th_marksheet": "10th_marksheet",
    "10th_certificate": "10th_marksheet",
    "10th_certificate_marksheet": "10th_marksheet",
    "marksheet": "10th_marksheet",
    "birth_certificate": "birth_certificate",
    "birth_cert": "birth_certificate",
    "domicile": "domicile",
    "domicile_certificate": "domicile",
    "electricity_bill": "electricity_bill",
    "rent_agreement": "rent_agreement",
    "bank_passbook": "bank_passbook",
    "ration_card": "ration_card",
}


def normalize_doc_key(doc_key):
    """
    Maps a loosely-formatted document key to its canonical guide key using whole-word matching.
    Avoids greedy substring matches.
    """
    if not doc_key:
        return None
    cleaned = str(doc_key).strip().lower().replace("-", " ")
    tokens = set(re.findall(r"[a-z0-9]+", cleaned))

    key_normalized = "_".join(re.findall(r"[a-z0-9]+", cleaned))
    if key_normalized in ALIASES:
        return ALIASES[key_normalized]

    if "aadhaar" in tokens or "aadhar" in tokens or "uidai" in tokens:
        return "aadhaar"
    if "pan" in tokens:
        return "pan"
    if "voter" in tokens or "epic" in tokens:
        return "voter_id"
    if "driving" in tokens or "dl" in tokens or "licence" in tokens or "license" in tokens:
        return "driving_licence"
    if "passport" in tokens:
        return "passport"
    if "marksheet" in tokens or "matriculation" in tokens or "ssc" in tokens or "10th" in tokens:
        return "10th_marksheet"
    if "birth" in tokens:
        return "birth_certificate"
    if "domicile" in tokens:
        return "domicile"
    if "electricity" in tokens or "electric" in tokens or "power" in tokens:
        return "electricity_bill"
    if "rent" in tokens or "tenancy" in tokens:
        return "rent_agreement"
    if "passbook" in tokens or "bank" in tokens:
        return "bank_passbook"
    if "ration" in tokens:
        return "ration_card"

    return None


def get_guidance(doc_key, field, doc_meta=None):
    """
    Returns correction guidance for a (document, field) pair.
    Dynamically routes 10th marksheets by educational board and domicile by state.
    """
    canonical = normalize_doc_key(doc_key)
    meta = doc_meta or {}
    if isinstance(meta, str):
        import json
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}

    if canonical and canonical in CORRECTION_GUIDE:
        field_guidance = CORRECTION_GUIDE[canonical].get(field)
        if field_guidance:
            result = {"document": canonical, **field_guidance}

            # Dynamic routing for 10th marksheet by issuer
            if canonical == "10th_marksheet":
                issuer = meta.get("issuer")
                if issuer == "maharashtra_board":
                    result["portal"] = "Maharashtra State Board e-Marksheet Portal"
                    result["portal_url"] = "https://boardmarksheet.maharashtra.gov.in/"
                    result["source_url"] = "https://mahahsscboard.in/"
                    result["notes"] = "For Maharashtra State Board (MSBSHSE SSC/HSC), duplicate marksheets and verification can be submitted via the Maharashtra e-Marksheet portal or Divisional Board offices."
                elif issuer == "cbse":
                    result["portal"] = "CBSE Duplicate Academic Document System (DADS)"
                    result["portal_url"] = "https://cbseit.in/cbse/web/dads/"
                    result["source_url"] = "https://www.cbse.gov.in/"
                    result["notes"] = "For CBSE, submit correction applications through the official CBSE DADS portal. Corrections must be forwarded by the school principal."
                elif issuer == "icse":
                    result["portal"] = "CISCE Council Portal"
                    result["portal_url"] = "https://cisce.org/"
                    result["source_url"] = "https://cisce.org/"

            # Dynamic routing for Domicile by state
            if canonical == "domicile":
                state = meta.get("state")
                if state == "Maharashtra":
                    result["portal"] = "Aaple Sarkar Portal (Maharashtra)"
                    result["portal_url"] = "https://aaplesarkar.mahaonline.gov.in/"
                    result["source_url"] = "https://aaplesarkar.mahaonline.gov.in/"
                elif state == "Delhi":
                    result["portal"] = "e-District Delhi Portal"
                    result["portal_url"] = "https://edistrict.delhigovt.nic.in/"
                    result["source_url"] = "https://edistrict.delhigovt.nic.in/"
                elif state == "Uttar Pradesh":
                    result["portal"] = "eDistrict Uttar Pradesh"
                    result["portal_url"] = "https://edistrict.up.gov.in/"
                    result["source_url"] = "https://edistrict.up.gov.in/"

            return result

    return {
        "document": str(doc_key),
        "channel": "unknown",
        "portal": "Official Government Department Portal",
        "portal_url": "https://services.india.gov.in/",
        "source_url": "https://services.india.gov.in/",
        "form": None,
        "notes": "Correction steps for this document type can be completed through the issuing department's official portal.",
        "fee": None,
        "turnaround": None,
        "needs_verification": True,
    }
