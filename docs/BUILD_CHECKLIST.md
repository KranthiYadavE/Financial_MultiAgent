# Step-by-Step Build Checklist

Use this as your hands-on learning path. Check off each item as you complete it.

## Week 1–2: Foundations

- [ ] Install Docker Desktop
- [ ] Install Ollama from https://ollama.com and run `ollama pull llama3.2:3b`
- [ ] Copy `.env.example` → `.env`
- [ ] Read [FULL_LEARNING_PLAN.md](FULL_LEARNING_PLAN.md) — master 12-week path
- [ ] Read [FILE_GUIDE.md](FILE_GUIDE.md) — understand project layout
- [ ] Read `scripts/generate_sample_data.py` — understand Bronze/Silver/Gold
- [ ] Run `python scripts/generate_sample_data.py` locally
- [ ] Inspect `data/bronze/`, `data/silver/`, `data/gold/`, `data/docs/`
- [ ] Read `shared/dlp.py` — test masking in a Python REPL
- [ ] Read `infra/postgres/init.sql` — understand Gold schema + read-only role

## Week 3–4: Agents

- [ ] `docker compose up -d postgres qdrant` — start data stores only
- [ ] `docker compose --profile init run --rm data-init` — load data
- [ ] Test DLP: `curl -X POST http://localhost:8001/mask -H "Content-Type: application/json" -d "{\"text\":\"PAN ABCDE1234F\"}"`
- [ ] Test Text-to-SQL: ask "Show last 10 transactions"
- [ ] Test RAG: ask "What is the NEFT transfer limit?"
- [ ] Trace a request through `services/orchestrator/router.py`
- [ ] Read Qdrant collection: `GET http://localhost:8003/collection-info`

## Week 5: Orchestrator + Kafka (intent topics)

- [ ] `docker compose up -d --build` — full stack
- [ ] Verify Kafka topics: `docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --describe`
- [ ] Send chat requests to `POST http://localhost:8000/chat`
- [ ] Run `python scripts/test_api.py`
- [ ] Check `GET http://localhost:8000/kafka/status`
- [ ] Watch intent topic: `docker compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic agent.requests.text_to_sql --from-beginning`
- [ ] Watch responses: `docker compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic agent.responses --from-beginning`
- [ ] Observe correlation IDs in logs (`X-Correlation-ID` header)
- [ ] Read [KAFKA_GUIDE.md](KAFKA_GUIDE.md) — complete all 5 labs

## Week 6: Redis + Workers + Scaling

- [ ] `GET http://localhost:8000/cache/status` — verify Redis
- [ ] Send same question twice — confirm `cache_hit: true` on second call
- [ ] `docker compose exec redis redis-cli KEYS "*"` — inspect keys
- [ ] Check worker health: `curl http://localhost:8011/health/worker` (sql-worker)
- [ ] Scale SQL workers: `docker compose up -d --scale sql-worker=2`
- [ ] Inspect consumer group: `docker compose exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group sql-worker-group`
- [ ] Inspect DLQ topic (after simulating failures): `agent.requests.dlq`

## Week 7: MCP (Model Context Protocol)

- [ ] Read [MCP_GUIDE.md](MCP_GUIDE.md) and [FULL_LEARNING_PLAN.md](FULL_LEARNING_PLAN.md) Week 6
- [ ] Read `services/mcp_server/server.py` and `shared/mcp_handlers.py`
- [ ] `pip install "mcp>=1.27,<2"` then `python scripts/mcp_client_demo.py`
- [ ] `GET http://localhost:8000/mcp/info`
- [ ] Copy `.cursor/mcp.json.example` → `.cursor/mcp.json` and enable in Cursor
- [ ] `docker compose up -d mcp-server` — HTTP MCP on port 8020
- [ ] Call `mcp_financial_chat` from Cursor; trace with correlation ID

## Week 8: Observability

- [ ] Open Grafana http://localhost:3000 (admin/admin)
- [ ] Open Prometheus http://localhost:9090 — query `orchestrator_requests_total`
- [ ] Query `kafka_worker_processed_total` and `kafka_worker_dlq_total`
- [ ] Open Kibana http://localhost:5601 — create index pattern `financial-agents-*`
- [ ] Generate load with `test_api.py` and watch dashboards
- [ ] Find a slow request via latency histograms

## Week 9–10: Cloud VM Deployment

- [ ] Read [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md) Tier 2
- [ ] Create Oracle Cloud / AWS free VM
- [ ] Run `deploy/vm/setup-ubuntu.sh`
- [ ] Deploy with `docker-compose.cloud.yml`
- [ ] Open firewall ports 8000, 8020
- [ ] Test API from your PC: `curl http://VM_IP:8000/health`

## Week 11: Kubernetes + CI/CD

- [ ] Read `k8s/README.md` and [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md) Tier 3
- [ ] `minikube start` and `kubectl apply -k k8s/`
- [ ] Run `./deploy/scripts/build-images.ps1`
- [ ] Enable GitHub Actions workflow `.github/workflows/docker-publish.yml`
- [ ] Inspect HPA: `kubectl get hpa -n financial-agents`

## Week 12: Managed Cloud Services (Optional)

- [ ] Read [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md) Tier 4
- [ ] Create free Neon Postgres or Upstash Redis
- [ ] Point `.env` to managed services
- [ ] Document your cloud architecture in README

## Week 13: Portfolio

- [ ] Oracle Cloud free tier / GCP trial / local only
- [ ] Move parquet to MinIO (S3-compatible, free)
- [ ] Document your architecture decisions in a personal blog/README

## Sample Test Questions

| Question | Expected Intent | Kafka Topic |
|----------|-----------------|-------------|
| Show my last 5 transactions | text_to_sql | agent.requests.text_to_sql |
| Total spent on groceries | text_to_sql | agent.requests.text_to_sql |
| What is the AML policy? | faq_rag | agent.requests.faq_rag |
| NEFT transfer limits | faq_rag | agent.requests.faq_rag |
| Mask PAN ABCDE1234F | dlp_only | agent.requests.dlp_only |
| Hello | fallback | agent.requests.fallback |
