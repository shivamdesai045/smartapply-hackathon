from threading import Event
from time import monotonic, sleep
import io
import pytest
from PIL import Image
from ocr_jobs import OcrJobs


def wait_done(jobs, job, owner):
    deadline = monotonic()+3
    while monotonic()<deadline:
        result=jobs.status(job,owner)
        if result['status'] in ('completed','failed','cancelled'): return result
        sleep(.01)
    pytest.fail('Job did not finish')


def test_queue_ownership_cancellation_duplicate_and_failure():
    jobs=OcrJobs(capacity=2)
    gate=Event(); started=Event(); cleaned=[]
    def work():
        started.set(); gate.wait(3)
        return {'ok':True},200
    try:
        first=jobs.submit(1,'identity',work)
        assert started.wait(1)
        second=jobs.submit(1,'address',lambda: ({'ok':True},200),lambda:cleaned.append(True))
        assert jobs.find_active(1,'identity') == first
        assert jobs.find_active(2,'identity') is None
        assert jobs.status(first,2) is None
        assert jobs.cancel(second,2) is None
        assert jobs.status(second,1)['ahead']==1
        with pytest.raises(ValueError): jobs.submit(1,'identity',work)
        with pytest.raises(ValueError): jobs.submit(1,'extra',work)
        assert jobs.cancel(second,1)
        assert cleaned==[True]
        assert jobs.status(second,1)['status']=='cancelled'
        gate.set()
        assert wait_done(jobs,first,1)['result']=={'ok':True}
        def bad(): raise RuntimeError('private content must not escape')
        failed=jobs.submit(1,'failure',bad)
        result=wait_done(jobs,failed,1)
        assert result['status']=='failed'
        assert 'private content' not in str(result)
    finally:
        gate.set(); jobs.executor.shutdown(wait=True)


def test_upload_returns_job_before_ocr_finishes_and_result_is_private(tmp_path,monkeypatch):
    import app as module
    import ocr_jobs
    jobs=OcrJobs(); gate=Event(); started=Event()
    monkeypatch.setattr(ocr_jobs,'jobs',jobs)
    monkeypatch.setattr(module,'UPLOAD_FOLDER',str(tmp_path))
    monkeypatch.setattr(module,'get_checklist',lambda *a:[{'name':'Identity','options':['Aadhaar Card']}])
    monkeypatch.setattr(module.db,'mark_uploaded',lambda *a,**kw:None)
    def extract(*a,**kw):
        started.set(); gate.wait(3)
        return {'name':'Synthetic Example','dob':'2002-08-19'}
    monkeypatch.setattr(module,'extract_fields',extract)
    stream=io.BytesIO(); Image.new('RGB',(100,100),'white').save(stream,format='PNG'); stream.seek(0)
    try:
        with module.app.test_client() as client:
            with client.session_transaction() as session: session['user_id']=987654
            response=client.post('/api/checklist/Test/upload',headers={'Prefer':'respond-async'},data={
                'session_id':'synthetic_job_session_12345678','requirement':'Identity',
                'chosen_option':'Aadhaar Card','file':(stream,'synthetic.png')})
            assert response.status_code==202
            job_id=response.get_json()['job_id']
            assert started.wait(1)
            lookup=client.get('/api/ocr/jobs/active',query_string={'session_id':'synthetic_job_session_12345678','service':'Test','variant':'adult','requirement':'Identity'})
            assert lookup.get_json()['job_id']==job_id
            assert client.get('/api/ocr/jobs/'+job_id).get_json()['status']=='reading'
            with client.session_transaction() as session: session['user_id']=987655
            assert client.get('/api/ocr/jobs/'+job_id).status_code==404
            assert client.delete('/api/ocr/jobs/'+job_id).status_code==404
            with client.session_transaction() as session: session['user_id']=987654
            gate.set()
            assert wait_done(jobs,job_id,987654)['status']=='completed'
            response=client.get('/api/ocr/jobs/'+job_id)
            assert response.get_json()['result']['extracted']['dob']=='2002-08-19'
            assert response.headers['Cache-Control']=='no-store'
        assert not list(tmp_path.rglob('tmp_*'))
    finally:
        gate.set(); jobs.executor.shutdown(wait=True)


def test_queue_wait_is_not_processing_time():
 jobs=OcrJobs();gate=Event()
 try:
  first=jobs.submit(1,'first',lambda:(gate.wait(2) and {},200))
  second=jobs.submit(2,'second',lambda:({'ok':True},200))
  sleep(.15)
  queued=jobs.status(second,2)
  assert queued['processing_seconds']==0 and queued['queue_seconds']>=.1
  gate.set();done=wait_done(jobs,second,2)
  assert done['queue_seconds']>=.1
  elapsed=done['elapsed_seconds'];sleep(.1)
  assert jobs.status(second,2)['elapsed_seconds']==elapsed
 finally:
  gate.set();jobs.executor.shutdown(wait=True)
