import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock

import pandas as pd
import pytest
from sqlalchemy import func, select, update

from app.core.errors import AnalysisError
from app.domain.models.models import AIAnalysis, AnalysisRequest, DailyPrice, Stock, User
from app.services.market_metadata import utcnow
from app.services.quota import quota_day
from tests.support import MODEL_RESPONSE, login, seed_market


@pytest.mark.asyncio
async def test_sync_requires_authentication(client):
    result = await client.post("/api/v1/stocks/BBCA.JK/sync")
    assert result.status_code == 401


@pytest.mark.asyncio
async def test_real_analysis_persists_once_and_reuses_without_quota(
    client, db_session, monkeypatch
):
    await seed_market(db_session)
    headers = await login(client)
    provider = AsyncMock(return_value=MODEL_RESPONSE)
    monkeypatch.setattr("app.services.ai_service.call_claude_sonnet", provider)
    first = await client.post("/api/v1/analysis/BBCA.JK", headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["result"]["confidence_score"] == 88
    second = await client.post("/api/v1/analysis/BBCA.JK", headers=headers)
    assert second.status_code == 200, second.text
    assert second.json()["result"]["id"] == first.json()["result"]["id"]
    assert second.json()["result"]["cached"]
    assert provider.await_count == 1
    profile = (await client.get("/api/v1/auth/me", headers=headers)).json()
    assert (profile["quota_used"], profile["quota_reserved"], profile["quota_remaining"]) == (
        1,
        0,
        2,
    )
    latest = (await client.get("/api/v1/stocks/BBCA.JK/analysis/latest", headers=headers)).json()
    assert latest["ai_summary"] == MODEL_RESPONSE["summary"]
    assert latest["ai_recommendation"] == "BUY"
    assert latest["analysis_matches_data"] is True
    picks = (await client.get("/api/v1/stocks/recommendations", headers=headers)).json()
    assert picks["data"][0]["ticker"] == "BBCA.JK"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["timeout", "invalid", "missing-key"])
async def test_ai_failure_preserves_result_and_releases_quota(
    client, db_session, monkeypatch, failure
):
    await seed_market(db_session)
    old = AIAnalysis(
        stock_ticker="BBCA.JK",
        analysis_date=quota_day(),
        ai_summary="Hasil nyata sebelumnya",
        recommendation="WAIT",
        confidence_score=40,
        provenance="real",
        data_revision="older-data",
        generated_at=utcnow(),
    )
    db_session.add(old)
    await db_session.commit()
    headers = await login(client)
    if failure == "timeout":
        provider = AsyncMock(
            side_effect=AnalysisError("AI_TIMEOUT", "Provider timeout", status=504)
        )
        monkeypatch.setattr("app.services.ai_service.call_claude_sonnet", provider)
    elif failure == "invalid":
        monkeypatch.setattr(
            "app.services.ai_service.call_claude_sonnet",
            AsyncMock(return_value={**MODEL_RESPONSE, "confidence_score": 88}),
        )
    else:
        monkeypatch.setattr("app.core.config.settings.ANTHROPIC_API_KEY", "")
    result = await client.post("/api/v1/analysis/BBCA.JK", headers=headers)
    assert result.status_code in (502, 503, 504), result.text
    assert result.json()["detail"]["stage"] == "analyzing"
    profile = (await client.get("/api/v1/auth/me", headers=headers)).json()
    assert profile["quota_used"] == profile["quota_reserved"] == 0
    assert await db_session.scalar(select(func.count()).select_from(AIAnalysis)) == 1
    latest = (await client.get("/api/v1/stocks/BBCA.JK/analysis/latest", headers=headers)).json()
    assert latest["ai_summary"] == "Hasil nyata sebelumnya"
    assert not latest["analysis_matches_data"]


