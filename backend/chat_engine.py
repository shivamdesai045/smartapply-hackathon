import os
import re
import json
import urllib.request
import urllib.error
from checklist_data import CHECKLISTS
from correction_guide import CORRECTION_GUIDE
from services_data import OFFICIAL_PORTALS

AADHAAR_REGEX = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
PAN_REGEX = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I)
FORGERY_KEYWORDS = [
    "fake", "forge", "forgery", "alter", "tamper", "photoshop", "bypass verification",
    "counterfeit", "buy certificate", "duplicate illegal", "manipulate date", "change photo illegally",
    "फर्जी", "नकली", "बनावटी", "खोटे", "बोगस"
]

def mask_sensitive_user_message(msg):
    """Masks 12-digit Aadhaar-like numbers and PAN patterns before processing."""
    masked = msg
    had_sensitive = False

    if AADHAAR_REGEX.search(masked):
        masked = AADHAAR_REGEX.sub("XXXX-XXXX-[ID]", masked)
        had_sensitive = True

    if PAN_REGEX.search(masked):
        masked = PAN_REGEX.sub("[PAN-MASKED]", masked)
        had_sensitive = True

    return masked, had_sensitive


def detect_message_language(text, ui_hint="en"):
    """
    Detects language and script from text content.
    Returns: 'en', 'hi', 'mr', 'roman_marathi', 'hinglish', etc.
    """
    if not text:
        return ui_hint or "en"

    # Check for Devanagari script (Hindi or Marathi)
    devanagari_chars = len(re.findall(r"[\u0900-\u097F]", text))
    if devanagari_chars >= 3:
        # Check for Marathi-specific vocabulary/endings
        marathi_markers = ["कसे", "कागदपत्रे", "करायचे", "नावात", "दुरुस्ती", "आहे", "नाही", "माहिती", "अर्ज", "कसा", "करावे", "कोणती"]
        if any(m in text for m in marathi_markers) or ui_hint == "mr":
            return "mr"
        return "hi"

    tl = text.lower()
    # Check for Roman-script Marathi
    roman_marathi_markers = ["kasa karaycha", "kase karave", "kagadpatra", "navat durusti", "kahi issue", "ahe ka", "sang na"]
    if any(m in tl for m in roman_marathi_markers):
        return "roman_marathi"

    # Check for Hinglish
    hinglish_markers = ["kya document", "kaise apply", "kahan se", "batao", "karna hai", "nahi ho raha", "chahiye"]
    if any(m in tl for m in hinglish_markers):
        return "hinglish"

    # Other regional script detection
    if len(re.findall(r"[\u0B80-\u0BFF]", text)) >= 3:
        return "ta"
    if len(re.findall(r"[\u0C00-\u0C7F]", text)) >= 3:
        return "te"
    if len(re.findall(r"[\u0980-\u09FF]", text)) >= 3:
        return "bn"
    if len(re.findall(r"[\u0A80-\u0AFF]", text)) >= 3:
        return "gu"
    if len(re.findall(r"[\u0C80-\u0CFF]", text)) >= 3:
        return "kn"
    if len(re.findall(r"[\u0D00-\u0D7F]", text)) >= 3:
        return "ml"
    if len(re.findall(r"[\u0A00-\u0A7F]", text)) >= 3:
        return "pa"

    return ui_hint if ui_hint in ("hi", "mr", "en") else "en"


