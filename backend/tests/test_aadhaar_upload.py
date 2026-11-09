import io
import pytest
import pymupdf as fitz
from PIL import Image
from werkzeug.datastructures import FileStorage
from aadhaar_upload import combine_aadhaar_photos


def photo(color='white'):
    stream = io.BytesIO()
    Image.new('RGB', (800, 500), color).save(stream, format='PNG')
    stream.seek(0)
    return FileStorage(stream=stream, filename='synthetic.png')


def test_two_photos_become_two_distinct_pdf_pages():
    result = combine_aadhaar_photos([photo('red'), photo('blue')])
    with fitz.open(stream=result.stream.read(), filetype='pdf') as pdf:
        assert len(pdf) == 2
        assert pdf[0].get_pixmap().samples[:3] == bytes([255, 0, 0])
        assert pdf[1].get_pixmap().samples[:3] == bytes([0, 0, 255])


@pytest.mark.parametrize('count', [0, 1, 3])
def test_wrong_file_count_is_rejected(count):
    with pytest.raises(ValueError):
        combine_aadhaar_photos([photo() for _ in range(count)])


def test_invalid_or_mislabelled_images_are_rejected():
    with pytest.raises(ValueError):
        combine_aadhaar_photos([photo(), FileStorage(stream=io.BytesIO(b'not an image'), filename='back.png')])
    wrong = photo()
    wrong.filename = 'back.jpg'
    with pytest.raises(ValueError):
        combine_aadhaar_photos([photo(), wrong])
