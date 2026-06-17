"""Intent-specific Kafka worker — one container per intent type."""

from __future__ import annotations

import os
from typing import Any

from services.orchestrator.kafka_bus import KafkaEventBus
from shared.config import Settings
from shared.fastapi_app import create_service_app
from shared.kafka_topics import group_id_for_intent, topic_for_intent
from shared.kafka_worker import handle_with_retries
from shared.logging_setup import set_correlation_id, setup_logging
from shared.redis_client import RedisStore

settings = Settings()
worker_intent = os.environ.get("WORKER_INTENT", settings.worker_intent or "text_to_sql")
worker_port = int(os.environ.get("WORKER_PORT", str(settings.worker_port)))
service_name = f"{worker_intent}-worker"

logger = setup_logging(service_name, settings.log_level)
kafka_bus = KafkaEventBus(settings)
redis_store = RedisStore(settings)

request_topic = topic_for_intent(worker_intent)
consumer_group = group_id_for_intent(worker_intent)


async def _handle_kafka_request(event: dict[str, Any]) -> None:
    cid = event.get("correlation_id")
    if cid:
        set_correlation_id(cid)
    await handle_with_retries(event, settings, redis_store, kafka_bus, worker_intent)


async def _startup() -> None:
    await redis_store.connect()
    await kafka_bus.start_producer()
    await kafka_bus.start_consumer(request_topic, _handle_kafka_request, group_id=consumer_group)
    logger.info(
        "Intent worker started",
        extra={"intent": worker_intent, "topic": request_topic, "group_id": consumer_group},
    )


async def _shutdown() -> None:
    await kafka_bus.stop()
    await redis_store.close()


app = create_service_app(
    service_name,
    log_level=settings.log_level,
    startup=_startup,
    shutdown=_shutdown,
)


@app.get("/health/worker")
async def worker_status() -> dict[str, str]:
    return {
        "status": "consuming",
        "intent": worker_intent,
        "topic": request_topic,
        "consumer_group": consumer_group,
        "redis": "ready" if redis_store.ready else "unavailable",
    }
