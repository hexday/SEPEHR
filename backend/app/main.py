"""
SEPEHR Backend — FastAPI Application Entry Point
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.exceptions import SEPEHRException
from app.infrastructure.cache.redis import close_redis, get_redis
from app.infrastructure.database.session import dispose_engine
from app.infrastructure.storage.minio import storage

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown procedures."""
    logger.info("SEPEHR backend starting up", version=settings.APP_VERSION, env=settings.ENVIRONMENT)

    # Verify Redis connection
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error("Redis connection failed", error=str(e))
        raise

    # Ensure MinIO buckets exist
    try:
        await storage.ensure_buckets()
        logger.info("MinIO buckets verified")
    except Exception as e:
        logger.warning("MinIO initialization issue", error=str(e))

    logger.info("SEPEHR backend ready to accept connections")

    yield  # Application running

    # Shutdown cleanup
    logger.info("SEPEHR backend shutting down")
    await close_redis()
    await dispose_engine()
    logger.info("Cleanup complete")


def create_application() -> FastAPI:
    app = FastAPI(
        title="SEPEHR API | سپهر",
        description="Secure Emergency Communication Platform",
        version=settings.APP_VERSION,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
    )

    # ── Security Headers Middleware ────────────────────────────────────────────

    @app.middleware("http")
    async def security_headers(request: Request, call_next) -> Response:
        start_time = time.monotonic()
        response = await call_next(request)
        process_time = time.monotonic() - start_time

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(self), geolocation=(self), payment=()"
        )
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))

        return response

    # ── Exception Handlers ─────────────────────────────────────────────────────

    @app.exception_handler(SEPEHRException)
    async def sepehr_exception_handler(request: Request, exc: SEPEHRException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "detail": exc.detail,
            },
            headers=exc.headers or {},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception", exc_info=exc, path=str(request.url))
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )

    # ── Prometheus Metrics ─────────────────────────────────────────────────────

    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/api/health", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    # ── Routes ─────────────────────────────────────────────────────────────────

    from app.api.v1.endpoints.auth import router as auth_router
    from app.api.v1.endpoints.messenger import router as messenger_router
    from app.api.v1.endpoints.news_alerts_map import (
        alerts_router,
        map_router,
        news_router,
    )
    from app.api.v1.endpoints.websocket import router as ws_router

    PREFIX = "/api/v1"

    app.include_router(auth_router, prefix=PREFIX)
    app.include_router(messenger_router, prefix=PREFIX)
    app.include_router(news_router, prefix=PREFIX)
    app.include_router(alerts_router, prefix=PREFIX)
    app.include_router(map_router, prefix=PREFIX)
    app.include_router(ws_router)

    # ── Health Check ───────────────────────────────────────────────────────────

    @app.get("/api/health", include_in_schema=False)
    async def health_check() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "SEPEHR",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/api/health/detailed", include_in_schema=False)
    async def detailed_health(request: Request) -> dict[str, Any]:
        """Detailed health check — only accessible from internal network."""
        client_ip = request.client.host if request.client else "unknown"
        # Only allow from loopback or internal IPs
        if not (client_ip.startswith("127.") or client_ip.startswith("10.") or
                client_ip.startswith("172.") or client_ip == "::1"):
            return JSONResponse(status_code=403, content={"error": "Forbidden"})

        from app.infrastructure.database.session import engine
        db_ok = False
        try:
            async with engine.connect() as conn:
                await conn.execute(sqlalchemy.text("SELECT 1"))
                db_ok = True
        except Exception:
            pass

        redis_ok = False
        try:
            redis = await get_redis()
            await redis.ping()
            redis_ok = True
        except Exception:
            pass

        return {
            "status": "ok" if (db_ok and redis_ok) else "degraded",
            "checks": {
                "database": "ok" if db_ok else "error",
                "redis": "ok" if redis_ok else "error",
            },
        }

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level="info",
        access_log=True,
    )
