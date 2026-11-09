"""Combine two local card photos into one lossless, two-page PDF for review."""
import io
from pathlib import Path

import pymupdf as fitz
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.datastructures import FileStorage

MAX_BYTES = 10 * 1024 * 1024
IMAGE_FORMATS = {'.png': 'PNG', '.jpg': 'JPEG', '.jpeg': 'JPEG', '.webp': 'WEBP',
                 '.bmp': 'BMP', '.tiff': 'TIFF'}


def combine_aadhaar_photos(files):
    if len(files) != 2:
        raise ValueError('Select exactly two Aadhaar photos, or one PDF containing both sides.')
    with fitz.open() as pdf:
        for file in files:
            extension = Path(file.filename or '').suffix.lower()
            if extension not in IMAGE_FORMATS:
                raise ValueError('For two files, select front and back images. Upload a PDF on its own.')
            content = file.stream.read(MAX_BYTES + 1)
            if not content or len(content) > MAX_BYTES:
                raise ValueError('Each Aadhaar image must be between 1 byte and 10 MB.')
            try:
                with Image.open(io.BytesIO(content)) as source:
                    if source.format != IMAGE_FORMATS[extension] or source.width * source.height > 40_000_000:
                        raise ValueError('Invalid image format or image dimensions exceed 40 megapixels.')
                    image = ImageOps.exif_transpose(source).convert('RGB')
                    encoded = io.BytesIO()
                    image.save(encoded, format='PNG')
                    page = pdf.new_page(width=image.width * .48, height=image.height * .48)
                    page.insert_image(page.rect, stream=encoded.getvalue())
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
                raise ValueError('One of the Aadhaar images is unreadable. Select a valid image.') from exc
        output = pdf.tobytes(deflate=True)
    if len(output) > MAX_BYTES:
        raise ValueError('The combined Aadhaar file exceeds 10 MB. Use smaller images.')
    return FileStorage(stream=io.BytesIO(output), filename='aadhaar-both-sides.pdf', content_type='application/pdf')
