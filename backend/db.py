import os
import re
import hmac
import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=env_path)
DATABASE_URL = os.getenv("DATABASE_URL")

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(minconn=1, maxconn=20, dsn=DATABASE_URL)
    return _pool

@contextmanager
def get_db_connection():
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)

def get_connection():
    """Legacy helper returning a direct connection for standalone scripts."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn

def hash_doc_number(doc_num_str):
    """Calculates HMAC-SHA256 hash using SECRET_KEY for sensitive document numbers."""
    if not doc_num_str:
        return None
    secret = (os.getenv("SECRET_KEY") or "sahayak-default-secret-salt").encode("utf-8")
    normalized = re.sub(r"[\s\-_:]+", "", str(doc_num_str)).upper()
    return hmac.new(secret, normalized.encode("utf-8"), hashlib.sha256).hexdigest()

def mask_doc_number(doc_num_str):
    """Masks Aadhaar numbers so only the last 4 digits are visible."""
    if not doc_num_str:
        return None
    s = str(doc_num_str).strip()
    m = re.search(r"\b(\d{4})\s*(\d{4})\s*(\d{4})\b", s)
    if m:
        last4 = m.group(3)
        return s.replace(m.group(0), f"XXXX XXXX {last4}")
    m12 = re.search(r"\b\d{12}\b", s)
    if m12:
        val = m12.group(0)
        return s.replace(val, f"XXXX XXXX {val[-4:]}")
    return s

def init_db():
    with get_db_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    mobile_number TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    preferred_language TEXT DEFAULT 'en',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS checklist_progress (
                    session_id TEXT NOT NULL,
                    service TEXT NOT NULL,
                    variant TEXT NOT NULL,
                    requirement TEXT NOT NULL,
                    chosen_option TEXT,
                    uploaded INTEGER NOT NULL DEFAULT 0,
                    file_path TEXT,
                    uploaded_at TEXT,
                    doc_name TEXT,
                    doc_dob TEXT,
                    doc_address TEXT,
                    doc_number TEXT,
                    PRIMARY KEY (session_id, service, variant, requirement)
                )
                """
            )
            cur.execute("ALTER TABLE checklist_progress ADD COLUMN IF NOT EXISTS doc_number TEXT")
            cur.execute("ALTER TABLE checklist_progress ADD COLUMN IF NOT EXISTS raw_text TEXT")
            cur.execute("ALTER TABLE checklist_progress ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
            cur.execute("ALTER TABLE checklist_progress ADD COLUMN IF NOT EXISTS manually_edited BOOLEAN DEFAULT FALSE")
            cur.execute("ALTER TABLE checklist_progress ADD COLUMN IF NOT EXISTS doc_meta TEXT")
            cur.execute("ALTER TABLE checklist_progress ADD COLUMN IF NOT EXISTS doc_number_hash TEXT")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_checklist_progress_user_id ON checklist_progress(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_checklist_progress_session_id ON checklist_progress(session_id)")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS mismatch_decisions (
                    session_id TEXT NOT NULL,
                    service TEXT NOT NULL,
                    variant TEXT NOT NULL,
                    issue_key TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    decided_at TEXT NOT NULL,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    PRIMARY KEY (session_id, service, variant, issue_key)
                )
                """
            )
            cur.execute("ALTER TABLE mismatch_decisions ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_mismatch_decisions_session_id ON mismatch_decisions(session_id)")
            cur.execute("ALTER TABLE checklist_progress ADD COLUMN IF NOT EXISTS id SERIAL")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS correction_steps (
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    service TEXT NOT NULL,
                    variant TEXT NOT NULL,
                    issue_key TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    completed BOOLEAN DEFAULT FALSE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, service, variant, issue_key, step_index)
                )
                """
            )
            # Data minimisation: purge raw_text and ensure doc_number masking
            cur.execute("UPDATE checklist_progress SET raw_text = NULL WHERE raw_text IS NOT NULL")
            cur.execute("SELECT session_id, service, variant, requirement, doc_number FROM checklist_progress WHERE doc_number IS NOT NULL")
            for r in cur.fetchall():
                if r[4]:
                    masked = mask_doc_number(r[4])
                    if masked != r[4]:
                        cur.execute(
                            "UPDATE checklist_progress SET doc_number = %s WHERE session_id = %s AND service = %s AND variant = %s AND requirement = %s",
                            (masked, r[0], r[1], r[2], r[3])
                        )

