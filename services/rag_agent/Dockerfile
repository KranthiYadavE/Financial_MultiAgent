FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic pydantic-settings qdrant-client sentence-transformers python-json-logger prometheus-client prometheus-fastapi-instrumentator tenacity
COPY shared/ ./shared/
COPY services/rag_agent/ ./services/rag_agent/
ENV PYTHONPATH=/app
EXPOSE 8003
CMD ["uvicorn", "services.rag_agent.main:app", "--host", "0.0.0.0", "--port", "8003"]
