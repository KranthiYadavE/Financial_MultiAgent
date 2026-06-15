import re
import time
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram
from sqlalchemy import create_engine, text

from shared.config import Settings
from shared.dlp import mask_schema_for_llm, validate_readonly_sql
from shared.fastapi_app import create_service_app
from shared.llm_client import OllamaClient
from shared.logging_setup import setup_logging

settings = Settings()
logger = setup_logging("text-to-sql-agent", settings.log_level)
app = create_service_app("text-to-sql-agent", log_level=settings.log_level)

SQL_REQUESTS = Counter("text_to_sql_requests_total", "Total text-to-sql requests")
SQL_ERRORS = Counter("text_to_sql_errors_total", "SQL generation/execution errors")
SQL_LATENCY = Histogram("text_to_sql_latency_seconds", "Text-to-SQL end-to-end latency")

# Read-only DB role — defense in depth alongside SELECT-only SQL validation
READONLY_DSN = (
    f"postgresql://agent_readonly:readonly_agent_password"
    f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
)
engine = create_engine(READONLY_DSN, pool_pre_ping=True)

SCHEMA_PROMPT = """
You are a PostgreSQL expert. Generate ONLY a single SELECT query.

Database schema (gold schema):
- gold.customers(customer_id, full_name, email, phone, pan, account_number, kyc_status, created_at)
- gold.transactions(transaction_id, customer_id, account_number, transaction_date, transaction_type, category, merchant, amount, currency, status, description, created_at)

Rules:
- SELECT only, no INSERT/UPDATE/DELETE
- Always prefix tables with gold.
- Limit to 50 rows unless user asks for count/sum
- Use transaction_date for date filters
- Return ONLY the SQL, no markdown, no explanation

User question: {question}
"""

FALLBACK_PATTERNS = [
    (
        re.compile(r"last\s+(\d+)\s+transactions?", re.I),
        "SELECT * FROM gold.transactions ORDER BY transaction_date DESC LIMIT {n}",
    ),
    (
        re.compile(r"total.*spent|sum.*amount", re.I),
        "SELECT category, SUM(amount) as total FROM gold.transactions WHERE transaction_type='debit' GROUP BY category ORDER BY total DESC LIMIT 20",
    ),
    (
        re.compile(r"grocery|groceries", re.I),
        "SELECT * FROM gold.transactions WHERE category='groceries' ORDER BY transaction_date DESC LIMIT 20",
    ),
    (
        re.compile(r"salary", re.I),
        "SELECT * FROM gold.transactions WHERE category='salary' ORDER BY transaction_date DESC LIMIT 20",
    ),
]


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


class QueryResponse(BaseModel):
    sql: str
    rows: list[dict[str, Any]]
    row_count: int
    source: str
    latency_ms: float


def _fallback_sql(question: str) -> str | None:
    for pattern, template in FALLBACK_PATTERNS:
        m = pattern.search(question)
        if m:
            if "{n}" in template:
                return template.format(n=m.group(1))
            return template
    if re.search(r"all transactions|show transactions|list transactions", question, re.I):
        return "SELECT * FROM gold.transactions ORDER BY transaction_date DESC LIMIT 20"
    return None


def _extract_sql(raw: str) -> str:
    raw = raw.strip()
    if "```" in raw:
        match = re.search(r"```(?:sql)?\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
        if match:
            raw = match.group(1).strip()
    return raw.split(";")[0].strip()


async def _generate_sql(question: str) -> tuple[str, str]:
    fallback = _fallback_sql(question)
    if fallback:
        return fallback, "rule_engine"

    client = OllamaClient(settings)
    if await client.is_available():
        try:
            raw = await client.generate(
                SCHEMA_PROMPT.format(question=question),
                system="You output SQL only.",
            )
            sql = _extract_sql(raw)
            if sql.lower().startswith("select"):
                return sql, "ollama"
        except Exception as exc:
            logger.warning("Ollama SQL generation failed", extra={"error": str(exc)})

    return (
        "SELECT transaction_id, transaction_date, category, merchant, amount, status "
        "FROM gold.transactions ORDER BY transaction_date DESC LIMIT 10",
        "default_fallback",
    )


def _execute_sql(sql: str) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
    return rows


@app.post("/query", response_model=QueryResponse)
async def query_transactions(req: QueryRequest):
    start = time.perf_counter()
    SQL_REQUESTS.inc()

    try:
        sql, source = await _generate_sql(req.question)
        valid, msg = validate_readonly_sql(sql)
        if not valid:
            SQL_ERRORS.inc()
            raise HTTPException(status_code=400, detail=f"Invalid SQL: {msg}")

        rows = _execute_sql(sql)
        for row in rows:
            for key in ("pan", "account_number", "email", "phone"):
                if key in row and row[key]:
                    val = str(row[key])
                    row[key] = val[:4] + "****" if len(val) > 4 else "****"

        latency = (time.perf_counter() - start) * 1000
        SQL_LATENCY.observe(latency / 1000)
        logger.info(
            "Query executed",
            extra={"source": source, "row_count": len(rows), "latency_ms": latency},
        )
        return QueryResponse(
            sql=sql,
            rows=rows,
            row_count=len(rows),
            source=source,
            latency_ms=round(latency, 2),
        )
    except HTTPException:
        raise
    except Exception as exc:
        SQL_ERRORS.inc()
        logger.exception("Query failed", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/schema")
async def get_schema():
    columns_customers = ["customer_id", "full_name", "email", "phone", "pan", "account_number", "kyc_status"]
    columns_txn = [
        "transaction_id", "customer_id", "account_number", "transaction_date",
        "transaction_type", "category", "merchant", "amount", "status",
    ]
    return {
        "gold.customers": mask_schema_for_llm(columns_customers),
        "gold.transactions": mask_schema_for_llm(columns_txn),
    }
