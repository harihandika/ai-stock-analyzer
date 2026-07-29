"""
AI Stock Analyzer - Auth Logout and Refresh Token Tests
"""

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient):
    """Test: Refresh token rotasi dan database validation."""
    # 1. Register
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.com",
            "password": "securepassword123",
            "full_name": "Refresh User",
        },
    )

    # 2. Login to get tokens
    login_response = await client.post(
        "/api/v1/auth/token",
        json={
            "email": "refresh@example.com",
            "password": "securepassword123",
        },
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    refresh_token = login_data["refresh_token"]

    import asyncio
    await asyncio.sleep(1)

    # 3. Use refresh token
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    new_refresh_token = refresh_data["refresh_token"]
    assert new_refresh_token != refresh_token

    # 4. Try to use the old refresh token again (should fail)
    old_refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert old_refresh_response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    """Test: Logout me-revoke refresh token."""
    # 1. Register
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@example.com",
            "password": "securepassword123",
            "full_name": "Logout User",
        },
    )

    # 2. Login
    login_response = await client.post(
        "/api/v1/auth/token",
        json={
            "email": "logout@example.com",
            "password": "securepassword123",
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    # 3. Logout
    logout_response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token}
    )
    assert logout_response.status_code == 200
    assert "berhasil" in logout_response.json()["message"]

    # 4. Try to refresh with revoked token
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 401

@pytest.mark.asyncio
async def test_logout_invalid_token(client: AsyncClient):
    """Test: Logout dengan token invalid tetap return 200."""
    logout_response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "some-invalid-token"}
    )
    # We should not leak information if token is not found
    assert logout_response.status_code == 200
