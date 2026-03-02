FROM python:3.12-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir . && pip install --no-cache-dir setuptools

# Run as non-root user
RUN adduser --disabled-password --gecos "" --uid 1000 appuser
USER appuser

EXPOSE 8090 8091
CMD ["python", "-m", "uvicorn", "ai_engine.main:app", "--host", "0.0.0.0", "--port", "8091"]
