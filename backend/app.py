import os
import re
import uuid
import secrets
import urllib.parse
import hmac
from functools import wraps

from flask import Flask, jsonify, request, send_file, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from dotenv import load_dotenv

from services_data import categories, get_service_portal
from rule_engine import check_mismatches
from checklist_data import get_checklist, get_variants
from correction_guide import get_guidance
from ocr_extract import extract_fields, validate_file, SUPPORTED_EXTENSIONS
from chat_engine import handle_chat_query
import db
from field_storage import FIELD_NAMES, sanitize, json_object

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=env_path)

GOOGLE_TRANSLATION_API_KEY = os.getenv("GOOGLE_TRANSLATION_API_KEY")
UPLOAD_FOLDER = os.path.abspath(os.getenv("UPLOAD_FOLDER") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads"))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
if os.getenv("ENV") == "production":
    from identity_store import cipher
    os.environ["IDENTITY_ENCRYPTION_REQUIRED"] = "1"
    cipher()  # Fail before accepting uploads if the production encryption key is invalid.
    if not os.getenv("UPLOAD_FOLDER"):
        raise RuntimeError("Production requires an explicit persistent UPLOAD_FOLDER")


# Security & Session Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("FLASK_ENV") == "production" or os.getenv("ENV") == "production":
        raise RuntimeError("FATAL: SECRET_KEY environment variable must be set in production.")
    SECRET_KEY = "dev-secret-key-for-sahayak"
app.secret_key = SECRET_KEY

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "false").lower() in ("true", "1")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB limit
app.config["RATELIMIT_ENABLED"] = not app.testing

# CORS setup
cors_origins_env = os.getenv("CORS_ORIGINS")
default_origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"]
origins = [o.strip() for o in cors_origins_env.split(",") if o.strip() and o.strip() != "*"] if cors_origins_env and cors_origins_env.strip() else default_origins
if not origins:
    origins = default_origins
CORS(app, supports_credentials=True, origins=origins)

@app.after_request
def private_api_responses(response):
    # The Vercel reverse proxy must never cache account, document or job responses.
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, private"
        response.headers["Vercel-CDN-Cache-Control"] = "no-store"
        response.headers["CDN-Cache-Control"] = "no-store"
    return response

# Rate limiter setup
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri="memory://"
)

db.init_db()

# Regex validators
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
MOBILE_REGEX = re.compile(r"^[6-9]\d{9}$")



