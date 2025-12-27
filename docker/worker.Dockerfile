FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY packages/core/src /app/packages/core/src
COPY apps/api/src /app/apps/api/src
COPY apps/worker/src /app/apps/worker/src
COPY storage /app/storage

ENV PYTHONPATH=/app/packages/core/src:/app/apps/api/src:/app/apps/worker/src

CMD ["python", "-m", "trustai_worker.worker"]