def build_system_context(service_name=None, variant="adult", user_mismatches_summary=None):
    """
    Builds verified factual context strictly from static data files.
    Never invents URLs or fees; includes only official .gov.in/.nic.in sources.
    """
    context_lines = [
        "YOU ARE SAHAYAK (SmartApply), an official government application guidance assistant.",
        "CRITICAL RULES:",
        "1. Strictly refuse to help forge, alter, fake, or tamper with any document or bypass government verification. State that Sahayak only assists with official, legal correction procedures.",
        "2. All guidance is informative assistance, not an official government verification or legal advice. Sahayak is not an official government website.",
        "3. Use ONLY the portal URLs and fees listed in the provided verified data below. Never invent external URLs.",
        "4. Reply in the EXACT SAME language and script the user writes in (Hindi in Devanagari, Marathi in Devanagari, English, Hinglish, Roman-script Marathi, etc.).",
        "5. Never ask the user for full Aadhaar numbers, PAN, OTPs, or passwords.",
        "6. Mention 'last verified' when quoting fees or turnaround times.",
        "\nVERIFIED SERVICES AND CHECKLIST DATA:"
    ]

    # Add services list
    for s_name, p_info in OFFICIAL_PORTALS.items():
        context_lines.append(f"- Service: {s_name} | Official Portal: {p_info.get('name')} ({p_info.get('url')}) | Turnaround: {p_info.get('turnaround')} | Fee: {p_info.get('fee')}")

    if service_name and service_name in CHECKLISTS:
        s_data = CHECKLISTS[service_name]
        v_data = s_data.get("variants", {}).get(variant or "adult", {})
        reqs = v_data.get("requirements", [])
        context_lines.append(f"\nDOCUMENT CHECKLIST FOR {service_name} ({variant}):")
        for r in reqs:
            opts = ", ".join(r.get("options", []))
            context_lines.append(f"  * {r.get('name')}: {opts} (Subject: {r.get('subject')}, Skippable: {r.get('skippable', False)})")

    context_lines.append("\nVERIFIED CORRECTION GUIDANCE:")
    for doc_k, doc_g in CORRECTION_GUIDE.items():
        doc_disp = doc_k.replace("_", " ").title()
        p_name = doc_g.get("portal", "")
        p_url = doc_g.get("portal_url", "")
        context_lines.append(f"- {doc_disp} Correction: Portal {p_name} ({p_url}), Form: {doc_g.get('form')}, Fee: {doc_g.get('fee')}, Steps: {doc_g.get('turnaround')}. {doc_g.get('notes', '')}")

    if user_mismatches_summary:
        context_lines.append(f"\nCURRENT USER DOCUMENT STATUS FOR {service_name}:")
        context_lines.append(user_mismatches_summary)

    return "\n".join(context_lines)


