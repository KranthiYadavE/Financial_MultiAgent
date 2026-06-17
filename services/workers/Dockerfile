FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic pydantic-settings aiokafka kafka-python redis python-json-logger prometheus-client prometheus-fastapi-instrumentator tenacity
COPY shared/ ./shared/
COPY services/orchestrator/ ./services/orchestrator/
COPY services/workers/ ./services/workers/
ENV PYTHONPATH=/app
ENV WORKER_PORT=8011
EXPOSE 8011
CMD ["sh", "-c", "uvicorn services.workers.main:app --host 0.0.0.0 --port ${WORKER_PORT}"]
