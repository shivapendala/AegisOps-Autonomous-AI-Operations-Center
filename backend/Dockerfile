# ==============================================================================
# AegisOps Backend Dockerfile
# Production-ready Python 3.11 image for FastAPI & Real-Time Monitoring Engine
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies needed for compiling psycopg2 and health checking
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend, models, database, and monitoring application code
COPY aegisops /app/aegisops
COPY backend /app/backend
COPY database /app/database
COPY monitoring /app/monitoring

# Expose backend REST & WebSocket port
EXPOSE 8000

# Health check to ensure FastAPI backend is responsive
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start Uvicorn ASGI server
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
