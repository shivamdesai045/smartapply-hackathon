"""Production boot checks in an isolated workspace; no real accounts or documents."""
import json
import os
from pathlib import Path
import subprocess
import sys
from cryptography.fernet import Fernet


def boot(tmp_path, code, **overrides):
    environment = dict(os.environ)
    environment.update(ENV="production", SECRET_KEY="synthetic-test-session-key-only",
        IDENTITY_ENCRYPTION_KEY=Fernet.generate_key().decode(), IDENTITY_ENCRYPTION_REQUIRED="1",
        SQLITE_PATH=str(tmp_path / "data" / "test.db"), UPLOAD_FOLDER=str(tmp_path / "uploads"),
        DATABASE_URL="", SESSION_COOKIE_SECURE="true", OCR_PRELOAD="0",
        FRONTEND_ORIGIN="https://synthetic.vercel.app", CORS_ORIGINS="https://synthetic.vercel.app")
    environment.update(overrides)
    return subprocess.run([sys.executable,"-c",code],cwd=Path(__file__).resolve().parents[1],
                          env=environment,capture_output=True,text=True,timeout=35)


def test_production_cookie_cache_and_storage(tmp_path):
    result=boot(tmp_path,"""
import app,db,json
with app.app.test_client() as client:
 response=client.get('/api/session')
 assert response.status_code==200
 assert 'Secure;' in response.headers['Set-Cookie']
 assert 'HttpOnly;' in response.headers['Set-Cookie']
 assert 'SameSite=Lax' in response.headers['Set-Cookie']
 assert response.headers['Vercel-CDN-Cache-Control']=='no-store'
 assert 'no-store' in response.headers['Cache-Control']
print('PRODUCTION_OK')
""")
    assert result.returncode==0,result.stderr
    assert 'PRODUCTION_OK' in result.stdout
    assert (tmp_path/'data'/'test.db').exists()
    assert (tmp_path/'uploads').exists()


def test_production_requires_persistent_database(tmp_path):
    result=boot(tmp_path,'import db',SQLITE_PATH='')
    assert result.returncode!=0
    assert 'persistent SQLITE_PATH' in result.stderr


def test_production_rejects_missing_encryption_key(tmp_path):
    result=boot(tmp_path,'import app',IDENTITY_ENCRYPTION_KEY='')
    assert result.returncode!=0
    assert 'encryption' in result.stderr.lower()


def test_production_database_failure_does_not_fallback(tmp_path):
    result=boot(tmp_path,'import db',DATABASE_URL='postgresql://synthetic:synthetic@127.0.0.1:1/missing')
    assert result.returncode!=0
    assert 'production database is unavailable' in result.stderr
    assert not (tmp_path/'data'/'test.db').exists()
