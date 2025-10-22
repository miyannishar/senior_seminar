# Multi-stage Dockerfile for Trustworthy RAG System
# Optimized for production deployment

# Stage 1: Base image with dependencies
FROM python:3.11-slim as base

LABEL maintainer="Trustworthy RAG Team"
LABEL description="Production-ready RAG system with privacy and security"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Dependencies
FROM base as dependencies

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Application
FROM base as application

# Copy dependencies from previous stage
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ /app/src/
COPY data/ /app/data/
COPY README.md /app/
COPY ARCHITECTURE.md /app/

# Create logs directory
RUN mkdir -p /app/logs

# Create non-root user for security
RUN useradd -m -u 1000 raguser && \
    chown -R raguser:raguser /app

USER raguser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports
EXPOSE 8000

# Default command - run API server
CMD ["python", "-m", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]

