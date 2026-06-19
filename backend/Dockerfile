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

EXPOSE 5000

CMD ["gunicorn", "-w", "2", "--threads", "4", "-b", "0.0.0.0:5000", "--timeout", "60", "wsgi:app"]
