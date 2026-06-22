# Financial Multi-Agent Retrieval System

A **production-style**, **100% open-source** learning project for building a fintech-grade multi-agent system. No paid APIs — uses **Ollama** (local LLM), **sentence-transformers** (local embeddings), and Docker for the full stack.

## What This System Does

| Capability | Agent | Technology |
|------------|-------|------------|
| Transaction lookup | Text-to-SQL | PostgreSQL Gold layer |
| Policy / FAQ answers | RAG | Qdrant + embeddings |
| PII masking | DLP | Regex + hard filtering |
| Request routing | Orchestrator | Keyword + Ollama classifier |
| LLM tool access | MCP Server | Tools, resources, prompts (Cursor-ready) |
| Event workflows | Kafka | Intent topics + partitions + DLQ |
| Caching / rate limits | Redis | Response cache + throttling |
| Logs | ELK | Elasticsearch + Logstash + Kibana |
| Metrics | Prometheus + Grafana | Latency, errors, intent counts |

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for diagrams.  
**Study guides:** [FULL_LEARNING_PLAN.md](docs/FULL_LEARNING_PLAN.md) · [FILE_GUIDE.md](docs/FILE_GUIDE.md) · [KAFKA_GUIDE.md](docs/KAFKA_GUIDE.md) · [MCP_GUIDE.md](docs/MCP_GUIDE.md) · [CLOUD_DEPLOYMENT.md](docs/CLOUD_DEPLOYMENT.md)

```
User → Orchestrator → [DLP] → Router → Kafka (intent topics)
                              ↓              ↓
                           Redis         sql/rag/dlp/fallback workers
                                              ↓
                                    Text-to-SQL | RAG | DLP agents
                                              ↓
                                    PostgreSQL / Qdrant
```

## Project Structure

```
GENAI_TESTING/
├── docker-compose.yml          # Full stack (all services)
├── shared/                     # DLP, logging, LLM client, config
├── services/
│   ├── orchestrator/           # Router + Kafka producer
│   ├── workers/                # Intent-specific Kafka consumers
│   ├── mcp_server/             # MCP tools/resources for LLM clients
│   ├── text_to_sql_agent/      # NL → SQL → transactions
│   ├── rag_agent/              # FAQ/policy semantic search
│   └── dlp_agent/              # PII masking + SQL validation
├── scripts/
│   ├── generate_sample_data.py # Bronze → Silver → Gold + docs
│   ├── init_kafka_topics.sh    # Kafka topic + partition setup
│   ├── load_to_postgres.py
│   ├── ingest_embeddings.py
│   └── test_api.py             # Smoke tests
├── data/
│   ├── bronze/                 # Raw parquet
│   ├── silver/                 # Cleaned parquet
│   ├── gold/                   # Analytics-ready parquet
│   └── docs/                   # Generated FAQ/policy JSON + txt
├── infra/postgres/init.sql     # Gold schema + read-only role
├── monitoring/                 # Prometheus, Grafana, Logstash
├── deploy/                     # Cloud VM bootstrap + image build scripts
├── k8s/                        # Kubernetes manifests (Ingress, HPA)
└── docs/
    ├── FULL_LEARNING_PLAN.md   # 12-week complete study path
    ├── FILE_GUIDE.md           # What every file does
    ├── KAFKA_GUIDE.md          # Topics, partitions, DLQ, scaling labs
    ├── MCP_GUIDE.md            # Model Context Protocol + Cursor setup
    ├── CLOUD_DEPLOYMENT.md     # VM, Kubernetes, GHCR, managed cloud
    ├── ARCHITECTURE.md         # System diagrams
    ├── BUILD_CHECKLIST.md      # Week-by-week tasks
    └── LEARNING_ROADMAP.md     # What to study per component
```

## Prerequisites (All Free)

1. **Docker Desktop** — https://www.docker.com/products/docker-desktop/
2. **Ollama** (optional but recommended) — https://ollama.com
   ```bash
   ollama pull llama3.2:3b
   ```
3. **Python 3.11+** (for local scripts without Docker)

> **RAM:** Full stack needs ~8GB RAM (ELK is the heaviest). For a lighter start: `docker compose up -d postgres qdrant dlp-agent text-to-sql-agent rag-agent orchestrator`

## Quick Start

### 1. Clone and configure

```powershell
cd "c:\Users\HP\OneDrive\Desktop\New folder\GENAI_TESTING"
copy .env.example .env
```

### 2. Generate sample data (optional — pre-generated in `data/`)

```powershell
pip install -r requirements.txt
python scripts/generate_sample_data.py
```

This creates:
- **50 customers**, **~1,100 transactions** (synthetic)
- **8 FAQ/policy documents** for RAG
- Bronze → Silver → Gold parquet files

### 3. Start infrastructure + agents

**Recommended (lighter, ~4GB RAM):**

```powershell
docker compose -f docker-compose.lite.yml up -d --build
```

