"""Factory for consistent FastAPI apps with metrics + logging."""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable

from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator

from shared.logging_setup import set_correlation_id, setup_logging


def create_service_app(
    service_name: str,
    version: str = "1.0.0",
    log_level: str = "INFO",
    startup: Callable | None = None,
    shutdown: Callable | None = None,
) -> FastAPI:
    logger = setup_logging(service_name, log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("Service starting", extra={"service": service_name})
        if startup:
            await startup() if _is_coroutine(startup) else startup()
        yield
        logger.info("Service shutting down", extra={"service": service_name})
        if shutdown:
            await shutdown() if _is_coroutine(shutdown) else shutdown()

    app = FastAPI(title=service_name, version=version, lifespan=lifespan)

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        cid = request.headers.get("X-Correlation-ID") or set_correlation_id()
        set_correlation_id(cid)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response

    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": service_name}

    return app


def _is_coroutine(fn: Callable) -> bool:
    import asyncio

    return asyncio.iscoroutinefunction(fn)
