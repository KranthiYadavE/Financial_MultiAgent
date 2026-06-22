# Kubernetes Deployment

Deploy the Financial Multi-Agent system to a Kubernetes cluster.

## Prerequisites

- `kubectl` installed
- A cluster: minikube, kind, GKE, EKS, or AKS
- Docker images built locally or pushed to GHCR

## Quick Start (minikube)

```powershell
minikube start --memory=8192 --cpus=4
minikube addons enable ingress
minikube addons enable metrics-server

# Load images into minikube
minikube -p minikube docker-env | Invoke-Expression
cd ..
./deploy/scripts/build-images.ps1

# Deploy
kubectl apply -k k8s/

# Watch rollout
kubectl get pods -n financial-agents -w

# Get orchestrator URL
minikube service orchestrator -n financial-agents --url
```

## Apply All Manifests

```bash
kubectl apply -k k8s/
```

Or individually:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
# Create real secret first:
kubectl create secret generic agent-secrets \
  --from-literal=POSTGRES_USER=finagent \
  --from-literal=POSTGRES_PASSWORD=yourpassword \
  --from-literal=POSTGRES_DB=financial_gold \
  -n financial-agents
kubectl apply -f k8s/
```

## Manifest Overview

| File | Kind | Purpose |
|------|------|---------|
| `namespace.yaml` | Namespace | Isolate resources |
| `configmap.yaml` | ConfigMap | Non-secret configuration |
| `secret.example.yaml` | Secret template | DB credentials |
| `redis-deployment.yaml` | Deployment+Service | Cache |
| `dlp-agent-deployment.yaml` | Deployment+Service | DLP |
| `text-to-sql-deployment.yaml` | Deployment+Service | SQL agent |
| `rag-agent-deployment.yaml` | Deployment+Service | RAG agent |
| `orchestrator-deployment.yaml` | Deployment+Service | API gateway |
| `sql-worker-deployment.yaml` | Deployment+Service | Kafka worker |
| `mcp-server-deployment.yaml` | Deployment+Service | MCP server |
| `ingress.yaml` | Ingress | HTTP routing |
| `hpa-orchestrator.yaml` | HPA | CPU autoscaling |

## Notes

- **Postgres & Qdrant** are not in K8s manifests yet — use managed services or add StatefulSets as an exercise.
- **Kafka** expects `kafka:9092` in-cluster — deploy Strimzi/Confluent operator or point to Confluent Cloud.
- Images default to `ghcr.io/kranthiyadave/financial-multiagent/*` — update after your GHCR push.

See [CLOUD_DEPLOYMENT.md](../docs/CLOUD_DEPLOYMENT.md) for full cloud learning path.
