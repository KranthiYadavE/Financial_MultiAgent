FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic pydantic-settings python-json-logger prometheus-client prometheus-fastapi-instrumentator sqlparse tenacity
COPY shared/ ./shared/
COPY services/dlp_agent/ ./services/dlp_agent/
ENV PYTHONPATH=/app
EXPOSE 8001
CMD ["uvicorn", "services.dlp_agent.main:app", "--host", "0.0.0.0", "--port", "8001"]
