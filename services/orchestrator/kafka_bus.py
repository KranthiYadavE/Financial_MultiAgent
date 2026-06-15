"""Kafka event bus for async agent workflows."""

import asyncio
import json
import logging
from typing import Any, Callable, Awaitable

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from shared.config import Settings

logger = logging.getLogger("orchestrator.kafka")


class KafkaEventBus:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self._producer: AIOKafkaProducer | None = None
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task | None = None

    async def start_producer(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self._producer.start()
        logger.info("Kafka producer started")

    async def stop(self) -> None:
        if self._consumer:
            await self._consumer.stop()
        if self._producer:
            await self._producer.stop()

    async def publish(self, topic: str, event: dict[str, Any]) -> None:
        if not self._producer:
            await self.start_producer()
        assert self._producer is not None
        await self._producer.send_and_wait(topic, event)
        logger.info("Event published", extra={"topic": topic, "event_type": event.get("type")})

    async def start_consumer(
        self,
        handler: Callable[[dict[str, Any]], Awaitable[None]],
        group_id: str = "orchestrator-group",
    ) -> None:
        self._consumer = AIOKafkaConsumer(
            self.settings.kafka_topic_requests,
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
        )
        await self._consumer.start()
        logger.info("Kafka consumer started", extra={"topic": self.settings.kafka_topic_requests})

        async def _loop():
            assert self._consumer is not None
            async for msg in self._consumer:
                try:
                    await handler(msg.value)
                except Exception as exc:
                    logger.exception("Kafka handler error", extra={"error": str(exc)})

        self._task = asyncio.create_task(_loop())
