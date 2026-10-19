import asyncio
from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select, update

from app.domain.models.models import (
    AIAnalysis,
    AlertEvent,
    AnalysisJob,
    DailyPrice,
    PasswordReset,
    Stock,
)
from app.services.alerts import evaluate_alerts
from app.services.jobs import process_one
from app.services.market_metadata import utcnow
from tests.conftest import TestSessionLocal
from tests.support import MODEL_RESPONSE, login, seed_market

PLAN = {
    "ticker": "BBCA.JK",
    "currency": "IDR",
    "entry_low": 990,
    "entry_high": 1010,
    "entry": 1000,
    "stop": 950,
    "target": 1100,
    "capital": 10000000,
    "risk_pct": 1,
    "lot_size": 100,
    "horizon": "10 sesi",
    "reason": "Pantau volume",
    "invalidation": "Harga di bawah support",
}


@pytest.mark.asyncio
async def test_plan_risk_versions_and_two_account_privacy(client, db_session):
    await seed_market(db_session)
    owner, other = (
        await login(client, "plan-owner@example.com"),
        await login(client, "plan-other@example.com"),
    )
    made = await client.post("/api/v1/trade-plans", headers=owner, json=PLAN)
    assert made.status_code == 201, made.text
    item = made.json()
    assert item["details"]["calculation"]["lots"] == 20
    assert item["details"]["calculation"]["estimated_risk"] == 100000
    assert item["details"]["calculation"]["reward_risk_before_fees"] == 2
    assert (await client.get("/api/v1/trade-plans", headers=other)).json()["data"] == []
    path = "/api/v1/trade-plans/" + item["id"]
    assert (
        await client.put(path, headers=other, json={**PLAN, "expected_version": 1})
    ).status_code == 404
    updated = await client.put(
        path, headers=owner, json={**PLAN, "target": 1200, "expected_version": 1}
    )
    assert updated.json()["version"] == 2
    assert updated.json()["versions"][0]["details"]["input"]["target"] == 1100
    assert (
        await client.put(path, headers=owner, json={**PLAN, "expected_version": 1})
    ).status_code == 409
    assert (
        await client.post(
            "/api/v1/trade-plans/calculate", headers=owner, json={**PLAN, "currency": "USD"}
        )
    ).status_code == 422
    assert (
        await client.post(
            "/api/v1/trade-plans/calculate", headers=owner, json={**PLAN, "lot_size": 1}
        )
    ).status_code == 422
    assert (
        await client.post(
            "/api/v1/trade-plans/calculate", headers=owner, json={**PLAN, "stop": 1050}
        )
    ).status_code == 422
    costs = (
        await client.post(
            "/api/v1/trade-plans/calculate",
            headers=owner,
            json={**PLAN, "buy_fee_bps": 10, "sell_fee_bps": 10, "slippage_bps": 10},
        )
    ).json()
    assert costs["lots"] < 20 and costs["estimated_risk"] <= costs["risk_budget"]
    await db_session.execute(update(Stock).values(data_revision="new"))
    await db_session.commit()
    assert (await client.get("/api/v1/trade-plans", headers=owner)).json()["data"][0][
        "needs_review"
    ]


@pytest.mark.asyncio
async def test_screener_filters_complete_universe_and_saved_filter_privacy(client, db_session):
    for i in range(25):
        await seed_market(db_session, ticker=f"T{i:03}.JK", revision=str(i))
    owner, other = (
        await login(client, "screen-owner@example.com"),
        await login(client, "screen-other@example.com"),
    )
    first = await client.get("/api/v1/screener?exchange=IDX&rsi_min=50&per_page=6", headers=owner)
    assert first.status_code == 200, first.text
    assert first.json()["pagination"] == {"page": 1, "per_page": 6, "total": 25, "total_pages": 5}
    last = (
        await client.get(
            "/api/v1/screener?exchange=IDX&rsi_min=50&per_page=6&page=5", headers=owner
        )
    ).json()
    assert [r["ticker"] for r in last["data"]] == ["T024.JK"]
    assert first.json()["coverage"]["with_aligned_data"] == 25
    assert (
        await client.get("/api/v1/screener?rsi_min=70&rsi_max=20", headers=owner)
    ).status_code == 422
    assert (await client.get("/api/v1/screener?sql=DROP", headers=owner)).status_code == 422
    preset = await client.post(
        "/api/v1/screener/presets",
        headers=owner,
        json={"name": "IDX RSI", "criteria": {"exchange": "IDX", "rsi_min": 50}},
    )
    assert preset.status_code == 201
    assert (await client.get("/api/v1/screener/presets", headers=other)).json()["data"] == []
    assert (
        await client.delete("/api/v1/screener/presets/" + preset.json()["id"], headers=other)
    ).status_code == 404
    await db_session.execute(
        update(Stock).where(Stock.ticker == "T024.JK").values(data_revision=None)
    )
    await db_session.commit()
    missing = (await client.get("/api/v1/screener?missing_only=true", headers=owner)).json()
    assert [r["ticker"] for r in missing["data"]] == ["T024.JK"]


