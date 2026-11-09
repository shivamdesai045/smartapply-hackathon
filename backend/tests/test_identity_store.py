import json,sqlite3
from contextlib import contextmanager
import pytest
from cryptography.fernet import Fernet,InvalidToken
import db,identity_store

@pytest.fixture
def database(tmp_path,monkeypatch):
 path=tmp_path/'isolated.db'
 monkeypatch.setenv('IDENTITY_ENCRYPTION_KEY',Fernet.generate_key().decode())
 monkeypatch.setattr(db,'USE_SQLITE',True)
 @contextmanager
 def connection():
  conn=db.SQLiteConnectionAdapter(sqlite3.connect(path))
  try:yield conn
  finally:conn.close()
 monkeypatch.setattr(db,'get_db_connection',connection)
 db.init_db()
 return path

def put(owner=101,number='ABCPE1234F',kind='PAN Card',requirement='Identity'):
 db.mark_uploaded('synthetic_encryption_session', 'Test', 'adult', requirement,kind,'synthetic.png',user_id=owner,
                  doc_name='Aarav Example',doc_number=number,doc_fields={'doc_number':{'value':number}})

def reveal(owner=101):
 with db.get_db_connection() as conn:return identity_store.reviewed_ids(conn,owner,'Test','adult')

def test_encrypted_at_rest_owner_isolation_and_masked_read(database):
 put()
 with sqlite3.connect(database) as conn:
  row=conn.execute('SELECT sensitive_ids,doc_number,doc_fields FROM checklist_progress').fetchone()
 assert 'ABCPE1234F' not in ''.join(row)
 assert reveal()[0]['ids']['pan']=='ABCPE1234F'
 assert reveal(202)==[]
 assert 'ABCPE1234F' not in json.dumps(db.get_progress(None,'Test','adult',user_id=101))

def test_ciphertext_tampering_and_context_binding(database):
 put()
 with db.get_db_connection() as conn:
  with conn.cursor() as cur:
   cur.execute('UPDATE checklist_progress SET user_id=%s',(202,))
  conn.commit()
 with pytest.raises(InvalidToken):reveal(202)
 with pytest.raises(InvalidToken):identity_store.unseal('tampered','ocr-internal')

def test_replace_and_manual_correction_do_not_reuse_old_id(database):
 put()
 db.update_fields('synthetic_encryption_session','Test','adult','Identity',None,None,None,user_id=101,doc_fields={'doc_number':{'value':'ABCPE9876F'}},manually_edited=True)
 assert reveal()[0]['ids']['pan']=='ABCPE9876F'
 db.update_fields('synthetic_encryption_session','Test','adult','Identity',None,None,None,user_id=101,doc_fields={'doc_number':{'value':'ABCPE1234F'}},manually_edited=False)
 assert reveal()[0]['ids']['pan']=='ABCPE9876F'
 db.update_fields('synthetic_encryption_session','Test','adult','Identity',None,None,None,user_id=101,doc_fields={'doc_number':{'value':''}},manually_edited=True)
 assert reveal()==[]
 put()
 put(number='XXXXXX1234')
 assert reveal()==[]

def test_migration_keeps_existing_pan_encrypted(database):
 with sqlite3.connect(database) as conn:
  conn.execute("INSERT INTO checklist_progress(session_id,service,variant,requirement,chosen_option,uploaded,user_id,doc_number,doc_fields) VALUES (?,?,?,?,?,?,?,?,?)",('legacy_session','Test','adult','Legacy','PAN Card',1,101,'PAN: ABCPE1234F',json.dumps({'doc_number':{'value':'ABCPE1234F'}})))
 with db.get_db_connection() as conn:identity_store.initialize(conn,sqlite=True)
 assert reveal()[0]['ids']['pan']=='ABCPE1234F'
 with sqlite3.connect(database) as conn:
  row=conn.execute('SELECT doc_number,doc_fields FROM checklist_progress').fetchone()
 assert 'ABCPE1234F' not in ''.join(row)

def test_aadhaar_capture_before_masking(database):
 from document_fields import enrich_fields
 from ocr_extract import validate_verhoeff
 prefix='23456789012';number=next(prefix+str(d) for d in range(10) if validate_verhoeff(prefix+str(d)))
 result=enrich_fields({}, {'text':f'Aadhaar\nName: Aarav Example\nDOB: 19/08/2002\n{number}','mean_confidence':95},'Aadhaar Card')
 token=result.pop('_identity_ciphertext')
 assert number not in json.dumps(result['doc_fields'])
 assert identity_store.unseal(token,'ocr-internal')['aadhaar']==number
 db.mark_uploaded('synthetic_encryption_session','Test','adult','Identity','Aadhaar Card','synthetic.png',user_id=101,doc_number=result['doc_number'],doc_fields=result['doc_fields'],sensitive_token=token)
 assert reveal()[0]['ids']['aadhaar']==number

def test_reveal_endpoint_auth_origin_and_no_store(database):
 import app
 put()
 with app.app.test_client() as client:
  assert client.post('/api/checklist/Test/reviewed-ids',json={'confirmed':True}).status_code==401
  with client.session_transaction() as session:session['user_id']=101
  assert client.post('/api/checklist/Test/reviewed-ids',json={}).status_code==400
  assert client.post('/api/checklist/Test/reviewed-ids',json={'confirmed':True},headers={'Origin':'https://untrusted.example'}).status_code==403
  response=client.post('/api/checklist/Test/reviewed-ids',json={'confirmed':True})
  assert response.status_code==200 and 'no-store' in response.headers['Cache-Control']
  assert response.get_json()['documents'][0]['ids']['pan']=='ABCPE1234F'
  with client.session_transaction() as session:session['user_id']=202
  assert client.post('/api/checklist/Test/reviewed-ids',json={'confirmed':True}).get_json()['documents']==[]


def test_missing_and_wrong_key_fail_closed(database,monkeypatch):
 put()
 monkeypatch.setenv('IDENTITY_ENCRYPTION_KEY',Fernet.generate_key().decode())
 with db.get_db_connection() as conn:
  with pytest.raises(InvalidToken):identity_store.initialize(conn,sqlite=True)
 monkeypatch.delenv('IDENTITY_ENCRYPTION_KEY')
 monkeypatch.setenv('IDENTITY_ENCRYPTION_REQUIRED','1')
 with pytest.raises(RuntimeError):identity_store.enabled()


def test_session_link_rebinds_encrypted_identity(database):
 put(owner=None)
 db.link_session_to_user('synthetic_encryption_session',101)
 assert reveal()[0]['ids']['pan']=='ABCPE1234F'


def test_skip_removes_saved_number(database):
 put()
 db.skip_requirement('synthetic_encryption_session','Test','adult','Identity',user_id=101)
 assert reveal()==[]


def test_lowercase_pan_is_masked(database):
 put(number='abcpe1234f')
 assert 'abcpe1234f' not in json.dumps(db.get_progress(None,'Test','adult',user_id=101)).lower()
 assert reveal()[0]['ids']['pan']=='ABCPE1234F'
