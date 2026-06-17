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

---

## `services/orchestrator/` — API gateway & router

| File | What it does | Study focus |
|------|--------------|-------------|
| `main.py` | `POST /chat` — DLP, route, Kafka publish, wait for response | Request lifecycle |
| `router.py` | Keyword + Ollama intent classification | Routing logic |
| `kafka_bus.py` | Async Kafka producer/consumer with partition keys | Event bus |
| `Dockerfile` | Container image for orchestrator | Deployment |

**Key endpoints:** `/chat`, `/agents/status`, `/kafka/status`, `/cache/status`, `/metrics`

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

## `k8s/` — Kubernetes (learning)

| File | What it does | Study focus |
|------|--------------|-------------|
| `namespace.yaml` | `financial-agents` namespace | K8s basics |
| `configmap.yaml` | Shared env config | Config management |
| `orchestrator-deployment.yaml` | Sample orchestrator deployment | Probes, replicas |

---

## `docs/` — Learning materials

| File | What it does |
|------|--------------|
| `ARCHITECTURE.md` | System diagrams and request lifecycle |
| `BUILD_CHECKLIST.md` | Week-by-week hands-on checklist |
| `LEARNING_ROADMAP.md` | Per-component study guide |
| `KAFKA_GUIDE.md` | Kafka topics, partitions, DLQ, scaling labs |
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

### Week 5 — Cache & observability
16. `shared/redis_client.py`
17. `monitoring/prometheus/prometheus.yml`
18. `monitoring/logstash/pipeline/logstash.conf`

### Week 6 — Deployment
19. `docker-compose.yml`
20. `k8s/`

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
| Kafka | 9092 |
| Redis | 6379 |
| Postgres | 5432 |
| Qdrant | 6333 |
| Prometheus | 9090 |
| Grafana | 3000 |
| Kibana | 5601 |
