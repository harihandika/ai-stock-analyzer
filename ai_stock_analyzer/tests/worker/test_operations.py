import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.domain.models.models import IngestionRun, WorkerHeartbeat
from app.services.market_metadata import as_utc, utcnow
from app.services.operations import worker_status
from app.worker import market_ops, product_worker
from tests.conftest import TestSessionLocal


@pytest.mark.asyncio
async def test_heartbeat_advances_during_slow_job_and_expires_without_progress(
    db_session, monkeypatch
):
    entered = asyncio.Event()

    async def slow_job(factory):
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(product_worker, "process_one", slow_job)
    task = asyncio.create_task(product_worker.run(TestSessionLocal, heartbeat_interval=0.03))
    try:
        await asyncio.wait_for(entered.wait(), 2)
        await asyncio.sleep(0.12)
        async with TestSessionLocal() as db:
            row = await db.scalar(select(WorkerHeartbeat))
            assert as_utc(row.heartbeat_at) > as_utc(row.started_at)
            assert row.progress_at is None
            current = await worker_status(db)
            assert current["state"] == "healthy"
            assert current["provider_connection"] == "not_verified_by_heartbeat"
            assert (await worker_status(db, now=as_utc(row.heartbeat_at) + timedelta(seconds=60)))[
                "state"
            ] == "unavailable"
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    async with TestSessionLocal() as db:
        assert (await db.scalar(select(WorkerHeartbeat))).stopped_at
        assert (await worker_status(db))["state"] == "unavailable"


@pytest.mark.asyncio
async def test_worker_failure_is_sanitized_and_once_reports_failure(
    db_session, monkeypatch, caplog
):
    monkeypatch.setattr(
        product_worker, "process_one", AsyncMock(side_effect=RuntimeError("private-provider-url"))
    )
    with pytest.raises(RuntimeError, match="^WORKER_CYCLE_FAILED$"):
        await product_worker.run(TestSessionLocal, once=True)
    async with TestSessionLocal() as db:
        row = await db.scalar(select(WorkerHeartbeat))
        assert row.error_code == "WORKER_CYCLE_FAILED"
        assert row.stopped_at and row.progress_at is None
    assert "private-provider-url" not in caplog.text


@pytest.mark.asyncio
async def test_ingestion_run_persists_blocked_and_sanitized_failure_with_retention(
    db_session, monkeypatch
):
    db_session.add(
        IngestionRun(
            started_at=utcnow() - timedelta(days=35),
            status="completed",
            provider="yahoo",
            tickers=["OLD.JK"],
            result={},
        )
    )
    await db_session.commit()
    monkeypatch.setattr(settings, "EOD_INGESTION_ENABLED", False)
    blocked = await market_ops.run_ingestion(TestSessionLocal, ["BBCA.JK"])
    async with TestSessionLocal() as db:
        rows = (await db.scalars(select(IngestionRun))).all()
        assert len(rows) == 1
        assert str(rows[0].id) == blocked["run_id"]
        assert rows[0].status == "blocked" and rows[0].finished_at
        assert rows[0].result["code"] == "INGESTION_DISABLED"
    monkeypatch.setattr(
        market_ops, "ingest", AsyncMock(side_effect=RuntimeError("private-provider-url"))
    )
    failed = await market_ops.run_ingestion(TestSessionLocal, ["AAPL"])
    assert failed["status"] == "failed"
    async with TestSessionLocal() as db:
        result = await market_ops.readiness(TestSessionLocal)
        assert result["ingestion_runs"][0]["status"] == "failed"
        assert "private-provider-url" not in str(result)
