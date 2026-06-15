"""Zero-shot style intent router — keyword + LLM hybrid (free via Ollama)."""

import re
from enum import Enum

from shared.llm_client import OllamaClient
from shared.config import Settings

settings = Settings()


class Intent(str, Enum):
    TEXT_TO_SQL = "text_to_sql"
    FAQ_RAG = "faq_rag"
    DLP_ONLY = "dlp_only"
    FALLBACK = "fallback"


SQL_KEYWORDS = re.compile(
    r"\b(transaction|transactions|spent|payment|debit|credit|amount|balance|"
    r"merchant|grocer|salary|emi|last \d+|show my|list my)\b",
    re.I,
)

# FAQ topics that mention "transfer" but are policy questions, not transaction lookups
FAQ_PRIORITY = re.compile(r"\b(neft|rtgs|imps|upi limit|transfer limit|transfer fee)\b", re.I)

FAQ_KEYWORDS = re.compile(
    r"\b(policy|policies|faq|interest rate|fee|kyc|aml|privacy|dispute|"
    r"account opening|neft|rtgs|emi rules|how do i|what is the)\b",
    re.I,
)

DLP_KEYWORDS = re.compile(
    r"\b(mask|redact|sanitize|pii|pan|account number)\b",
    re.I,
)

ROUTER_PROMPT = """Classify this user message into exactly one category:
- text_to_sql: user wants their transaction data, spending, payments
- faq_rag: user asks about bank policies, FAQs, fees, procedures
- dlp_only: user wants to mask/redact sensitive data
- fallback: unclear or greeting

Reply with ONLY the category name, nothing else.

Message: {message}
Category:"""


async def classify_intent(message: str) -> tuple[Intent, str]:
    msg = message.strip()

    if DLP_KEYWORDS.search(msg) and not SQL_KEYWORDS.search(msg):
        return Intent.DLP_ONLY, "keyword_router"

    if FAQ_PRIORITY.search(msg) or (
        FAQ_KEYWORDS.search(msg) and not SQL_KEYWORDS.search(msg)
    ):
        return Intent.FAQ_RAG, "keyword_router"

    if SQL_KEYWORDS.search(msg) and not FAQ_KEYWORDS.search(msg):
        return Intent.TEXT_TO_SQL, "keyword_router"

    if SQL_KEYWORDS.search(msg) and FAQ_KEYWORDS.search(msg):
        return Intent.FALLBACK, "ambiguous_keywords"

    client = OllamaClient(settings)
    if await client.is_available():
        try:
            raw = await client.generate(ROUTER_PROMPT.format(message=msg))
            label = raw.strip().lower().replace(" ", "_")
            for intent in Intent:
                if intent.value in label:
                    return intent, "ollama_router"
        except Exception:
            pass

    if any(g in msg.lower() for g in ("hello", "hi", "help")):
        return Intent.FALLBACK, "greeting"

    return Intent.FALLBACK, "default_fallback"
