import asyncio
import time
import uuid
from typing import Any

import httpx
from fastapi import HTTPException, Request
from prometheus_client import Counter
from pydantic import BaseModel, Field

from services.orchestrator.kafka_bus import KafkaEventBus
from services.orchestrator.router import Intent, classify_intent
from shared.config import Settings
from shared.fastapi_app import create_service_app
from shared.kafka_topics import KAFKA_TOPIC_RESPONSES, topic_for_intent
from shared.logging_setup import set_correlation_id, setup_logging
from shared.redis_client import RedisStore

settings = Settings()
logger = setup_logging("orchestrator", settings.log_level)
kafka_bus = KafkaEventBus(settings)
redis_store = RedisStore(settings)

ORCH_REQUESTS = Counter("orchestrator_requests_total", "Total orchestrator requests", ["intent"])
ORCH_ERRORS = Counter("orchestrator_errors_total", "Orchestrator errors")
ORCH_KAFKA_TIMEOUTS = Counter("orchestrator_kafka_timeouts_total", "Kafka response timeouts")
ORCH_CACHE_HITS = Counter("orchestrator_cache_hits_total", "Cached chat responses served")
ORCH_RATE_LIMITED = Counter("orchestrator_rate_limited_total", "Rate-limited chat requests")
KAFKA_RESPONSE_TIMEOUT_SECONDS = 95.0
_pending_responses: dict[str, asyncio.Future] = {}
_kafka_ready = False


async def _startup():
    global _kafka_ready
    await redis_store.connect()
    if not kafka_bus.enabled:
        logger.info("Kafka disabled — using direct HTTP fallback")
        _kafka_ready = False
        return
    try:
        await kafka_bus.start_producer()
        await kafka_bus.start_consumer(
            KAFKA_TOPIC_RESPONSES,
            _on_kafka_response,
            group_id=f"orchestrator-responses-{uuid.uuid4()}",
        )
        _kafka_ready = True
    except Exception as exc:
        logger.warning("Kafka event bus unavailable at startup", extra={"error": str(exc)})
        _kafka_ready = False


async def _shutdown():
    await kafka_bus.stop()
    await redis_store.close()
    for future in _pending_responses.values():
        if not future.done():
            future.cancel()
    _pending_responses.clear()


