"""Run in the isolated test workspace: app import initializes its own database."""
import io
from pathlib import Path

import pytest
import pymupdf as fitz
import app as module
from ocr_fixtures.check_aadhaar_sides import card

SID = 'synthetic_aadhaar_session_12345678'


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'UPLOAD_FOLDER', str(tmp_path))
    monkeypatch.setattr(module, 'get_checklist', lambda *args: [{'name': 'Identity', 'options': ['Aadhaar Card']}])
    monkeypatch.setattr(module.db, 'mark_uploaded', lambda *args, **kwargs: None)
    module.app.config['TESTING'] = True
    with module.app.test_client() as client:
        with client.session_transaction() as session:
            session['user_id'] = 987654
        yield client


def data(files):
    return {'session_id': SID, 'requirement': 'Identity', 'chosen_option': 'Aadhaar Card', 'file': files}


@pytest.mark.parametrize('reverse', [False, True])
def test_real_two_photo_upload_and_ocr(client, reverse):
    files = []
    for back in ([True, False] if reverse else [False, True]):
        stream = io.BytesIO()
        card(back).save(stream, format='PNG')
        stream.seek(0)
        files.append((stream, 'synthetic.png'))
    response = client.post('/api/checklist/Test/upload', data=data(files))
    assert response.status_code == 200
    result = response.get_json()
    fields = result['extracted']
    assert fields['name'] == 'Aarav Example'
    assert fields['dob'] == '2002-08-19'
    assert fields['pincode'] == '411001'
    assert fields['address'] == 'C/O: Meera Example, Flat 12 Test Nagar, Pune Maharashtra 411001'
    assert fields['father_name'] is None
    with fitz.open(result['filePath']) as pdf:
        assert len(pdf) == 2


def protected_pdf():
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 50), 'Aadhaar\nName: Aarav Example\nDOB: 19/08/2002\nMale\nXXXX XXXX 1234')
        return pdf.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw='synthetic-owner', user_pw='synthetic-password')


def test_password_failure_preserves_previous_upload(client):
    _, previous = module.get_safe_upload_path(SID, 'Test', 'adult', 'Identity', '.pdf')
    Path(previous).write_bytes(b'previous synthetic document')
    response = client.post('/api/checklist/Test/upload', data=data((io.BytesIO(protected_pdf()), 'protected.pdf')))
    assert response.status_code == 400
    assert response.get_json()['code'] == 'PDF_PASSWORD_REQUIRED'
    assert Path(previous).read_bytes() == b'previous synthetic document'
    assert not list(Path(previous).parent.glob('tmp_*'))


def test_password_unlocks_without_echoing_secret(client):
    payload = data((io.BytesIO(protected_pdf()), 'protected.pdf'))
    payload['password'] = 'synthetic-password'
    response = client.post('/api/checklist/Test/upload', data=payload)
    assert response.status_code == 200
    assert response.get_json()['extracted']['name'] == 'Aarav Example'
    assert 'synthetic-password' not in response.get_data(as_text=True)


def test_three_photos_are_rejected(client):
    response = client.post('/api/checklist/Test/upload', data=data([(io.BytesIO(b'bad'), 'photo.png') for _ in range(3)]))
    assert response.status_code == 400


def test_async_real_two_photo_upload(client):
    import time
    files=[]
    for back in (False,True):
        stream=io.BytesIO(); card(back).save(stream,format='PNG'); stream.seek(0)
        files.append((stream,'synthetic.png'))
    response=client.post('/api/checklist/Test/upload',data=data(files),headers={'Prefer':'respond-async'})
    assert response.status_code==202
    job=response.get_json()['job_id']
    deadline=time.monotonic()+150
    while time.monotonic()<deadline:
        status=client.get('/api/ocr/jobs/'+job).get_json()
        if status['status'] in ('failed','completed'): break
        time.sleep(.1)
    assert status['status']=='completed',status.get('result',{}).get('code')
    fields=status['result']['extracted']
    assert fields['name']=='Aarav Example'
    assert fields['dob']=='2002-08-19'
    assert fields['pincode']=='411001'
