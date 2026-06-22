"""HTTP handlers used by the MCP server to call existing microservices."""

from __future__ import annotations

import json
from typing import Any

import httpx

from shared.config import Settings


async def _post_json(url: str, payload: dict[str, Any], timeout: float = 90.0) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()


async def mask_sensitive_text(text: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings()
    return await _post_json(f"{settings.dlp_agent_url}/mask", {"text": text}, timeout=15.0)


async def query_transactions(question: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings()
    return await _post_json(
        f"{settings.text_to_sql_agent_url}/query",
        {"question": question},
        timeout=60.0,
    )


async def ask_policy(question: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings()
    return await _post_json(
        f"{settings.rag_agent_url}/ask",
        {"question": question},
        timeout=90.0,
    )


async def financial_chat(
    message: str,
    correlation_id: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings()
    payload: dict[str, Any] = {"message": message}
    if correlation_id:
        payload["correlation_id"] = correlation_id
    return await _post_json(f"{settings.orchestrator_url}/chat", payload, timeout=120.0)


async def agents_health(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.orchestrator_url}/agents/status", timeout=10.0)
        resp.raise_for_status()
        return resp.json()


def format_tool_result(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, default=str)
