# Step-by-Step Build Checklist

Use this as your hands-on learning path. Check off each item as you complete it.

## Week 1–2: Foundations

- [ ] Install Docker Desktop
- [ ] Install Ollama from https://ollama.com and run `ollama pull llama3.2:3b`
- [ ] Copy `.env.example` → `.env`
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

## Week 5: Orchestrator + Kafka

- [ ] `docker compose up -d` — full stack
- [ ] Send chat requests to `POST http://localhost:8000/chat`
- [ ] Run `python scripts/test_api.py`
- [ ] Use Kafka UI or `docker compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic agent.requests --from-beginning`
- [ ] Observe correlation IDs in logs (`X-Correlation-ID` header)

## Week 6: Observability

- [ ] Open Grafana http://localhost:3000 (admin/admin)
- [ ] Open Prometheus http://localhost:9090 — query `orchestrator_requests_total`
- [ ] Open Kibana http://localhost:5601 — create index pattern `financial-agents-*`
- [ ] Generate load with `test_api.py` and watch dashboards
- [ ] Find a slow request via latency histograms

## Week 7–8: Deployment

- [ ] Build images: `docker compose build`
- [ ] Read `k8s/` manifests
- [ ] Deploy to minikube or kind (optional): `kubectl apply -f k8s/`
- [ ] Configure HPA and resource limits (exercise)

## Week 9–10: Cloud (free tier options)

- [ ] Oracle Cloud free tier / GCP trial / local only
- [ ] Move parquet to MinIO (S3-compatible, free)
- [ ] Document your architecture decisions in a personal blog/README

## Sample Test Questions

| Question | Expected Intent |
|----------|-----------------|
| Show my last 5 transactions | text_to_sql |
| Total spent on groceries | text_to_sql |
| What is the AML policy? | faq_rag |
| NEFT transfer limits | faq_rag |
| Mask PAN ABCDE1234F | dlp_only |
| Hello | fallback |