def rule_based_fallback_answer(message, user_lang, service_name=None, variant="adult", user_mismatches=None):
    """
    Deterministic answerer that runs when no external LLM API key is configured.
    Handles service document requirements, application portals, and mismatch guidance.
    """
    msg_lower = message.lower()
    sources = []
    suggestions = []

    # 1. Forgery / Alteration check
    if any(k in msg_lower for k in FORGERY_KEYWORDS):
        if user_lang == "mr":
            reply = (
                "मी कोणत्याही कागदपत्रांमध्ये खाडाखोड, बदल किंवा बनावट कागदपत्रे तयार करण्यास मदत करू शकत नाही. "
                "सह्यक केवळ अधिकृत सरकारी पोर्टलद्वारे कायदेशीर दुरुस्ती आणि पडताळणी मार्गदर्शन प्रदान करतो. "
                "कृपया आपल्या कागदपत्रातील दुरुस्तीसाठी अधिकृत सरकारी केंद्राशी किंवा अधिकृत पोर्टलशी संपर्क साधा."
            )
        elif user_lang in ("hi", "hinglish"):
            reply = (
                "मैं किसी भी दस्तावेज़ में हेरफेर, बदलाव या फर्जी दस्तावेज़ बनाने में सहायता नहीं कर सकता। "
                "सहायक केवल आधिकारिक सरकारी पोर्टलों के माध्यम से कानूनी सुधार और मार्गदर्शन प्रदान करता है। "
                "कृपया अपने दस्तावेज़ में सुधार के लिए आधिकारिक सरकारी पोर्टल या केंद्र का उपयोग करें।"
            )
        elif user_lang == "roman_marathi":
            reply = (
                "Mi konatyahi document madhye fake badal kinva forgery sathi madat karu shakat nahi. "
                "Sahayak fakt official government portal varun legal correction margadarshan deto. "
                "Krupaya official legal process follow kara."
            )
        else:
            reply = (
                "I cannot assist with fabricating, altering, or falsifying any government documents or bypassing verification checks. "
                "Sahayak only assists with official, legal correction procedures through authorized government channels. "
                "Please follow the legal correction process through official government portals."
            )
        return {
            "reply": reply,
            "language": user_lang,
            "sources": [{"title": "National Portal of India", "url": "https://www.india.gov.in"}],
            "suggestions": ["How do I legally correct my name?", "Where do I update my Aadhaar details?"]
        }

    # 2. Match a service from message
    matched_service = service_name
    if not matched_service:
        for s in OFFICIAL_PORTALS.keys():
            if s.lower() in msg_lower:
                matched_service = s
                break

    # 3. Handle "Where do I apply" / Portal inquiry
    if any(k in msg_lower for k in ["where to apply", "apply portal", "official link", "website", "kidhar apply", "kahan apply", "kuthe apply"]):
        target_service = matched_service or "Passport"
        portal_info = OFFICIAL_PORTALS.get(target_service, OFFICIAL_PORTALS.get("Passport", {}))
        sources.append({"title": portal_info.get("name", "Official Portal"), "url": portal_info.get("url", "https://www.india.gov.in")})

        if user_lang == "mr":
            reply = (
                f"{target_service} साठी अधिकृत अर्ज पोर्टल **{portal_info.get('name')}** आहे. "
                f"अधिकृत संकेतस्थळ: {portal_info.get('url')} "
                f"(अपेक्षित वेळ: {portal_info.get('turnaround', '15 दिवस')}, शुल्क: {portal_info.get('fee', 'लागू शुल्कानुसार')}). "
                "कृपया अंतिम अर्ज केवळ याच अधिकृत सरकारी पोर्टलवर सबमिट करा."
            )
        elif user_lang in ("hi", "hinglish"):
            reply = (
                f"{target_service} के लिए आधिकारिक आवेदन पोर्टल **{portal_info.get('name')}** है। "
                f"आधिकारिक वेबसाइट: {portal_info.get('url')} "
                f"(समय: {portal_info.get('turnaround', '15 कार्य दिवस')}, शुल्क: {portal_info.get('fee', 'सरकारी नियमानुसार')})। "
                "कृपया अंतिम आवेदन केवल इस आधिकारिक पोर्टल पर ही जमा करें।"
            )
        else:
            reply = (
                f"The official portal to apply for **{target_service}** is **{portal_info.get('name')}** ({portal_info.get('url')}). "
                f"Standard turnaround is {portal_info.get('turnaround', '15 working days')} with statutory fee {portal_info.get('fee', 'as applicable')}. "
                "Always verify and submit directly on this official government portal."
            )
        suggestions = ["What documents are required for this service?", "How do I check for mismatches in my documents?"]
        return {"reply": reply, "language": user_lang, "sources": sources, "suggestions": suggestions}

    # 4. Handle "What documents do I need"
    if any(k in msg_lower for k in ["document", "documents", "checklist", "kagadpatra", "kaise", "kya chahiye", "documents needed"]):
        target_service = matched_service or "Passport"
        portal_info = OFFICIAL_PORTALS.get(target_service, {})
        if portal_info.get("url"):
            sources.append({"title": portal_info.get("name", target_service), "url": portal_info.get("url")})

        s_data = CHECKLISTS.get(target_service, {})
        v_data = s_data.get("variants", {}).get(variant or "adult", {})
        reqs = v_data.get("requirements", [])

        if reqs:
            req_bullets = "\n".join([f"- **{r.get('name')}**: {', '.join(r.get('options', []))}" for r in reqs])
            if user_lang == "mr":
                reply = (
                    f"**{target_service}** साठी आवश्यक कागदपत्रे खालीलप्रमाणे आहेत:\n\n{req_bullets}\n\n"
                    f"तुम्ही ही कागदपत्रे सह्यकवर अपलोड करून नावातील किंवा जन्मतारखेतील त्रुटी तपासू शकता."
                )
            elif user_lang in ("hi", "hinglish"):
                reply = (
                    f"**{target_service}** के लिए आवश्यक दस्तावेज़ निम्नलिखित हैं:\n\n{req_bullets}\n\n"
                    f"आप इन दस्तावेज़ों को सहायक पर अपलोड करके नाम और जन्मतिथि के अंतर की जांच कर सकते हैं।"
                )
            else:
                reply = (
                    f"The required documents for **{target_service}** ({variant}) are:\n\n{req_bullets}\n\n"
                    f"You can upload these documents on Sahayak to cross-check spelling and date consistency."
                )
        else:
            reply = f"For {target_service}, standard identity proof (Aadhaar/PAN) and address proof are required. Please check the service checklist."

        suggestions = [f"Where do I apply for {target_service}?", "How to resolve spelling differences?"]
        return {"reply": reply, "language": user_lang, "sources": sources, "suggestions": suggestions}

    # 5. Handle mismatch resolution inquiry
    if any(k in msg_lower for k in ["mismatch", "spelling", "correction", "durusti", "sudhar", "fix", "dob", "name change"]):
        field = "name"
        if "dob" in msg_lower or "birth" in msg_lower or "tarikh" in msg_lower:
            field = "dob"
        elif "address" in msg_lower or "pata" in msg_lower:
            field = "address"

        sources.append({"title": "UIDAI Official Portal", "url": "https://myaadhaar.uidai.gov.in"})
        sources.append({"title": "Protean eGov NSDL", "url": "https://www.onlineservices.nsdl.com"})

        if user_lang == "mr":
            reply = (
                f"दस्तऐवजांमधील **{field}** दुरुस्तीसाठी:\n"
                "- **आधार कार्ड:** नाव किंवा पत्ता दुरुस्ती myAadhaar पोर्टलवर किंवा आधार सेवा केंद्रावर बायोमेट्रिकद्वारे करता येते.\n"
                "- **पॅन कार्ड:** NSDL/UTIITSL पोर्टलवर 'Changes or Correction in existing PAN Data' अर्ज दाखल करा.\n"
                "- **१० वी गुणपत्रिका:** राज्य माध्यमिक शिक्षण मंडळ किंवा CBSE पोर्टलद्वारे दुरुस्ती अर्ज करावा लागतो."
            )
        elif user_lang in ("hi", "hinglish"):
            reply = (
                f"दस्तावेज़ों में **{field}** सुधार के लिए आधिकारिक प्रक्रिया:\n"
                "- **आधार कार्ड:** myAadhaar पोर्टल या आधार सेवा केंद्र पर डेमोग्राफिक सुधार कराएं।\n"
                "- **पैन कार्ड:** NSDL पोर्टल पर 'Changes or Correction in PAN Data' फॉर्म भरें।\n"
                "- **10वीं अंकतालिका:** संबंधित शिक्षा बोर्ड के आधिकारिक पोर्टल से सुधार के लिए आवेदन करें।"
            )
        else:
            reply = (
                f"To correct a discrepancy in your **{field}** across official records:\n"
                "- **Aadhaar Card:** Update demographics via myAadhaar (https://myaadhaar.uidai.gov.in) or visit an authorized Aadhaar Seva Kendra for mandatory biometric verification.\n"
                "- **PAN Card:** Submit Form 49A correction on the official Protean NSDL portal (https://www.onlineservices.nsdl.com).\n"
                "- **10th Marksheet:** Apply for correction through your respective state or CBSE board portal."
            )
        suggestions = ["Where is the nearest Aadhaar Seva Kendra?", "What are the fees for PAN correction?"]
        return {"reply": reply, "language": user_lang, "sources": sources, "suggestions": suggestions}

    # 6. Default general guidance
    sources.append({"title": "National Portal of India", "url": "https://www.india.gov.in"})
    if user_lang == "mr":
        reply = (
            "नमस्कार! मी सह्यक सहाय्यक आहे. मी तुम्हाला सरकारी सेवांसाठी आवश्यक कागदपत्रे, "
            "नावातील व जन्मतारखेतील त्रुटींची पडताळणी आणि अधिकृत सरकारी पोर्टलबद्दल मार्गदर्शन करू शकतो. "
            "तुम्हाला कोणत्या सेवेबद्दल माहिती हवी आहे?"
        )
    elif user_lang in ("hi", "hinglish"):
        reply = (
            "नमस्ते! मैं सहायक चैटबॉट हूँ। मैं आपको सरकारी योजनाओं और सेवाओं के लिए आवश्यक दस्तावेज़, "
            "दस्तावेज़ों में अंतर (mismatches) सुधारने और आधिकारिक सरकारी पोर्टलों की जानकारी दे सकता हूँ। "
            "आप किस सेवा के बारे में जानना चाहते हैं?"
        )
    else:
        reply = (
            "Hello! I am Sahayak Assistant. I can help guide you on required documents for Indian civil services, "
            "how to resolve inconsistencies between records (Name, DOB, Address), and direct you to verified official government portals. "
            "How can I assist your document preparation today?"
        )

    suggestions = ["What documents do I need for Passport?", "How do I fix an Aadhaar mismatch?", "Driving Licence requirements"]
    return {"reply": reply, "language": user_lang, "sources": sources, "suggestions": suggestions}


