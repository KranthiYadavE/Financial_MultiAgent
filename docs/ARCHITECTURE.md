# System Architecture

## High-Level Diagram

```mermaid
flowchart TB
    User[User / API Client] --> Orch[Orchestrator :8000]
    Orch --> Router{Intent Router}
    Router -->|transactions| SQL[Text-to-SQL Agent :8002]
    Router -->|policy/faq| RAG[RAG Agent :8003]
    Router -->|mask pii| DLP[DLP Agent :8001]
    Router -->|all paths| DLP

    Orch --> Kafka[(Kafka Event Bus)]
    Kafka --> Topics[agent.requests / agent.responses]

    SQL --> PG[(PostgreSQL Gold)]
    RAG --> QD[(Qdrant Vector DB)]
    RAG --> Embed[Sentence Transformers]

    SQL --> Ollama[Ollama LLM - local free]
    RAG --> Ollama
    Orch --> Ollama

    Orch --> Prom[Prometheus]
    SQL --> Prom
    RAG --> Prom
    DLP --> Prom
    Prom --> Graf[Grafana Dashboards]

    Orch --> Logs[JSON Logs]
    Logs --> LS[Logstash]
    LS --> ES[(Elasticsearch)]
    ES --> Kib[Kibana]

    Bronze[Bronze Parquet] --> Silver[Silver Parquet]
    Silver --> Gold[Gold Parquet + PostgreSQL]
    Docs[FAQ/Policy JSON] --> QD
```

## Medallion Data Flow

```mermaid
flowchart LR
  Raw[Raw Feeds] --> B[Bronze Layer]
  B --> S[Silver Layer]
  S --> G[Gold Layer]
  G --> PG[(PostgreSQL)]
  Docs[Policy Docs] --> Emb[Embeddings]
  Emb --> QD[(Qdrant)]
```

## Request Lifecycle

1. User sends message to `POST /chat`
2. **DLP Agent** masks PII in the user message (hard filter)
3. **Router** classifies intent (keyword rules + optional Ollama)
4. Event published to **Kafka** (`agent.requests`)
5. Appropriate agent handles the request
6. Response published to **Kafka** (`agent.responses`)
7. Structured JSON logs flow to **ELK**; metrics to **Prometheus/Grafana**

## Security Layers

| Layer | Mechanism |
|-------|-----------|
| Input | DLP regex masking + hard block |
| SQL | SELECT-only validation, sqlparse |
| DB | `agent_readonly` role, RLS enabled |
| Output | Column masking for PAN/account in results |
| Schema | Aliased column names in LLM prompts |
