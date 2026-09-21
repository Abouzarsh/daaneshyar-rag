from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.container import AppContainer
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    configure_logging(runtime_settings.debug)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = AppContainer(runtime_settings)
        app.state.container = container
        logger.info(
            "application_started",
            extra={"environment": runtime_settings.environment},
        )
        try:
            yield
        finally:
            container.close()
            logger.info("application_stopped")

    app = FastAPI(
        title=runtime_settings.app_name,
        version=runtime_settings.app_version,
        description=("Persian-first, source-grounded RAG API with hybrid retrieval."),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "http_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception):
        logger.exception(
            "unhandled_exception",
            extra={"path": request.url.path},
        )
        detail = str(exc) if runtime_settings.debug else "Internal server error"
        return JSONResponse(status_code=500, content={"detail": detail})

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "name": runtime_settings.app_name,
            "version": runtime_settings.app_version,
            "docs": "/docs",
            "health": f"{runtime_settings.api_prefix}/health",
        }

    app.include_router(api_router, prefix=runtime_settings.api_prefix)
    return app


app = create_app()
