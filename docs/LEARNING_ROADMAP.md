# Learning Roadmap by Component

> **Start here:** [FILE_GUIDE.md](FILE_GUIDE.md) lists every file and a recommended reading order.

## FastAPI Microservices
**What to learn:** routing, Pydantic models, lifespan hooks, middleware  
**Files:** `services/*/main.py`, `shared/fastapi_app.py`  
**Exercise:** Add a `/version` endpoint to each service

## PostgreSQL + Text-to-SQL
**What to learn:** schema design, read-only roles, RLS, SQL injection prevention  
**Files:** `infra/postgres/init.sql`, `services/text_to_sql_agent/main.py`  
**Exercise:** Add a new `gold.merchants` table and extend the SQL agent

## Qdrant + RAG
**What to learn:** embeddings, cosine similarity, chunking, retrieval-augmented generation  
**Files:** `scripts/ingest_embeddings.py`, `services/rag_agent/main.py`  
**Exercise:** Add 3 new FAQ docs and re-ingest; measure retrieval scores

## DLP & Security
**What to learn:** regex PII detection, defense in depth, schema masking  
**Files:** `shared/dlp.py`, `services/dlp_agent/main.py`  
**Exercise:** Add Aadhaar number detection pattern

## Kafka Event Bus (production patterns)
**What to learn:** topics, partitions, partition keys, consumer groups, DLQ, horizontal scaling  
**Files:** `shared/kafka_topics.py`, `services/orchestrator/kafka_bus.py`, `shared/kafka_worker.py`, `services/workers/main.py`, `scripts/init_kafka_topics.sh`  
**Guide:** [KAFKA_GUIDE.md](KAFKA_GUIDE.md)  
**Exercises:**
- Scale `sql-worker` to 2 replicas and inspect `kafka-consumer-groups`
- Trace one `correlation_id` from orchestrator → intent topic → worker → responses topic
- Read a message from `agent.requests.dlq` after a simulated agent failure

## Redis Cache & Rate Limiting
**What to learn:** TTL caches, sliding-window rate limits, request state  
**Files:** `shared/redis_client.py`, orchestrator `/cache/status`  
**Exercise:** Add a cache invalidation endpoint; tune `REDIS_RATE_LIMIT_PER_MINUTE`

## Medallion Architecture
**What to learn:** Bronze (raw) → Silver (cleaned) → Gold (analytics-ready)  
**Files:** `scripts/generate_sample_data.py`, `scripts/load_to_postgres.py`  
**Exercise:** Add a Silver validation step that rejects invalid PAN formats

## Observability
**What to learn:** structured logging, Prometheus metrics, Grafana dashboards, ELK  
**Files:** `shared/logging_setup.py`, `monitoring/`  
**Exercise:** Add a custom metric `dlp_findings_total` labeled by finding type

## Ollama (Free LLM)
**What to learn:** local inference, prompt engineering, fallbacks  
**Files:** `shared/llm_client.py`  
**Exercise:** Compare answers with and without Ollama running

## Kubernetes
**What to learn:** Deployments, Services, ConfigMaps, probes, autoscaling  
**Files:** `k8s/`  
**Exercise:** Deploy to minikube and scale orchestrator to 3 replicas

## Recommended Free Resources
- FastAPI docs: https://fastapi.tiangolo.com
- Qdrant docs: https://qdrant.tech/documentation
- Kafka concepts: https://kafka.apache.org/documentation
- Prometheus: https://prometheus.io/docs
- LangChain: https://python.langchain.com
- Ollama: https://ollama.com
