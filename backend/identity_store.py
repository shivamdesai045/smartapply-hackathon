"""Authenticated encryption for ID values. The key must live outside the database."""
import json
import os
import re
from cryptography.fernet import Fernet, InvalidToken


def enabled():
    if os.getenv('IDENTITY_ENCRYPTION_REQUIRED')=='1' and not os.getenv('IDENTITY_ENCRYPTION_KEY'):
        raise RuntimeError('Required identity encryption key is missing')
    return bool(os.getenv('IDENTITY_ENCRYPTION_KEY'))


def cipher():
    key=os.getenv('IDENTITY_ENCRYPTION_KEY')
    if not key: raise RuntimeError('Identity encryption is not configured')
    return Fernet(key.encode('ascii'))


def seal(ids, context):
    return cipher().encrypt(json.dumps({'context':context,'ids':ids},sort_keys=True).encode()).decode('ascii')


def unseal(token, context):
    payload=json.loads(cipher().decrypt(token.encode('ascii')))
    if payload.get('context')!=context: raise InvalidToken('Identity context mismatch')
    return payload['ids']


def identify(value, kind):
    if isinstance(value,dict):value=value.get('value',value.get('number'))
    if isinstance(value,dict):value=value.get('number')
    if not isinstance(value,str):return {}
    if re.search(r'aadh?aar',kind or '',re.I):
        match=re.fullmatch(r'(?:aadh?aar(?: card)?\s*:\s*)?([2-9][0-9 -]{10,15})',value.strip(),re.I)
        number=re.sub(r'[ -]','',match[1]) if match else ''
        if len(number)==12:
            from document_fields import validate_number
            valid,_=validate_number({'type':'Aadhaar','number':number},'Aadhaar Card',None)
            if valid:return {'aadhaar':number}
    if re.search(r'\bpan\b',kind or '',re.I):
        match=re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b',value.upper())
        if match:return {'pan':match[0]}
    return {}


def context(row):
    return [row.get('user_id'),row['session_id'],row['service'],row['variant'],row['requirement']]


def save_row(conn,row,entry=None,token=None,replacement=False,explicit_clear=False):
    if not enabled():return
    ids=identify(entry,row.get('chosen_option',''))
    if token:
        ids=unseal(token,'ocr-internal')
        ids=identify(ids.get('aadhaar') or ids.get('pan'),row.get('chosen_option',''))
    if not ids and not replacement and not explicit_clear:return
    encrypted=seal(ids,context(row)) if ids else None
    with conn.cursor() as cur:
        from db import hash_doc_number
        fingerprint=hash_doc_number(next(iter(ids))+':'+next(iter(ids.values()))) if ids else None
        cur.execute('UPDATE checklist_progress SET sensitive_ids = %s, doc_number_hash = %s WHERE session_id=%s AND service=%s AND variant=%s AND requirement=%s',(encrypted,fingerprint,row['session_id'],row['service'],row['variant'],row['requirement']))


def initialize(conn, sqlite=False):
    # Column lives with the owning row, so document deletion also deletes the ciphertext.
    with conn.cursor() as cur:
        if sqlite:
            cur.execute('PRAGMA table_info(checklist_progress)')
            if 'sensitive_ids' not in [r[1] for r in cur.fetchall()]:cur.execute('ALTER TABLE checklist_progress ADD COLUMN sensitive_ids TEXT')
        else:cur.execute('ALTER TABLE checklist_progress ADD COLUMN IF NOT EXISTS sensitive_ids TEXT')
    if enabled():
        from psycopg2.extras import RealDictCursor
        from field_storage import sanitize,json_object
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT id,user_id,session_id,service,variant,requirement,chosen_option,doc_number,doc_fields,doc_meta,sensitive_ids FROM checklist_progress')
            rows=cur.fetchall()
        # Validate all existing ciphertext before modifying any legacy values.
        for row in rows:
            if row['sensitive_ids']:unseal(row['sensitive_ids'],context(row))
        for row in rows:
            fields=json_object(row['doc_fields'])
            if not row['sensitive_ids']:
                entry=fields.get('doc_number') or row['doc_number']
                ids=identify(entry,row.get('chosen_option','')) or identify(row['doc_number'],row.get('chosen_option',''))
                if ids:save_row(conn,row,ids.get('aadhaar') or ids.get('pan'))
            with conn.cursor() as cur:
                cur.execute('UPDATE checklist_progress SET doc_number=%s,doc_fields=%s,doc_meta=%s,raw_text=NULL WHERE session_id=%s AND service=%s AND variant=%s AND requirement=%s',
                            (sanitize(row['doc_number']),json.dumps(sanitize(fields)),json.dumps(sanitize(json_object(row['doc_meta']))),row['session_id'],row['service'],row['variant'],row['requirement']))
    conn.commit()


def reviewed_ids(conn,user_id,service,variant):
    from psycopg2.extras import RealDictCursor
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT id,user_id,session_id,service,variant,requirement,chosen_option,sensitive_ids FROM checklist_progress WHERE user_id=%s AND service=%s AND variant=%s AND uploaded=1 AND sensitive_ids IS NOT NULL',(user_id,service,variant))
        rows=cur.fetchall()
    return [{'requirement':row['requirement'],'chosenOption':row['chosen_option'],'ids':unseal(row['sensitive_ids'],context(row))} for row in rows if not re.search(r'father|mother|parent|guardian',row['requirement'],re.I)]


def rebind_session(conn,session_id,user_id):
    from psycopg2.extras import RealDictCursor
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT user_id,session_id,service,variant,requirement,sensitive_ids FROM checklist_progress WHERE session_id=%s AND user_id IS NULL AND sensitive_ids IS NOT NULL',(session_id,))
        rows=cur.fetchall()
    for row in rows:
        ids=unseal(row['sensitive_ids'],context(row))
        row['user_id']=user_id
        with conn.cursor() as cur:
            cur.execute('UPDATE checklist_progress SET sensitive_ids=%s WHERE session_id=%s AND service=%s AND variant=%s AND requirement=%s',(seal(ids,context(row)),row['session_id'],row['service'],row['variant'],row['requirement']))
