categories = [
    {
        "id": "identity-civil",
        "title": "Identity & Civil Documents",
        "icon": "🪪",
        "services": [
            {"name": "Aadhaar Card", "desc": "New enrollment, correction, update"},
            {"name": "PAN Card", "desc": "New application, correction, e-PAN"},
            {"name": "Voter ID", "desc": "New registration, correction, address change"},
            {"name": "Birth Certificate", "desc": "New application, correction"},
            {"name": "Ration Card", "desc": "New application, member update"},
            {"name": "Death Certificate", "desc": "Registration, duplicate copy"},
        ],
    },
    {
        "id": "licenses-transport",
        "title": "Licenses & Transport",
        "icon": "🚗",
        "services": [
            {"name": "Driving Licence", "desc": "New DL, renewal, duplicate"},
            {"name": "Passport", "desc": "New, renewal, Tatkal, reissue"},
            {"name": "Vehicle Registration (RC)", "desc": "New RC, renewal, duplicate"},
            {"name": "Vehicle Transfer / NOC", "desc": "Ownership transfer, NOC for relocation"},
        ],
    },
    {
        "id": "exam-forms",
        "title": "Government Exam Forms",
        "icon": "📝",
        "services": [
            {"name": "UPSC", "desc": "Civil Services exam application"},
            {"name": "MHT-CET", "desc": "Maharashtra state CET application"},
            {"name": "JEE", "desc": "JEE Main / Advanced application"},
            {"name": "NEET", "desc": "Medical entrance exam application"},
        ],
    },
    {
        "id": "govt-schemes",
        "title": "Government Schemes",
        "icon": "🏛️",
        "services": [
            {"name": "PM-KISAN", "desc": "Income support scheme for farmers"},
            {"name": "Ayushman Bharat", "desc": "Health insurance coverage application"},
            {"name": "PM Awas Yojana", "desc": "Housing scheme application"},
            {"name": "PM Ujjwala Yojana", "desc": "LPG connection for eligible households"},
            {"name": "Scholarship Schemes", "desc": "State & central scholarship application"},
        ],
    },
]

