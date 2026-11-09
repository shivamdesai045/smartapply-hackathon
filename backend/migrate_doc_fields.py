"""Idempotent additive migration; JSONB on PostgreSQL, JSON text on SQLite.

Run from backend: ../.venv/Scripts/python migrate_doc_fields.py
Existing four-column records remain readable without guessed confidence.
"""

def migrate(conn, sqlite=False):
    columns = {
        "doc_fields": "TEXT NOT NULL DEFAULT '{}'" if sqlite else "JSONB NOT NULL DEFAULT '{}'::jsonb",
        "ocr_version": "TEXT",
        "needs_review": "BOOLEAN NOT NULL DEFAULT TRUE",
        "user_verified": "BOOLEAN NOT NULL DEFAULT FALSE",
    }
    with conn.cursor() as cur:
        if sqlite:
            cur.execute("PRAGMA table_info(checklist_progress)")
            existing = {row[1] for row in cur.fetchall()}
            for name, definition in columns.items():
                if name not in existing:
                    cur.execute(f"ALTER TABLE checklist_progress ADD COLUMN {name} {definition}")
        else:
            for name, definition in columns.items():
                cur.execute(f"ALTER TABLE checklist_progress ADD COLUMN IF NOT EXISTS {name} {definition}")
    conn.commit()


if __name__ == "__main__":
    import db
    db.init_db()
    print("Document field migration complete.")
