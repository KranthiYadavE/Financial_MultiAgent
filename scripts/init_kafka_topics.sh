#!/bin/bash
# Create Kafka topics with explicit partition counts for workload management.
set -euo pipefail

BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}"

create_topic() {
  local topic="$1"
  local partitions="$2"
  echo "Creating topic: ${topic} (partitions=${partitions})"
  kafka-topics --bootstrap-server "${BOOTSTRAP}" \
    --create --if-not-exists \
    --topic "${topic}" \
    --partitions "${partitions}" \
    --replication-factor 1
}

# Intent-specific request topics — scale workers per workload type
create_topic "agent.requests.text_to_sql" 3
create_topic "agent.requests.faq_rag" 3
create_topic "agent.requests.dlp_only" 2
create_topic "agent.requests.fallback" 1

# Shared response stream — orchestrator consumers wait here
create_topic "agent.responses" 6

# Dead-letter queue — failed messages after retries
create_topic "agent.requests.dlq" 1

echo ""
echo "=== Kafka topics ==="
kafka-topics --bootstrap-server "${BOOTSTRAP}" --describe
