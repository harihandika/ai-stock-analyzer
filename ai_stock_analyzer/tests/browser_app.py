"""Isolated browser-test backend. Never use with a development/production database."""

import asyncio
import os
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd

from app.api.routers import stocks
from app.core.config import settings
from app.core.errors import AnalysisError
from app.domain.models.models import Stock
from app.infrastructure import market_data
from app.infrastructure.database import AsyncSessionLocal
from app.main import app
from app.services import ai_service
from app.worker import backtester
from tests.support import MODEL_RESPONSE

if os.getenv("BROWSER_SMOKE") != "1" or "browser-r1" not in settings.DATABASE_URL:
    raise RuntimeError(
        "Browser fixtures require BROWSER_SMOKE=1 and a dedicated browser-r1 database"
    )


async def history(ticker, period="1y"):
    if ticker == "RELOAD.JK":
        await asyncio.sleep(5)
    if ticker in ("MISSING.JK", "INVALIDXYZ"):
        return pd.DataFrame()
    close = 100 + np.sin(np.arange(130) / 3) * 5 + np.arange(130) * 0.03
    return pd.DataFrame(
        {
            "trading_date": pd.bdate_range("2025-01-01", periods=130).date,
            "open": close - 0.2,
            "close": close,
            "high": close + 2,
            "low": close - 2,
            "volume": np.arange(130) * 123 % 1500 + 1000,
        }
    )


async def info(ticker):
    return {
        "longName": "Bank Fixture" if ticker.endswith(".JK") else "US Fixture",
        "currency": "IDR" if ticker.endswith(".JK") else "USD",
        "exchange": "IDX" if ticker.endswith(".JK") else "NASDAQ",
    }


async def analysis(system, prompt):
    if "FAILAI.JK" in prompt:
        raise AnalysisError("AI_TIMEOUT", "Provider AI melewati batas waktu.", status=504)
    return MODEL_RESPONSE


stocks.fetch_stock_history_async = history
stocks.fetch_stock_info_async = info
market_data.fetch_stock_history_async = history
# Backtester imports the function directly.

backtester.fetch_stock_history_async = history
ai_service.call_claude_sonnet = analysis
original_lifespan = app.router.lifespan_context


@asynccontextmanager
async def test_lifespan(application):
    async with original_lifespan(application):
        async with AsyncSessionLocal() as db:
            for ticker in [
                "BBCA.JK",
                "AAPL",
                "FAILAI.JK",
                "RELOAD.JK",
                *[f"BROWSE{i:02}.JK" for i in range(1, 9)],
            ]:
                if not await db.get(Stock, ticker):
                    db.add(
                        Stock(
                            ticker=ticker,
                            company_name=(
                                "Saham Pengujian " + ticker
                                if ticker.startswith("BROWSE")
                                else "Bank Fixture"
                                if ticker.endswith(".JK")
                                else "US Fixture"
                            ),
                            currency="IDR" if ticker.endswith(".JK") else "USD",
                            exchange="IDX" if ticker.endswith(".JK") else "NASDAQ",
                        )
                    )
            await db.commit()
        yield


app.router.lifespan_context = test_lifespan
