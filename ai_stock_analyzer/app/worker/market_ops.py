"""Operator CLI: safe readiness and opt-in EOD ingestion, never AI or user quota.

Run one designated scheduler. A nonblocking local file lock prevents overlapping
cron runs on that host; it is not a distributed scheduler for multiple hosts.
"""

import argparse
import asyncio
import hashlib
import json
import re
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.routers.stocks import do_sync_stock
from app.core.config import settings
from app.core.errors import AnalysisError
from app.domain.models.models import AnalysisJob, DailyPrice, Stock
from app.infrastructure.ai_client import ai_configured
from app.infrastructure.database import AsyncSessionLocal, engine
from app.infrastructure.market_data import market_identity
from app.services.jobs import ACTIVE
from app.services.market_metadata import session_status, utcnow


def universe(value):
    tickers = list(dict.fromkeys(t.strip().upper() for t in value.split(",") if t.strip()))
    if (
        not tickers
        or len(tickers) > 20
        or any(not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]{0,19}", ticker) for ticker in tickers)
    ):
        raise ValueError(
            "Tetapkan 1–20 ticker eksplisit; tidak ada universe seluruh pasar otomatis."
        )
    return tickers


async def readiness(factory):
    async with factory() as db:
        counts = {}
        for name, where in {
            "queued": AnalysisJob.status == "queued",
            "running": AnalysisJob.status.in_(ACTIVE),
            "failed": AnalysisJob.status == "failed",
            "overdue": AnalysisJob.status.in_(ACTIVE) & (AnalysisJob.deadline < utcnow()),
        }.items():
            counts[name] = await db.scalar(
                select(func.count()).select_from(AnalysisJob).where(where)
            )
        rows = (
            await db.execute(
                select(Stock, func.max(DailyPrice.trading_date))
                .outerjoin(DailyPrice, DailyPrice.stock_ticker == Stock.ticker)
                .where(Stock.is_active.is_(True))
                .group_by(Stock.ticker)
                .order_by(Stock.ticker)
            )
        ).all()
        return {
            "ai_provider": settings.AI_PROVIDER,
            "ai_credential_configured": ai_configured(),
            "market_provider": settings.MARKET_DATA_PROVIDER,
            "market_credential_configured": bool(settings.EODHD_API_KEY)
            if settings.MARKET_DATA_PROVIDER == "eodhd"
            else None,
            "smtp_configured": bool(settings.SMTP_HOST and settings.SMTP_FROM),
            "calendar_verified": settings.MARKET_CALENDAR_VERIFIED,
            "ingestion_enabled": settings.EOD_INGESTION_ENABLED,
            "live_provider_and_delivery": "not_verified_by_this_read_only_command",
            "jobs": counts,
            "stocks": [
                {
                    "ticker": stock.ticker,
                    "source": stock.market_source,
                    "market_as_of": day,
                    **session_status(stock, day),
                }
                for stock, day in rows
            ],
        }


async def ingest(factory, tickers, *, now=None, refresh=False):
    tickers = universe(",".join(tickers))
    if not settings.EOD_INGESTION_ENABLED:
        return {"status": "blocked", "code": "INGESTION_DISABLED", "results": []}
    if not settings.MARKET_CALENDAR_VERIFIED or settings.EOD_PUBLICATION_DELAY_MINUTES is None:
        return {"status": "blocked", "code": "CALENDAR_NOT_VERIFIED", "results": []}
    if settings.MARKET_DATA_PROVIDER == "eodhd" and not settings.EODHD_API_KEY:
        return {"status": "blocked", "code": "MARKET_NOT_CONFIGURED", "results": []}
    results = []
    for ticker in tickers:
        async with factory() as db:
            stock = await db.get(Stock, ticker)
            if not stock or not stock.is_active:
                results.append(
                    {
                        "ticker": ticker,
                        "status": "blocked",
                        "code": "REGISTER_ACTIVE_INSTRUMENT_FIRST",
                    }
                )
                continue
            day = await db.scalar(
                select(func.max(DailyPrice.trading_date)).where(DailyPrice.stock_ticker == ticker)
            )
            policy = SimpleNamespace(
                exchange=stock.exchange,
                publication_delay_minutes=settings.EOD_PUBLICATION_DELAY_MINUTES,
            )
            expected = session_status(policy, day, now=now).get("expected_market_date")
            if not expected:
                results.append({"ticker": ticker, "status": "blocked", "code": "SESSION_UNKNOWN"})
                continue
            if (
                not refresh
                and day
                and day.isoformat() == expected
                and stock.market_source == market_identity()
                and stock.data_revision
                and stock.publication_delay_minutes == settings.EOD_PUBLICATION_DELAY_MINUTES
            ):
                results.append(
                    {"ticker": ticker, "status": "current", "market_as_of": day, "attempts": 0}
                )
                continue
        attempts = 0
        try:
            async with asyncio.timeout(120):
                for attempts in (1, 2):
                    try:
                        async with factory() as db:
                            result = await do_sync_stock(ticker, db)
                        current = result["metadata"]
                        results.append(
                            {
                                "ticker": ticker,
                                "status": "synced"
                                if current["data_state"] == "fresh"
                                else "awaiting_fresh_data",
                                "market_as_of": current["market_as_of"],
                                "source": current["source"],
                                "attempts": attempts,
                            }
                        )
                        break
                    except (AnalysisError, HTTPException) as exc:
                        status = exc.status if isinstance(exc, AnalysisError) else exc.status_code
                        if attempts == 2 or status < 500:
                            raise
                        await asyncio.sleep(1)
        except Exception as exc:
            # Never emit provider URLs, exception messages, credentials or payloads.
            results.append(
                {
                    "ticker": ticker,
                    "status": "failed",
                    "code": "INGESTION_TIMEOUT"
                    if isinstance(exc, TimeoutError)
                    else "INGESTION_FAILED",
                    "attempts": attempts,
                }
            )
    okay = all(r["status"] in ("synced", "current") for r in results)
    return {"status": "completed" if okay else "incomplete", "results": results}


@contextmanager
def ingestion_lock(path):
    import fcntl

    with Path(path).open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["status", "ingest"])
    parser.add_argument("--tickers", default=settings.EOD_INGESTION_TICKERS)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refetch a current session deliberately (provider cost applies).",
    )
    args = parser.parse_args()
    try:
        if args.command == "status":
            result = await readiness(AsyncSessionLocal)
        else:
            identity = hashlib.sha256(settings.DATABASE_URL.encode()).hexdigest()[:16]
            try:
                with ingestion_lock(f"/tmp/stock-eod-{identity}.lock"):
                    result = await ingest(
                        AsyncSessionLocal, universe(args.tickers), refresh=args.refresh
                    )
            except BlockingIOError:
                result = {"status": "blocked", "code": "INGESTION_ALREADY_RUNNING"}
        print(json.dumps(result, default=str))
        return 0 if result.get("status") in (None, "completed") else 1
    except ValueError:
        print(json.dumps({"status": "blocked", "code": "INVALID_UNIVERSE"}))
        return 1
    except Exception:
        print(json.dumps({"status": "failed", "code": "OPERATOR_COMMAND_FAILED"}))
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
