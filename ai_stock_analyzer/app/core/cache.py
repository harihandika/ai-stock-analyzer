"""
AI Stock Analyzer - Caching Layer
Menyediakan integrasi Redis untuk caching response API.
"""

import json
import logging
from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.backends.redis import RedisBackend
from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client = None

async def setup_redis_cache():
    """Inisialisasi koneksi Redis dan setup FastAPI Cache."""
    global redis_client
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        FastAPICache.init(RedisBackend(redis_client), prefix="ai_stock_cache")
        logger.info(f"✅ Redis Cache diinisialisasi sukses di {settings.REDIS_URL}")
    except Exception as e:
        redis_client = None
        FastAPICache.init(InMemoryBackend(), prefix="ai_stock_cache")
        logger.error(f"❌ Gagal inisialisasi Redis Cache, fallback ke InMemory: {e}")

async def get_cache(key: str) -> dict | None:
    if not redis_client:
        return None
    try:
        val = await redis_client.get(key)
        if val:
            return json.loads(val)
    except Exception as e:
        logger.warning(f"Cache get error for {key}: {e}")
    return None

async def set_cache(key: str, value: dict, ttl: int = 86400):
    if not redis_client:
        return
    try:
        await redis_client.set(key, json.dumps(value), ex=ttl)
    except Exception as e:
        logger.warning(f"Cache set error for {key}: {e}")

async def delete_cache(key: str):
    if not redis_client:
        return
    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.warning(f"Cache delete error for {key}: {e}")