def get_progress(session_id, service, variant, user_id=None):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if user_id:
                cur.execute(
                    "SELECT id, requirement, chosen_option, uploaded, file_path, uploaded_at, "
                    "doc_name, doc_dob, doc_address, doc_number, raw_text, manually_edited, doc_meta "
                    "FROM checklist_progress "
                    "WHERE user_id = %s AND service = %s AND variant = %s",
                    (user_id, service, variant),
                )
            else:
                cur.execute(
                    "SELECT id, requirement, chosen_option, uploaded, file_path, uploaded_at, "
                    "doc_name, doc_dob, doc_address, doc_number, raw_text, manually_edited, doc_meta "
                    "FROM checklist_progress "
                    "WHERE session_id = %s AND service = %s AND variant = %s",
                    (session_id, service, variant),
                )
            rows = cur.fetchall()

    res = {}
    for row in rows:
        meta = {}
        if row.get("doc_meta"):
            try:
                meta = json.loads(row["doc_meta"]) if isinstance(row["doc_meta"], str) else row["doc_meta"]
            except Exception:
                pass
        res[row["requirement"]] = {
            "id": row.get("id"),
            "chosenOption": row["chosen_option"],
            "uploaded": bool(row["uploaded"]),
            "filePath": row["file_path"],
            "uploadedAt": row["uploaded_at"],
            "docName": row["doc_name"],
            "docDob": row["doc_dob"],
            "docAddress": row["doc_address"],
            "docNumber": row["doc_number"],
            "rawText": row.get("raw_text"),
            "manuallyEdited": bool(row.get("manually_edited")),
            "skipped": bool(meta.get("skipped") or row.get("file_path") == "SKIPPED"),
        }
    return res

