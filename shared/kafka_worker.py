"""Shared Kafka worker logic: process intent, cache, retries, DLQ."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import HTTPException
from prometheus_client import Counter

from services.orchestrator.router import Intent
from shared.config import Settings
from shared.kafka_topics import KAFKA_TOPIC_DLQ, KAFKA_TOPIC_RESPONSES
from shared.redis_client import RedisStore

logger = logging.getLogger("shared.kafka_worker")

WORKER_PROCESSED = Counter("kafka_worker_processed_total", "Messages processed", ["intent", "status"])
WORKER_DLQ = Counter("kafka_worker_dlq_total", "Messages sent to DLQ", ["intent"])

FALLBACK_MESSAGE = (
    "I can help with:\n"
    "• Transaction lookups — e.g. 'Show my last 10 transactions' or 'Total spent on groceries'\n"
    "• Policy/FAQ questions — e.g. 'What is the NEFT transfer limit?' or 'AML policy'\n"
    "• DLP masking — e.g. 'Mask this PAN ABCDE1234F'"
)


def format_sql_answer(data: dict) -> str:
    rows = data.get("rows", [])
    if not rows:
        return "No transactions found matching your query."
    lines = [f"Found {len(rows)} transaction(s) (via {data.get('source', 'sql')}):"]
    for row in rows[:5]:
        parts = [
            str(row.get("transaction_date", "")),
            str(row.get("category", row.get("merchant", ""))),
            f"INR {row.get('amount', row.get('total', ''))}",
        ]
        lines.append(" • " + " | ".join(p for p in parts if p))
    if len(rows) > 5:
        lines.append(f" ... and {len(rows) - 5} more (see full data in response)")
    return "\n".join(lines)


async def call_text_to_sql(settings: Settings, question: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.text_to_sql_agent_url}/query",
            json={"question": question},
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()


async def call_rag(settings: Settings, question: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.rag_agent_url}/ask",
            json={"question": question},
            timeout=90.0,
        )
        resp.raise_for_status()
        return resp.json()


async def process_intent_event(
    event: dict[str, Any],
    settings: Settings,
    redis_store: RedisStore,
    expected_intent: str,
) -> dict[str, Any]:
    intent = event.get("intent", expected_intent)
    message = event.get("message", "")
    data: dict[str, Any] = {}
    answer = FALLBACK_MESSAGE

    if intent in {Intent.TEXT_TO_SQL.value, Intent.FAQ_RAG.value}:
        cached = await redis_store.get_cached_response(intent, message)
        if cached:
            data = dict(cached.get("data", {}))
            data["cache_hit"] = True
            return {
                "type": "agent.response",
                "correlation_id": event.get("correlation_id"),
                "intent": intent,
                "answer": cached.get("answer", FALLBACK_MESSAGE),
                "data": data,
            }

    if intent == Intent.TEXT_TO_SQL.value:
        result = await call_text_to_sql(settings, message)
        data["sql_result"] = result
        answer = format_sql_answer(result)
    elif intent == Intent.FAQ_RAG.value:
        result = await call_rag(settings, message)
        data["rag_result"] = result
        answer = result.get("answer", FALLBACK_MESSAGE)
    elif intent == Intent.DLP_ONLY.value:
        data["masked"] = {"masked": message}
        answer = f"Masked text:\n{message}"
    else:
        data["hint"] = "ambiguous_or_greeting"

    if intent in {Intent.TEXT_TO_SQL.value, Intent.FAQ_RAG.value}:
        await redis_store.set_cached_response(intent, message, answer, data)

    return {
        "type": "agent.response",
        "correlation_id": event.get("correlation_id"),
        "intent": intent,
        "answer": answer,
        "data": data,
    }


def build_error_response(event: dict[str, Any], detail: str) -> dict[str, Any]:
    return {
        "type": "agent.response",
        "correlation_id": event.get("correlation_id"),
        "intent": event.get("intent", Intent.FALLBACK.value),
        "answer": detail,
        "data": {"error": detail},
    }


async def handle_with_retries(
    event: dict[str, Any],
    settings: Settings,
    redis_store: RedisStore,
    kafka_bus: Any,
    expected_intent: str,
) -> None:
    """Process event with retries; on final failure send to DLQ + error response."""
    cid = event.get("correlation_id", "")
    intent = event.get("intent", expected_intent)
    last_error = "Unknown error"

    for attempt in range(1, settings.kafka_max_retries + 1):
        try:
            response_event = await process_intent_event(event, settings, redis_store, expected_intent)
            await kafka_bus.publish(KAFKA_TOPIC_RESPONSES, response_event, key=cid or None)
            WORKER_PROCESSED.labels(intent=intent, status="success").inc()
            logger.info(
                "Worker processed message",
                extra={"intent": intent, "correlation_id": cid, "attempt": attempt},
            )
            return
        except HTTPException as exc:
            last_error = str(exc.detail)
            logger.warning(
                "Worker attempt failed",
                extra={"intent": intent, "correlation_id": cid, "attempt": attempt, "error": last_error},
            )
        except Exception as exc:
            last_error = str(exc)
            logger.warning(
                "Worker attempt failed",
                extra={"intent": intent, "correlation_id": cid, "attempt": attempt, "error": last_error},
            )

    WORKER_PROCESSED.labels(intent=intent, status="failed").inc()
    WORKER_DLQ.labels(intent=intent).inc()

    dlq_event = {
        **event,
        "type": "agent.request.dlq",
        "error": last_error,
        "attempts": settings.kafka_max_retries,
    }
    await kafka_bus.publish(KAFKA_TOPIC_DLQ, dlq_event, key=cid or None)

    error_response = build_error_response(
        event,
        f"Request failed after {settings.kafka_max_retries} attempts: {last_error}",
    )
    await kafka_bus.publish(KAFKA_TOPIC_RESPONSES, error_response, key=cid or None)
    logger.error(
        "Message sent to DLQ",
        extra={"intent": intent, "correlation_id": cid, "error": last_error},
    )
