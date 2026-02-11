# Citation Format Checker — Docker image for GCP Cloud Run
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Install dependencies from lockfile
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY app.py index.html ./

# Cloud Run sets PORT at runtime
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uv run uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