def call_external_llm(provider, api_key, model, system_prompt, user_message, history=None):
    """
    Calls external LLM (Gemini, Anthropic, or OpenAI-compatible) using standard HTTP requests.
    """
    if provider == "gemini":
        model_name = model or "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        contents = []
        if history:
            for turn in history[-10:]:
                role = "user" if turn.get("from") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": turn.get("text", "")}]})
        contents.append({"role": "user", "parts": [{"text": user_message}]})

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 600}
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            return text

    elif provider == "anthropic":
        model_name = model or "claude-3-haiku-20240307"
        url = "https://api.anthropic.com/v1/messages"
        messages = []
        if history:
            for turn in history[-10:]:
                role = "user" if turn.get("from") == "user" else "assistant"
                messages.append({"role": role, "content": turn.get("text", "")})
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": model_name,
            "system": system_prompt,
            "messages": messages,
            "max_tokens": 600,
            "temperature": 0.2
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            return res_data["content"][0]["text"]

    elif provider == "openai_compatible":
        base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        url = f"{base_url.rstrip('/')}/chat/completions"
        model_name = model or "gpt-4o-mini"
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for turn in history[-10:]:
                role = "user" if turn.get("from") == "user" else "assistant"
                messages.append({"role": role, "content": turn.get("text", "")})
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 600,
            "temperature": 0.2
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            return res_data["choices"][0]["message"]["content"]

    raise ValueError(f"Unsupported LLM provider: {provider}")


