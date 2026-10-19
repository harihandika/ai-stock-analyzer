import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_integration_health(client: AsyncClient):
    """Test endpoint health dan root"""
    response = await client.get("/")
    assert response.status_code == 200
    assert "AI Stock Analyzer API" in response.json().get("message", "")


@pytest.mark.asyncio
async def test_integration_auth(client: AsyncClient):
    """Test registrasi dan login flow"""
    # 1. Register User
    reg_payload = {
        "email": "test_integration@example.com",
        "password": "StrongPassword123!",
        "full_name": "Integration Tester",
    }
    res_reg = await client.post("/api/v1/auth/register", json=reg_payload)
    # 201 Created atau 400 Bad Request jika user sudah ada (test idempotency)
    assert res_reg.status_code in [201, 400]

    # 2. Login User
    login_payload = {"email": "test_integration@example.com", "password": "StrongPassword123!"}
    res_login = await client.post("/api/v1/auth/token", json=login_payload)
    assert res_login.status_code == 200
    token = res_login.json().get("access_token")
    assert token is not None

    # 3. Test Protected Endpoint
    res_me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "test_integration@example.com"


@pytest.mark.asyncio
async def test_integration_sync_pipeline(client: AsyncClient, monkeypatch):
    """Real API/database pipeline with controlled external providers."""
    from unittest.mock import AsyncMock

    import numpy as np
    import pandas as pd

    from tests.support import MODEL_RESPONSE, login

    frame = pd.DataFrame(
        {
            "trading_date": pd.bdate_range("2025-01-01", periods=80).date,
            "open": np.linspace(100, 120, 80),
            "close": np.linspace(101, 121, 80),
            "high": np.linspace(105, 125, 80),
            "low": np.linspace(95, 115, 80),
            "volume": np.arange(80) + 1000,
        }
    )
    monkeypatch.setattr(
        "app.api.routers.stocks.fetch_stock_history_async", AsyncMock(return_value=frame)
    )
    monkeypatch.setattr(
        "app.api.routers.stocks.fetch_stock_info_async",
        AsyncMock(return_value={"currency": "IDR", "exchange": "IDX", "longName": "Bank Test"}),
    )
    monkeypatch.setattr(
        "app.services.ai_service.call_claude_sonnet", AsyncMock(return_value=MODEL_RESPONSE)
    )
    headers = await login(client)
    response = await client.post("/api/v1/stocks/BBCA.JK/sync", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["total_days_synced"] == 80
    result = await client.post("/api/v1/analysis/BBCA.JK", headers=headers)
    assert result.status_code == 200, result.text
    latest = (await client.get("/api/v1/stocks/BBCA.JK/analysis/latest", headers=headers)).json()
    assert latest["analysis_id"] == result.json()["result"]["id"]
    assert latest["ai_recommendation"] == "BUY"
    assert latest["confidence_score"] == 88
    assert latest["metadata"]["currency"] == "IDR"
    assert latest["analysis_matches_data"]