def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({
                "error": "Please log in to continue.",
                "code": "LOGIN_REQUIRED"
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def detect_mime_from_bytes(file_path):
    """Detects MIME type from magic bytes to prevent trusting extension alone."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(16)
        if header.startswith(b"%PDF-"):
            return "application/pdf"
        elif header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        elif header.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
            return "image/gif"
    except Exception:
        pass
    return "application/octet-stream"

SESSION_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]{20,64}$")

def is_valid_session_token(val):
    if not val:
        return False
    return bool(SESSION_ID_REGEX.fullmatch(str(val)))

def is_valid_uuid(val):
    if not val:
        return False
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def get_request_session_id():
    """Extracts session_id from query params, form data, JSON body, or header."""
    sid = request.args.get("session_id") or request.form.get("session_id")
    if not sid and request.is_json:
        sid = (request.get_json(silent=True) or {}).get("session_id")
    if not sid:
        sid = request.headers.get("X-Session-ID")
    return str(sid).strip() if sid else None


def session_or_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        req_session_id = get_request_session_id()
        user_id = session.get("user_id")

        if not user_id and not req_session_id:
            return jsonify({"error": "Please log in to continue.", "code": "LOGIN_REQUIRED"}), 401

        if req_session_id:
            # Prevent path traversal characters in session_id
            unquoted = urllib.parse.unquote(req_session_id)
            if ".." in req_session_id or ".." in unquoted or os.path.isabs(unquoted) or unquoted.startswith("/") or unquoted.startswith("\\") or not is_valid_session_token(req_session_id):
                return jsonify({"error": "Invalid session_id format."}), 400
                return jsonify({"error": "Invalid session_id format."}), 400

            # Session ownership verification for anonymous requests
            if not user_id:
                cookie_sid = session.get("session_id")
                if not cookie_sid:
                    # In test suites or first request before cookie roundtrip
                    session["session_id"] = secrets.token_urlsafe(32)
                    return jsonify({"error": "Forbidden: unauthenticated session ID rejected."}), 403
                elif cookie_sid != req_session_id:
                    # Reject attempted cross-session spoofing
                    return jsonify({"error": "Forbidden: session ID does not match signed cookie."}), 403

        return f(*args, **kwargs)

    return decorated_function


def get_safe_upload_path(session_id, service_name, variant, requirement=None, ext=None):
    """Generates contained directory and file paths to guarantee path traversal protection."""
    base_dir = os.path.realpath(UPLOAD_FOLDER)
    for val in [session_id, service_name, variant, requirement]:
        if val is not None:
            s_val = str(val)
            unquoted = urllib.parse.unquote(s_val)
            if ".." in s_val or ".." in unquoted or os.path.isabs(unquoted) or unquoted.startswith("/") or unquoted.startswith("\\"):
                raise ValueError("Path traversal detected in upload parameters.")

    if not is_valid_session_token(session_id):
        raise ValueError("Invalid session_id format.")

    safe_sid = secure_filename(str(session_id))
    safe_srv = secure_filename(service_name.replace(" ", "_"))
    safe_var = secure_filename(variant.replace(" ", "_"))

    folder = os.path.realpath(os.path.join(base_dir, safe_sid, safe_srv, safe_var))
    try:
        common = os.path.commonpath([base_dir, folder])
    except ValueError:
        raise ValueError("Path traversal detected in upload directory.")
    if common != base_dir or folder == base_dir:
        raise ValueError("Path traversal detected in upload directory.")
    os.makedirs(folder, exist_ok=True)

    if requirement and ext:
        safe_req = secure_filename(requirement.replace(" ", "_").replace("/", "-"))
        clean_ext = secure_filename(ext.lstrip("."))
        final_path = os.path.realpath(os.path.join(folder, f"{safe_req}.{clean_ext}"))
        try:
            file_common = os.path.commonpath([base_dir, final_path])
        except ValueError:
            raise ValueError("Path traversal detected in file path.")
        if file_common != base_dir:
            raise ValueError("Path traversal detected in file path.")
        return folder, final_path

    return folder, None



def compare_documents(documents, service_name=None, variant="adult"):
    profile = None
    if session.get("user_id") and variant == "adult":
        user = db.get_user_by_id(session["user_id"])
        if user:
            profile = {"full_name": user.get("full_name"), "mobile_number": user.get("mobile_number")}
    from verification_policy import get_policy
    return check_mismatches(documents, profile=profile, policy=get_policy(service_name))

def build_issue_key(field, doc_a, doc_b):
    """Stable key for a mismatch issue, regardless of document order."""
    parts = sorted([doc_a.strip().lower(), doc_b.strip().lower()])
    return f"{field}::{parts[0]}|{parts[1]}"


def ocr_error_message(code):
    return {
        "OCR_BUSY": "Another document is still being read. Wait for that scan to finish, then retry.",
        "OCR_TIMEOUT": "Reading this page exceeded 70 seconds. Try a clear cropped image or a PDF with selectable text.",
        "OCR_WORKER_CRASH": "The local OCR process stopped. Retry once; if it repeats, this file needs investigation.",
        "OCR_MODEL_ERROR": "The OCR model could not read this file. Try a clear upright image or another PDF export.",
        "OCR_ENGINE_FAILED": "OCR could not process this file. Try another image or PDF export.",
        "PDF_PASSWORD_REQUIRED": "This PDF needs its password. Enter it before uploading.",
    }.get(code, "Unable to read document. Check the PDF password or file.")


@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Sahayak backend is running",
                    "ocr_engine": os.getenv("OCR_ENGINE", "paddleocr")})


@app.route("/api/session", methods=["GET"])
def get_session():
    """Generates a secure server session UUID and sets signed HTTP cookie."""
    sid = session.get("session_id")
    if not sid or not is_valid_session_token(sid):
        sid = secrets.token_urlsafe(32)
        session["session_id"] = sid
    return jsonify({
        "sessionId": sid,
        "userId": session.get("user_id")
    }), 200


@app.route("/api/services", methods=["GET"])
def get_services():
    total_categories = len(categories)
    total_services = sum(len(cat["services"]) for cat in categories)
    return jsonify(
        {
            "categories": categories,
            "totalCategories": total_categories,
            "totalServices": total_services,
        }
    )


@app.route("/api/services/<category_id>", methods=["GET"])
def get_category(category_id):
    for cat in categories:
        if cat["id"] == category_id:
            return jsonify(cat)
    return jsonify({"error": "Category not found"}), 404


@app.route("/api/checklist/<service_name>/variants", methods=["GET"])
def get_checklist_variants(service_name):
    variants = get_variants(service_name)
    if variants is None:
        return jsonify({"error": f"No checklist defined for '{service_name}'"}), 404
    variant_list = [{"key": k, "label": v} for k, v in variants.items()]
    return jsonify({
        "service": service_name,
        "variants": variants,
        "variantList": variant_list,
    })


@app.route("/api/checklist/<service_name>", methods=["GET"])
def get_checklist_route(service_name):
    variant = request.args.get("variant", "adult")
    requirements = get_checklist(service_name, variant)
    if requirements is None:
        return jsonify(
            {"error": f"No checklist defined for '{service_name}' with variant '{variant}'"}
        ), 404
    return jsonify({"service": service_name, "variant": variant, "requirements": requirements})


@app.route("/api/checklist/<service_name>/status", methods=["GET"])
@session_or_login_required
def get_checklist_status(service_name):
    session_id = request.args.get("session_id")
    variant = request.args.get("variant", "adult")

    if not session_id:
        return jsonify({"error": "session_id query parameter is required"}), 400

    requirements = get_checklist(service_name, variant)
    if requirements is None:
        return jsonify(
            {"error": f"No checklist defined for '{service_name}' with variant '{variant}'"}
        ), 404

    user_id = session.get("user_id")
    progress = db.get_progress(session_id, service_name, variant, user_id=user_id)

    status_list = []
    for req in requirements:
        req_progress = progress.get(
            req["name"],
            {
                "chosenOption": None,
                "uploaded": False,
                "filePath": None,
                "uploadedAt": None,
                "docName": None,
                "docDob": None,
                "docAddress": None,
                "docNumber": None,
                "manuallyEdited": False,
            },
        )
        status_list.append(
            {
                "requirement": req["name"],
                "options": req["options"],
                "notes": req.get("notes"),
                "subject": req.get("subject", "applicant"),
                "compare": req.get("compare", True),
                "skippable": req.get("skippable", False),
                "skipped": bool(req_progress.get("skipped", False)),
                "chosenOption": req_progress["chosenOption"] or req["options"][0],
                "uploaded": bool(req_progress["uploaded"]),
                "uploadedAt": req_progress["uploadedAt"],
                "docName": req_progress["docName"],
                "docDob": req_progress["docDob"],
                "docAddress": req_progress["docAddress"],
                "docNumber": req_progress.get("docNumber"),
            "doc_fields": req_progress.get("doc_fields", {}),
            "docFields": req_progress.get("doc_fields", {}),
            "ocr_version": req_progress.get("ocr_version"),
            "needs_review": req_progress.get("needs_review", True),
            "user_verified": req_progress.get("user_verified", False),
                "manuallyEdited": req_progress.get("manuallyEdited", False),
                "fieldConfidence": req_progress.get("fieldConfidence", {}),
                "fieldConfidences": req_progress.get("fieldConfidence", {}),
                "needsReview": req_progress.get("needsReview", {}),
                "aadhaarReviewReasons": (req_progress.get("docMeta") or {}).get("aadhaar_review_reasons", []),
            }
        )

    uploaded_count = sum(1 for s in status_list if s["uploaded"])
    total_count = len(status_list)
    user_id = session.get("user_id")
    docs_with_data = db.get_documents_with_data(session_id, service_name, variant, user_id=user_id)
    comparable_count = min(len(docs_with_data), total_count)

    # Ready counter: only uploaded items where required fields are verified or manually edited
    ready_count = sum(
        1 for s in status_list
        if s["uploaded"] and not s.get("skipped") and (
            s.get("manuallyEdited") or (s.get("docName") and not any(s.get("needsReview", {}).values()))
        )
    )
    ready_count = min(ready_count, total_count)

    return jsonify(
        {
            "service": service_name,
            "variant": variant,
            "sessionId": session_id,
            "requirements": status_list,
            "status": status_list,
            "uploadedCount": uploaded_count,
            "comparableCount": comparable_count,
            "readyCount": ready_count,
            "totalCount": total_count,
            "complete": uploaded_count == total_count,
            "servicePortal": get_service_portal(service_name),
        }
    )


def run_document_job(work, key, cleanup=lambda: None):
    if request.headers.get("Prefer") != "respond-async":
        try:
            return work()
        finally:
            cleanup()
    from ocr_jobs import jobs
    owner = session.get("user_id")
    def execute():
        with app.app_context():
            response = app.make_response(work())
            return response.get_json(), response.status_code
    try:
        job_id = jobs.submit(owner, key, execute, cleanup)
    except ValueError as exc:
        cleanup()
        return jsonify({"error": str(exc), "code": "OCR_QUEUE_FULL_OR_DUPLICATE"}), 409
    return jsonify({"job_id": job_id, "status": "accepted"}), 202


@app.route("/api/ocr/health", methods=["GET"])
def ocr_health():
    from paddle_engine import worker_status
    response = jsonify(worker_status())
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.route("/api/ocr/jobs/active", methods=["GET"])
@login_required
def active_ocr_job():
    from ocr_jobs import jobs
    key = tuple(request.args.get(k) for k in ("session_id", "service", "variant", "requirement"))
    if not all(key): return jsonify({"error": "Missing checklist context"}), 400
    response = jsonify({"job_id": jobs.find_active(session.get("user_id"), key)})
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.route("/api/ocr/jobs/<job_id>", methods=["GET", "DELETE"])
@limiter.limit("600 per minute", override_defaults=True)
@login_required
def ocr_job_status(job_id):
    from ocr_jobs import jobs
    owner = session.get("user_id")
    if request.method == "DELETE":
        cancelled = jobs.cancel(job_id, owner)
        if cancelled is None: return jsonify({"error": "OCR job not found"}), 404
        if not cancelled: return jsonify({"error": "This document is already being read."}), 409
    result = jobs.status(job_id, owner)
    if result is None: return jsonify({"error": "OCR job expired or the backend restarted. Please retry."}), 404
    response = jsonify(result)
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.route("/api/checklist/<service_name>/upload", methods=["POST"])
@login_required
def upload_checklist_file(service_name):
    """
    Expects multipart/form-data:
      required: session_id, requirement, chosen_option, file
      optional: variant (defaults 'adult')
    Performs atomic file upload with validation before replacing existing file.
    """
    session_id = request.form.get("session_id")
    variant = request.form.get("variant", "adult")
    requirement = request.form.get("requirement")
    chosen_option = request.form.get("chosen_option")
    file = request.files.get("file")

    if not session_id or not requirement or not chosen_option or not file:
        return jsonify(
            {"error": "session_id, requirement, chosen_option, and file are all required"}
        ), 400

    requirements = get_checklist(service_name, variant)
    if requirements is None:
        return jsonify(
            {"error": f"No checklist defined for '{service_name}' with variant '{variant}'"}
        ), 404

    matching_req = next((r for r in requirements if r["name"] == requirement), None)
    if matching_req is None:
        return jsonify({"error": f"'{requirement}' is not a valid requirement for '{service_name}'"}), 400

    if chosen_option not in matching_req["options"]:
        return jsonify(
            {"error": f"'{chosen_option}' is not an accepted option for '{requirement}'"}
        ), 400

    files = request.files.getlist("file")
    if len(files) > 1:
        if not re.search(r"aadh?aar|adhar", chosen_option, re.I):
            return jsonify({"error": "Multiple photos are supported for Aadhaar only."}), 400
        from aadhaar_upload import combine_aadhaar_photos
        try:
            file = combine_aadhaar_photos(files)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    orig_filename = secure_filename(file.filename) or "upload"
    ext = os.path.splitext(orig_filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return jsonify({"error": f"Unsupported file type '{ext}'."}), 400

    try:
        folder, final_path = get_safe_upload_path(session_id, service_name, variant, requirement, ext)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Write initially to a temporary file
    temp_filename = f"tmp_{uuid.uuid4().hex}{ext}"
    temp_path = os.path.join(folder, temp_filename)
    file.save(temp_path)

    # Validate file format, magic bytes, and size on the temp file
    is_valid, err_msg = validate_file(temp_path, file.filename)
    if not is_valid:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        return jsonify({"error": err_msg}), 400

    original_name = file.filename
    password = request.form.get("password")
    user_id = session.get("user_id")
    def finish_upload():
        # Run OCR on the validated file to extract identity fields
        ocr_fields = extract_fields(temp_path, original_name, chosen_option=chosen_option, cache_scope=(user_id, session_id),
                                    **({"password": password} if password else {}))
        sensitive_token=ocr_fields.pop("_identity_ciphertext",None)
        ocr_fields = sanitize(ocr_fields)
        if ocr_fields.get("error_code"):
            # Passwords never enter the DB, logs, or a response. Allow a fresh upload retry.
            os.remove(temp_path)
            return jsonify({"error": ocr_error_message(ocr_fields.get("error_code")),
                            "code": ocr_fields["error_code"],
                            "password_required": ocr_fields.get("password_required", False)}), 400
        # Keep the previous upload intact if OCR/password validation fails.
        try:
            os.replace(temp_path, final_path)
        except OSError:
            os.remove(temp_path)
            return jsonify({"error": "The existing document is in use. Close its viewer and retry."}), 409
        doc_name = ocr_fields.get("name")
        doc_dob = ocr_fields.get("dob")
        doc_address = ocr_fields.get("address")
        doc_number = ocr_fields.get("doc_number")
        raw_text = ocr_fields.get("raw_text")


        doc_meta_payload = {
            **(ocr_fields.get("doc_meta") or {}),
            "fieldConfidence": ocr_fields.get("fieldConfidence", {}),
            "fieldConfidences": ocr_fields.get("fieldConfidence", {}),
            "needsReview": ocr_fields.get("needsReview", {}),
            "quality": ocr_fields.get("quality"),
            "detectedType": ocr_fields.get("detectedType"),
            "documentTypeWarning": ocr_fields.get("documentTypeWarning"),
        }

        db.mark_uploaded(
            session_id, service_name, variant, requirement, chosen_option, final_path,
            doc_name=doc_name, doc_dob=doc_dob, doc_address=doc_address, doc_number=doc_number,
            raw_text=None, user_id=user_id, doc_meta=doc_meta_payload,
            doc_fields=ocr_fields.get("doc_fields"), ocr_version=ocr_fields.get("ocr_version"), sensitive_token=sensitive_token,
        )

        return jsonify(
            {
                "message": "Uploaded and scanned successfully",
                "requirement": requirement,
                "chosenOption": chosen_option,
                "filePath": final_path,
                "ocrExtracted": ocr_fields,
                "extracted": ocr_fields,
                "quality": ocr_fields.get("quality"),
                "documentTypeWarning": ocr_fields.get("documentTypeWarning"),
                "detectedType": ocr_fields.get("detectedType"),
            }
        )

    def cleanup_upload():
        if os.path.exists(temp_path):
            os.remove(temp_path)
    return run_document_job(finish_upload, (session_id, service_name, variant, requirement), cleanup_upload)


@app.route("/api/checklist/<service_name>/update-fields", methods=["POST"])
@login_required
def update_checklist_fields(service_name):
    """
    Lets the user correct OCR-extracted values (or fill them in manually).
    Marks record as manually_edited = True.
    Captures user correction into the continuous adaptation feedback store.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    session_id = data.get("session_id")
    variant = data.get("variant", "adult")
    requirement = data.get("requirement")

    if not session_id or not requirement:
        return jsonify({"error": "session_id and requirement are required"}), 400

    user_id = session.get("user_id")

    progress = db.get_progress(session_id, service_name, variant, user_id=user_id)
    if requirement not in progress:
        return jsonify({"error": "Document not found"}), 404
    fields = data.get("doc_fields", data.get("fields", {}))
    if not isinstance(fields, dict) or any(k not in FIELD_NAMES for k in fields):
        return jsonify({"error": "Unknown field or invalid fields object"}), 400
    # Legacy four-field editor remains supported. Only supplied keys are changed.
    fields = dict(fields)
    for name, aliases in {"name": ("doc_name", "docName"), "dob": ("doc_dob", "docDob"),
                          "address": ("doc_address", "docAddress"), "doc_number": ("doc_number", "docNumber")}.items():
        for alias in aliases:
            if alias in data:
                fields[name] = data[alias]
                break
    try:
        db.update_fields(session_id, service_name, variant, requirement, None, None, None,
                         manually_edited=True, user_id=user_id, doc_fields=fields)
    except (ValueError, TypeError):
        return jsonify({"error": "Field values must be text or null, at most 4000 characters"}), 400
    updated = db.get_progress(session_id, service_name, variant, user_id=user_id)[requirement]
    return jsonify({"message": "Fields updated successfully", "doc_fields": updated["doc_fields"],
                    "needs_review": updated["needs_review"], "user_verified": updated["user_verified"]})


@app.route("/api/feedback", methods=["POST"])
@session_or_login_required
@limiter.limit("30 per minute")
def submit_feedback():
    """
    Explicit endpoint for recording user corrections & feedback for continuous ML adaptation.
    """
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    from ml.feedback.feedback_store import record_feedback

    session_id = data.get("session_id") or get_request_session_id() or session.get("session_id")
    service_name = data.get("service") or data.get("service_name")
    variant = data.get("variant", "adult")
    requirement = data.get("requirement")
    doc_type = data.get("doc_type") or data.get("chosen_option") or requirement or "General"

    orig_fields = data.get("original") or data.get("original_fields") or {}
    corr_fields = data.get("corrected") or data.get("corrected_fields") or {}
    field_confidences = data.get("field_confidences") or {}

    user_id = session.get("user_id")
    file_path = None
    if session_id and service_name and requirement:
        file_path = db.get_file_path(session_id, service_name, variant, requirement, user_id=user_id)

    record = record_feedback(
        doc_type=doc_type,
        original_fields=orig_fields,
        corrected_fields=corr_fields,
        field_confidences=field_confidences,
        file_path=file_path,
        session_id=session_id,
        service_name=service_name,
        variant=variant,
        requirement=requirement,
    )

    return jsonify({
        "status": "ok",
        "feedback_id": record["feedback_id"] if record else None,
        "feature_samples_captured": record["feature_samples_count"] if record else 0,
    }), 200


@app.route("/api/feedback/stats", methods=["GET"])
@session_or_login_required
def feedback_stats():
    """Returns summary counts of captured user feedback."""
    from ml.feedback.feedback_store import get_feedback_stats
    stats = get_feedback_stats()
    return jsonify(stats), 200


@app.route("/api/checklist/<service_name>/skip", methods=["POST"])
@session_or_login_required
def skip_checklist_requirement(service_name):
    """Marks a skippable requirement as Not Applicable or restores it."""
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id") or request.args.get("session_id")
    variant = data.get("variant", "adult")
    requirement = data.get("requirement")
    skipped = data.get("skipped", True)

    if not session_id or not requirement:
        return jsonify({"error": "session_id and requirement are required"}), 400

    db.skip_requirement(session_id, service_name, variant, requirement, skipped=skipped)
    return jsonify({
        "message": f"Requirement '{requirement}' {'skipped' if skipped else 'restored'}",
        "requirement": requirement,
        "skipped": skipped,
    }), 200


@app.route("/api/checklist/<service_name>/rescan", methods=["POST"])
@login_required
def rescan_checklist_file(service_name):
    """
    Explicitly re-scans the uploaded file on disk with OCR, resetting manual edits.
    """
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id") or request.args.get("session_id")
    variant = data.get("variant", "adult")
    requirement = data.get("requirement")

    if not session_id or not requirement:
        return jsonify({"error": "session_id and requirement are required"}), 400

    user_id = session.get("user_id")
    file_path = db.get_file_path(session_id, service_name, variant, requirement, user_id=user_id)
    if not file_path:
        return jsonify({"error": "No uploaded file found for this requirement"}), 404

    base_dir = os.path.realpath(UPLOAD_FOLDER)
    real_path = os.path.realpath(os.path.abspath(file_path))
    try:
        file_common = os.path.commonpath([base_dir, real_path])
    except ValueError:
        return jsonify({"error": "File not found or access denied"}), 404
    if file_common != base_dir or real_path == base_dir or not os.path.exists(real_path):
        return jsonify({"error": "Uploaded file not found on disk or access denied"}), 404

    user_id = session.get("user_id")
    progress = db.get_progress(session_id, service_name, variant, user_id=user_id)
    chosen_opt = (progress.get(requirement) or {}).get("chosenOption")

    def finish_rescan():
        fresh = extract_fields(real_path, os.path.basename(real_path), chosen_option=chosen_opt,
                               **({"password": data.get("password")} if data.get("password") else {}))
        sensitive_token=fresh.pop("_identity_ciphertext",None)
        fresh = sanitize(fresh)
        if fresh.get("error_code"):
            return jsonify({"error": ocr_error_message(fresh.get("error_code")),
                            "code": fresh["error_code"], "password_required": fresh.get("password_required", False)}), 400
        fresh_meta = {
            **(fresh.get("doc_meta") or {}),
            "fieldConfidence": fresh.get("fieldConfidence", {}),
            "fieldConfidences": fresh.get("fieldConfidence", {}),
            "needsReview": fresh.get("needsReview", {}),
            "quality": fresh.get("quality"),
            "detectedType": fresh.get("detectedType"),
            "documentTypeWarning": fresh.get("documentTypeWarning"),
        }
        db.update_fields(
            session_id, service_name, variant, requirement,
            fresh.get("name"), fresh.get("dob"), fresh.get("address"), fresh.get("doc_number"),
            raw_text=None, manually_edited=False, user_id=user_id, doc_meta=fresh_meta,
            doc_fields=fresh.get("doc_fields"), ocr_version=fresh.get("ocr_version"), sensitive_token=sensitive_token
        )
        return jsonify({
            "message": "Document rescanned successfully",
            "requirement": requirement,
            "extracted": fresh
        }), 200
    return run_document_job(finish_rescan, (session_id, service_name, variant, requirement))


@app.route("/api/checklist/<service_name>/file", methods=["GET"])
@login_required
def get_checklist_file(service_name):
    """Serves back the uploaded file with magic-byte MIME detection and strict security headers."""
    session_id = request.args.get("session_id")
    variant = request.args.get("variant", "adult")
    requirement = request.args.get("requirement")
    is_download = request.args.get("download") in ("1", "true")

    if not requirement:
        return jsonify({"error": "requirement query parameter is required"}), 400

    user_id = session.get("user_id")
    file_path = db.get_file_path(session_id, service_name, variant, requirement, user_id=user_id)
    if not file_path:
        return jsonify({"error": "No file found for this requirement"}), 404

    base_dir = os.path.realpath(UPLOAD_FOLDER)
    real_path = os.path.realpath(os.path.abspath(file_path))
    try:
        file_common = os.path.commonpath([base_dir, real_path])
    except ValueError:
        return jsonify({"error": "File not found or access denied"}), 404
    if file_common != base_dir or real_path == base_dir or not os.path.exists(real_path):
        return jsonify({"error": "File not found or access denied"}), 404

    mime_type = detect_mime_from_bytes(real_path)
    safe_name = secure_filename(os.path.basename(real_path)) or "document"
    disposition = "attachment" if is_download else "inline"

    resp = send_file(
        real_path,
        mimetype=mime_type,
        as_attachment=is_download,
        download_name=safe_name,
    )
    resp.headers["Content-Disposition"] = f'{disposition}; filename="{safe_name}"'
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Cache-Control"] = "private, no-store, max-age=0"
    resp.headers["Content-Security-Policy"] = "sandbox"
    return resp


@app.route("/api/checklist/<service_name>/mismatches", methods=["GET"])
@login_required
def get_checklist_mismatches(service_name):
    """
    Runs the mismatch engine on all uploaded documents for this session.
    Returns full field-by-field comparisons, summary statistics, and issues with decision states.
    """
    session_id = request.args.get("session_id")
    variant = request.args.get("variant", "adult")

    if not session_id:
        return jsonify({"error": "session_id query parameter is required"}), 400

    user_id = session.get("user_id")
    documents = db.get_documents_with_data(session_id, service_name, variant, user_id=user_id)
    decisions = db.get_decisions(session_id, service_name, variant, user_id=user_id)

    if not documents:
        satisfied_info = []
        for doc_k, doc_val in documents.items():
            reqs = doc_val.get("requirements", [])
            if len(reqs) > 1:
                req_str = ", ".join(reqs)
                satisfied_info.append(f"{doc_k} (satisfies: {req_str})")

        if satisfied_info:
            msg = (
                f"You have uploaded {' and '.join(satisfied_info)}. "
                "A single document cannot be cross-compared against itself. "
                "Please upload at least one other distinct document (such as PAN Card or 10th Marksheet) to cross-check records."
            )
        else:
            msg = "Upload at least 2 distinct documents to compare their details."

        return jsonify(
            {
                "documentsWithData": list(documents.keys()),
                "uploadedCount": len(documents),
                "enoughData": False,
                "clean": True,
                "issues": [],
                "comparisons": [],
                "summary": {
                    "totalComparisons": 0,
                    "matches": 0,
                    "possibleMismatches": 0,
                    "mismatches": 0,
                    "unableToCompare": 0,
                },
                "pendingCount": 0,
                "message": msg,
            }
        )

    result = compare_documents(documents, service_name, variant)

    issues_with_decisions = []
    pending_count = 0
    for issue in result["issues"]:
        key = build_issue_key(issue["field"], issue["documents"][0], issue["documents"][1])
        decision = decisions.get(key)
        if decision is None:
            pending_count += 1
        issues_with_decisions.append({**issue, "issueKey": key, "decision": decision})

    return jsonify(
        {
            "documentsWithData": list(documents.keys()),
            "uploadedCount": len(documents),
            "enoughData": result.get("enoughData", True),
            "clean": len(issues_with_decisions) == 0,
            "issues": issues_with_decisions,
            "comparisons": result.get("comparisons", []),
            "summary": result.get("summary", {}),
            "pendingCount": pending_count,
            "readableDocuments": result.get("readableDocuments", []),
            "unreadableDocuments": result.get("unreadableDocuments", []),
            "verificationStatus": result.get("verificationStatus", "partially_verified"),
            "verifiedFieldCount": result.get("verifiedFieldCount", 0),
            "unverifiedFieldCount": result.get("unverifiedFieldCount", 0),
            "message": result.get("message"),
            "servicePortal": get_service_portal(service_name),
        }
    )


@app.route("/api/checklist/<service_name>/mismatch-decision", methods=["POST"])
@login_required
def post_mismatch_decision(service_name):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    session_id = data.get("session_id")
    variant = data.get("variant", "adult")
    field = data.get("field")
    documents = data.get("documents")
    decision = data.get("decision")

    if not session_id or not field or not documents or len(documents) != 2 or decision not in ("confirmed", "ignored"):
        return jsonify(
            {"error": "session_id, field, documents (list of 2), and decision ('confirmed'/'ignored') are required"}
        ), 400

    key = build_issue_key(field, documents[0], documents[1])
    db.save_decision(session_id, service_name, variant, key, decision, user_id=session.get("user_id"))

    return jsonify({"message": "Decision saved", "issueKey": key, "decision": decision})


@app.route("/api/correction-guidance-pair", methods=["GET"])
def correction_guidance_pair():
    doc_a = request.args.get("doc_a")
    doc_b = request.args.get("doc_b")
    field = request.args.get("field")

    if not doc_a or not doc_b or not field:
        return jsonify({"error": "doc_a, doc_b, and field query parameters are all required"}), 400

    return jsonify([get_guidance(doc_a, field), get_guidance(doc_b, field)])


@app.route("/api/check-mismatches", methods=["POST"])
@session_or_login_required
def check_mismatches_route():
    data = request.get_json(silent=True)
    if not data or "documents" not in data:
        return jsonify({"error": "Request body must include a 'documents' object"}), 400

    documents = data["documents"]
    if not isinstance(documents, dict) or len(documents) < 2:
        return jsonify({"error": "Provide at least 2 documents to compare"}), 400

    result = compare_documents(documents, data.get("service"), data.get("variant", "adult"))
    return jsonify(result)


@app.route("/api/translate", methods=["POST"])
@limiter.limit("30 per minute")
@login_required
def translate_text():
    data = request.get_json(silent=True)
    if not data or "text" not in data or "target_language" not in data:
        return jsonify({"error": "text and target_language are required"}), 400

    target_language = data.get("target_language")
    if target_language not in {"en", "hi", "mr"}:
        return jsonify({"error": f"Unsupported target language '{target_language}'. Supported: en, hi, mr"}), 400

    text = data.get("text") or ""
    if len(text) > 2000:
        return jsonify({"error": "Text length exceeds maximum allowed limit of 2000 characters."}), 400

    if not GOOGLE_TRANSLATION_API_KEY:
        return jsonify({"error": "Translation API key not configured"}), 500

    try:
        url = f"https://translation.googleapis.com/language/translate/v2?key={GOOGLE_TRANSLATION_API_KEY}"
        payload = {"q": text, "target": target_language}
        response = requests.post(url, json=payload, timeout=10)
        response_data = response.json()

        if response.status_code == 200:
            translated_text = response_data["data"]["translations"][0]["translatedText"]
            return jsonify({"translatedText": translated_text})
        else:
            return jsonify({"error": response_data.get("error", {}).get("message", "Translation failed")}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/register", methods=["POST"])
@limiter.limit("10 per minute")
def register():
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    mobile_number = (data.get("mobile_number") or "").strip()
    password = data.get("password") or ""
    preferred_language = data.get("preferred_language", "en")

    if not all([full_name, email, mobile_number, password]):
        return jsonify({"error": "Missing required fields"}), 400

    if not EMAIL_REGEX.match(email):
        return jsonify({"error": "Invalid email address format."}), 400

    if not MOBILE_REGEX.match(mobile_number):
        return jsonify({"error": "Invalid Indian mobile number. Must be 10 digits starting with 6-9."}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters long."}), 400

    if db.get_user_by_email(email):
        return jsonify({"error": "User with this email already exists"}), 409

    password_hash = generate_password_hash(password)
    user = db.create_user(full_name, email, mobile_number, password_hash, preferred_language)
    if not user:
        return jsonify({"error": "User with this email already exists"}), 409

    session["user_id"] = user["id"]

    # Migrate any unauthenticated session progress to this newly created user
    req_session_id = get_request_session_id() or session.get("session_id")
    if req_session_id:
        db.link_session_to_user(req_session_id, user["id"])

    return jsonify({"message": "User registered successfully", "user": user}), 201


@app.route("/api/auth/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    user = db.get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    session["user_id"] = user["id"]

    # Migrate any anonymous session progress to this user
    req_session_id = get_request_session_id() or session.get("session_id")
    if req_session_id:
        db.link_session_to_user(req_session_id, user["id"])

    user_data = {
        "id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "preferred_language": user["preferred_language"],
    }
    return jsonify({"message": "Login successful", "user": user_data}), 200


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    from ocr_result_cache import clear_owner
    clear_owner(session.get("user_id"))
    session.clear()
    return jsonify({"message": "Logout successful"}), 200


@app.route("/api/auth/me", methods=["GET"])
def get_me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"user": {
        "id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "preferred_language": user["preferred_language"]
    }}), 200


@app.route("/api/session/data", methods=["DELETE"])
@session_or_login_required
def delete_session_data_route():
    """Wipes all uploaded files and database records for the caller's session."""
    session_id = get_request_session_id() or session.get("session_id")
    user_id = session.get("user_id")
    if not session_id and not user_id:
        return jsonify({"error": "session_id is required"}), 400
    from ocr_result_cache import clear_owner
    clear_owner(user_id)
    db.delete_session_data(session_id, user_id=user_id)
    return jsonify({"message": "Session data and files wiped successfully"}), 200


@app.route("/api/checklist/<service_name>/diagnostics", methods=["GET"])
@session_or_login_required
def get_checklist_diagnostics(service_name):
    """
    Development-only diagnostic route exposing raw OCR text vs parsed fields.
    Allowed ONLY if DIAGNOSTICS_ENABLED == 'true' AND not in production.
    Client-controlled bypasses like X-Dev-Mode or ?dev=true are strictly ignored.
    """
    is_prod = os.getenv("FLASK_ENV") == "production" or os.getenv("ENV") == "production"
    admin_token_env = os.getenv("ADMIN_TOKEN")
    req_token = request.headers.get("X-Admin-Token") or request.args.get("admin_token")
    has_valid_token = bool(admin_token_env and req_token and hmac.compare_digest(req_token.strip(), admin_token_env.strip()))
    user_id = session.get("user_id")
    is_admin = False
    if user_id:
        user = db.get_user_by_id(user_id) if hasattr(db, "get_user_by_id") else None
        if user and (user.get("is_admin") or user.get("role") == "admin"):
            is_admin = True
    if is_prod or not (has_valid_token or is_admin):
        return jsonify({"error": "Diagnostic view is restricted to development mode and disabled in production."}), 403

    session_id = get_request_session_id()
    variant = request.args.get("variant", "adult")

    if not session_id:
        return jsonify({"error": "session_id query parameter is required"}), 400

    docs = db.get_document_diagnostics(session_id, service_name, variant)
    return jsonify({
        "isDev": True,
        "service": service_name,
        "variant": variant,
        "sessionId": session_id,
        "documents": docs,
    }), 200



@app.route("/api/documents", methods=["GET"])
@login_required
def get_user_documents_route():
    """Returns list of all uploaded documents for the logged-in user across all services."""
    user_id = session.get("user_id")
    docs = db.get_user_documents(user_id)
    result = []
    base_dir = os.path.realpath(UPLOAD_FOLDER)
    for doc in docs:
        fpath = doc.get("file_path")
        file_name = os.path.basename(fpath) if fpath else None
        file_size_bytes = 0
        mime_type = "application/octet-stream"
        if fpath and fpath != "SKIPPED":
            real = os.path.realpath(os.path.abspath(fpath))
            if real.startswith(base_dir) and os.path.exists(real):
                file_size_bytes = os.path.getsize(real)
                mime_type = detect_mime_from_bytes(real)

        result.append({
            "id": doc["id"],
            "service": doc["service"],
            "variant": doc["variant"],
            "requirement": doc["requirement"],
            "chosen_option": doc["chosen_option"],
            "file_name": file_name,
            "file_size_bytes": file_size_bytes,
            "mime_type": mime_type,
            "uploaded_at": doc["uploaded_at"].isoformat() if hasattr(doc.get("uploaded_at"), "isoformat") else str(doc.get("uploaded_at")) if doc.get("uploaded_at") else None,
            "has_data": bool(doc.get("doc_name") or doc.get("doc_dob") or doc.get("doc_address") or doc.get("doc_number")),
            "doc_name": doc.get("doc_name"),
            "doc_dob": doc.get("doc_dob"),
            "doc_address": doc.get("doc_address"),
            "doc_number": doc.get("doc_number"),
            "doc_fields": json_object(doc.get("doc_fields")),
            "ocr_version": doc.get("ocr_version"),
            "needs_review": bool(doc.get("needs_review", True)),
            "user_verified": bool(doc.get("user_verified", False)),
        })
    return jsonify({"documents": result}), 200


@app.route("/api/documents/<int:doc_id>", methods=["DELETE"])
@login_required
def delete_user_document_route(doc_id):
    """Deletes a single document owned by the logged-in user."""
    user_id = session.get("user_id")
    from ocr_result_cache import clear_owner
    clear_owner(user_id)
    fpath = db.delete_user_document(user_id, doc_id)
    if not fpath:
        return jsonify({"error": "Document not found or access denied"}), 404

    if fpath != "SKIPPED":
        base_dir = os.path.realpath(UPLOAD_FOLDER)
        real = os.path.realpath(os.path.abspath(fpath))
        if real.startswith(base_dir) and os.path.exists(real):
            try:
                os.remove(real)
            except OSError:
                pass

    return jsonify({"message": "Document deleted successfully", "id": doc_id}), 200


@app.route("/api/documents", methods=["DELETE"])
@login_required
def delete_all_user_documents_route():
    """Deletes all documents owned by the logged-in user."""
    user_id = session.get("user_id")
    from ocr_result_cache import clear_owner
    clear_owner(user_id)
    file_paths = db.delete_all_user_documents(user_id)
    base_dir = os.path.realpath(UPLOAD_FOLDER)
    for fpath in file_paths:
        if fpath and fpath != "SKIPPED":
            real = os.path.realpath(os.path.abspath(fpath))
            if real.startswith(base_dir) and os.path.exists(real):
                try:
                    os.remove(real)
                except OSError:
                    pass

    return jsonify({"message": "All documents deleted successfully"}), 200


@app.route("/api/checklist/<service_name>/correction-steps", methods=["GET"])
@login_required
def get_correction_steps_route(service_name):
    """Retrieves completion state for mismatch guidance steps."""
    variant = request.args.get("variant", "adult")
    user_id = session.get("user_id")
    steps = db.get_correction_steps(user_id, service_name, variant)
    return jsonify({"service": service_name, "variant": variant, "steps": steps}), 200


@app.route("/api/checklist/<service_name>/correction-steps", methods=["POST"])
@login_required
def post_correction_step_route(service_name):
    """Saves completion state for a mismatch guidance step checkbox."""
    data = request.get_json(silent=True) or {}
    user_id = session.get("user_id")
    variant = data.get("variant", "adult")
    issue_key = data.get("issue_key")
    step_index = data.get("step_index")
    completed = data.get("completed", True)

    if not issue_key or step_index is None:
        return jsonify({"error": "issue_key and step_index are required"}), 400

    db.save_correction_step(user_id, service_name, variant, issue_key, int(step_index), completed)
    return jsonify({
        "message": "Correction step updated",
        "service": service_name,
        "variant": variant,
        "issueKey": issue_key,
        "stepIndex": int(step_index),
        "completed": bool(completed)
    }), 200


@app.route('/api/checklist/<service_name>/reviewed-ids', methods=['POST'])
@login_required
def get_reviewed_identity_numbers(service_name):
    from identity_store import reviewed_ids
    from cryptography.fernet import InvalidToken
    data=request.get_json(silent=True) or {}
    if data.get('confirmed') is not True:return jsonify({'error':'Confirm that you want to use these IDs for autofill.'}),400
    origin=request.headers.get('Origin')
    allowed={request.host_url.rstrip('/'),'http://localhost:5173','http://127.0.0.1:5173',os.getenv('FRONTEND_ORIGIN','')}
    if origin and origin not in allowed:return jsonify({'error':'Untrusted origin'}),403
    try:
        with db.get_db_connection() as conn:documents=reviewed_ids(conn,session['user_id'],service_name,data.get('variant','adult'))
    except (InvalidToken,RuntimeError,ValueError):
        return jsonify({'error':'Stored IDs could not be unlocked. Check the server encryption key; do not replace it.'}),503
    response=jsonify({'documents':documents})
    response.headers['Cache-Control']='no-store, private'
    response.headers['Pragma']='no-cache'
    return response


@app.route("/api/report/<service_name>", methods=["GET"])
def get_verification_report(service_name):
    """Generates printable verification summary report and readiness score."""
    variant = request.args.get("variant", "adult")
    session_id = request.args.get("session_id")
    user_id = session.get("user_id")

    requirements = get_checklist(service_name, variant)
    if requirements is None:
        return jsonify({"error": f"No checklist defined for '{service_name}'"}), 404

    progress = db.get_progress(session_id, service_name, variant, user_id=user_id) if (user_id or session_id) else {}
    docs_data = db.get_documents_with_data(session_id, service_name, variant, user_id=user_id) if (user_id or session_id) else {}
    decisions = db.get_decisions(session_id, service_name, variant, user_id=user_id) if (user_id or session_id) else {}
    correction_steps = db.get_correction_steps(user_id, service_name, variant) if user_id else {}

    # Calculate mismatch results
    mismatch_result = compare_documents(docs_data, service_name, variant) if docs_data else {
        "issues": [], "comparisons": [], "enoughData": False, "clean": True, "verificationStatus": "insufficient_data"
    }

    issues_with_decisions = []
    for issue in mismatch_result.get("issues", []):
        key = build_issue_key(issue["field"], issue["documents"][0], issue["documents"][1])
        guidance = [get_guidance(issue["documents"][0], issue["field"]), get_guidance(issue["documents"][1], issue["field"])]
        completed_step_indices = correction_steps.get(key, [])
        issues_with_decisions.append({
            **issue,
            "issueKey": key,
            "decision": decisions.get(key),
            "guidance": guidance,
            "completedSteps": completed_step_indices
        })

    doc_statuses = []
    uploaded_count = 0
    total_count = len(requirements)
    has_unresolved_mismatches = any(i["decision"] != "confirmed" for i in issues_with_decisions)

    for req in requirements:
        p = progress.get(req["name"], {})
        is_uploaded = bool(p.get("uploaded"))
        is_skipped = bool(p.get("skipped"))
        if is_uploaded:
            uploaded_count += 1

        status = "Missing"
        if is_skipped:
            status = "Skipped"
        elif is_uploaded:
            doc_opt = p.get("chosenOption") or ""
            has_issue = any(doc_opt in i.get("documents", []) for i in issues_with_decisions if i["decision"] != "confirmed")
            status = "Mismatch" if has_issue else "Verified"

        doc_statuses.append({
            "requirement": req["name"],
            "options": req["options"],
            "chosenOption": p.get("chosenOption"),
            "uploaded": is_uploaded,
            "skipped": is_skipped,
            "status": status,
            "docName": p.get("docName"),
            "docDob": p.get("docDob"),
            "docAddress": p.get("docAddress"),
            "docNumber": p.get("docNumber"),
            "doc_fields": p.get("doc_fields", {}),
        })

    if total_count == 0:
        readiness_score = 100
    else:
        req_score = (uploaded_count / total_count) * 60
        clean_score = 40 if (len(issues_with_decisions) == 0 or not has_unresolved_mismatches) else max(0, 40 - len(issues_with_decisions) * 15)
        readiness_score = int(min(100, req_score + clean_score))

    if uploaded_count == 0:
        readiness_score = 0
        readiness_label = "Not Started"
    elif readiness_score >= 90 and not has_unresolved_mismatches and uploaded_count == total_count:
        readiness_label = "100% Ready"
        readiness_score = 100
    elif has_unresolved_mismatches or uploaded_count < total_count:
        readiness_label = f"{readiness_score}% Needs Attention"
    else:
        readiness_label = f"{readiness_score}% Ready"

    if request.args.get("finalize") in ("1", "true") or request.args.get("delete_files") in ("1", "true"):
        from ocr_result_cache import clear_owner
        clear_owner(user_id)
        db.delete_verified_files(session_id, service_name, variant, user_id=user_id)

    return jsonify({
        "service": service_name,
        "variant": variant,
        "readinessScore": readiness_score,
        "readinessLabel": readiness_label,
        "complete": uploaded_count == total_count,
        "uploadedCount": uploaded_count,
        "totalCount": total_count,
        "documents": doc_statuses,
        "issues": issues_with_decisions,
        "comparisons": mismatch_result.get("comparisons", []),
        "servicePortal": get_service_portal(service_name),
    }), 200


@app.route("/api/checklist/<service_name>/purge-files", methods=["POST"])
@session_or_login_required
def purge_checklist_files(service_name):
    """Deletes uploaded files on disk after verification has completed."""
    session_id = get_request_session_id() or session.get("session_id")
    user_id = session.get("user_id")
    variant = request.args.get("variant", "adult")
    from ocr_result_cache import clear_owner
    clear_owner(user_id)
    db.delete_verified_files(session_id, service_name, variant, user_id=user_id)
    return jsonify({"message": "Uploaded files safely purged after verification."}), 200


@app.route("/api/chat", methods=["POST"])
@limiter.limit("20 per minute")
def chat():
    """Grounded Chatbot endpoint with LLM provider support & rule-based statutory fallback."""
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400

    service = data.get("service")
    variant = data.get("variant", "adult")
    language = data.get("language", "en")
    history = data.get("history", [])

    user_id = session.get("user_id")
    session_id = get_request_session_id() or session.get("session_id")
    mismatches_summary = None
    if service and (user_id or session_id):
        docs = db.get_documents_with_data(session_id, service, variant, user_id=user_id)
        if len(docs) >= 2:
            res = compare_documents(docs, service, variant)
            if res.get("issues"):
                mismatches_summary = [f"{i['field']} differs between {i['documents'][0]} and {i['documents'][1]}" for i in res["issues"]]

    response_data = handle_chat_query(
        message,
        ui_language=language,
        service_name=service,
        variant=variant,
        user_mismatches_summary=mismatches_summary,
        history=history,
    )
    return jsonify(response_data), 200

if os.getenv("OCR_PRELOAD") == "1" and os.getenv("OCR_ENGINE", "paddleocr").lower() == "paddleocr":
    from paddle_engine import start_warmup
    start_warmup()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
