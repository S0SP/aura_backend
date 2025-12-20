# ==========================================
# AURA Fact-Checker - Backend Dockerfile
# Production-ready multi-stage build
# ==========================================

# Stage 1: Base image with dependencies
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Stage 2: Dependencies installation
FROM base AS dependencies

WORKDIR /app

# Copy requirements first for better caching
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Stage 3: Production image
FROM dependencies AS production

WORKDIR /app

# Copy application code
COPY backend/ .

# Create logs directory
RUN mkdir -p logs

# Create non-root user for security
RUN adduser --disabled-password --gecos '' --uid 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# ==========================================
# Development stage (optional)
# ==========================================
FROM dependencies AS development

WORKDIR /app

COPY backend/ .

RUN mkdir -p logs

# Install dev dependencies
RUN pip install pytest pytest-asyncio pytest-cov black isort flake8

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
