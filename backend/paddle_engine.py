"""Local PaddleOCR adapter. Models are cached once; documents are inferred locally."""
import os
import threading
from pathlib import Path

# Bound native thread pools before NumPy/Paddle are imported.
for variable in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(variable, '2')

import numpy as np
from PIL import ImageOps

os.environ.setdefault('PADDLE_PDX_CACHE_HOME', str(Path(__file__).resolve().parents[1] / 'work' / 'paddle-cache'))
os.environ.setdefault('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK', 'True')
os.environ.setdefault('PADDLE_PDX_MODEL_SOURCE', 'huggingface')
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
_engine = None
_lock = threading.Lock()
_warmup_done = threading.Event()
_warmup_done.set()


def _get_engine():
    global _engine
    if _engine is None:
        print('OCR_STAGE loading_models', flush=True)
        from paddleocr import PaddleOCR
        cache = Path(os.environ['PADDLE_PDX_CACHE_HOME']) / 'official_models'
        local_models = {}
        for option, name in [('text_detection_model_dir', 'PP-OCRv5_mobile_det'),
                             ('text_recognition_model_dir', 'en_PP-OCRv5_mobile_rec'),
                             ('textline_orientation_model_dir', 'PP-LCNet_x1_0_textline_ori')]:
            if (cache / name / 'inference.pdiparams').is_file():
                local_models[option] = str(cache / name)
        _engine = PaddleOCR(
            **local_models,
            ocr_version='PP-OCRv5',
            text_detection_model_name='PP-OCRv5_mobile_det',
            text_recognition_model_name='en_PP-OCRv5_mobile_rec',
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=os.getenv("OCR_LINE_ORIENTATION", "0") == "1",
            device='cpu', enable_mkldnn=False, cpu_threads=max(1,min(4,int(os.getenv('OCR_CPU_THREADS','2')))),
            text_recognition_batch_size=max(1, min(8, int(os.getenv("OCR_REC_BATCH_SIZE", "1")))), text_det_limit_side_len=int(os.getenv('OCR_DET_MAX_SIDE','960')), text_det_limit_type='max',
        )
    return _engine


def convert_result(result, width, height):
    words, lines = [], []
    for index, (text, score, polygon) in enumerate(zip(result['rec_texts'], result['rec_scores'], result['rec_polys'])):
        text = str(text).strip()
        if not text:
            continue
        points = np.asarray(polygon)
        x0, y0 = points.min(axis=0)
        x1, y1 = points.max(axis=0)
        bbox = [max(0., min(1., float(value))) for value in (x0/width, y0/height, x1/width, y1/height)]
        word = {'text': text, 'confidence': round(float(score)*100, 2), 'bbox': bbox,
                'pixel_bbox': [float(x0), float(y0), float(x1), float(y1)], 'line_no': index, 'word_no': 0,
                'granularity': 'text_line'}
        words.append(word)
        lines.append({'text': text, 'bbox': bbox, 'pixel_bbox': word['pixel_bbox'],
                      'mean_confidence': word['confidence'], 'words': [word]})
    return {'text': '\n'.join(line['text'] for line in lines), 'words': words, 'lines': lines,
            'mean_confidence': round(sum(w['confidence'] for w in words)/len(words), 2) if words else 0,
            'width': width, 'height': height, 'engine': 'paddleocr', 'passes': []}


def _recognize_in_process(image):
    image = ImageOps.exif_transpose(image).convert('RGB')
    image.thumbnail((int(os.getenv("OCR_MAX_SIDE", "1600")),) * 2)
    width, height = image.size
    # Paddle accepts BGR arrays. Predictor instances are shared but not thread-safe.
    array = np.asarray(image)[:, :, ::-1].copy()
    with _lock:
        import time
        started = time.monotonic()
        engine = _get_engine()
        loaded = time.monotonic()
        print('OCR_STAGE inference', flush=True)
        cpu_started = time.process_time()
        result = next(iter(engine.predict(array)))
        # Only timings and image dimensions; never document text.
        print('OCR_TIMING load=%.2f infer=%.2f cpu=%.2f size=%dx%d' % (loaded-started, time.monotonic()-loaded, time.process_time()-cpu_started, width, height), flush=True)
        converted = convert_result(result, width, height)
        converted['timings'] = {'model_load_seconds': round(loaded-started, 3),
                                'inference_seconds': round(time.monotonic()-loaded, 3),
                                'inference_cpu_seconds': round(time.process_time()-cpu_started, 3)}
        return converted


class OcrError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


_worker = None
_replies = None
_worker_ready = threading.Event()


def _stop_worker():
    global _worker, _replies
    _worker_ready.clear()
    if _worker is not None:
        if _worker.poll() is None:
            _worker.kill()
        _worker.wait(timeout=5)
        for stream in (_worker.stdin, _worker.stdout, _worker.stderr):
            if stream:
                stream.close()
    _worker = None
    _replies = None


