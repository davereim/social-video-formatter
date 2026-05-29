FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
COPY ui ./ui

RUN pip install --upgrade pip && pip install .

RUN mkdir -p /app/data

EXPOSE 8080

CMD ["sh", "-c", "python -m uvicorn social_video_formatter.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