@pytest.mark.asyncio
async def test_history_comparison_exports_do_not_call_ai_or_expose_owner(client, db_session):
    await seed_market(db_session)
    headers = await login(client)
    for rec, score in [("BUY", 80), ("WAIT", 60)]:
        db_session.add(
            AIAnalysis(
                stock_ticker="BBCA.JK",
                analysis_date=date(2026, 10, 16),
                recommendation=rec,
                confidence_score=score,
                ai_summary="=untrusted spreadsheet text",
                generated_at=utcnow(),
                provenance="real",
                model_name="model",
                data_revision=rec,
                details={"limitations": "Teknikal saja"},
            )
        )
    await db_session.commit()
    history = (
        await client.get("/api/v1/stocks/BBCA.JK/analyses?per_page=1", headers=headers)
    ).json()
    assert history["pagination"]["total"] == 2
    a = (
        await db_session.scalars(select(AIAnalysis).order_by(AIAnalysis.confidence_score.desc()))
    ).all()
    compared = (
        await client.get(
            f"/api/v1/analyses/compare?first={a[0].id}&second={a[1].id}", headers=headers
        )
    ).json()
    assert compared["confidence_change_points"] == -20
    assert compared["inputs_differ"]
    assert "analyzed_by" not in str(compared)
    csv = await client.get("/api/v1/stocks/BBCA.JK/analyses/export", headers=headers)
    assert csv.status_code == 200 and csv.text.count("'=untrusted") == 2
    pdf = await client.get("/api/v1/stocks/BBCA.JK/analyses/export?format=pdf", headers=headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert (await client.get("/api/v1/auth/me", headers=headers)).json()["quota_used"] == 0


@pytest.mark.asyncio
async def test_job_acceptance_idempotency_ownership_execution_and_recovery(
    client, db_session, monkeypatch
):
    await seed_market(db_session)
    owner, other = (
        await login(client, "job-owner@example.com"),
        await login(client, "job-other@example.com"),
    )
    body = {"ticker": "BBCA.JK", "idempotency_key": "job-click-1"}
    made = await client.post("/api/v1/analysis/jobs", headers=owner, json=body)
    assert made.status_code == 202, made.text
    assert made.json()["status"] == "queued"
    job_id = made.json()["id"]
    assert (await client.post("/api/v1/analysis/jobs", headers=owner, json=body)).json()[
        "id"
    ] == job_id
    assert (
        await client.post("/api/v1/analysis/jobs", headers=owner, json={**body, "ticker": "AAPL"})
    ).status_code == 409
    assert (await client.get("/api/v1/analysis/jobs/" + job_id, headers=other)).status_code == 404
    monkeypatch.setattr("app.api.routers.stocks.do_sync_stock", AsyncMock())
    provider = AsyncMock(return_value=MODEL_RESPONSE)
    monkeypatch.setattr("app.services.ai_service.call_claude_sonnet", provider)
    assert await process_one(TestSessionLocal)
    finished = (await client.get("/api/v1/analysis/jobs/" + job_id, headers=owner)).json()
    assert finished["status"] == "succeeded", finished
    assert finished["result_id"]
    assert provider.await_count == 1
    assert (await client.get("/api/v1/auth/me", headers=owner)).json()["quota_used"] == 1
    # A separate worker instance still sees the terminal record and cannot rerun it.
    assert not await process_one(TestSessionLocal)
    assert provider.await_count == 1
    from uuid import UUID

    stale = await db_session.get(AnalysisJob, UUID(job_id))
    await db_session.refresh(stale)
    stale.status, stale.deadline = "analyzing", utcnow() - timedelta(seconds=1)
    stale.lease_token = "interrupted"
    await db_session.commit()
    assert not await process_one(TestSessionLocal)
    assert (await client.get("/api/v1/analysis/jobs/" + job_id, headers=owner)).json()["error"][
        "code"
    ] == "JOB_INTERRUPTED"


@pytest.mark.asyncio
async def test_job_failure_releases_quota_and_preserves_last_result(
    client, db_session, monkeypatch
):
    from app.core.errors import AnalysisError

    await seed_market(db_session)
    headers = await login(client)
    made = await client.post(
        "/api/v1/analysis/jobs",
        headers=headers,
        json={"ticker": "BBCA.JK", "idempotency_key": "failed-job"},
    )
    monkeypatch.setattr("app.api.routers.stocks.do_sync_stock", AsyncMock())
    monkeypatch.setattr(
        "app.services.ai_service.call_claude_sonnet",
        AsyncMock(side_effect=AnalysisError("AI_NOT_CONFIGURED", "AI belum siap", status=400)),
    )
    await process_one(TestSessionLocal)
    failed = (
        await client.get("/api/v1/analysis/jobs/" + made.json()["id"], headers=headers)
    ).json()
    assert failed["status"] == "failed"
    assert (await client.get("/api/v1/auth/me", headers=headers)).json()["quota_reserved"] == 0


@pytest.mark.asyncio
async def test_cancelled_execution_releases_reservation(client, db_session, monkeypatch):
    await seed_market(db_session)
    headers = await login(client)
    started = asyncio.Event()

    async def provider(*args):
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr("app.services.ai_service.call_claude_sonnet", provider)
    call = asyncio.create_task(client.post("/api/v1/analysis/BBCA.JK", headers=headers))
    await asyncio.wait_for(started.wait(), 5)
    call.cancel()
    with pytest.raises(asyncio.CancelledError):
        await call
    me = (await client.get("/api/v1/auth/me", headers=headers)).json()
    assert me["quota_used"] == me["quota_reserved"] == 0


@pytest.mark.asyncio
async def test_alert_crossings_are_fresh_private_and_deduplicated(client, db_session, monkeypatch):
    from app.services import alerts

    await seed_market(db_session)
    owner, other = (
        await login(client, "alert-owner@example.com"),
        await login(client, "alert-other@example.com"),
    )
    rule = await client.post(
        "/api/v1/alerts",
        headers=owner,
        json={"ticker": "BBCA.JK", "kind": "price", "threshold": 110, "direction": "above"},
    )
    assert rule.status_code == 201
    # Unknown freshness is not sufficient to establish a baseline or emit an event.
    await evaluate_alerts(db_session)
    assert not (await client.get("/api/v1/alerts", headers=owner)).json()["data"][0][
        "baseline_established"
    ]
    monkeypatch.setattr(alerts, "metadata", lambda *args: {"data_state": "fresh"})
    await evaluate_alerts(db_session)
    assert (await client.get("/api/v1/alerts", headers=owner)).json()["data"][0][
        "baseline_established"
    ]
    db_session.add(
        DailyPrice(
            stock_ticker="BBCA.JK",
            trading_date=date(2025, 3, 2),
            open=115,
            high=120,
            low=110,
            close=115,
            volume=1000,
        )
    )
    await db_session.commit()
    await evaluate_alerts(db_session)
    await evaluate_alerts(db_session)
    assert await db_session.scalar(select(func.count()).select_from(AlertEvent)) == 1
    assert (await client.get("/api/v1/notifications", headers=owner)).json()["unread"] == 1
    assert (await client.get("/api/v1/notifications", headers=other)).json()["data"] == []
    event = await db_session.scalar(select(AlertEvent))
    assert (
        await client.patch(f"/api/v1/notifications/{event.id}/read", headers=other)
    ).status_code == 404
    assert (
        await client.patch(f"/api/v1/notifications/{event.id}/read", headers=owner)
    ).status_code == 200
    assert (await client.get("/api/v1/notifications", headers=owner)).json()["unread"] == 0


@pytest.mark.asyncio
async def test_account_reset_is_one_use_and_revokes_sessions(client, db_session, monkeypatch):
    headers = await login(client)
    monkeypatch.setattr("app.core.config.settings.SMTP_HOST", "smtp.test")
    monkeypatch.setattr("app.core.config.settings.SMTP_FROM", "noreply@example.com")
    delivery = AsyncMock()
    monkeypatch.setattr("app.api.routers.account.send_password_reset", delivery)
    known = await client.post("/api/v1/auth/password-reset", json={"email": "r1@example.com"})
    unknown = await client.post(
        "/api/v1/auth/password-reset", json={"email": "unknown@example.com"}
    )
    assert known.json() == unknown.json()
    token = delivery.await_args.args[1]
    reset = await db_session.scalar(select(PasswordReset))
    assert token != reset.token_hash
    assert token not in known.text
    body = {"token": token, "new_password": "new-test-password-456"}
    assert (await client.post("/api/v1/auth/password-reset/confirm", json=body)).status_code == 200
    assert (await client.post("/api/v1/auth/password-reset/confirm", json=body)).status_code == 400
    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 401
    response = await client.post(
        "/api/v1/auth/token", json={"email": "r1@example.com", "password": body["new_password"]}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_profile_update_cannot_change_tier_and_password_change_revokes_all(
    client, db_session
):
    headers = await login(client)
    assert (
        await client.patch(
            "/api/v1/auth/me",
            headers=headers,
            json={"full_name": "Tester", "subscription_tier": "premium"},
        )
    ).status_code == 422
    response = await client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"full_name": "Nama Baru", "notifications_enabled": False},
    )
    assert response.status_code == 200 and not response.json()["notifications_enabled"]
    assert (
        await client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={"current_password": "wrong", "new_password": "new-password-123"},
        )
    ).status_code == 400
    assert (
        await client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={"current_password": "test-password-123", "new_password": "new-password-123"},
        )
    ).status_code == 200
    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 401
