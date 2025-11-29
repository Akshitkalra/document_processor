# Python 3.11 + Tesseract OCR
FROM python:3.11-slim

# System dependencies: Tesseract (OCR engine) and libGL for PyMuPDF/Pillow.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# Install the CPU-only PyTorch build first (no CUDA) so sentence-transformers
# reuses it instead of pulling ~2 GB of NVIDIA CUDA wheels. This runs on CPU.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
