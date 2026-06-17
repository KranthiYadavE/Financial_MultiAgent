FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic pydantic-settings aiokafka kafka-python redis python-json-logger prometheus-client prometheus-fastapi-instrumentator tenacity
COPY shared/ ./shared/
COPY services/orchestrator/ ./services/orchestrator/
COPY services/stream_worker/ ./services/stream_worker/
ENV PYTHONPATH=/app
EXPOSE 8010
CMD ["uvicorn", "services.stream_worker.main:app", "--host", "0.0.0.0", "--port", "8010"]