def mark_uploaded(session_id, service, variant, requirement, chosen_option, file_path,
                   doc_name=None, doc_dob=None, doc_address=None, doc_number=None, raw_text=None,
                   user_id=None, doc_meta=None):
    raw_doc_num_str = None
    if isinstance(doc_number, dict):
        raw_doc_num_str = f"{doc_number.get('type')}: {doc_number.get('number')}"
    elif doc_number:
        raw_doc_num_str = str(doc_number)

    doc_number_hash = hash_doc_number(raw_doc_num_str)
    masked_doc_num_str = mask_doc_number(raw_doc_num_str)

    # Data minimisation: raw OCR text is never stored in DB
    stored_raw_text = None
    doc_meta_str = json.dumps(doc_meta) if isinstance(doc_meta, dict) else (doc_meta or None)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO checklist_progress
                    (session_id, service, variant, requirement, chosen_option, uploaded,
                     file_path, uploaded_at, doc_name, doc_dob, doc_address, doc_number,
                     raw_text, user_id, doc_meta, doc_number_hash, manually_edited)
                VALUES (%s, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
                ON CONFLICT(session_id, service, variant, requirement)
                DO UPDATE SET
                    chosen_option = excluded.chosen_option,
                    uploaded = 1,
                    file_path = excluded.file_path,
                    uploaded_at = excluded.uploaded_at,
                    doc_name = excluded.doc_name,
                    doc_dob = excluded.doc_dob,
                    doc_address = excluded.doc_address,
                    doc_number = excluded.doc_number,
                    raw_text = excluded.raw_text,
                    user_id = COALESCE(excluded.user_id, checklist_progress.user_id),
                    doc_meta = excluded.doc_meta,
                    doc_number_hash = excluded.doc_number_hash,
                    manually_edited = FALSE
                """,
                (session_id, service, variant, requirement, chosen_option, file_path,
                 datetime.now().isoformat(), doc_name, doc_dob, doc_address, masked_doc_num_str,
                 stored_raw_text, user_id, doc_meta_str, doc_number_hash),
            )
        conn.commit()

NON_IDENTITY_REQUIREMENTS = {
    "photograph", "photo", "signature", "thumb impression", "specimen signature", "declaration", "not applicable"
}

def is_identity_document(requirement, chosen_option=""):
    """
    Returns True if this requirement represents an identity/address/age document
    whose extracted text fields should be compared against other documents.
    Excludes auxiliary non-identity records like passport photographs and signatures.
    """
    combined = f"{requirement or ''} {chosen_option or ''}".lower()
    return not any(tok in combined for tok in NON_IDENTITY_REQUIREMENTS)

def get_documents_with_data(session_id, service, variant, user_id=None):
    """
    Returns {doc_key: {name, dob, address, doc_number, doc_number_hash, requirement, chosen_option}}
    for every uploaded identity document for this session.
    Automatically filters out non-identity items (e.g. photos/signatures).
    Uses persisted database fields without re-running OCR on read.
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if user_id:
                cur.execute(
                    "SELECT id, requirement, chosen_option, doc_name, doc_dob, doc_address, doc_number, "
                    "file_path, raw_text, doc_meta, doc_number_hash, manually_edited "
                    "FROM checklist_progress "
                    "WHERE user_id = %s AND service = %s AND variant = %s AND uploaded = 1",
                    (user_id, service, variant),
                )
            else:
                cur.execute(
                    "SELECT id, requirement, chosen_option, doc_name, doc_dob, doc_address, doc_number, "
                    "file_path, raw_text, doc_meta, doc_number_hash, manually_edited "
                    "FROM checklist_progress "
                    "WHERE session_id = %s AND service = %s AND variant = %s AND uploaded = 1",
                    (session_id, service, variant),
                )
            rows = cur.fetchall()

    documents = {}

    for row in rows:
        req = row.get("requirement") or ""
        chosen = row.get("chosen_option") or ""
        if row.get("file_path") == "SKIPPED" or "not applicable" in (chosen or "").lower():
            continue

        if not is_identity_document(req, chosen):
            continue

        doc_name = row.get("doc_name")
        doc_dob = row.get("doc_dob")
        doc_address = row.get("doc_address")
        doc_number = row.get("doc_number")
        doc_number_hash = row.get("doc_number_hash")
        fpath = row.get("file_path")
        row_raw_text = row.get("raw_text") or ""
        doc_meta = row.get("doc_meta")
        if isinstance(doc_meta, str):
            try:
                doc_meta = json.loads(doc_meta)
            except Exception:
                pass

        # Group and consolidate rows representing the exact same document
        matched_key = None
        for k, ent in documents.items():
            # 1. Same document number hash or number
            if doc_number_hash and ent.get("doc_number_hash") and doc_number_hash == ent.get("doc_number_hash"):
                matched_key = k
                break
            if doc_number and ent.get("doc_number") and doc_number == ent.get("doc_number"):
                matched_key = k
                break
            # 2. Same non-empty file path
            if fpath and ent.get("file_path") and fpath == ent.get("file_path"):
                matched_key = k
                break
            # 3. Same chosen option
            if chosen and ent.get("chosen_option") == chosen:
                matched_key = k
                break

        if matched_key:
            ent = documents[matched_key]
            if req and req not in ent["requirements"]:
                ent["requirements"].append(req)
            ent["name"] = ent["name"] or doc_name
            ent["dob"] = ent["dob"] or doc_dob
            ent["address"] = ent["address"] or doc_address
            ent["doc_number"] = ent["doc_number"] or doc_number
            ent["doc_number_hash"] = ent.get("doc_number_hash") or doc_number_hash
            ent["raw_text"] = ent.get("raw_text") or row_raw_text
            ent["text_length"] = max(ent.get("text_length", 0), len(row_raw_text))
            ent["has_data"] = any([ent["name"], ent["dob"], ent["address"], ent["doc_number"]])
            if not ent.get("doc_meta") and doc_meta:
                ent["doc_meta"] = doc_meta
        else:
            label = chosen or req
            documents[label] = {
                "id": row.get("id"),
                "name": doc_name,
                "dob": doc_dob,
                "address": doc_address,
                "doc_number": doc_number,
                "doc_number_hash": doc_number_hash,
                "raw_text": row_raw_text,
                "text_length": len(row_raw_text),
                "requirement": req,
                "requirements": [req] if req else [],
                "chosen_option": chosen,
                "file_path": fpath,
                "has_data": any([doc_name, doc_dob, doc_address, doc_number]),
                "doc_meta": doc_meta or {},
                "manually_edited": bool(row.get("manually_edited")),
            }
    return documents

def update_fields(session_id, service, variant, requirement, doc_name, doc_dob, doc_address,
                  doc_number=None, raw_text=None, manually_edited=True, user_id=None):
    """Updates the typed/OCR'd metadata for an already-uploaded item."""
    raw_doc_num_str = None
    if isinstance(doc_number, dict):
        raw_doc_num_str = f"{doc_number.get('type')}: {doc_number.get('number')}"
    elif doc_number:
        raw_doc_num_str = str(doc_number)

    doc_number_hash = hash_doc_number(raw_doc_num_str) if raw_doc_num_str else None
    masked_doc_num_str = mask_doc_number(raw_doc_num_str) if raw_doc_num_str else None

    # Data minimisation: raw OCR text is never stored in DB
    stored_raw_text = None

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if user_id:
                cur.execute(
                    """
                    UPDATE checklist_progress
                    SET doc_name = %s, doc_dob = %s, doc_address = %s,
                        doc_number = COALESCE(%s, doc_number),
                        doc_number_hash = COALESCE(%s, doc_number_hash),
                        raw_text = COALESCE(%s, raw_text),
                        manually_edited = %s
                    WHERE user_id = %s AND service = %s AND variant = %s AND requirement = %s
                    """,
                    (doc_name, doc_dob, doc_address, masked_doc_num_str, doc_number_hash,
                     stored_raw_text, manually_edited, user_id, service, variant, requirement),
                )
            else:
                cur.execute(
                    """
                    UPDATE checklist_progress
                    SET doc_name = %s, doc_dob = %s, doc_address = %s,
                        doc_number = COALESCE(%s, doc_number),
                        doc_number_hash = COALESCE(%s, doc_number_hash),
                        raw_text = COALESCE(%s, raw_text),
                        manually_edited = %s
                    WHERE session_id = %s AND service = %s AND variant = %s AND requirement = %s
                    """,
                    (doc_name, doc_dob, doc_address, masked_doc_num_str, doc_number_hash,
                     stored_raw_text, manually_edited, session_id, service, variant, requirement),
                )
        conn.commit()

def get_file_path(session_id, service, variant, requirement, user_id=None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if user_id:
                cur.execute(
                    "SELECT file_path FROM checklist_progress "
                    "WHERE user_id = %s AND service = %s AND variant = %s AND requirement = %s AND uploaded = 1",
                    (user_id, service, variant, requirement),
                )
            else:
                cur.execute(
                    "SELECT file_path FROM checklist_progress "
                    "WHERE session_id = %s AND service = %s AND variant = %s AND requirement = %s AND uploaded = 1",
                    (session_id, service, variant, requirement),
                )
            row = cur.fetchone()
    return row[0] if row else None

def get_decisions(session_id, service, variant, user_id=None):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if user_id:
                cur.execute(
                    "SELECT issue_key, decision FROM mismatch_decisions "
                    "WHERE user_id = %s AND service = %s AND variant = %s",
                    (user_id, service, variant),
                )
            else:
                cur.execute(
                    "SELECT issue_key, decision FROM mismatch_decisions "
                    "WHERE session_id = %s AND service = %s AND variant = %s",
                    (session_id, service, variant),
                )
            rows = cur.fetchall()
    return {row["issue_key"]: row["decision"] for row in rows}

def save_decision(session_id, service, variant, issue_key, decision, user_id=None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO mismatch_decisions (session_id, service, variant, issue_key, decision, decided_at, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(session_id, service, variant, issue_key)
                DO UPDATE SET decision = excluded.decision, decided_at = excluded.decided_at,
                              user_id = COALESCE(excluded.user_id, mismatch_decisions.user_id)
                """,
                (session_id, service, variant, issue_key, decision, datetime.now().isoformat(), user_id),
            )
        conn.commit()

def create_user(full_name, email, mobile_number, password_hash, preferred_language="en"):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (full_name, email, mobile_number, password_hash, preferred_language)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id, full_name, email, mobile_number, preferred_language
                    """,
                    (full_name, email, mobile_number, password_hash, preferred_language),
                )
                row = cur.fetchone()
            conn.commit()
            return {
                "id": row[0],
                "full_name": row[1],
                "email": row[2],
                "mobile_number": row[3],
                "preferred_language": row[4],
            }
    except psycopg2.IntegrityError:
        return None

def get_user_by_email(email):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
    return user

def get_user_by_id(user_id):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
    return user

def link_session_to_user(session_id, user_id):
    """Associates unauthenticated session uploads and decisions to the logged-in user."""
    if not session_id or not user_id:
        return
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE checklist_progress SET user_id = %s WHERE session_id = %s AND (user_id IS NULL OR user_id = %s)",
                (user_id, session_id, user_id),
            )
            cur.execute(
                "UPDATE mismatch_decisions SET user_id = %s WHERE session_id = %s AND (user_id IS NULL OR user_id = %s)",
                (user_id, session_id, user_id),
            )
        conn.commit()

def skip_requirement(session_id, service, variant, requirement, skipped=True, user_id=None):
    now_str = datetime.now(timezone.utc).isoformat()
    meta = json.dumps({"skipped": bool(skipped)})
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if skipped:
                cur.execute(
                    """
                    INSERT INTO checklist_progress
                        (session_id, service, variant, requirement, chosen_option, uploaded, file_path, uploaded_at, doc_meta)
                    VALUES (%s, %s, %s, %s, %s, 1, 'SKIPPED', %s, %s)
                    ON CONFLICT (session_id, service, variant, requirement)
                    DO UPDATE SET
                        chosen_option = EXCLUDED.chosen_option,
                        uploaded = 1,
                        file_path = 'SKIPPED',
                        uploaded_at = EXCLUDED.uploaded_at,
                        doc_name = NULL,
                        doc_dob = NULL,
                        doc_address = NULL,
                        doc_number = NULL,
                        doc_meta = EXCLUDED.doc_meta
                    """,
                    (session_id, service, variant, requirement, "Not Applicable", now_str, meta),
                )
                if user_id:
                    cur.execute(
                        "UPDATE checklist_progress SET user_id = %s WHERE session_id = %s AND service = %s AND variant = %s AND requirement = %s",
                        (user_id, session_id, service, variant, requirement),
                    )
            else:
                if user_id:
                    cur.execute(
                        """
                        DELETE FROM checklist_progress
                        WHERE user_id = %s AND service = %s AND variant = %s AND requirement = %s
                        """,
                        (user_id, service, variant, requirement),
                    )
                else:
                    cur.execute(
                        """
                        DELETE FROM checklist_progress
                        WHERE session_id = %s AND service = %s AND variant = %s AND requirement = %s
                        """,
                        (session_id, service, variant, requirement),
                    )
            conn.commit()


def delete_session_data(session_id, user_id=None):
    """Wipes all files and database rows associated with a session or user."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if user_id:
                cur.execute("SELECT file_path FROM checklist_progress WHERE session_id = %s OR user_id = %s", (session_id, user_id))
            else:
                cur.execute("SELECT file_path FROM checklist_progress WHERE session_id = %s", (session_id,))
            rows = cur.fetchall()
            if user_id:
                cur.execute("DELETE FROM checklist_progress WHERE session_id = %s OR user_id = %s", (session_id, user_id))
                cur.execute("DELETE FROM mismatch_decisions WHERE session_id = %s OR user_id = %s", (session_id, user_id))
            else:
                cur.execute("DELETE FROM checklist_progress WHERE session_id = %s", (session_id,))
                cur.execute("DELETE FROM mismatch_decisions WHERE session_id = %s", (session_id,))
        conn.commit()

    for row in rows:
        fpath = row.get("file_path")
        if fpath and os.path.exists(fpath):
            try:
                os.remove(fpath)
            except OSError:
                pass

    sess_folder = os.path.join("uploads", str(session_id))
    if os.path.exists(sess_folder):
        try:
            shutil.rmtree(sess_folder, ignore_errors=True)
        except OSError:
            pass

def cleanup_expired_uploads(retention_hours=2):
    """Deletes uploaded files and database records older than retention_hours."""
    cutoff = datetime.now() - timedelta(hours=retention_hours)
    cutoff_iso = cutoff.isoformat()
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT file_path FROM checklist_progress WHERE uploaded_at < %s", (cutoff_iso,))
            rows = cur.fetchall()
            cur.execute("DELETE FROM checklist_progress WHERE uploaded_at < %s", (cutoff_iso,))
        conn.commit()

    for r in rows:
        fp = r.get("file_path")
        if fp and os.path.exists(fp):
            try:
                os.remove(fp)
            except OSError:
                pass

def get_document_diagnostics(session_id, service, variant):
    """
    Development-only retrieval of uploaded documents including full raw OCR text
    and parsed fields for inspection.
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT requirement, chosen_option, uploaded, file_path, uploaded_at, "
                "doc_name, doc_dob, doc_address, doc_number, raw_text, manually_edited "
                "FROM checklist_progress "
                "WHERE session_id = %s AND service = %s AND variant = %s AND uploaded = 1",
                (session_id, service, variant),
            )
            rows = cur.fetchall()

    return [
        {
            "requirement": row["requirement"],
            "chosenOption": row["chosen_option"],
            "filePath": row["file_path"],
            "uploadedAt": row["uploaded_at"],
            "rawOcrText": row.get("raw_text") or "",
            "extractedFields": {
                "name": row["doc_name"],
                "dob": row["doc_dob"],
                "address": row["doc_address"],
                "docNumber": row["doc_number"],
            },
            "manuallyEdited": bool(row.get("manually_edited")),
        }
        for row in rows
    ]


def get_user_documents(user_id):
    """Lists all uploaded documents across all services for the given user_id."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, service, variant, requirement, chosen_option, file_path, "
                "uploaded_at, doc_name, doc_dob, doc_address, doc_number, manually_edited "
                "FROM checklist_progress "
                "WHERE user_id = %s AND uploaded = 1 "
                "ORDER BY uploaded_at DESC",
                (user_id,),
            )
            return cur.fetchall()


def delete_user_document(user_id, doc_id):
    """Deletes a specific uploaded document row if owned by user_id, returning its file_path."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, file_path FROM checklist_progress WHERE id = %s AND user_id = %s",
                (doc_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            fpath = row.get("file_path")
            cur.execute(
                "DELETE FROM checklist_progress WHERE id = %s AND user_id = %s",
                (doc_id, user_id),
            )
            conn.commit()
            return fpath


def delete_all_user_documents(user_id):
    """Deletes all uploaded documents and decisions for user_id, returning list of file_paths."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT file_path FROM checklist_progress WHERE user_id = %s AND file_path IS NOT NULL AND file_path != 'SKIPPED'",
                (user_id,),
            )
            rows = cur.fetchall()
            cur.execute("DELETE FROM checklist_progress WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM mismatch_decisions WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM correction_steps WHERE user_id = %s", (user_id,))
            conn.commit()
            return [r["file_path"] for r in rows if r.get("file_path")]


def get_correction_steps(user_id, service, variant):
    """Returns {issue_key: [step_index, ...]} of completed guidance steps."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT issue_key, step_index FROM correction_steps "
                "WHERE user_id = %s AND service = %s AND variant = %s AND completed = TRUE",
                (user_id, service, variant),
            )
            rows = cur.fetchall()
    res = {}
    for r in rows:
        ik = r["issue_key"]
        res.setdefault(ik, []).append(r["step_index"])
    return res


def save_correction_step(user_id, service, variant, issue_key, step_index, completed):
    """Saves completion state for a guidance step checkbox."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO correction_steps (user_id, service, variant, issue_key, step_index, completed, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, service, variant, issue_key, step_index)
                DO UPDATE SET completed = excluded.completed, updated_at = excluded.updated_at
                """,
                (user_id, service, variant, issue_key, step_index, bool(completed), datetime.now(timezone.utc)),
            )
            conn.commit()