OFFICIAL_PORTALS = {
    "Aadhaar Card": {
        "name": "myAadhaar Portal (UIDAI)",
        "url": "https://myaadhaar.uidai.gov.in/",
        "authority": "Unique Identification Authority of India (UIDAI)",
        "description": "Official UIDAI portal for Aadhaar updates, verification, and appointment booking.",
    },
    "PAN Card": {
        "name": "Protean NSDL / UTIITSL PAN Portal",
        "url": "https://www.onlineservices.nsdl.com/paam/endUserRegisterContact.html",
        "authority": "Income Tax Department, Government of India",
        "description": "Official portal for new PAN cards, reprints, and personal data corrections.",
    },
    "Voter ID": {
        "name": "Voters' Service Portal (ECI)",
        "url": "https://voters.eci.gov.in/",
        "authority": "Election Commission of India",
        "description": "Official ECI portal for voter registration, Form 6/8, and EPIC download.",
    },
    "Birth Certificate": {
        "name": "Civil Registration System (ORGI)",
        "url": "https://crsorgi.gov.in/",
        "authority": "Office of the Registrar General & Census Commissioner, India",
        "description": "Official portal for birth and death registration and certificate verification.",
    },
    "Ration Card": {
        "name": "National Food Security Portal (NFSA)",
        "url": "https://nfsa.gov.in/",
        "authority": "Department of Food & Public Distribution",
        "description": "Official portal for state-wise Ration Card management and citizen services.",
    },
    "Death Certificate": {
        "name": "Civil Registration System (ORGI)",
        "url": "https://crsorgi.gov.in/",
        "authority": "Office of the Registrar General & Census Commissioner, India",
        "description": "Official national registration portal for death event reporting and certification.",
    },
    "Driving Licence": {
        "name": "Sarathi Parivahan (MoRTH)",
        "url": "https://sarathi.parivahan.gov.in/",
        "authority": "Ministry of Road Transport and Highways",
        "description": "Official portal for Learner's Licence, Driving Licence renewal, and contactless services.",
    },
    "Passport": {
        "name": "Passport Seva Portal",
        "url": "https://www.passportindia.gov.in/",
        "authority": "Ministry of External Affairs, Government of India",
        "description": "Official portal for fresh/re-issue passport applications and appointment booking.",
    },
    "Vehicle Registration (RC)": {
        "name": "Vahan Parivahan (MoRTH)",
        "url": "https://vahan.parivahan.gov.in/",
        "authority": "Ministry of Road Transport and Highways",
        "description": "Official portal for vehicle RC services, fitness, and tax payments.",
    },
    "Vehicle Transfer / NOC": {
        "name": "Parivahan Sewa (MoRTH)",
        "url": "https://parivahan.gov.in/",
        "authority": "Ministry of Road Transport and Highways",
        "description": "Official portal for vehicle ownership transfer and inter-state NOC issuance.",
    },
    "UPSC": {
        "name": "UPSC Online Portal",
        "url": "https://upsconline.nic.in/",
        "authority": "Union Public Service Commission",
        "description": "Official portal for UPSC civil services examination and recruitment applications.",
    },
    "MHT-CET": {
        "name": "State CET Cell Maharashtra",
        "url": "https://cetcell.mahacet.org/",
        "authority": "Government of Maharashtra CET Cell",
        "description": "Official portal for Maharashtra higher and technical education entrance exams.",
    },
    "JEE": {
        "name": "JEE (Main) Portal (NTA)",
        "url": "https://jeemain.nta.nic.in/",
        "authority": "National Testing Agency (NTA)",
        "description": "Official examination portal for Joint Entrance Examination (Main).",
    },
    "NEET": {
        "name": "NEET (UG) Portal (NTA)",
        "url": "https://neet.nta.nic.in/",
        "authority": "National Testing Agency (NTA)",
        "description": "Official examination portal for National Eligibility cum Entrance Test (Undergraduate).",
    },
    "PM-KISAN": {
        "name": "PM-KISAN Samman Nidhi Portal",
        "url": "https://pmkisan.gov.in/",
        "authority": "Ministry of Agriculture and Farmers Welfare",
        "description": "Official portal for farmer income support, e-KYC, and beneficiary status.",
    },
    "Ayushman Bharat": {
        "name": "Ayushman Beneficiary Portal (PM-JAY)",
        "url": "https://beneficiary.nha.gov.in/",
        "authority": "National Health Authority (NHA)",
        "description": "Official portal to check eligibility and generate Ayushman Golden Card (PM-JAY).",
    },
    "PM Awas Yojana": {
        "name": "PMAY-Urban Portal",
        "url": "https://pmaymis.gov.in/",
        "authority": "Ministry of Housing and Urban Affairs",
        "description": "Official portal for Pradhan Mantri Awas Yojana housing subsidies and application tracking.",
    },
    "PM Ujjwala Yojana": {
        "name": "PMUY 2.0 Official Portal",
        "url": "https://www.pmuy.gov.in/",
        "authority": "Ministry of Petroleum and Natural Gas",
        "description": "Official portal for new LPG connection applications under Ujjwala 2.0 scheme.",
    },
    "Scholarship Schemes": {
        "name": "National Scholarship Portal (NSP)",
        "url": "https://scholarships.gov.in/",
        "authority": "Ministry of Electronics & Information Technology",
        "description": "One-stop portal for Central and State government student scholarship schemes.",
    },
}


def get_service_portal(service_name):
    """Returns official portal metadata for a given service name, slug, or alias."""
    if not service_name:
        return None
    cleaned = service_name.strip().lower().replace("-", " ")
    for k, v in OFFICIAL_PORTALS.items():
        if k.lower() == cleaned or k.lower().replace("-", " ") == cleaned:
            return {"service": k, **v}
    for k, v in OFFICIAL_PORTALS.items():
        if cleaned in k.lower() or k.lower() in cleaned:
            return {"service": k, **v}
    return None

