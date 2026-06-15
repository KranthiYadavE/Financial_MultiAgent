"""Quick smoke test against the orchestrator."""

import json
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

QUESTIONS = [
    "Show my last 5 transactions",
    "What is the NEFT transfer limit?",
    "Mask this email test@example.com and PAN ABCDE1234F",
    "Hello, what can you do?",
]


def main() -> None:
    print(f"Testing orchestrator at {BASE}\n")
    with httpx.Client(timeout=120.0) as client:
        health = client.get(f"{BASE}/health")
        print("Health:", health.json())

        agents = client.get(f"{BASE}/agents/status")
        print("Agents:", json.dumps(agents.json(), indent=2), "\n")

        for q in QUESTIONS:
            print("=" * 60)
            print("Q:", q)
            resp = client.post(f"{BASE}/chat", json={"message": q})
            data = resp.json()
            print("Intent:", data.get("intent"), "| Router:", data.get("router"))
            print("Answer:", data.get("answer", "")[:500])
            print()


if __name__ == "__main__":
    main()
