"""Small, authenticated-scope OCR cache. Memory only; never cache errors or passwords."""
import copy
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from collections import OrderedDict

_entries = OrderedDict()
_lock = threading.RLock()
_secret = secrets.token_bytes(32)
_generation = 0
TTL = 300
CAPACITY = 16


def clear_owner(owner):
    global _generation
    with _lock:
        _generation += 1  # Reject results from jobs already running when data is cleared.
        for key in list(_entries):
            if key[0][0] == owner:
                _entries.pop(key)['timer'].cancel()


def cached_extraction(path, filename, chosen_option, password, scope, work):
    if not scope:
        return work()
    from document_fields import OCR_VERSION
    from field_storage import sanitize
    started = time.monotonic()
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for chunk in iter(lambda: source.read(1024*1024), b''):
            digest.update(chunk)
    settings = [os.getenv(k, '') for k in ('OCR_ENGINE','OCR_MAX_SIDE','OCR_LINE_ORIENTATION','OCR_REC_BATCH_SIZE','OCR_RETRY_BUDGET_SECONDS','OCR_CPU_THREADS','OCR_DET_MAX_SIDE','OCR_FAST_TEXT_PASS')]
    signature = hmac.new(_secret, json.dumps([digest.hexdigest(),chosen_option,password,OCR_VERSION,settings,os.path.splitext(filename)[1].lower()]).encode(),hashlib.sha256).hexdigest()
    key = (tuple(scope), signature)
    with _lock:
        generation = _generation
        cached = _entries.get(key)
        if cached and cached['expires'] > time.monotonic():
            _entries.move_to_end(key)
            result = copy.deepcopy(cached['result'])
            result['timings'] = {'cache_hit':True,'total_seconds':round(time.monotonic()-started,3)}
            return result
    result = work()
    result.setdefault('timings', {})['cache_hit'] = False
    # Reuse only successful extraction; explicit Re-scan bypasses this cache.
    if result.get('error_code') or not result.get('ocrAttempted') or not any(result.get(k) for k in ('name','dob','doc_number')):
        return result
    safe = sanitize(copy.deepcopy(result))
    if len(json.dumps(safe)) > 1024*1024:
        return result
    token = object()
    def expire():
        with _lock:
            if _entries.get(key,{}).get('token') is token:
                _entries.pop(key,None)
    timer = threading.Timer(TTL, expire)
    timer.daemon = True
    with _lock:
        if generation != _generation:
            return result
        previous = _entries.pop(key,None)
        if previous: previous['timer'].cancel()
        while len(_entries) >= CAPACITY:
            _entries.popitem(last=False)[1]['timer'].cancel()
        _entries[key] = {'result':safe,'expires':time.monotonic()+TTL,'timer':timer,'token':token}
        timer.start()
    return result
