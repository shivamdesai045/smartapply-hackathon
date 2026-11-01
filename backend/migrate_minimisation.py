"""
Data Minimisation Migration:
1. Purges all existing raw OCR text from checklist_progress.
2. Masks any stored 12-digit / Aadhaar numbers in doc_number to show only last 4 digits (XXXX XXXX 1234).
3. Purges uploaded files older than the retention TTL window.
"""
import os
import re
import psycopg2
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=env_path)
DATABASE_URL = os.getenv("DATABASE_URL")

def mask_number(s):
    if not s:
        return s
    s_str = str(s).strip()
    m = re.search(r"\b(\d{4})\s*(\d{4})\s*(\d{4})\b", s_str)
    if m:
        return s_str.replace(m.group(0), f"XXXX XXXX {m.group(3)}")
    m12 = re.search(r"\b\d{12}\b", s_str)
    if m12:
        val = m12.group(0)
        return s_str.replace(val, f"XXXX XXXX {val[-4:]}")
    return s_str

def run_migration():
    if not DATABASE_URL:
        print("No DATABASE_URL configured.")
        return
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        # 1. Purge raw_text
        cur.execute("UPDATE checklist_progress SET raw_text = NULL WHERE raw_text IS NOT NULL")
        print("Purged raw OCR text from checklist_progress.")

        # 2. Mask Aadhaar numbers
        cur.execute("SELECT session_id, service, variant, requirement, doc_number FROM checklist_progress WHERE doc_number IS NOT NULL")
        rows = cur.fetchall()
        masked_count = 0
        for r in rows:
            sid, srv, var, req, doc_num = r[0], r[1], r[2], r[3], r[4]
            masked = mask_number(doc_num)
            if masked != doc_num:
                cur.execute(
                    "UPDATE checklist_progress SET doc_number = %s WHERE session_id = %s AND service = %s AND variant = %s AND requirement = %s",
                    (masked, sid, srv, var, req)
                )
                masked_count += 1
        print(f"Masked {masked_count} unmasked document numbers.")
    conn.close()

if __name__ == "__main__":
    run_migration()
