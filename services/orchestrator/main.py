import time
import uuid
from typing import Any

import httpx
from fastapi import HTTPException
from prometheus_client import Counter
from pydantic import BaseModel, Field

from services.orchestrator.kafka_bus import KafkaEventBus
from services.orchestrator.router import Intent, classify_intent
from shared.config import Settings
from shared.fastapi_app import create_service_app
from shared.logging_setup import set_correlation_id, setup_logging

settings = Settings()
logger = setup_logging("orchestrator", settings.log_level)
kafka_bus = KafkaEventBus(settings)

ORCH_REQUESTS = Counter("orchestrator_requests_total", "Total orchestrator requests", ["intent"])
ORCH_ERRORS = Counter("orchestrator_errors_total", "Orchestrator errors")


async def _startup():
    try:
        await kafka_bus.start_producer()
    except Exception as exc:
        logger.warning("Kafka producer unavailable at startup", extra={"error": str(exc)})


async def _shutdown():
    await kafka_bus.stop()


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


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    start = time.perf_counter()
    cid = set_correlation_id(req.correlation_id or str(uuid.uuid4()))

    try:
        dlp_pre = await _call_dlp_mask(req.message)
        if dlp_pre.get("blocked"):
            ORCH_ERRORS.inc()
            raise HTTPException(status_code=400, detail=dlp_pre.get("block_reason", "Blocked by DLP"))

        safe_message = dlp_pre.get("masked", req.message)
        intent, router = await classify_intent(safe_message)
        ORCH_REQUESTS.labels(intent=intent.value).inc()

        await kafka_bus.publish(
            settings.kafka_topic_requests,
            {
                "type": "agent.request",
                "correlation_id": cid,
                "intent": intent.value,
                "message": safe_message,
            },
        )

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

        latency = (time.perf_counter() - start) * 1000

        response_payload = {
            "type": "agent.response",
            "correlation_id": cid,
            "intent": intent.value,
            "answer": answer,
            "latency_ms": latency,
        }
        try:
            await kafka_bus.publish(settings.kafka_topic_responses, response_payload)
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
