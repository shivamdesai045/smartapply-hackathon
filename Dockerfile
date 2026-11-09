FROM python:3.13-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 \
    PADDLE_PDX_CACHE_HOME=/opt/paddle-cache PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
    PADDLE_PDX_MODEL_SOURCE=huggingface HF_HUB_DISABLE_XET=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-eng libgomp1 libglib2.0-0 libgl1 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
# Download English mobile models at image-build time, not during the first upload.
RUN python -c "from paddle_engine import _get_engine; _get_engine()"
EXPOSE 10000
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
