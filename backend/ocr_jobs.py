"""Bounded, process-local OCR jobs. No document text is logged or written here."""
from concurrent.futures import ThreadPoolExecutor
from threading import RLock
from time import monotonic
from uuid import uuid4


class OcrJobs:
    def __init__(self, capacity=8, retention=900):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='ocr-job')
        self.capacity, self.retention = capacity, retention
        self.lock, self.jobs = RLock(), {}

    def submit(self, owner, key, work, cleanup=lambda: None):
        with self.lock:
            now = monotonic()
            self.jobs = {i: j for i,j in self.jobs.items()
                         if not j['future'].done() or now-j.get('finished', now) < self.retention}
            active = [j for j in self.jobs.values() if not j['future'].done()]
            if any(j['owner'] == owner and j['key'] == key for j in active):
                raise ValueError('This document is already being processed.')
            if len(active) >= self.capacity:
                raise ValueError('The OCR queue is full. Wait for a document to finish.')
            job_id = uuid4().hex
            entry = {'owner':owner,'key':key,'created':now}
            def timed_work():
                with self.lock: entry['started'] = monotonic()
                return work()
            future = self.executor.submit(timed_work)
            entry['future'] = future
            self.jobs[job_id] = entry
            def finished(_):
                try: cleanup()
                finally:
                    with self.lock: entry['finished'] = monotonic()
            future.add_done_callback(finished)
            return job_id

    def status(self, job_id, owner):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or job['owner'] != owner:
                return None
            f = job['future']
            if f.done() and monotonic()-job.get('finished', monotonic()) >= self.retention:
                self.jobs.pop(job_id, None)
                return None
            now = monotonic()
            end = job.get('finished', now)
            begun = job.get('started')
            result = {'job_id':job_id,'elapsed_seconds':round(end-job['created']),
                      'queue_seconds':round((begun or end)-job['created'],1),
                      'processing_seconds':round(end-begun,1) if begun else 0}
            if f.cancelled(): return {**result, 'status': 'cancelled'}
            if f.done():
                try:
                    body, code = f.result()
                    return {**result, 'status': 'completed' if code < 400 else 'failed', 'result': body, 'http_status': code}
                except Exception:
                    return {**result, 'status': 'failed', 'http_status': 500,
                            'result': {'error': 'Document processing failed. Please retry.', 'code': 'OCR_JOB_FAILED'}}
            if f.running(): return {**result, 'status': 'reading'}
            ahead = sum(j['created'] < job['created'] and not j['future'].done() for j in self.jobs.values())
            return {**result, 'status': 'queued', 'ahead': ahead}

    def find_active(self, owner, key):
        with self.lock:
            return next((job_id for job_id, job in self.jobs.items()
                         if job['owner'] == owner and job['key'] == key and not job['future'].done()), None)

    def cancel(self, job_id, owner):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or job['owner'] != owner: return None
            return job['future'].cancel()


jobs = OcrJobs()
