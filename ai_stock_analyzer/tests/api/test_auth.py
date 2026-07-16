"""
AI Stock Analyzer - Authentication API Tests
Menguji endpoint registrasi, login, dan profil pengguna.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test: Registrasi pengguna baru berhasil."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@example.com",
            "password": "securepassword123",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "user" in data
    assert data["user"]["email"] == "testuser@example.com"
    assert data["user"]["full_name"] == "Test User"
    assert data["user"]["subscription_tier"] == "free"
    # Pastikan password tidak bocor di response
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test: Registrasi dengan email yang sudah ada harus gagal (409)."""
    payload = {
        "email": "duplicate@example.com",
        "password": "password12345",
        "full_name": "Duplicate User",
    }
    # Registrasi pertama (berhasil)
    await client.post("/api/v1/auth/register", json=payload)

    # Registrasi kedua (harus gagal)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "sudah terdaftar" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """Test: Registrasi dengan format email yang tidak valid harus gagal (422)."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "password12345",
            "full_name": "User",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    """Test: Registrasi dengan password kurang dari 8 karakter harus gagal (422)."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "short",
            "full_name": "User",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test: Login dengan credentials yang benar harus mengembalikan JWT token."""
    # Registrasi dulu
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "loginuser@example.com",
            "password": "correctpassword",
            "full_name": "Login User",
        },
    )

    # Login
    response = await client.post(
        "/api/v1/auth/token",
        json={
            "email": "loginuser@example.com",
            "password": "correctpassword",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test: Login dengan password salah harus gagal (401)."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpass@example.com",
            "password": "correctpassword",
            "full_name": "Wrong Pass User",
        },
    )

    response = await client.post(
        "/api/v1/auth/token",
        json={
            "email": "wrongpass@example.com",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient):
    """Test: Login dengan email yang tidak terdaftar harus gagal (401)."""
    response = await client.post(
        "/api/v1/auth/token",
        json={
            "email": "nonexistent@example.com",
            "password": "somepassword",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_profile(client: AsyncClient):
    """Test: Mendapatkan profil pengguna yang sedang login dengan JWT token."""
    # Registrasi
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "profile@example.com",
            "password": "profilepassword",
            "full_name": "Profile User",
        },
    )

    # Login
    login_response = await client.post(
        "/api/v1/auth/token",
        json={
            "email": "profile@example.com",
            "password": "profilepassword",
        },
    )
    token = login_response.json()["access_token"]

    # Dapatkan profil
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "profile@example.com"
    assert data["full_name"] == "Profile User"


@pytest.mark.asyncio
async def test_get_profile_without_token(client: AsyncClient):
    """Test: Mengakses profil tanpa token harus gagal (401)."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_profile_with_invalid_token(client: AsyncClient):
    """Test: Mengakses profil dengan token yang tidak valid harus gagal (401)."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer this.is.not.valid"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test: Health check endpoint harus selalu mengembalikan 200."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
