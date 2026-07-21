"""
AI Stock Analyzer - Caching Layer
Menyediakan integrasi Redis untuk caching response API.
"""

from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

async def setup_redis_cache():
    """Inisialisasi koneksi Redis dan setup FastAPI Cache."""
    try:
        FastAPICache.init(InMemoryBackend(), prefix="ai_stock_cache")
        logger.info(f"✅ InMemory Cache diinisialisasi sebagai fallback")
    except Exception as e:
        logger.error(f"❌ Gagal inisialisasi Redis Cache: {e}")
