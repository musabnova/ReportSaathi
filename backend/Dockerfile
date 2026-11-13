# =============================================================================
# ReportSaathi - Backend Dockerfile
# Production-ready container image for Python 3.11 with OCR and Poppler support
# Designed for deployment on platforms like Render, Cloud Run, or Docker Compose
# =============================================================================

FROM python:3.11-slim

# Prevent Python from writing bytecode (.pyc) and enable unbuffered streaming logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install Linux system dependencies:
# - tesseract-ocr: Tesseract OCR engine
# - tesseract-ocr-hin: Hindi language trained data
# - tesseract-ocr-kan: Kannada language trained data
# - poppler-utils: pdftoppm utility used by pdf2image for scanned PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-kan \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside container
WORKDIR /app

# Install Python dependencies first (leverages Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code into container
# Note: Sensitive files like .env and virtual environments are excluded via .dockerignore
COPY . .

# Expose standard application port (informational)
EXPOSE 8000

# Start FastAPI application using uvicorn
# Uses shell form to dynamically resolve the $PORT environment variable assigned by hosting platforms (e.g., Render)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

