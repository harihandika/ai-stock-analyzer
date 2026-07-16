"""
AI Stock Analyzer - Caching Layer
Menyediakan integrasi Redis untuk caching response API.
"""

from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

async def setup_redis_cache():
    """Inisialisasi koneksi Redis dan setup FastAPI Cache."""
    try:
        # Default Redis URL for development if REDIS_URL is not set
        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379")
        redis = aioredis.from_url(redis_url, encoding="utf8", decode_responses=True)
        FastAPICache.init(RedisBackend(redis), prefix="ai_stock_cache")
        logger.info(f"✅ Redis Cache diinisialisasi pada {redis_url}")
    except Exception as e:
        logger.error(f"❌ Gagal inisialisasi Redis Cache: {e}")
