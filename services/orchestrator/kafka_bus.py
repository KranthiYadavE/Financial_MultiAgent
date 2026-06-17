"""Kafka event bus — producers, consumers, partition keys, DLQ."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from shared.config import Settings

logger = logging.getLogger("orchestrator.kafka")


class KafkaEventBus:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self._producer: AIOKafkaProducer | None = None
        self._consumers: list[AIOKafkaConsumer] = []
        self._tasks: list[asyncio.Task] = []

    @property
    def enabled(self) -> bool:
        servers = self.settings.kafka_bootstrap_servers.strip().lower()
        return not self.settings.kafka_disabled and servers not in ("", "disabled", "false")

    async def start_producer(self) -> None:
        if not self.enabled:
            raise RuntimeError("Kafka is disabled")
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        await self._producer.start()
        logger.info("Kafka producer started")

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        for consumer in self._consumers:
            await consumer.stop()
        self._consumers = []
        if self._producer:
            await self._producer.stop()
            self._producer = None

    async def publish(
        self,
        topic: str,
        event: dict[str, Any],
        key: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        if not self._producer:
            await self.start_producer()
        assert self._producer is not None
        await self._producer.send_and_wait(topic, value=event, key=key)
        logger.info(
            "Event published",
            extra={
                "topic": topic,
                "event_type": event.get("type"),
                "partition_key": key,
                "correlation_id": event.get("correlation_id"),
            },
        )

    async def start_consumer(
        self,
        topic: str,
        handler: Callable[[dict[str, Any]], Awaitable[None]],
        group_id: str = "orchestrator-group",
    ) -> None:
        if not self.enabled:
            raise RuntimeError("Kafka is disabled")
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
        )
        await consumer.start()
        logger.info("Kafka consumer started", extra={"topic": topic, "group_id": group_id})

        async def _loop():
            async for msg in consumer:
                try:
                    await handler(msg.value)
                except Exception as exc:
                    logger.exception(
                        "Kafka handler error",
                        extra={"error": str(exc), "topic": topic, "partition": msg.partition},
                    )

        self._consumers.append(consumer)
        self._tasks.append(asyncio.create_task(_loop()))
