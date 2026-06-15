FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic pydantic-settings sqlalchemy psycopg2-binary python-json-logger prometheus-client prometheus-fastapi-instrumentator sqlparse tenacity
COPY shared/ ./shared/
COPY services/text_to_sql_agent/ ./services/text_to_sql_agent/
ENV PYTHONPATH=/app
EXPOSE 8002
CMD ["uvicorn", "services.text_to_sql_agent.main:app", "--host", "0.0.0.0", "--port", "8002"]