app = create_service_app(
    "orchestrator",
    log_level=settings.log_level,
    startup=_startup,
    shutdown=_shutdown,
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    correlation_id: str | None = None


class ChatResponse(BaseModel):
    correlation_id: str
    intent: str
    router: str
    answer: str
    data: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float


FALLBACK_MESSAGE = (
    "I can help with:\n"
    "• Transaction lookups — e.g. 'Show my last 10 transactions' or 'Total spent on groceries'\n"
    "• Policy/FAQ questions — e.g. 'What is the NEFT transfer limit?' or 'AML policy'\n"
    "• DLP masking — e.g. 'Mask this PAN ABCDE1234F'"
)


async def _call_dlp_mask(text: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{settings.dlp_agent_url}/mask", json={"text": text}, timeout=15.0)
        resp.raise_for_status()
        return resp.json()


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


async def _on_kafka_response(event: dict[str, Any]) -> None:
    cid = event.get("correlation_id")
    if not cid:
        return
    future = _pending_responses.get(cid)
    if future and not future.done():
        future.set_result(event)


async def _wait_for_kafka_response(correlation_id: str, timeout_seconds: float) -> dict[str, Any]:
    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()
    _pending_responses[correlation_id] = future
    try:
        result = await asyncio.wait_for(future, timeout=timeout_seconds)
        return result
    finally:
        _pending_responses.pop(correlation_id, None)


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


async def _run_direct_intent(intent: Intent, safe_message: str, dlp_pre: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    data: dict[str, Any] = {"dlp_findings": dlp_pre.get("findings", [])}
    answer = FALLBACK_MESSAGE
    if intent == Intent.TEXT_TO_SQL:
        result = await _call_text_to_sql(safe_message)
        data["sql_result"] = result
        answer = _format_sql_answer(result)
    elif intent == Intent.FAQ_RAG:
        result = await _call_rag(safe_message)
        data["rag_result"] = result
        answer = result.get("answer", FALLBACK_MESSAGE)
    elif intent == Intent.DLP_ONLY:
        data["masked"] = dlp_pre
        answer = f"Masked text:\n{dlp_pre.get('masked', '')}"
    else:
        data["hint"] = "ambiguous_or_greeting"
    return answer, data


def _client_key(request: Request) -> str:
    client_id = request.headers.get("X-Client-ID")
    if client_id:
        return client_id.strip()[:128]
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()[:128]
    if request.client and request.client.host:
        return request.client.host
    return "anonymous"


def _cacheable_intent(intent: Intent) -> bool:
    return intent in {Intent.TEXT_TO_SQL, Intent.FAQ_RAG}


async def _cache_response(intent: Intent, message: str, answer: str, data: dict[str, Any]) -> None:
    if _cacheable_intent(intent):
        await redis_store.set_cached_response(intent.value, message, answer, data)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    start = time.perf_counter()
    cid = set_correlation_id(req.correlation_id or str(uuid.uuid4()))

    try:
        if not await redis_store.check_rate_limit(_client_key(request)):
            ORCH_RATE_LIMITED.inc()
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")

        dlp_pre = await _call_dlp_mask(req.message)
        if dlp_pre.get("blocked"):
            ORCH_ERRORS.inc()
            raise HTTPException(status_code=400, detail=dlp_pre.get("block_reason", "Blocked by DLP"))

        safe_message = dlp_pre.get("masked", req.message)
        intent, router = await classify_intent(safe_message)
        ORCH_REQUESTS.labels(intent=intent.value).inc()

        cached = await redis_store.get_cached_response(intent.value, safe_message)
        if cached:
            ORCH_CACHE_HITS.inc()
            latency = (time.perf_counter() - start) * 1000
            data = dict(cached.get("data", {}))
            data["dlp_findings"] = dlp_pre.get("findings", [])
            data["cache_hit"] = True
            return ChatResponse(
                correlation_id=cid,
                intent=intent.value,
                router=router,
                answer=cached.get("answer", FALLBACK_MESSAGE),
                data=data,
                latency_ms=round(latency, 2),
            )

        if _kafka_ready:
            await redis_store.set_request_state(cid, "pending")
            intent_topic = topic_for_intent(intent.value)
            await kafka_bus.publish(
                intent_topic,
                {
                    "type": "agent.request",
                    "correlation_id": cid,
                    "intent": intent.value,
                    "message": safe_message,
                    "router": router,
                },
                key=cid,
            )
            response_event = await _wait_for_kafka_response(cid, KAFKA_RESPONSE_TIMEOUT_SECONDS)
            data: dict[str, Any] = response_event.get("data", {})
            data["dlp_findings"] = dlp_pre.get("findings", [])
            answer = response_event.get("answer", FALLBACK_MESSAGE)
            await redis_store.set_request_state(cid, "completed")
        else:
            answer, data = await _run_direct_intent(intent, safe_message, dlp_pre)

        await _cache_response(intent, safe_message, answer, data)

        latency = (time.perf_counter() - start) * 1000

        response_payload = {
            "type": "orchestrator.response",
            "correlation_id": cid,
            "intent": intent.value,
            "answer": answer,
            "latency_ms": latency,
        }
        try:
            await kafka_bus.publish(settings.kafka_topic_responses, response_payload, key=cid)
        except Exception as exc:
            logger.warning("Failed to publish response event", extra={"error": str(exc)})

        logger.info(
            "Request routed",
            extra={"intent": intent.value, "router": router, "latency_ms": latency},
        )

        return ChatResponse(
            correlation_id=cid,
            intent=intent.value,
            router=router,
            answer=answer,
            data=data,
            latency_ms=round(latency, 2),
        )
    except asyncio.TimeoutError:
        ORCH_ERRORS.inc()
        ORCH_KAFKA_TIMEOUTS.inc()
        logger.error("Timed out waiting for Kafka response", extra={"correlation_id": cid})
        answer, data = await _run_direct_intent(intent, safe_message, dlp_pre)
        await _cache_response(intent, safe_message, answer, data)
        latency = (time.perf_counter() - start) * 1000
        return ChatResponse(
            correlation_id=cid,
            intent=intent.value,
            router=router,
            answer=answer,
            data=data,
            latency_ms=round(latency, 2),
        )
    except HTTPException:
        raise
    except Exception as exc:
        ORCH_ERRORS.inc()
        logger.exception("Orchestrator error", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/agents/status")
async def agents_status():
    status = {}
    async with httpx.AsyncClient() as client:
        for name, url in [
            ("dlp", settings.dlp_agent_url),
            ("text_to_sql", settings.text_to_sql_agent_url),
            ("rag", settings.rag_agent_url),
        ]:
            try:
                resp = await client.get(f"{url}/health", timeout=5.0)
                status[name] = resp.json()
            except Exception as exc:
                status[name] = {"status": "unreachable", "error": str(exc)}
    return status


@app.get("/kafka/status")
async def kafka_status():
    from shared.kafka_topics import INTENT_REQUEST_TOPICS, TOPIC_PARTITIONS

    return {
        "kafka_ready": _kafka_ready,
        "intent_topics": INTENT_REQUEST_TOPICS,
        "partitions": TOPIC_PARTITIONS,
        "responses_topic": KAFKA_TOPIC_RESPONSES,
        "dlq_topic": settings.kafka_topic_dlq,
    }


@app.get("/cache/status")
async def cache_status():
    return {
        "redis": "ready" if redis_store.ready else "unavailable",
        "cache_ttl_seconds": settings.redis_cache_ttl_seconds,
        "rate_limit_per_minute": settings.redis_rate_limit_per_minute,
    }
