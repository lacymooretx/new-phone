FROM python:3.12-slim-bookworm

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY alembic.ini .
COPY alembic/ alembic/
COPY tests/ tests/

# Install dependencies
RUN uv pip install --system -e ".[dev]"

# Default command
CMD ["uvicorn", "new_phone.main:app", "--host", "0.0.0.0", "--port", "8000"]
