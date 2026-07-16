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
