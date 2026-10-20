import pytest
from sqlalchemy import select

from app.api.routers import monitoring
from app.domain.models.models import AlertRule, WorkerHeartbeat
from app.services.market_metadata import utcnow
from tests.support import login, seed_market


@pytest.mark.asyncio
async def test_readiness_distinguishes_data_worker_baseline_pause_and_missing_signal(
    client, db_session, monkeypatch
):
    await seed_market(db_session)
    headers = await login(client)
    made = await client.post(
        "/api/v1/alerts",
        headers=headers,
        json={"ticker": "BBCA.JK", "kind": "price", "threshold": 105},
    )
    assert made.status_code == 201

    async def status():
        return (await client.get("/api/v1/alerts", headers=headers)).json()

    assert (await status())["data"][0]["evaluation_state"] == "waiting_for_data"
    monkeypatch.setattr(monitoring, "metadata", lambda *args: {"data_state": "fresh"})
    assert (await status())["data"][0]["evaluation_state"] == "waiting_for_worker"
    now = utcnow()
    db_session.add(WorkerHeartbeat(id="controlled-worker", started_at=now, heartbeat_at=now))
    await db_session.commit()
    assert (await status())["data"][0]["evaluation_state"] == "waiting_for_baseline"
    rule = await db_session.scalar(select(AlertRule))
    rule.previous_met = False
    await db_session.commit()
    assert (await status())["data"][0]["evaluation_state"] == "ready"
    assert (await status())["worker"]["provider_connection"] == "not_verified_by_heartbeat"
    await client.patch(
        "/api/v1/alerts/" + made.json()["id"], headers=headers, json={"enabled": False}
    )
    assert (await status())["data"][0]["evaluation_state"] == "paused"
    for signal in ["BUY", "HOLD", "WAIT"]:
        response = await client.post(
            "/api/v1/alerts",
            headers=headers,
            json={"ticker": "BBCA.JK", "kind": "signal", "signal": signal},
        )
        assert response.status_code == 201, response.text
    signal_rules = [row for row in (await status())["data"] if row["kind"] == "signal"]
    assert len(signal_rules) == 3 and {row["evaluation_state"] for row in signal_rules} == {
        "waiting_for_analysis"
    }
    other = await login(client, "monitoring-other@example.com")
    assert (await client.get("/api/v1/alerts", headers=other)).json()["data"] == []