def handle_chat_query(message, history=None, ui_language="en", service_name=None, variant="adult", user_mismatches_summary=None):
    """
    Main entry point for processing chat inquiries.
    Enforces masking, rate limiting checks, provider integration, and fallback.
    """
    cleaned_msg = (message or "").strip()[:1000]
    masked_msg, had_sensitive = mask_sensitive_user_message(cleaned_msg)
    user_lang = detect_message_language(cleaned_msg, ui_hint=ui_language)

    warning = "Please don't share sensitive ID numbers here." if had_sensitive else None

    # Check for configured LLM provider
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "").strip()

    if not api_key or not provider:
        res = rule_based_fallback_answer(
            masked_msg,
            user_lang=user_lang,
            service_name=service_name,
            variant=variant,
            user_mismatches=user_mismatches_summary
        )
        res["suggestedQuestions"] = res.get("suggestions", [])
        if warning:
            res["warning"] = warning
        return res

    system_prompt = build_system_context(service_name, variant, user_mismatches_summary)

    try:
        llm_reply = call_external_llm(provider, api_key, model, system_prompt, masked_msg, history=history)

        # Extract verified sources mentioned in prompt
        sources = []
        for s_name, p_info in OFFICIAL_PORTALS.items():
            if p_info.get("url") and p_info["url"] in llm_reply:
                sources.append({"title": p_info.get("name", s_name), "url": p_info["url"]})

        if not sources and service_name and service_name in OFFICIAL_PORTALS:
            p = OFFICIAL_PORTALS[service_name]
            sources.append({"title": p.get("name", service_name), "url": p.get("url")})

        suggestions = ["What are the required documents?", "Where do I apply?", "How do I fix name mismatch?"]

        return {
            "reply": llm_reply,
            "language": user_lang,
            "sources": sources,
            "suggestions": suggestions,
            "suggestedQuestions": suggestions,
            "warning": warning
        }
    except Exception as e:
        # Fall back gracefully to rule-based responder
        res = rule_based_fallback_answer(
            masked_msg,
            user_lang=user_lang,
            service_name=service_name,
            variant=variant,
            user_mismatches=user_mismatches_summary
        )
        res["suggestedQuestions"] = res.get("suggestions", [])
        if warning:
            res["warning"] = warning
        return res