@pytest.mark.asyncio
async def test_changed_data_invalidates_analysis_cache(client, db_session, monkeypatch):
    await seed_market(db_session)
    headers = await login(client)
    provider = AsyncMock(return_value=MODEL_RESPONSE)
    monkeypatch.setattr("app.services.ai_service.call_claude_sonnet", provider)
    first = await client.post("/api/v1/analysis/BBCA.JK", headers=headers)
    await db_session.execute(update(Stock).values(data_revision="revision-2"))
    await db_session.commit()
    second = await client.post("/api/v1/analysis/BBCA.JK", headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["result"]["id"] != second.json()["result"]["id"]
    assert provider.await_count == 2
    latest = (await client.get("/api/v1/stocks/BBCA.JK/analysis/latest", headers=headers)).json()
    assert latest["analysis_id"] == second.json()["result"]["id"]
    assert latest["analysis_matches_data"]


@pytest.mark.asyncio
async def test_concurrent_duplicate_uses_one_provider_call(client, db_session, monkeypatch):
    await seed_market(db_session)
    headers = await login(client)
    entered, finish = asyncio.Event(), asyncio.Event()

    async def provider(*args):
        entered.set()
        await finish.wait()
        return MODEL_RESPONSE

    call = AsyncMock(side_effect=provider)
    monkeypatch.setattr("app.services.ai_service.call_claude_sonnet", call)
    first = asyncio.create_task(client.post("/api/v1/analysis/BBCA.JK", headers=headers))
    await asyncio.wait_for(entered.wait(), 5)
    try:
        second = await client.post("/api/v1/analysis/BBCA.JK", headers=headers)
        assert second.status_code == 409, second.text
    finally:
        finish.set()
    assert (await first).status_code == 200
    assert call.await_count == 1


@pytest.mark.asyncio
async def test_concurrent_last_quota_cannot_be_overspent(client, db_session, monkeypatch):
    await seed_market(db_session)
    await seed_market(db_session, ticker="TLKM.JK", revision="tlkm")
    headers = await login(client)
    await db_session.execute(
        update(User).values(analysis_quota_used=2, last_quota_reset=quota_day())
    )
    await db_session.commit()
    entered, finish = asyncio.Event(), asyncio.Event()

    async def provider(*args):
        entered.set()
        await finish.wait()
        return MODEL_RESPONSE

    monkeypatch.setattr(
        "app.services.ai_service.call_claude_sonnet", AsyncMock(side_effect=provider)
    )
    first = asyncio.create_task(client.post("/api/v1/analysis/BBCA.JK", headers=headers))
    await asyncio.wait_for(entered.wait(), 5)
    try:
        second = await client.post("/api/v1/analysis/TLKM.JK", headers=headers)
        assert second.status_code == 403, second.text
    finally:
        finish.set()
    assert (await first).status_code == 200
    me = (await client.get("/api/v1/auth/me", headers=headers)).json()
    assert (me["quota_used"], me["quota_reserved"], me["quota_remaining"]) == (3, 0, 0)


@pytest.mark.asyncio
async def test_idempotency_key_rejects_changed_input(client, db_session, monkeypatch):
    await seed_market(db_session)
    headers = {**await login(client), "Idempotency-Key": "user-click-1"}
    monkeypatch.setattr(
        "app.services.ai_service.call_claude_sonnet", AsyncMock(return_value=MODEL_RESPONSE)
    )
    assert (await client.post("/api/v1/analysis/BBCA.JK", headers=headers)).status_code == 200
    await db_session.execute(update(Stock).values(data_revision="changed"))
    await db_session.commit()
    assert (await client.post("/api/v1/analysis/BBCA.JK", headers=headers)).status_code == 409


@pytest.mark.asyncio
async def test_cached_response_also_binds_idempotency_key(client, db_session, monkeypatch):
    await seed_market(db_session)
    owner = await login(client, "owner@example.com")
    reader = {**await login(client, "reader@example.com"), "Idempotency-Key": "cached-click"}
    provider = AsyncMock(return_value=MODEL_RESPONSE)
    monkeypatch.setattr("app.services.ai_service.call_claude_sonnet", provider)
    assert (await client.post("/api/v1/analysis/BBCA.JK", headers=owner)).status_code == 200
    cached = await client.post("/api/v1/analysis/BBCA.JK", headers=reader)
    assert cached.status_code == 200, cached.text
    assert cached.json()["result"]["cached"]
    me = (await client.get("/api/v1/auth/me", headers=reader)).json()
    assert me["quota_used"] == me["quota_reserved"] == 0
    await db_session.execute(update(Stock).values(data_revision="changed-after-cache"))
    await db_session.commit()
    assert (await client.post("/api/v1/analysis/BBCA.JK", headers=reader)).status_code == 409
    assert provider.await_count == 1


@pytest.mark.asyncio
async def test_profile_reset_and_expired_reservation(client, db_session):
    headers = await login(client)
    user = (await db_session.execute(select(User))).scalar_one()
    user.analysis_quota_used = 2
    user.analysis_quota_reserved = 1
    user.last_quota_reset = quota_day() - timedelta(days=1)
    db_session.add(
        AnalysisRequest(
            user_id=user.id,
            request_key="expired",
            input_revision="old",
            status="running",
            quota_day=user.last_quota_reset,
            expires_at=utcnow() - timedelta(minutes=1),
        )
    )
    await db_session.commit()
    profile = (await client.get("/api/v1/auth/me", headers=headers)).json()
    assert (profile["quota_used"], profile["quota_reserved"], profile["quota_remaining"]) == (
        0,
        0,
        3,
    )
    assert profile["quota_reset_at"].endswith("+07:00")
    await db_session.refresh(user)
    # Previous-day reservations cannot debit today's quota.
    assert user.last_quota_reset < quota_day()


@pytest.mark.asyncio
async def test_missing_prices_and_unknown_analysis_never_fabricated(client, db_session):
    db_session.add(Stock(ticker="AAPL", company_name="Apple", currency="USD"))
    db_session.add(
        AIAnalysis(
            stock_ticker="AAPL",
            analysis_date=quota_day(),
            recommendation="BUY",
            ai_summary="Legacy placeholder",
            confidence_score=88,
        )
    )
    await db_session.commit()
    headers = await login(client)
    quote = (await client.get("/api/v1/stocks/AAPL/price")).json()
    assert quote["current_price"] is quote["change_percent"] is None
    assert quote["metadata"]["data_state"] == "unavailable"
    assert quote["metadata"]["currency"] == "USD"
    latest = (await client.get("/api/v1/stocks/AAPL/analysis/latest", headers=headers)).json()
    assert latest["ai_recommendation"] is None
    assert (await client.get("/api/v1/stocks/recommendations", headers=headers)).json()[
        "data"
    ] == []


@pytest.mark.asyncio
async def test_failed_sync_preserves_history(client, db_session, monkeypatch):
    await seed_market(db_session)
    headers = await login(client)
    monkeypatch.setattr(
        "app.api.routers.stocks.fetch_stock_history_async", AsyncMock(return_value=pd.DataFrame())
    )
    result = await client.post("/api/v1/stocks/BBCA.JK/sync", headers=headers)
    assert result.status_code == 503
    quote = (await client.get("/api/v1/stocks/BBCA.JK/price")).json()
    assert quote["current_price"] == pytest.approx(105.9)
    assert quote["change_percent"] == pytest.approx((105.9 - 105.8) / 105.8 * 100)
    assert quote["metadata"]["data_revision"] == "revision-1"
    assert await db_session.scalar(select(func.count()).select_from(DailyPrice)) == 60


@pytest.mark.asyncio
async def test_watchlist_notes_are_private(client, db_session):
    await seed_market(db_session)
    a, b = await login(client, "a@example.com"), await login(client, "b@example.com")
    assert (
        await client.post("/api/v1/stocks/watchlist", headers=a, json={"ticker": "BBCA.JK"})
    ).status_code == 201
    assert (
        await client.patch("/api/v1/stocks/watchlist/BBCA.JK", headers=b, json={"notes": "stolen"})
    ).status_code == 404
    assert (
        await client.patch(
            "/api/v1/stocks/watchlist/BBCA.JK", headers=a, json={"notes": "Pantau volume"}
        )
    ).status_code == 200
    assert (await client.get("/api/v1/stocks/watchlist", headers=a)).json()[0][
        "notes"
    ] == "Pantau volume"
    assert (
        await client.patch("/api/v1/stocks/watchlist/BBCA.JK", headers=a, json={"notes": "x" * 501})
    ).status_code == 422
