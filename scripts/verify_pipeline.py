"""
End-to-end pipeline verification.
Run after: docker compose -f docker-compose.lite.yml up -d --build
           docker compose -f docker-compose.lite.yml --profile init run --rm data-init
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

PASS = 0
FAIL = 0


def ok(name: str, detail: str = "") -> None:
    global PASS
    PASS += 1
    print(f"  PASS  {name}" + (f" — {detail}" if detail else ""))


def fail(name: str, detail: str = "") -> None:
    global FAIL
    FAIL += 1
    print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


def section(title: str) -> None:
    print(f"\n{'='*60}\n{title}\n{'='*60}")


def check_local_data() -> None:
    section("1. Local data pipeline (no Docker)")
    gold = ROOT / "data" / "gold"
    docs = ROOT / "docs" if (ROOT / "docs").exists() else ROOT / "data" / "docs"
    try:
        cust = pd.read_parquet(gold / "customers.parquet")
        txn = pd.read_parquet(gold / "transactions.parquet")
        faq = docs / "faq_policies.json"
        if not faq.exists():
            faq = ROOT / "data" / "docs" / "faq_policies.json"
        doc_count = len(json.loads(faq.read_text(encoding="utf-8")))
        ok("Parquet files", f"{len(cust)} customers, {len(txn)} transactions")
        ok("FAQ/policy docs", f"{doc_count} documents")
    except Exception as exc:
        fail("Local data", str(exc))


def check_python_logic() -> None:
    section("2. Core Python logic (no Docker)")
    try:
        from shared.dlp import mask_pii, validate_readonly_sql
        from services.orchestrator.router import classify_intent, Intent

        r = mask_pii("PAN ABCDE1234F email a@b.com")
        assert "pan" in r.findings
        ok("DLP masking", r.masked[:60])

        assert validate_readonly_sql("SELECT 1 FROM gold.transactions")[0]
        assert not validate_readonly_sql("DELETE FROM gold.transactions")[0]
        ok("SQL read-only guard")

        async def router_checks():
            cases = [
                ("Show my last 5 transactions", Intent.TEXT_TO_SQL),
                ("What is the NEFT transfer limit?", Intent.FAQ_RAG),
                ("Mask PAN ABCDE1234F", Intent.DLP_ONLY),
            ]
            for q, exp in cases:
                got, _ = await classify_intent(q)
                assert got == exp, f"{q} -> {got}"

        asyncio.run(router_checks())
        ok("Intent router")
    except Exception as exc:
        fail("Python logic", str(exc))


def check_services(client: httpx.Client) -> None:
    section("3. Service health checks")
    for name, url in [
        ("orchestrator", f"{BASE}/health"),
        ("dlp-agent", "http://localhost:8001/health"),
        ("text-to-sql", "http://localhost:8002/health"),
        ("rag-agent", "http://localhost:8003/health"),
    ]:
        try:
            r = client.get(url, timeout=10)
            if r.status_code == 200:
                ok(name, r.json().get("status", "up"))
            else:
                fail(name, f"HTTP {r.status_code}")
        except Exception as exc:
            fail(name, str(exc))


def check_agents(client: httpx.Client) -> None:
    section("4. Direct agent endpoints")

    try:
        r = client.post(
            "http://localhost:8001/mask",
            json={"text": "PAN ABCDE1234F and email user@bank.com"},
            timeout=15,
        )
        data = r.json()
        if r.status_code == 200 and "[PAN_MASKED]" in data.get("masked", ""):
            ok("DLP /mask", data["masked"][:70])
        else:
            fail("DLP /mask", str(data))
    except Exception as exc:
        fail("DLP /mask", str(exc))

    try:
        r = client.post(
            "http://localhost:8002/query",
            json={"question": "Show my last 5 transactions"},
            timeout=60,
        )
        data = r.json()
        if r.status_code == 200 and data.get("row_count", 0) > 0:
            ok("Text-to-SQL /query", f"{data['row_count']} rows via {data.get('source')}")
        else:
            fail("Text-to-SQL /query", str(data)[:200])
    except Exception as exc:
        fail("Text-to-SQL /query", str(exc))

    try:
        r = client.get("http://localhost:8003/collection-info", timeout=15)
        info = r.json()
        if info.get("points_count", 0) > 0:
            ok("Qdrant collection", f"{info['points_count']} vectors")
        else:
            fail("Qdrant collection", "empty — run data-init")
    except Exception as exc:
        fail("Qdrant collection", str(exc))

    try:
        r = client.post(
            "http://localhost:8003/ask",
            json={"question": "What is the NEFT transfer limit?"},
            timeout=120,
        )
        data = r.json()
        if r.status_code == 200 and data.get("answer"):
            ok("RAG /ask", data["answer"][:80] + "...")
        else:
            fail("RAG /ask", str(data)[:200])
    except Exception as exc:
        fail("RAG /ask", str(exc))


def check_orchestrator(client: httpx.Client) -> None:
    section("5. Orchestrator end-to-end /chat")
    tests = [
        ("Show my last 5 transactions", "text_to_sql"),
        ("What is the NEFT transfer limit?", "faq_rag"),
        ("Mask PAN ABCDE1234F", "dlp_only"),
    ]
    for message, expected_intent in tests:
        try:
            r = client.post(f"{BASE}/chat", json={"message": message}, timeout=120)
            data = r.json()
            intent = data.get("intent")
            if r.status_code == 200 and intent == expected_intent:
                ok(f"chat: {message[:40]}", f"intent={intent}")
            else:
                fail(f"chat: {message[:40]}", f"got {intent}, expected {expected_intent}")
        except Exception as exc:
            fail(f"chat: {message[:40]}", str(exc))


def check_metrics(client: httpx.Client) -> None:
    section("6. Prometheus metrics")
    try:
        r = client.get(f"{BASE}/metrics", timeout=10)
        body = r.text
        if r.status_code == 200 and "orchestrator_requests_total" in body:
            ok("Prometheus /metrics exposed")
        else:
            fail("Prometheus /metrics", f"HTTP {r.status_code}")
    except Exception as exc:
        fail("Prometheus /metrics", str(exc))


def main() -> None:
    print(f"\nFinancial Multi-Agent Pipeline Verification")
    print(f"Orchestrator: {BASE}\n")

    check_local_data()
    check_python_logic()

    section("Docker services (requires stack running)")
    docker_up = False
    try:
        with httpx.Client() as client:
            r = client.get(f"{BASE}/health", timeout=5)
            docker_up = r.status_code == 200
    except Exception:
        docker_up = False

    if not docker_up:
        print("  SKIP  Docker services not reachable at localhost:8000")
        print("\n  To run full verification:")
        print('    copy .env.example .env')
        print('    docker compose -f docker-compose.lite.yml up -d --build')
        print('    docker compose -f docker-compose.lite.yml --profile init run --rm data-init')
        print('    python scripts/verify_pipeline.py')
    else:
        with httpx.Client(timeout=120) as client:
            check_services(client)
            check_agents(client)
            check_orchestrator(client)
            check_metrics(client)

    section("SUMMARY")
    total = PASS + FAIL
    print(f"  Passed: {PASS}/{total}  Failed: {FAIL}/{total}")
    if FAIL == 0:
        print("\n  ALL CHECKS PASSED")
    else:
        print("\n  SOME CHECKS FAILED — see details above")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
