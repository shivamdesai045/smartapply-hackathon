import os
import sqlite3
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

# Load DATABASE_URL from .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env")
    exit(1)

SQLITE_PATH = "sahayak.db"

def get_sqlite_conn():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_pg_db_if_missing():
    try:
        # Connect without dbname to create it
        temp_url = DATABASE_URL.rsplit('/', 1)[0] + '/postgres'
        conn = psycopg2.connect(temp_url)
        conn.autocommit = True
        cur = conn.cursor()
        db_name = DATABASE_URL.rsplit('/', 1)[1]
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        if not cur.fetchone():
            print(f"Creating PostgreSQL database '{db_name}'...")
            cur.execute(f"CREATE DATABASE {db_name}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Failed to check/create database: {e}")
        # Will fail if postgres user doesn't have permissions or connection string is invalid

def get_pg_conn():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_pg_tables(conn):
    print("Initializing PostgreSQL tables...")
    cur = conn.cursor()
    cur.execute("""
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
            PRIMARY KEY (session_id, service, variant, requirement)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mismatch_decisions (
            session_id TEXT NOT NULL,
            service TEXT NOT NULL,
            variant TEXT NOT NULL,
            issue_key TEXT NOT NULL,
            decision TEXT NOT NULL,
            decided_at TEXT NOT NULL,
            PRIMARY KEY (session_id, service, variant, issue_key)
        )
    """)
    conn.commit()
    cur.close()

def migrate_data():
    print("Extracting data from SQLite...")
    sqlite_conn = get_sqlite_conn()
    sqlite_progress = sqlite_conn.execute("SELECT * FROM checklist_progress").fetchall()
    sqlite_decisions = sqlite_conn.execute("SELECT * FROM mismatch_decisions").fetchall()
    sqlite_conn.close()

    print(f"Found {len(sqlite_progress)} checklist_progress records.")
    print(f"Found {len(sqlite_decisions)} mismatch_decisions records.")

    pg_conn = get_pg_conn()
    init_pg_tables(pg_conn)
    
    cur = pg_conn.cursor()
    
    print("Inserting data into PostgreSQL...")
    
    # Insert checklist_progress
    for row in sqlite_progress:
        cur.execute("""
            INSERT INTO checklist_progress
                (session_id, service, variant, requirement, chosen_option, uploaded,
                 file_path, uploaded_at, doc_name, doc_dob, doc_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id, service, variant, requirement) DO NOTHING
        """, (
            row["session_id"], row["service"], row["variant"], row["requirement"],
            row["chosen_option"], row["uploaded"], row["file_path"], row["uploaded_at"],
            row["doc_name"], row["doc_dob"], row["doc_address"]
        ))
        
    # Insert mismatch_decisions
    for row in sqlite_decisions:
        cur.execute("""
            INSERT INTO mismatch_decisions (session_id, service, variant, issue_key, decision, decided_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id, service, variant, issue_key) DO NOTHING
        """, (
            row["session_id"], row["service"], row["variant"],
            row["issue_key"], row["decision"], row["decided_at"]
        ))
        
    pg_conn.commit()
    
    # Verify
    cur.execute("SELECT COUNT(*) FROM checklist_progress")
    pg_progress_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM mismatch_decisions")
    pg_decisions_count = cur.fetchone()[0]
    
    print("Migration Verification:")
    print(f"SQLite checklist_progress: {len(sqlite_progress)} | PostgreSQL checklist_progress: {pg_progress_count}")
    print(f"SQLite mismatch_decisions: {len(sqlite_decisions)} | PostgreSQL mismatch_decisions: {pg_decisions_count}")
    
    if len(sqlite_progress) == pg_progress_count and len(sqlite_decisions) == pg_decisions_count:
        print("MIGRATION SUCCESSFUL!")
    else:
        print("WARNING: Row counts do not match!")

    cur.close()
    pg_conn.close()

if __name__ == "__main__":
    create_pg_db_if_missing()
    migrate_data()
