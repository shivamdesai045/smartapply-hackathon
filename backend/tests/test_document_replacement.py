"""Use an isolated SQLite database; never access the user's saved documents."""
import sqlite3
from contextlib import contextmanager

import db


def test_replacement_resets_old_corrections_but_rescan_preserves_them(tmp_path, monkeypatch):
    database = tmp_path / 'synthetic.db'

    @contextmanager
    def connection():
        conn = db.SQLiteConnectionAdapter(sqlite3.connect(database))
        try:
            yield conn
        finally:
            conn.close()

    monkeypatch.setattr(db, 'USE_SQLITE', True)
    monkeypatch.setattr(db, 'get_db_connection', connection)
    db.init_db()
    key = ('synthetic_session_1234567890', 'Test', 'adult', 'Identity')
    original = {'name': {'value': 'First Example', 'confidence': .85, 'needs_review': False}}
    db.mark_uploaded(*key, 'Aadhaar Card', 'synthetic-first.pdf', doc_name='First Example', doc_fields=original)
    db.update_fields(*key, 'Corrected Example', None, None, manually_edited=True,
                     doc_fields={'name': {'value': 'Corrected Example'}})
    db.update_fields(*key, 'New OCR Guess', None, None, manually_edited=False,
                     doc_fields={'name': {'value': 'New OCR Guess', 'confidence': .85}})
    assert db.get_progress(*key[:3])['Identity']['docName'] == 'Corrected Example'
    replacement = {'name': {'value': 'Second Example', 'confidence': .85, 'needs_review': False}}
    db.mark_uploaded(*key, 'Aadhaar Card', 'synthetic-second.pdf', doc_name='Second Example', doc_fields=replacement)
    result = db.get_progress(*key[:3])['Identity']
    assert result['docName'] == 'Second Example'
    assert result['doc_fields']['name']['user_verified'] is False
    assert result['manuallyEdited'] is False
