"""Structured JSON logging with correlation IDs — feeds ELK via Logstash."""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

from pythonjsonlogger import jsonlogger

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get() or "-"
        record.service = getattr(record, "service", "unknown")
        return True


def setup_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(service_name)
    if logger.handlers:
        return logger

    logger.setLevel(level.upper())
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s "
        "%(correlation_id)s %(service)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationFilter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def set_correlation_id(cid: str | None = None) -> str:
    value = cid or str(uuid.uuid4())
    correlation_id_var.set(value)
    return value


def log_extra(**kwargs: Any) -> dict[str, Any]:
    return {"extra": kwargs}
