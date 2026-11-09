import numpy as np
from PIL import Image
import paddle_engine
import ocr_boxes
import ocr_extract


def test_adapter_preserves_text_geometry_and_confidence():
    result = paddle_engine.convert_result({'rec_texts': ['Aarav Example'], 'rec_scores': [.93],
        'rec_polys': [np.array([[10, 20], [90, 20], [90, 40], [10, 40]])]}, 100, 100)
    assert result['text'] == 'Aarav Example'
    assert result['lines'][0]['bbox'] == [.1, .2, .9, .4]
    assert result['mean_confidence'] == 93
    assert result['engine'] == 'paddleocr'


def test_image_default_is_paddle(monkeypatch):
    monkeypatch.delenv('OCR_ENGINE', raising=False)
    monkeypatch.setattr(paddle_engine, 'recognize_image', lambda image: {'engine': 'paddleocr'})
    monkeypatch.setattr(ocr_boxes, 'ocr_image_with_best_variant', lambda image: (_ for _ in ()).throw(AssertionError('Unexpected Tesseract')))
    assert ocr_boxes.run_image_ocr(Image.new('RGB', (100, 100)))['engine'] == 'paddleocr'


def test_engine_failure_does_not_use_legacy_ocr(tmp_path, monkeypatch):
    path = tmp_path / 'test.png'
    Image.new('RGB', (100, 100)).save(path)
    monkeypatch.setattr(paddle_engine, 'recognize_image', lambda image: (_ for _ in ()).throw(RuntimeError('synthetic failure')))
    monkeypatch.setenv('OCR_ENGINE', 'paddleocr')
    monkeypatch.setattr(ocr_extract, 'extract_text', lambda *args: (_ for _ in ()).throw(AssertionError('Unexpected fallback')))
    result = ocr_extract.extract_fields(str(path), path.name, 'Aadhaar Card')
    assert result['error_code'] == 'OCR_ENGINE_FAILED'


def test_scanned_pdf_uses_paddle_for_each_page(tmp_path, monkeypatch):
    path = tmp_path / 'sides.pdf'
    Image.new('RGB', (200, 100), 'white').save(path, save_all=True, append_images=[Image.new('RGB', (200, 100), 'white')])
    calls = []
    def fake(image):
        calls.append(True)
        return paddle_engine.convert_result({'rec_texts': ['Example'], 'rec_scores': [.9],
                'rec_polys': [np.array([[1, 1], [50, 1], [50, 20], [1, 20]])]}, image.width, image.height)
    monkeypatch.setenv('OCR_ENGINE', 'paddleocr')
    monkeypatch.setattr(paddle_engine, 'recognize_image', fake)
    result = ocr_boxes.extract_ocr_with_boxes(str(path))
    assert len(calls) == 2
    assert [line['page'] for line in result['lines']] == [1, 2]
    assert result['engine'] == 'paddleocr'


def test_native_worker_failure_is_a_python_error(monkeypatch):
    import io, queue, types, pytest
    replies=queue.Queue(); replies.put({'error':'OCR_WORKER_CRASH'})
    monkeypatch.setattr(paddle_engine, '_get_worker', lambda: (types.SimpleNamespace(stdin=io.StringIO()),replies))
    monkeypatch.setattr(paddle_engine, '_stop_worker', lambda: None)
    with pytest.raises(paddle_engine.OcrError) as error:
        paddle_engine.recognize_image(Image.new('RGB',(100,100)))
    assert error.value.code == 'OCR_WORKER_CRASH'


def test_native_worker_timeout_is_bounded(monkeypatch):
    import io, queue, types, pytest
    stopped=[]
    def timeout(**kwargs):
        assert kwargs['timeout'] == 70
        raise queue.Empty
    monkeypatch.setattr(paddle_engine, '_get_worker', lambda: (types.SimpleNamespace(stdin=io.StringIO()),types.SimpleNamespace(get=timeout)))
    monkeypatch.setattr(paddle_engine, '_stop_worker', lambda: stopped.append(True))
    with pytest.raises(paddle_engine.OcrError) as error:
        paddle_engine.recognize_image(Image.new('RGB',(100,100)))
    assert error.value.code == 'OCR_TIMEOUT'
    assert stopped


def test_large_pdf_render_is_capped_before_ocr(tmp_path, monkeypatch):
    monkeypatch.setenv('OCR_MAX_SIDE', '1600')
    monkeypatch.setenv('OCR_ENGINE', 'paddleocr')
    import pymupdf
    path = tmp_path / 'large.pdf'
    with pymupdf.open() as doc:
        doc.new_page(width=4000, height=3000)
        doc.save(path)
    sizes = []
    def fake(image):
        sizes.append(image.size)
        return {'words': [], 'lines': [], 'text': '', 'mean_confidence': 0}
    monkeypatch.setattr(ocr_boxes, 'run_image_ocr', fake)
    ocr_boxes.extract_pdf_with_boxes(str(path))
    assert sizes == [(1600, 1200)]


def test_english_only_even_when_other_language_packs_exist(monkeypatch):
    monkeypatch.setattr(ocr_boxes, 'get_available_tesseract_languages', lambda: {'eng', 'hin', 'mar'})
    assert ocr_boxes.get_ocr_language_string() == 'eng'
    assert ocr_extract.get_ocr_language() == 'eng'
