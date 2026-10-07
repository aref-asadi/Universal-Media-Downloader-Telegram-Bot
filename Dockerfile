# Dockerfile for Universal Media Downloader Bot (Render optimized)
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 botuser
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /tmp/ubd/downloads /tmp/ubd/logs && chown -R botuser:botuser /tmp/ubd
COPY --chown=botuser:botuser . .
USER botuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONMALLOC=malloc
ENV RENDER=true

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8082/health || exit 1

CMD ["python", "-m", "bot.main"]