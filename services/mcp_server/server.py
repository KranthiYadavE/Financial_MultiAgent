"""MCP server — exposes financial agent tools, resources, and prompts for LLM clients."""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from shared.config import Settings
from shared.mcp_handlers import (
    agents_health,
    ask_policy,
    financial_chat,
    format_tool_result,
    mask_sensitive_text,
    query_transactions,
)

settings = Settings()
ROOT = Path(__file__).resolve().parents[2]

mcp = FastMCP(
    "Financial Multi-Agent",
    instructions=(
        "Tools for a fintech multi-agent system: transaction SQL queries, "
        "policy/FAQ RAG, PII masking, and full orchestrated chat. "
        "Use query_transactions for spending/transaction data. "
        "Use ask_policy for bank policies and FAQs. "
        "Use mask_sensitive_text before sharing user PII. "
        "Use financial_chat when intent is unclear."
    ),
)


@mcp.tool()
async def mcp_query_transactions(question: str) -> str:
    """Query customer transactions using natural language (Text-to-SQL over PostgreSQL gold layer).

    Args:
        question: Natural language question, e.g. 'Show my last 5 transactions' or 'Total spent on groceries'.
    """
    result = await query_transactions(question, settings)
    return format_tool_result(result)


@mcp.tool()
async def mcp_ask_policy(question: str) -> str:
    """Answer bank policy or FAQ questions using RAG over embedded policy documents.

    Args:
        question: Policy question, e.g. 'What is the NEFT transfer limit?' or 'AML policy summary'.
    """
    result = await ask_policy(question, settings)
    return format_tool_result(result)


@mcp.tool()
async def mcp_mask_sensitive_text(text: str) -> str:
    """Detect and mask PII (PAN, email, phone, account numbers) in text.

    Args:
        text: Raw user text that may contain sensitive data.
    """
    result = await mask_sensitive_text(text, settings)
    return format_tool_result(result)


@mcp.tool()
async def mcp_financial_chat(message: str, correlation_id: str = "") -> str:
    """Full orchestrated chat: DLP → intent routing → Kafka workers → agent response.

    Args:
        message: User message in natural language.
        correlation_id: Optional trace ID for logs and Kafka (leave empty to auto-generate).
    """
    cid = correlation_id.strip() or None
    result = await financial_chat(message, correlation_id=cid, settings=settings)
    return format_tool_result(result)


@mcp.tool()
async def mcp_agents_health() -> str:
    """Check health of DLP, Text-to-SQL, and RAG agents via the orchestrator."""
    result = await agents_health(settings)
    return format_tool_result(result)


@mcp.resource("schema://gold/postgresql")
def gold_schema_resource() -> str:
    """PostgreSQL gold schema (customers + transactions) used by Text-to-SQL."""
    init_sql = ROOT / "infra" / "postgres" / "init.sql"
    if init_sql.exists():
        return init_sql.read_text(encoding="utf-8")
    return "Schema file not found at infra/postgres/init.sql"


@mcp.resource("docs://faq/index")
def faq_index_resource() -> str:
    """List of FAQ and policy document files available for RAG."""
    docs_dir = ROOT / "data" / "docs"
    if not docs_dir.exists():
        return json.dumps({"docs": [], "note": "Run scripts/generate_sample_data.py first"})
    files = sorted(p.name for p in docs_dir.iterdir() if p.is_file())
    return json.dumps({"docs": files, "count": len(files)}, indent=2)


@mcp.resource("config://kafka/topics")
def kafka_topics_resource() -> str:
    """Kafka topic layout: intent topics, partitions, DLQ."""
    from shared.kafka_topics import INTENT_REQUEST_TOPICS, TOPIC_PARTITIONS

    return json.dumps(
        {
            "intent_topics": INTENT_REQUEST_TOPICS,
            "partitions": TOPIC_PARTITIONS,
            "responses": "agent.responses",
            "dlq": "agent.requests.dlq",
        },
        indent=2,
    )


@mcp.prompt(title="Analyze Spending")
def prompt_analyze_spending(category: str = "groceries") -> str:
    """Prompt template for transaction analysis queries."""
    return (
        f"Use query_transactions to analyze spending on '{category}'. "
        f"Show total amount and last 10 transactions. Summarize in plain language."
    )


@mcp.prompt(title="Policy Review")
def prompt_policy_review(topic: str = "NEFT transfers") -> str:
    """Prompt template for policy/FAQ questions."""
    return (
        f"Use ask_policy to explain the bank policy about '{topic}'. "
        f"Cite retrieved sources and keep the answer concise."
    )


@mcp.prompt(title="Safe PII Handling")
def prompt_safe_pii() -> str:
    """Prompt template for DLP-first workflows."""
    return (
        "Before processing user text, call mask_sensitive_text. "
        "If blocked, explain why. Never echo raw PAN or account numbers."
    )


def run_stdio() -> None:
    """Run MCP server on stdio — use with Cursor / Claude Desktop."""
    mcp.run(transport="stdio")


def run_http(host: str = "0.0.0.0", port: int = 8020) -> None:
    """Run MCP server with Streamable HTTP — use for browser/MCP Inspector."""
    mcp.settings.host = host
    mcp.settings.port = port
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    run_http()
