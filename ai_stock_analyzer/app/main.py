"""
AI Stock Analyzer - FastAPI Application Entrypoint
Mendaftarkan semua router, middleware, dan event handler.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routers import auth, stocks, analysis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager untuk FastAPI.
    Kode sebelum 'yield' dijalankan saat startup.
    Kode setelah 'yield' dijalankan saat shutdown.
    """
    # ---- Startup ----
    print(f"🚀 {settings.APP_NAME} starting up in '{settings.APP_ENV}' mode...")
    # Sprint 2+: Di sini kita bisa melakukan inisialisasi koneksi DB atau warm-up cache

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

# ---- CORS Middleware ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routers ----
API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(stocks.router, prefix=API_PREFIX)
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
