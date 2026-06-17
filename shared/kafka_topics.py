"""Kafka topic names, partition layout, and intent routing."""

from __future__ import annotations

# Intent-specific request topics (orchestrator publishes here after routing)
INTENT_REQUEST_TOPICS: dict[str, str] = {
    "text_to_sql": "agent.requests.text_to_sql",
    "faq_rag": "agent.requests.faq_rag",
    "dlp_only": "agent.requests.dlp_only",
    "fallback": "agent.requests.fallback",
}

# Shared response topic (all workers publish here)
KAFKA_TOPIC_RESPONSES = "agent.responses"

# Dead-letter queue for messages that fail after retries
KAFKA_TOPIC_DLQ = "agent.requests.dlq"

# Legacy single-topic name (kept for backward compatibility in env)
KAFKA_TOPIC_REQUESTS_LEGACY = "agent.requests"

# Topic → partition count (used by init_kafka_topics.sh and docs)
TOPIC_PARTITIONS: dict[str, int] = {
    "agent.requests.text_to_sql": 3,
    "agent.requests.faq_rag": 3,
    "agent.requests.dlp_only": 2,
    "agent.requests.fallback": 1,
    "agent.responses": 6,
    "agent.requests.dlq": 1,
}

# Consumer group per intent worker type
WORKER_GROUP_IDS: dict[str, str] = {
    "text_to_sql": "sql-worker-group",
    "faq_rag": "rag-worker-group",
    "dlp_only": "dlp-worker-group",
    "fallback": "fallback-worker-group",
}


def topic_for_intent(intent: str) -> str:
    return INTENT_REQUEST_TOPICS.get(intent, INTENT_REQUEST_TOPICS["fallback"])


def group_id_for_intent(intent: str) -> str:
    return WORKER_GROUP_IDS.get(intent, WORKER_GROUP_IDS["fallback"])
