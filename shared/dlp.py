"""Data Loss Prevention — regex masking + hard filtering before LLM exposure."""

import re
from dataclasses import dataclass, field

# Indian PAN: ABCDE1234F
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
# Account numbers: 10-18 digits
ACCOUNT_PATTERN = re.compile(r"\b\d{10,18}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b")
# Credit card-ish (16 digits with optional separators)
CARD_PATTERN = re.compile(r"\b(?:\d{4}[\s-]?){3}\d{4}\b")

MASK_MAP = {
    "pan": "[PAN_MASKED]",
    "account": "[ACCOUNT_MASKED]",
    "email": "[EMAIL_MASKED]",
    "phone": "[PHONE_MASKED]",
    "card": "[CARD_MASKED]",
}


@dataclass
class DLPResult:
    original: str
    masked: str
    findings: list[str] = field(default_factory=list)
    blocked: bool = False
    block_reason: str = ""


def mask_pii(text: str) -> DLPResult:
    findings: list[str] = []
    masked = text

    for label, pattern, token in [
        ("pan", PAN_PATTERN, MASK_MAP["pan"]),
        ("account", ACCOUNT_PATTERN, MASK_MAP["account"]),
        ("email", EMAIL_PATTERN, MASK_MAP["email"]),
        ("phone", PHONE_PATTERN, MASK_MAP["phone"]),
        ("card", CARD_PATTERN, MASK_MAP["card"]),
    ]:
        if pattern.search(masked):
            findings.append(label)
            masked = pattern.sub(token, masked)

    return DLPResult(original=text, masked=masked, findings=findings)


def hard_filter(text: str, block_raw_accounts: bool = True) -> DLPResult:
    """Block content that still contains sensitive patterns after masking."""
    result = mask_pii(text)

    if block_raw_accounts and ACCOUNT_PATTERN.search(text):
        # Allow masked placeholders but block if long digit sequences remain
        unmasked_digits = re.findall(r"\b\d{10,18}\b", result.masked)
        if unmasked_digits:
            result.blocked = True
            result.block_reason = "Unmasked account-like numbers detected"

    return result


def mask_schema_for_llm(columns: list[str]) -> dict[str, str]:
    """Map real column names to safe aliases for LLM prompts."""
    sensitive = {"pan", "account_number", "email", "phone", "card_number"}
    mapping: dict[str, str] = {}
    for col in columns:
        if col.lower() in sensitive:
            mapping[col] = f"col_{col[:3]}_masked"
        else:
            mapping[col] = col
    return mapping


FORBIDDEN_SQL_KEYWORDS = frozenset(
    {
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "create",
        "grant",
        "revoke",
        "exec",
        "execute",
        "merge",
        "call",
    }
)


def validate_readonly_sql(sql: str) -> tuple[bool, str]:
    """Ensure generated SQL is SELECT-only (defense in depth with DB role)."""
    import sqlparse

    parsed = sqlparse.parse(sql.strip())
    if not parsed:
        return False, "Empty SQL"

    for statement in parsed:
        stmt_type = statement.get_type()
        if stmt_type and stmt_type.upper() != "SELECT":
            return False, f"Only SELECT allowed, got {stmt_type}"

        tokens = " ".join(str(t).lower() for t in statement.flatten())
        for kw in FORBIDDEN_SQL_KEYWORDS:
            if re.search(rf"\b{kw}\b", tokens):
                return False, f"Forbidden keyword: {kw}"

    if ";" in sql.strip().rstrip(";"):
        return False, "Multiple statements not allowed"

    return True, "OK"
