"""
AI Stock Analyzer - Celery Background Tasks
Task background untuk otomatisasi sinkronisasi data dan analisis AI.
"""

import asyncio
import logging
from celery import shared_task
from sqlalchemy import select

from app.worker.celery_app import celery_app
from app.infrastructure.database import AsyncSessionLocal
from app.domain.models.models import Stock
from app.api.routers.stocks import do_sync_stock # We need to separate sync logic from router in ideal world, but we'll adapt.
from app.services.ai_service import run_ai_analysis

logger = logging.getLogger(__name__)

async def _async_sync_and_analyze(ticker: str) -> dict:
    """Helper coroutine to run the full pipeline asynchronously"""
    logger.info(f"Mulai background pipeline untuk {ticker}")
    async with AsyncSessionLocal() as db:
        # 1. Sync data (using logic similar to endpoint)
        # However, calling router function directly requires mocking dependencies if it uses FastAPI Depends.
        # Wait, the sync_stock_data expects (ticker, db). Let's use it directly!
        try:
            sync_res = await do_sync_stock(ticker=ticker, db=db)
            logger.info(f"Sync selesai untuk {ticker}: {sync_res}")
        except Exception as e:
            logger.error(f"Gagal sync {ticker}: {e}")
            return {"status": "error", "message": f"Sync failed: {e}"}

        # 2. Run AI Analysis
        try:
            ai_res = await run_ai_analysis(ticker, db)
            logger.info(f"AI Analysis selesai untuk {ticker}: {ai_res.get('recommendation')}")
        except Exception as e:
            logger.error(f"Gagal AI Analysis {ticker}: {e}")
            return {"status": "error", "message": f"AI Analysis failed: {e}"}

        return {
            "status": "success",
            "ticker": ticker,
            "recommendation": ai_res.get('recommendation')
        }

@celery_app.task(name="task_sync_and_analyze", bind=True, max_retries=3)
def task_sync_and_analyze(self, ticker: str) -> dict:
    """
    Task untuk sinkronisasi dan analisis 1 saham.
    Dipanggil secara asinkron.
    """
    # Karena ini function async di dalam celery (yang sync), kita pakai asyncio.run
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    result = loop.run_until_complete(_async_sync_and_analyze(ticker))
    return result

async def _async_daily_batch() -> dict:
    """Helper coroutine for batch analysis"""
    logger.info("Memulai batch harian analisis saham")
    async with AsyncSessionLocal() as db:
        stmt = select(Stock.ticker).where(Stock.is_active == True)
        res = await db.execute(stmt)
        tickers = res.scalars().all()
        
    for ticker in tickers:
        # Trigger Celery task secara asinkron untuk setiap ticker
        task_sync_and_analyze.delay(ticker)
        
    return {"message": f"Triggered {len(tickers)} tasks"}

@celery_app.task(name="task_daily_batch_analysis")
def task_daily_batch_analysis() -> dict:
    """
    Task yang dijadwalkan jalan tiap jam 17:30.
    Mengambil semua saham aktif dan mengirimkannya ke antrean task_sync_and_analyze.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_async_daily_batch())
