FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install CPU-only PyTorch first (avoids pulling ~4GB of CUDA libs)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install backend deps
COPY backend/pyproject.toml .
RUN pip install --no-cache-dir .

# Copy the engine package from repo root
COPY mcp_embedded_docs/ /app/mcp_embedded_docs/

# Copy backend application code
COPY backend/app/ /app/app/
COPY backend/alembic.ini /app/alembic.ini
COPY backend/alembic/ /app/alembic/

# Ensure app is importable
ENV PYTHONPATH=/app

RUN mkdir -p /data/uploads /data/indices

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
