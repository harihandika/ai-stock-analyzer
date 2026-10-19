"""
AI Stock Analyzer - FastAPI Application Entrypoint
Mendaftarkan semua router, middleware, dan event handler.
"""

import logging
import uuid as _uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routers import account, analysis, auth, jobs, monitoring, plans, research, stocks
from app.core.cache import setup_redis_cache
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.rate_limiter import limiter, rate_limit_exceeded_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager untuk FastAPI.
    Kode sebelum 'yield' dijalankan saat startup.
    Kode setelah 'yield' dijalankan saat shutdown.
    """
    # ---- Startup ----
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 {settings.APP_NAME} starting up in '{settings.APP_ENV}' mode...")
    await setup_redis_cache()

    yield

    # ---- Shutdown ----
    print(f"🛑 {settings.APP_NAME} shutting down...")


# ---- Inisialisasi Aplikasi FastAPI ----
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Platform analisis saham berbasis AI yang menggunakan Volume Price Analysis (VPA), "
        "Wyckoff Theory, dan Smart Money Concepts (SMC) untuk mengidentifikasi peluang investasi "
        "dengan probabilitas tinggi."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ---- Rate Limiting ----
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ---- CORS Middleware ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Correlation ID Middleware ----


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(_uuid.uuid4()))
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


app.add_middleware(CorrelationIdMiddleware)

# ---- Routers ----
API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(account.router, prefix=API_PREFIX)
app.include_router(stocks.router, prefix=API_PREFIX)
app.include_router(jobs.router, prefix=API_PREFIX)
app.include_router(monitoring.router, prefix=API_PREFIX)
app.include_router(research.router, prefix=API_PREFIX)
app.include_router(plans.router, prefix=API_PREFIX)
app.include_router(analysis.router, prefix=API_PREFIX)


# ---- Health Check Endpoint ----
@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """
    Health check endpoint.
    Digunakan oleh UptimeRobot untuk memastikan server tetap aktif.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "1.0.0",
    }


@app.get("/", tags=["System"])
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs": "/docs",
        "health": "/health",
        "api_prefix": API_PREFIX,
    }


# Preserve legacy string errors, add correlation to structured operational errors.


@app.exception_handler(StarletteHTTPException)
async def operational_error_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict):
        exc.detail = {**exc.detail, "request_id": getattr(request.state, "correlation_id", None)}
    return await http_exception_handler(request, exc)