def _get_worker():
    import subprocess, sys, queue, json
    global _worker, _replies
    if _worker is not None and _worker.poll() is None:
        return _worker, _replies
    _stop_worker()
    bootstrap = "import sys,runpy;sys.path[:0]=" + repr(sys.path) + ";sys.argv=" + repr([str(Path(__file__).resolve()), '--serve']) + ";runpy.run_path(sys.argv[0],run_name='__main__')"
    process = subprocess.Popen(
        [getattr(sys, '_base_executable', sys.executable), '-u', '-c', bootstrap],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )
    replies = queue.Queue()
    def read_replies():
        try:
            for line in process.stdout:
                if line.startswith('SAHAYAK_RESULT '):
                    replies.put(json.loads(line[len('SAHAYAK_RESULT '):]))
        except (ValueError, OSError):
            pass
        finally:
            replies.put({'error': 'OCR_WORKER_CRASH'})
    def read_diagnostics():
        import logging
        try:
            for line in process.stderr:
                if line.startswith(('OCR_TIMING ', 'OCR_STAGE ')):
                    logging.warning(line.strip())
        except (ValueError, OSError):
            pass
    threading.Thread(target=read_diagnostics, daemon=True).start()
    threading.Thread(target=read_replies, daemon=True).start()
    _worker, _replies = process, replies
    return process, replies


def recognize_image(image):
    """Reuse a single isolated predictor; native failures cannot kill Flask."""
    if not _warmup_done.wait(timeout=70):
        raise OcrError("OCR_BUSY")
    if not _lock.acquire(timeout=3):
        raise OcrError('OCR_BUSY')
    try:
        return _run_worker(image)
    finally:
        _lock.release()


def _run_worker(image):
    import tempfile, json, queue, time, logging
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='sahayak_ocr_') as directory:
        source, output = Path(directory)/'page.png', Path(directory)/'result.json'
        prepared = ImageOps.exif_transpose(image).convert('RGB')
        prepared.thumbnail((int(os.getenv("OCR_MAX_SIDE", "1600")),) * 2)
        prepared.save(source, compress_level=1)
        del prepared
        prepared_at = time.monotonic()
        process, replies = _get_worker()
        try:
            process.stdin.write(json.dumps({'source': str(source), 'output': str(output)}) + '\n')
            process.stdin.flush()
            reply = replies.get(timeout=70)
            if reply.get('error') or not output.exists():
                raise OcrError(reply.get('error', 'OCR_WORKER_CRASH'))
            result = json.loads(output.read_text(encoding='utf-8'))
            _worker_ready.set()
            result['ocr_seconds'] = round(time.monotonic()-started, 2)
            result.setdefault('timings', {}).update(prepare_seconds=round(prepared_at-started, 3),
                                                   worker_roundtrip_seconds=round(time.monotonic()-prepared_at, 3))
            return result
        except queue.Empty:
            _stop_worker()
            logging.warning('OCR worker timeout after %.1fs', time.monotonic()-started)
            raise OcrError('OCR_TIMEOUT') from None
        except (OcrError, BrokenPipeError, OSError) as exc:
            _stop_worker()
            code = getattr(exc, 'code', 'OCR_WORKER_CRASH')
            logging.warning('OCR worker failure: %s after %.1fs', code, time.monotonic()-started)
            raise OcrError(code) from None


def worker_status():
    alive = _worker is not None and _worker.poll() is None
    return {'ready': bool(alive and _worker_ready.is_set() and _warmup_done.is_set()),
            'warming': not _warmup_done.is_set(), 'engine': 'paddleocr'}


def start_warmup():
    _warmup_done.clear()
    def warm():
        import logging
        from PIL import Image, ImageDraw
        page = Image.new('RGB', (400, 120), 'white')
        ImageDraw.Draw(page).text((20, 30), 'OCR readiness check', fill='black')
        try:
            with _lock:
                _run_worker(page)
            from parsers.ml_generalizer import get_classifier
            get_classifier()  # Avoid a second lazy model load on the first difficult document.
            logging.warning('OCR warmup ready')
        except OcrError as exc:
            logging.warning('OCR warmup failed: %s', exc.code)
        finally:
            _warmup_done.set()
    threading.Thread(target=warm, daemon=True).start()


import atexit
atexit.register(_stop_worker)


if __name__ == '__main__':
    import json, sys, contextlib
    from PIL import Image
    def handle(source, output):
        # Model logging must not contaminate the reply protocol. Never log page text.
        with contextlib.redirect_stdout(sys.stderr), Image.open(source) as page:
            result = _recognize_in_process(page)
        Path(output).write_text(json.dumps(result), encoding='utf-8')
    if len(sys.argv) > 1 and sys.argv[1] == '--serve':
        for command in sys.stdin:
            try:
                job = json.loads(command)
                handle(job['source'], job['output'])
                reply = {'ok': True}
            except Exception as exc:
                reply = {'error': 'OCR_MODEL_ERROR', 'exception_type': type(exc).__name__}
            print('SAHAYAK_RESULT ' + json.dumps(reply), flush=True)
    else:
        handle(sys.argv[1], sys.argv[2])