def delete_verified_files(session_id, service, variant, user_id=None):
    """Deletes uploaded files on disk for a verified checklist to minimize stored identity data."""
    files_to_delete = []
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if user_id:
                cur.execute(
                    "SELECT file_path FROM checklist_progress WHERE (user_id = %s OR session_id = %s) AND service = %s AND variant = %s AND file_path IS NOT NULL",
                    (user_id, session_id, service, variant)
                )
            else:
                cur.execute(
                    "SELECT file_path FROM checklist_progress WHERE session_id = %s AND service = %s AND variant = %s AND file_path IS NOT NULL",
                    (session_id, service, variant)
                )
            rows = cur.fetchall()
            files_to_delete = [r["file_path"] for r in rows if r.get("file_path")]
            if user_id:
                cur.execute(
                    "UPDATE checklist_progress SET file_path = NULL WHERE (user_id = %s OR session_id = %s) AND service = %s AND variant = %s",
                    (user_id, session_id, service, variant)
                )
            else:
                cur.execute(
                    "UPDATE checklist_progress SET file_path = NULL WHERE session_id = %s AND service = %s AND variant = %s",
                    (session_id, service, variant)
                )
        conn.commit()

    for fp in files_to_delete:
        if fp and os.path.exists(fp):
            try:
                os.remove(fp)
            except OSError:
                pass