**Full stack (ELK + Kafka, ~8GB RAM):**

```powershell
docker compose up -d --build
```

Wait ~30s (lite) or ~2 min (full) for health checks.

### 4. Load data into PostgreSQL + Qdrant

```powershell
docker compose -f docker-compose.lite.yml --profile init run --rm data-init
```

### 5. Verify everything works

```powershell
python scripts/verify_pipeline.py
```

Or run the all-in-one script:

```powershell
.\scripts\run_full_verify.ps1
```

### 6. Test the system manually

```powershell
# Health check
curl http://localhost:8000/health

# Chat API
curl -X POST http://localhost:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\": \"Show my last 5 transactions\"}"

curl -X POST http://localhost:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\": \"What is the NEFT transfer limit?\"}"

# Or run the smoke test script
python scripts/test_api.py
```


## API Examples

### Chat (orchestrated)

```json
POST /chat
{
  "message": "Total spent on groceries"
}
```

Response includes `intent`, `router`, `answer`, `data`, and `correlation_id`.

### Direct agent calls

```bash
# Text-to-SQL
POST http://localhost:8002/query
{"question": "Show last 10 transactions"}

# RAG
POST http://localhost:8003/ask
{"question": "What is the AML policy?"}

# DLP
POST http://localhost:8001/mask
{"text": "My PAN is ABCDE1234F and email is user@bank.com"}
```

## How It Works Without Paid LLMs

| Component | Free Solution | Fallback |
|-----------|---------------|----------|
| LLM | Ollama (llama3.2:3b) | Rule-based SQL + extractive RAG |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 | Local CPU |
| Vector DB | Qdrant (Docker) | — |
| Message bus | Apache Kafka (Confluent image) | — |

If Ollama is not running, the system still works using keyword routing and rule-based SQL patterns.

## Learning Path

1. **Start here:** [docs/BUILD_CHECKLIST.md](docs/BUILD_CHECKLIST.md) — week-by-week checklist
2. **Deep dives:** [docs/LEARNING_ROADMAP.md](docs/LEARNING_ROADMAP.md) — per-component study guide
3. **Architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — diagrams and security layers

### Recommended study order

1. `scripts/generate_sample_data.py` — understand data
2. `shared/dlp.py` — security basics
3. `services/dlp_agent/` — first microservice
4. `services/text_to_sql_agent/` — SQL generation
5. `services/rag_agent/` — embeddings + retrieval
6. `services/orchestrator/` — routing + Kafka
7. `monitoring/` — observability

## Observability

### Prometheus metrics (examples)

```
orchestrator_requests_total{intent="text_to_sql"}
text_to_sql_latency_seconds
rag_latency_seconds
text_to_sql_errors_total
vector_search_latency_seconds
```

### Grafana

Open http://localhost:3000 → **Financial Multi-Agent Overview** dashboard.

### ELK / structured logs

All services emit JSON logs with `correlation_id` and `service` fields. Configure Kibana index pattern: `financial-agents-*`.

## Medallion Architecture

| Layer | Location | Contents |
|-------|----------|----------|
| Bronze | `data/bronze/` | Raw customer + transaction exports |
| Silver | `data/silver/` | Cleaned, normalized, filtered |
| Gold | `data/gold/` + PostgreSQL `gold.*` | Analytics-ready relational data |
| Docs | `data/docs/` | FAQ/policy for RAG embeddings |

## Security Features (Learning)

- **DLP masking** before any agent processes user text
- **SELECT-only SQL** validation via sqlparse
- **Read-only DB role** (`agent_readonly`) for the SQL agent
- **Row-level security** enabled on transactions (PostgreSQL)
- **Output masking** for PAN/account columns in query results
- **Schema aliasing** so LLM prompts don't expose sensitive column semantics

## Kubernetes (Optional)

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/orchestrator-deployment.yaml
```

Build and tag images locally first. Use minikube or kind for free local K8s.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Ollama connection refused | Install Ollama, run `ollama serve`, pull model |
| Qdrant empty | Run `docker compose --profile init run --rm data-init` |
| Elasticsearch won't start | Increase Docker RAM to 8GB+ or disable ELK services |
| Kafka slow startup | Wait 30–60s after `docker compose up` |
| SQL returns no rows | Re-run data-init to reload PostgreSQL |

## Tech Stack Summary

- **Backend:** FastAPI, Python 3.11
- **Agents:** LangChain-compatible patterns, custom orchestrator
- **LLM:** Ollama (free, local)
- **Embeddings:** sentence-transformers (free, local)
- **OLTP:** PostgreSQL 16
- **Vector:** Qdrant
- **Events:** Kafka
- **Containers:** Docker Compose
- **Orchestration:** Kubernetes manifests included
- **Monitoring:** Prometheus, Grafana, ELK

---

Built for end-to-end learning. Work through the checklist, break things, read the code, and extend each agent as you go.
