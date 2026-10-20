import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import update

from app.core.errors import AnalysisError
from app.domain.models.models import AnalysisJob
from app.services.jobs import process_one
from app.services.market_metadata import utcnow
from tests.conftest import TestSessionLocal
from tests.support import MODEL_RESPONSE, login, seed_market


@pytest.mark.asyncio
async def test_retryable_job_uses_two_attempts_but_one_successful_quota(
    client, db_session, monkeypatch
):
    await seed_market(db_session)
    headers = await login(client)
    response = await client.post(
        "/api/v1/analysis/jobs",
        headers=headers,
        json={"ticker": "BBCA.JK", "idempotency_key": "retryable-job"},
    )
    monkeypatch.setattr("app.api.routers.stocks.do_sync_stock", AsyncMock())
    provider = AsyncMock(
        side_effect=[AnalysisError("AI_RATE_LIMITED", "Coba lagi", status=503), MODEL_RESPONSE]
    )
    monkeypatch.setattr("app.services.ai_service.call_claude_sonnet", provider)
    await process_one(TestSessionLocal)
    path = "/api/v1/analysis/jobs/" + response.json()["id"]
    first = (await client.get(path, headers=headers)).json()
    assert first["status"] == "queued" and first["attempts"] == 1
    assert (await client.get("/api/v1/auth/me", headers=headers)).json()["quota_reserved"] == 0
    await db_session.execute(
        update(AnalysisJob).values(available_at=utcnow() - timedelta(seconds=1))
    )
    await db_session.commit()
    await process_one(TestSessionLocal)
    final = (await client.get(path, headers=headers)).json()
    assert final["status"] == "succeeded" and final["attempts"] == 2
    assert (await client.get("/api/v1/auth/me", headers=headers)).json()["quota_used"] == 1
    assert provider.await_count == 2


@pytest.mark.asyncio
async def test_expired_queue_never_calls_provider(client, db_session, monkeypatch):
    await seed_market(db_session)
    headers = await login(client)
    response = await client.post(
        "/api/v1/analysis/jobs",
        headers=headers,
        json={"ticker": "BBCA.JK", "idempotency_key": "expired-job"},
    )
    await db_session.execute(update(AnalysisJob).values(expires_at=utcnow() - timedelta(seconds=1)))
    await db_session.commit()
    provider = AsyncMock()
    monkeypatch.setattr("app.services.ai_service.call_claude_sonnet", provider)
    assert not await process_one(TestSessionLocal)
    assert (
        await client.get("/api/v1/analysis/jobs/" + response.json()["id"], headers=headers)
    ).json()["error"]["code"] == "QUEUE_EXPIRED"
    provider.assert_not_awaited()


@pytest.mark.asyncio
async def test_backtest_run_and_export_are_stored_and_private(client, db_session, monkeypatch):
    from app.worker.backtester import Backtester
    from tests.services.test_backtester import manual

    owner, other = (
        await login(client, "run-owner@example.com"),
        await login(client, "run-other@example.com"),
    )

    async def prepare(self):
        self.df = manual()
        self.df.loc[58, ["is_spring", "stopping_volume"]] = True
        self.df.loc[59, "close"] = 110
        self.data_revision = "fixture-prices"
        return True

    monkeypatch.setattr(Backtester, "_fetch_and_prepare_data", prepare)
    response = await client.post(
        "/api/v1/analysis/AAPL/backtest",
        headers=owner,
        json={"initial_capital": 100.1, "lot_size": 1, "buy_fee_bps": 10, "sell_fee_bps": 10},
    )
    assert response.status_code == 200, response.text
    run = response.json()
    assert datetime.fromisoformat(run["created_at"]).tzinfo is not None
    assert run["data_revision"] == "fixture-prices"
    assert run["total_fees"] == pytest.approx(0.21)
    path = "/api/v1/backtests/" + run["run_id"]
    assert (await client.get(path, headers=owner)).json()["effective_parameters"][
        "buy_fee_bps"
    ] == 10
    assert (await client.get(path, headers=other)).status_code == 404
    assert (await client.get(path + "/export", headers=other)).status_code == 404
    # SQL-generated SQLite timestamps lose tzinfo on read. The documented
    # writer contract is UTC; list/detail/export must retain the same instant.
    import uuid

    from app.domain.models.models import BacktestRun

    instant = datetime(2026, 10, 20, 4, 58, 39, tzinfo=UTC)
    await db_session.execute(
        update(BacktestRun)
        .where(BacktestRun.id == uuid.UUID(run["run_id"]))
        .values(created_at=instant)
    )
    await db_session.commit()
    history = (await client.get("/api/v1/backtests", headers=owner)).json()["data"][0]
    detail = (await client.get(path, headers=owner)).json()
    assert datetime.fromisoformat(history["created_at"]) == instant
    assert datetime.fromisoformat(detail["created_at"]) == instant
    assert detail["data_revision"] == history["data_revision"] == "fixture-prices"
    assert detail["run_id"] == history["id"]
    exported = await client.get(path + "/export", headers=owner)
    assert instant.isoformat() in exported.text
    assert exported.status_code == 200
    assert (
        "fixture-prices" in exported.text
        and "summary" in exported.text
        and "trade" in exported.text
    )
    assert (await client.get("/api/v1/backtests", headers=other)).json()["pagination"]["total"] == 0


