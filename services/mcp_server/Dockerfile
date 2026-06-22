FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir mcp httpx pydantic pydantic-settings python-json-logger
COPY shared/ ./shared/
COPY services/mcp_server/ ./services/mcp_server/
COPY infra/ ./infra/
COPY data/docs/ ./data/docs/
ENV PYTHONPATH=/app
EXPOSE 8020
CMD ["python", "-m", "services.mcp_server.server"]
