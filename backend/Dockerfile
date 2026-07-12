FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple

COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

RUN addgroup --system --gid 10001 appgroup \
    && adduser --system --uid 10001 --ingroup appgroup --home /app appuser \
    && mkdir -p /app/.runtime \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '5000') + '/api/health', timeout=3)" || exit 1

CMD ["sh", "-c", "exec gunicorn -w ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} -b 0.0.0.0:${PORT:-5000} --timeout ${GUNICORN_TIMEOUT:-60} wsgi:app"]
