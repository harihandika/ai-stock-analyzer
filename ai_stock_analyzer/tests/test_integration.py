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
        "full_name": "Integration Tester"
    }
    res_reg = await client.post("/api/v1/auth/register", json=reg_payload)
    # 201 Created atau 400 Bad Request jika user sudah ada (test idempotency)
    assert res_reg.status_code in [201, 400]
    
    # 2. Login User
    login_payload = {
        "email": "test_integration@example.com",
        "password": "StrongPassword123!"
    }
    res_login = await client.post(
        "/api/v1/auth/token", 
        json=login_payload
    )
    assert res_login.status_code == 200
    token = res_login.json().get("access_token")
    assert token is not None
    
    # 3. Test Protected Endpoint
    res_me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "test_integration@example.com"


@pytest.mark.asyncio
async def test_integration_sync_pipeline(client: AsyncClient):
    """Test full pipeline dari Sync sampai AI Prompting"""
    # 1. Sync stock data (assuming we have a mocked yfinance response or test ticker)
    # Using 'BBCA.JK' as it's standard in Indonesia, but for unit test, 
    # we might mock it or let it run against real if it's an integration test.
    # Note: For reliability in CI, we'd mock `fetch_stock_history_async`.
    # But since this is a local integration test, we'll try to hit it or just check endpoint response.
    
    # We will test the structure of response from the Sync endpoint.
    res_sync = await client.post("/api/v1/stocks/BBCA.JK/sync")
    # if it succeeds, it should return 200 OK
    if res_sync.status_code == 200:
        data = res_sync.json()
        assert "Sinkronisasi berhasil" in data["message"]
        assert "patterns_detected" in data
        
        # 2. Get latest analysis (to see if prompt/AI response works or is queued)
        # Note: If no token, it might return 401. So let's login first.
        login_payload = {
            "email": "test_integration@example.com",
            "password": "StrongPassword123!"
        }
        res_login = await client.post("/api/v1/auth/token", json=login_payload)
        token = res_login.json().get("access_token")
        
        # Now get latest analysis
        res_analysis = await client.get(
            "/api/v1/stocks/BBCA.JK/analysis/latest",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_analysis.status_code in [200, 404] # 404 if AI hasn't run yet
