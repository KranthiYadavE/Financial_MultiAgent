# File Guide — What Every File Does

Use this as your **study map**. Read files in the order listed under [Recommended Reading Order](#recommended-reading-order).

---

## Root

| File | What it does | Study focus |
|------|--------------|-------------|
| `README.md` | Project overview, quick start, ports | Start here |
| `.env.example` | Environment variable template | Config / secrets |
| `requirements.txt` | Python dependencies | What libraries are used |
| `docker-compose.yml` | Full stack: DB, Kafka, Redis, ELK, agents, workers | Infrastructure wiring |
| `docker-compose.lite.yml` | Lightweight stack (no Kafka/ELK) | Local dev with less RAM |
| `docker-compose.cloud.yml` | Cloud VM stack (public API + MCP) | Oracle/AWS free tier |

---

## `shared/` — Code used by all services

| File | What it does | Study focus |
|------|--------------|-------------|
| `config.py` | Settings from env (Postgres, Kafka, Redis, Ollama URLs) | 12-factor config |
| `fastapi_app.py` | Factory: health, metrics, correlation-ID middleware | Cross-cutting concerns |
| `logging_setup.py` | JSON logs + `correlation_id` in every log line | Distributed tracing |
| `dlp.py` | PII regex detection and masking rules | Security |
| `llm_client.py` | Ollama HTTP client with fallback | Local LLM integration |
| `redis_client.py` | Cache, rate limiting, request state | Performance + guardrails |
| `kafka_topics.py` | Topic names, partitions, intent → topic map | Kafka design |
| `kafka_worker.py` | Shared worker: process, retry, DLQ, cache | Event-driven processing |
| `mcp_handlers.py` | HTTP bridge from MCP tools to microservices | MCP integration |

---

## `services/mcp_server/` — MCP for LLM clients (Cursor, agents)

| File | What it does | Study focus |
|------|--------------|-------------|
| `server.py` | FastMCP tools, resources, prompts | Model Context Protocol |
| `run_stdio.py` | Stdio transport for Cursor | Local MCP connection |
| `Dockerfile` | MCP HTTP server container (port 8020) | Deployment |

**Tools:** `mcp_query_transactions`, `mcp_ask_policy`, `mcp_mask_sensitive_text`, `mcp_financial_chat`, `mcp_agents_health`

**Guide:** [MCP_GUIDE.md](MCP_GUIDE.md)

---

## `services/orchestrator/` — API gateway & router

| File | What it does | Study focus |
|------|--------------|-------------|
| `main.py` | `POST /chat` — DLP, route, Kafka publish, wait for response | Request lifecycle |
| `router.py` | Keyword + Ollama intent classification | Routing logic |
| `kafka_bus.py` | Async Kafka producer/consumer with partition keys | Event bus |
| `Dockerfile` | Container image for orchestrator | Deployment |

**Key endpoints:** `/chat`, `/agents/status`, `/kafka/status`, `/mcp/info`, `/cache/status`, `/metrics`

---

## `services/workers/` — Intent-specific Kafka consumers

| File | What it does | Study focus |
|------|--------------|-------------|
| `main.py` | One worker per intent (`WORKER_INTENT` env) | Consumer groups |
| `Dockerfile` | Shared image for all worker types | Scale with `--scale` |

**Containers:** `sql-worker` (8011), `rag-worker` (8012), `dlp-worker` (8013), `fallback-worker` (8014)

> **Note:** `services/stream_worker/` is the older single-topic worker — replaced by intent workers.

---

## `services/dlp_agent/`

| File | What it does | Study focus |
|------|--------------|-------------|
| `main.py` | `POST /mask` — mask PII in text | Input security |
| `Dockerfile` | DLP service container | — |

---

## `services/text_to_sql_agent/`

| File | What it does | Study focus |
|------|--------------|-------------|
| `main.py` | NL → SQL → PostgreSQL (read-only role) | SQL injection defense |
| `Dockerfile` | SQL agent container | — |

---

## `services/rag_agent/`

| File | What it does | Study focus |
|------|--------------|-------------|
| `main.py` | Embed question → Qdrant search → answer | RAG pipeline |
| `Dockerfile` | RAG agent container | — |

---

## `scripts/` — Data & ops

| File | What it does | Study focus |
|------|--------------|-------------|
| `generate_sample_data.py` | Bronze → Silver → Gold parquet + FAQ docs | Medallion architecture |
| `load_to_postgres.py` | Gold parquet → PostgreSQL | ETL |
| `ingest_embeddings.py` | FAQ docs → Qdrant vectors | RAG indexing |
| `init_kafka_topics.sh` | Create Kafka topics with partition counts | Kafka ops |
| `mcp_client_demo.py` | Demo MCP client (list tools, call health) | MCP learning |
| `run_init.py` | Full local data initialization | One-command setup |
| `test_api.py` | Smoke test all intents via `/chat` | Integration testing |
| `verify_pipeline.py` | Validate data files and DB load | Data quality |
| `run_full_verify.ps1` | PowerShell end-to-end verification | Windows workflow |
| `Dockerfile` | Image for `data-init` compose profile | — |

---

## `data/` — Datasets

| Path | What it does | Study focus |
|------|--------------|-------------|
| `bronze/` | Raw parquet (generated locally) | Landing zone |
| `silver/` | Cleaned parquet | Data quality |
| `gold/` | Analytics-ready parquet | Business tables |
| `docs/` | FAQ/policy JSON + txt for RAG | Unstructured knowledge |

---

## `infra/postgres/`

| File | What it does | Study focus |
|------|--------------|-------------|
| `init.sql` | `gold` schema, read-only role, RLS | DB security |

---

## `monitoring/`

| Path | What it does | Study focus |
|------|--------------|-------------|
| `prometheus/prometheus.yml` | Scrape targets for all services + workers | Metrics collection |
| `grafana/provisioning/` | Auto-loaded dashboards | Visualization |
| `logstash/pipeline/logstash.conf` | JSON log ingestion → Elasticsearch | Log pipeline |

---

## `deploy/` — Cloud deployment scripts

| Path | Purpose |
|------|---------|
| `deploy/cloud/.env.cloud.example` | Cloud VM environment template |
| `deploy/vm/setup-ubuntu.sh` | Bootstrap Ubuntu VM with Docker |
| `deploy/scripts/build-images.ps1` | Build all service Docker images |
| `deploy/scripts/push-images.ps1` | Push images to GHCR |

---

## `k8s/` — Kubernetes manifests

See [k8s/README.md](../k8s/README.md) and [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md).

---

## `docs/` — Learning materials

| File | What it does |
|------|--------------|
| `FULL_LEARNING_PLAN.md` | **12-week master study path** |
| `ARCHITECTURE.md` | System diagrams and request lifecycle |
| `BUILD_CHECKLIST.md` | Week-by-week hands-on checklist |
| `LEARNING_ROADMAP.md` | Per-component study guide |
| `KAFKA_GUIDE.md` | Kafka topics, partitions, DLQ, scaling labs |
| `MCP_GUIDE.md` | MCP tools, Cursor setup, client demo |
| `CLOUD_DEPLOYMENT.md` | VM, K8s, GHCR, managed cloud services |
| `FILE_GUIDE.md` | This file |

---

## Recommended Reading Order

### Week 1 — Data foundation
1. `scripts/generate_sample_data.py`
2. `infra/postgres/init.sql`
3. `scripts/load_to_postgres.py`
4. `scripts/ingest_embeddings.py`

### Week 2 — Security & agents
5. `shared/dlp.py` → `services/dlp_agent/main.py`
6. `services/text_to_sql_agent/main.py`
7. `services/rag_agent/main.py`

### Week 3 — Orchestration
8. `shared/fastapi_app.py` → `shared/logging_setup.py`
9. `services/orchestrator/router.py`
10. `services/orchestrator/main.py`

### Week 4 — Event streaming
11. `shared/kafka_topics.py`
12. `services/orchestrator/kafka_bus.py`
13. `shared/kafka_worker.py` → `services/workers/main.py`
14. `scripts/init_kafka_topics.sh`
15. `docs/KAFKA_GUIDE.md`

### Week 5 — Cache
16. `shared/redis_client.py`

### Week 6 — MCP
17. `shared/mcp_handlers.py` → `services/mcp_server/server.py`
18. `scripts/mcp_client_demo.py`
19. `docs/MCP_GUIDE.md`

### Week 7 — Observability
20. `monitoring/prometheus/prometheus.yml`
21. `monitoring/logstash/pipeline/logstash.conf`

### Week 8+ — Deployment
22. `docker-compose.yml`
23. `k8s/`

> Full 12-week path: [FULL_LEARNING_PLAN.md](FULL_LEARNING_PLAN.md)

---

## Port Reference

| Service | Port |
|---------|------|
| Orchestrator | 8000 |
| DLP | 8001 |
| Text-to-SQL | 8002 |
| RAG | 8003 |
| SQL worker | 8011 |
| RAG worker | 8012 |
| DLP worker | 8013 |
| Fallback worker | 8014 |
| MCP server | 8020 |
| Kafka | 9092 |
| Redis | 6379 |
| Postgres | 5432 |
| Qdrant | 6333 |
| Prometheus | 9090 |
| Grafana | 3000 |
| Kibana | 5601 |
