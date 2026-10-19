"""Local, disposable benchmark: 100 tickers, five calendar years, 20 users.

Start a separate app.main API using the same empty benchmark database. No worker
or external provider is used. This measures local reads/admission, not staging or
analysis completion. Requires BENCHMARK_SETUP=1 and 'benchmark' in DATABASE_URL.
"""

import argparse
import asyncio
import json
import os
import secrets
import statistics
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import httpx
import pandas as pd
from sqlalchemy import func, insert, select

from app.core.config import settings
from app.core.security import hash_password
from app.domain.models.models import DailyPrice, Stock, TechnicalIndicator, User
from app.infrastructure.database import AsyncSessionLocal, engine


async def run(base, server_workers=1):
    if os.getenv("BENCHMARK_SETUP") != "1" or "benchmark" not in settings.DATABASE_URL:
        raise RuntimeError("Use a disposable benchmark database and BENCHMARK_SETUP=1.")
    if urlparse(base).hostname not in ("127.0.0.1", "localhost"):
        raise RuntimeError("Only an explicitly local API may be benchmarked.")
    password = secrets.token_urlsafe(24)
    password_hash = hash_password(password)
    end = datetime.now(UTC).date() - timedelta(days=1)
    dates = pd.bdate_range(pd.Timestamp(end) - pd.DateOffset(years=5), end).date
    async with AsyncSessionLocal() as db:
        for model in (Stock, User):
            if await db.scalar(select(func.count()).select_from(model)):
                raise RuntimeError(
                    "Benchmark requires an empty disposable database; nothing was deleted."
                )
        for i in range(100):
            ticker = f"BENCH{i:03}.JK"
            db.add(
                Stock(
                    ticker=ticker,
                    company_name="Local benchmark " + ticker,
                    exchange="IDX",
                    currency="IDR",
                    market_source="benchmark_fixture",
                    data_revision="benchmark-only",
                    data_fetched_at=datetime.now(UTC),
                )
            )
        await db.flush()
        for i in range(100):
            ticker = f"BENCH{i:03}.JK"
            await db.execute(
                insert(DailyPrice),
                [
                    {
                        "stock_ticker": ticker,
                        "trading_date": day,
                        "open": 100,
                        "high": 105,
                        "low": 95,
                        "close": 101,
                        "volume": 100000,
                    }
                    for day in dates
                ],
            )
            await db.execute(
                insert(TechnicalIndicator),
                [
                    {
                        "stock_ticker": ticker,
                        "trading_date": day,
                        "rsi_14": 55,
                        "ema_50": 100,
                        "ema_200": 99,
                        "wyckoff_phase": "Phase C",
                        "smc_patterns": {},
                    }
                    for day in dates
                ],
            )
        for i in range(20):
            db.add(
                User(
                    email=f"benchmark-{i}@example.com",
                    full_name="Local benchmark",
                    password_hash=password_hash,
                    subscription_tier="free",
                )
            )
        await db.commit()
    async with httpx.AsyncClient(base_url=base, timeout=60) as client:
        listed = await client.get("/api/v1/stocks?per_page=1")
        assert listed.status_code == 200 and listed.json()["data"][0]["company_name"].startswith(
            "Local benchmark"
        )
        headers = []
        for i in range(20):
            response = await client.post(
                "/api/v1/auth/token",
                json={"email": f"benchmark-{i}@example.com", "password": password},
            )
            assert response.status_code == 200, response.status_code
            headers.append({"Authorization": "Bearer " + response.json()["access_token"]})
        paths = {
            "list": "/api/v1/stocks?per_page=20",
            "price": "/api/v1/stocks/BENCH000.JK/price",
            "chart_5y": "/api/v1/stocks/BENCH000.JK/chart?per_page=1825",
            "screener": "/api/v1/screener?exchange=IDX&per_page=20",
            "job_admission": "/api/v1/analysis/jobs",
        }
        results = {}
        for name, path in paths.items():

            async def request(i):
                started = time.perf_counter()
                response = (
                    await client.post(
                        path,
                        headers=headers[i],
                        json={"ticker": "BENCH000.JK", "idempotency_key": "benchmark-local-job"},
                    )
                    if name == "job_admission"
                    else await client.get(path, headers=headers[i])
                )
                return time.perf_counter() - started, response.status_code

            # First round is reported separately; three warm rounds, 20 users each.
            cold = await asyncio.gather(*(request(i) for i in range(20)))
            warm = []
            for _ in range(3):
                warm.extend(await asyncio.gather(*(request(i) for i in range(20))))
            latencies = sorted(t for t, _ in warm)
            results[name] = {
                "first_round_max_seconds": round(max(t for t, _ in cold), 4),
                "warm_p50_seconds": round(statistics.median(latencies), 4),
                "warm_p95_seconds": round(latencies[int(0.95 * (len(latencies) - 1))], 4),
                "samples": len(warm),
                "errors": sum(s not in (200, 202) for _, s in cold + warm),
                "target_p95_seconds": 1,
            }
        return {
            "server_workers_configured_by_operator": server_workers,
            "environment": "local_disposable_postgresql",
            "provider": "synthetic_fixture_no_external_requests",
            "users": 20,
            "tickers": 100,
            "bars_per_ticker": len(dates),
            "data_start": str(dates[0]),
            "data_end": str(dates[-1]),
            "rate_limits": "disabled_only_in_separate_TESTING_server",
            "worker": "not_started_admission_only",
            "results": results,
        }


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8002")
    parser.add_argument(
        "--server-workers",
        type=int,
        default=1,
        help="Record the separately started API worker count; does not configure it.",
    )
    args = parser.parse_args()
    try:
        print(json.dumps(await run(args.base, args.server_workers), indent=2))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
