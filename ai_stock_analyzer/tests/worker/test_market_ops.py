from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.core.config import settings
from app.core.errors import AnalysisError
from app.worker import market_ops
from tests.conftest import TestSessionLocal
from tests.support import seed_market


@pytest.mark.asyncio
async def test_ingestion_is_opt_in_and_never_calls_provider_before_readiness(
    db_session, monkeypatch
):
    sync = AsyncMock()
    monkeypatch.setattr(market_ops, "do_sync_stock", sync)
    monkeypatch.setattr(settings, "EOD_INGESTION_ENABLED", False)
    assert (await market_ops.ingest(TestSessionLocal, ["BBCA.JK"]))["code"] == "INGESTION_DISABLED"
    monkeypatch.setattr(settings, "EOD_INGESTION_ENABLED", True)
    monkeypatch.setattr(settings, "MARKET_CALENDAR_VERIFIED", False)
    assert (await market_ops.ingest(TestSessionLocal, ["BBCA.JK"]))[
        "code"
    ] == "CALENDAR_NOT_VERIFIED"
    sync.assert_not_awaited()
    for invalid in ("", "BAD/TICKER", ",".join("T" + str(i) for i in range(21))):
        with pytest.raises(ValueError):
            market_ops.universe(invalid)


@pytest.mark.asyncio
async def test_current_session_is_skipped_and_retry_is_bounded(db_session, monkeypatch):
    stock = await seed_market(db_session)
    stock.market_source = "Yahoo Finance"
    stock.publication_delay_minutes = 30
    await db_session.commit()
    monkeypatch.setattr(settings, "EOD_INGESTION_ENABLED", True)
    monkeypatch.setattr(settings, "MARKET_CALENDAR_VERIFIED", True)
    monkeypatch.setattr(settings, "EOD_PUBLICATION_DELAY_MINUTES", 30)
    monkeypatch.setattr(settings, "MARKET_DATA_PROVIDER", "yahoo")
    monkeypatch.setattr(
        market_ops,
        "session_status",
        lambda *a, **k: {"expected_market_date": "2025-03-01", "data_state": "fresh"},
    )
    sync = AsyncMock()
    monkeypatch.setattr(market_ops, "do_sync_stock", sync)
    result = await market_ops.ingest(TestSessionLocal, ["BBCA.JK", "BBCA.JK"])
    assert result["status"] == "completed" and len(result["results"]) == 1
    assert result["results"][0]["attempts"] == 0
    sync.assert_not_awaited()
    sync.side_effect = [
        AnalysisError("RATE_LIMIT", "private URL must not escape", status=503),
        {
            "metadata": {
                "data_state": "fresh",
                "market_as_of": "2026-10-16",
                "source": "Yahoo Finance",
            }
        },
    ]
    result = await market_ops.ingest(TestSessionLocal, ["BBCA.JK"], refresh=True)
    assert result["status"] == "completed" and result["results"][0]["attempts"] == 2
    sync.side_effect = AnalysisError("RATE_LIMIT", "private URL must not escape", status=503)
    result = await market_ops.ingest(TestSessionLocal, ["BBCA.JK"], refresh=True)
    assert result["status"] == "incomplete" and result["results"][0]["attempts"] == 2
    assert "private URL" not in str(result)
    await db_session.refresh(stock)
    assert stock.data_revision == "revision-1"


@pytest.mark.asyncio
async def test_status_does_not_emit_credentials_and_does_not_claim_live_readiness(
    db_session, monkeypatch
):
    await seed_market(db_session)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "private-test-value")
    result = await market_ops.readiness(TestSessionLocal)
    assert "private-test-value" not in str(result)
    assert result["live_provider_and_delivery"] == "not_verified_by_this_read_only_command"
    assert result["jobs"]["queued"] == 0
    assert result["stocks"][0]["market_as_of"] == date(2025, 3, 1)


def test_single_host_lock_rejects_overlapping_scheduler_runs(tmp_path):
    path = tmp_path / "ingestion.lock"
    with market_ops.ingestion_lock(path):
        with pytest.raises(BlockingIOError), market_ops.ingestion_lock(path):
            pass
    with market_ops.ingestion_lock(path):
        pass
