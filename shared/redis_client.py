"""Async Redis helpers for caching, rate limiting, and request state."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from redis.asyncio import Redis

from shared.config import Settings

logger = logging.getLogger("shared.redis")


def response_cache_key(intent: str, message: str) -> str:
    digest = hashlib.sha256(f"{intent}:{message}".encode("utf-8")).hexdigest()
    return f"cache:response:{digest}"


def rate_limit_key(client_id: str) -> str:
    return f"ratelimit:chat:{client_id}"


def request_state_key(correlation_id: str) -> str:
    return f"req:state:{correlation_id}"


class RedisStore:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self._client: Redis | None = None
        self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready

    async def connect(self) -> None:
        if not self.settings.redis_enabled:
            logger.info("Redis disabled by configuration")
            return
        try:
            self._client = Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                password=self.settings.redis_password or None,
                decode_responses=True,
            )
            await self._client.ping()
            self._ready = True
            logger.info("Redis connected", extra={"host": self.settings.redis_host})
        except Exception as exc:
            self._client = None
            self._ready = False
            logger.warning("Redis unavailable", extra={"error": str(exc)})

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
        self._client = None
        self._ready = False

    async def get_json(self, key: str) -> dict[str, Any] | None:
        if not self._ready or not self._client:
            return None
        try:
            raw = await self._client.get(key)
            if not raw:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("Redis get failed", extra={"key": key, "error": str(exc)})
            return None

    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        if not self._ready or not self._client:
            return
        try:
            await self._client.setex(key, ttl_seconds, json.dumps(value))
        except Exception as exc:
            logger.warning("Redis set failed", extra={"key": key, "error": str(exc)})

    async def check_rate_limit(self, client_id: str) -> bool:
        """Return True when request is allowed, False when rate limit exceeded."""
        if not self._ready or not self._client:
            return True
        key = rate_limit_key(client_id)
        limit = self.settings.redis_rate_limit_per_minute
        try:
            count = await self._client.incr(key)
            if count == 1:
                await self._client.expire(key, 60)
            return count <= limit
        except Exception as exc:
            logger.warning("Redis rate limit check failed", extra={"error": str(exc)})
            return True

    async def get_cached_response(self, intent: str, message: str) -> dict[str, Any] | None:
        return await self.get_json(response_cache_key(intent, message))

    async def set_cached_response(
        self,
        intent: str,
        message: str,
        answer: str,
        data: dict[str, Any],
    ) -> None:
        payload = {"intent": intent, "answer": answer, "data": data}
        await self.set_json(
            response_cache_key(intent, message),
            payload,
            self.settings.redis_cache_ttl_seconds,
        )

    async def set_request_state(self, correlation_id: str, state: str) -> None:
        if not self._ready or not self._client:
            return
        key = request_state_key(correlation_id)
        try:
            await self._client.setex(key, self.settings.redis_request_state_ttl_seconds, state)
        except Exception as exc:
            logger.warning("Redis request state set failed", extra={"error": str(exc)})

    async def get_request_state(self, correlation_id: str) -> str | None:
        if not self._ready or not self._client:
            return None
        key = request_state_key(correlation_id)
        try:
            return await self._client.get(key)
        except Exception as exc:
            logger.warning("Redis request state get failed", extra={"error": str(exc)})
            return None
