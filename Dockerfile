# Production Dockerfile for AI Radio Presenter System

FROM python:3.11.9-slim as base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 radio && chown -R radio:radio /app

FROM base as builder
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM base as runtime
COPY --from=builder /root/.local /home/radio/.local
ENV PATH=/home/radio/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
COPY --chown=radio:radio . .
USER radio

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python - <<'PY'
import urllib.request
try:
    urllib.request.urlopen('http://127.0.0.1:10000/health', timeout=5)
except Exception:
    raise SystemExit(1)
PY

EXPOSE 10000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