@pytest.mark.asyncio
async def test_provider_namespace_prevents_shared_model_cache_collision(
    client, db_session, monkeypatch
):
    from app.core.config import settings

    await seed_market(db_session)
    headers = await login(client)
    provider = AsyncMock(return_value=MODEL_RESPONSE)
    monkeypatch.setattr("app.services.ai_service.call_claude_sonnet", provider)
    first = await client.post("/api/v1/analysis/BBCA.JK", headers=headers)
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_MODEL", settings.AI_MODEL_OPERATIONAL)
    second = await client.post("/api/v1/analysis/BBCA.JK", headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["result"]["id"] != second.json()["result"]["id"]
    assert second.json()["result"]["provider_name"] == "gemini"
    assert provider.await_count == 2


@pytest.mark.asyncio
async def test_two_workers_cannot_execute_the_same_claim(client, db_session, monkeypatch):
    await seed_market(db_session)
    headers = await login(client)
    await client.post(
        "/api/v1/analysis/jobs",
        headers=headers,
        json={"ticker": "BBCA.JK", "idempotency_key": "two-workers"},
    )
    monkeypatch.setattr("app.api.routers.stocks.do_sync_stock", AsyncMock())
    entered, finish = asyncio.Event(), asyncio.Event()

    async def model(*args):
        entered.set()
        await finish.wait()
        return MODEL_RESPONSE

    provider = AsyncMock(side_effect=model)
    monkeypatch.setattr("app.services.ai_service.call_claude_sonnet", provider)
    first = asyncio.create_task(process_one(TestSessionLocal))
    await asyncio.wait_for(entered.wait(), 5)
    try:
        assert not await process_one(TestSessionLocal)
    finally:
        finish.set()
    assert await first
    assert provider.await_count == 1


@pytest.mark.asyncio
async def test_concurrent_watchlist_add_is_not_duplicated(client, db_session):
    await seed_market(db_session)
    headers = await login(client)
    responses = await asyncio.gather(
        *[
            client.post("/api/v1/stocks/watchlist", headers=headers, json={"ticker": "BBCA.JK"})
            for _ in range(2)
        ]
    )
    assert sorted(r.status_code for r in responses) == [201, 409]
    assert len((await client.get("/api/v1/stocks/watchlist", headers=headers)).json()) == 1


@pytest.mark.asyncio
async def test_two_tabs_cannot_queue_duplicate_active_ticker(client, db_session):
    await seed_market(db_session)
    headers = await login(client)
    responses = await asyncio.gather(
        *[
            client.post(
                "/api/v1/analysis/jobs",
                headers=headers,
                json={"ticker": "BBCA.JK", "idempotency_key": "browser-tab-" + str(i)},
            )
            for i in range(2)
        ]
    )
    assert sorted(r.status_code for r in responses) == [202, 409]
    jobs = (await client.get("/api/v1/analysis/jobs?active=true", headers=headers)).json()["data"]
    assert len(jobs) == 1
    accepted_index = next(i for i, response in enumerate(responses) if response.status_code == 202)
    repeated = await client.post(
        "/api/v1/analysis/jobs",
        headers=headers,
        json={"ticker": "BBCA.JK", "idempotency_key": "browser-tab-" + str(accepted_index)},
    )
    assert repeated.status_code == 202 and repeated.json()["id"] == jobs[0]["id"]
