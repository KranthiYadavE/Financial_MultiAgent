"""DEPRECATED: Use services/workers/ intent-specific workers instead.

This single-topic worker is kept for reference only. The production learning path uses:
  - agent.requests.text_to_sql / faq_rag / dlp_only / fallback
  - services/workers/main.py with WORKER_INTENT env
"""

import asyncio
from typing import Any

import httpx
from fastapi import HTTPException

from services.orchestrator.kafka_bus import KafkaEventBus
from services.orchestrator.router import Intent
from shared.config import Settings
from shared.fastapi_app import create_service_app
from shared.logging_setup import set_correlation_id, setup_logging
from shared.redis_client import RedisStore

settings = Settings()
logger = setup_logging("stream_worker", settings.log_level)
kafka_bus = KafkaEventBus(settings)
redis_store = RedisStore(settings)

FALLBACK_MESSAGE = (
    "I can help with:\n"
    "• Transaction lookups — e.g. 'Show my last 10 transactions' or 'Total spent on groceries'\n"
    "• Policy/FAQ questions — e.g. 'What is the NEFT transfer limit?' or 'AML policy'\n"
    "• DLP masking — e.g. 'Mask this PAN ABCDE1234F'"
)


def _format_sql_answer(data: dict) -> str:
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


async def _call_text_to_sql(question: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.text_to_sql_agent_url}/query",
            json={"question": question},
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()


async def _call_rag(question: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.rag_agent_url}/ask",
            json={"question": question},
            timeout=90.0,
        )
        resp.raise_for_status()
        return resp.json()


async def _process_request(event: dict[str, Any]) -> dict[str, Any]:
    intent = event.get("intent", Intent.FALLBACK.value)
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
        result = await _call_text_to_sql(message)
        data["sql_result"] = result
        answer = _format_sql_answer(result)
    elif intent == Intent.FAQ_RAG.value:
        result = await _call_rag(message)
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


async def _handle_kafka_request(event: dict[str, Any]) -> None:
    cid = event.get("correlation_id")
    if cid:
        set_correlation_id(cid)
    try:
        response_event = await _process_request(event)
    except HTTPException as exc:
        response_event = {
            "type": "agent.response",
            "correlation_id": cid,
            "intent": event.get("intent", Intent.FALLBACK.value),
            "answer": f"Upstream service failed: {exc.detail}",
            "data": {"error": str(exc.detail)},
        }
    except Exception as exc:
        logger.exception("Worker request processing failed", extra={"error": str(exc)})
        response_event = {
            "type": "agent.response",
            "correlation_id": cid,
            "intent": event.get("intent", Intent.FALLBACK.value),
            "answer": "Sorry, the request failed while being processed.",
            "data": {"error": str(exc)},
        }

    await kafka_bus.publish(settings.kafka_topic_responses, response_event)


async def _startup() -> None:
    await redis_store.connect()
    await kafka_bus.start_producer()
    await kafka_bus.start_consumer(
        settings.kafka_topic_requests,
        _handle_kafka_request,
        group_id="stream-worker-group",
    )
    logger.info("Stream worker started")


async def _shutdown() -> None:
    await kafka_bus.stop()
    await redis_store.close()


app = create_service_app(
    "stream_worker",
    log_level=settings.log_level,
    startup=_startup,
    shutdown=_shutdown,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/worker")
async def worker_status() -> dict[str, str]:
    return {"status": "consuming", "redis": "ready" if redis_store.ready else "unavailable"}


@app.post("/debug/process")
async def debug_process(event: dict[str, Any]) -> dict[str, Any]:
    return await _process_request(event)
