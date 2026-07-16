import pytest
from httpx import AsyncClient
from unittest.mock import patch
import pandas as pd
import numpy as np

# Fungsi bantuan untuk mendapatkan token auth
async def get_auth_token(client: AsyncClient, email="testuser@example.com"):
    # Coba register dulu, abaikan error jika sudah ada
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test User"},
    )
    # Dapatkan token
    resp = await client.post(
        "/api/v1/auth/token",
        json={"email": email, "password": "password123"},
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_get_stocks_empty(client: AsyncClient):
    """Test get stocks saat belum ada data."""
    response = await client.get("/api/v1/stocks")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_sync_stock_data_success(client: AsyncClient):
    """Test sinkronisasi data saham dengan mock market data."""
    
    # Mock return value untuk yfinance fetch info
    mock_info = {"longName": "Bank Central Asia Tbk", "sector": "Financial", "exchange": "JKSE"}
    
    # Mock return value untuk yfinance fetch history
    dates = pd.date_range(start="2023-01-01", periods=100, freq="B")
    mock_history = pd.DataFrame({
        'trading_date': dates,
        'open': np.linspace(8000, 9000, 100),
        'high': np.linspace(8100, 9100, 100),
        'low': np.linspace(7900, 8900, 100),
        'close': np.linspace(8050, 9050, 100),
        'volume': np.random.randint(1000000, 5000000, 100)
    })
    
    # Patch fungsi async market_data
    with patch("app.api.routers.stocks.fetch_stock_info_async", return_value=mock_info), \
         patch("app.api.routers.stocks.fetch_stock_history_async", return_value=mock_history):
        
        response = await client.post("/api/v1/stocks/BBCA.JK/sync")
        
        assert response.status_code == 200
        data = response.json()
        assert "Sinkronisasi berhasil" in data["message"]
        assert data["total_days_synced"] == 100


@pytest.mark.asyncio
async def test_get_stocks_list_after_sync(client: AsyncClient):
    """Test get stocks list setelah ada data yang disync."""
    mock_info = {"longName": "Bank Central Asia Tbk", "sector": "Financial", "exchange": "JKSE"}
    dates = pd.date_range(start="2023-01-01", periods=10, freq="B")
    mock_history = pd.DataFrame({
        'trading_date': dates,
        'open': np.linspace(8000, 9000, 10),
        'high': np.linspace(8100, 9100, 10),
        'low': np.linspace(7900, 8900, 10),
        'close': np.linspace(8050, 9050, 10),
        'volume': np.random.randint(1000000, 5000000, 10)
    })
    with patch("app.api.routers.stocks.fetch_stock_info_async", return_value=mock_info), \
         patch("app.api.routers.stocks.fetch_stock_history_async", return_value=mock_history):
        await client.post("/api/v1/stocks/BBCA.JK/sync")
        
    response = await client.get("/api/v1/stocks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["ticker"] == "BBCA.JK"
    assert data[0]["company_name"] == "Bank Central Asia Tbk"


@pytest.mark.asyncio
async def test_get_stock_chart(client: AsyncClient):
    """Test get chart data."""
    mock_info = {"longName": "Bank Central Asia Tbk", "sector": "Financial", "exchange": "JKSE"}
    dates = pd.date_range(start="2023-01-01", periods=30, freq="B")
    mock_history = pd.DataFrame({
        'trading_date': dates,
        'open': np.linspace(8000, 9000, 30),
        'high': np.linspace(8100, 9100, 30),
        'low': np.linspace(7900, 8900, 30),
        'close': np.linspace(8050, 9050, 30),
        'volume': np.random.randint(1000000, 5000000, 30)
    })
    with patch("app.api.routers.stocks.fetch_stock_info_async", return_value=mock_info), \
         patch("app.api.routers.stocks.fetch_stock_history_async", return_value=mock_history):
        await client.post("/api/v1/stocks/BBCA.JK/sync")

    response = await client.get("/api/v1/stocks/BBCA.JK/chart?days=30")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 30
    assert "close" in data[0]
    assert "volume" in data[0]
    assert "trading_date" in data[0]


@pytest.mark.asyncio
async def test_get_stock_chart_not_found(client: AsyncClient):
    """Test get chart untuk saham yang tidak ada."""
    response = await client.get("/api/v1/stocks/TIDAKADA/chart")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_watchlist_crud(client: AsyncClient):
    """Test Create, Read, Delete watchlist."""
    token = await get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    mock_info = {"longName": "Bank Central Asia Tbk", "sector": "Financial", "exchange": "JKSE"}
    dates = pd.date_range(start="2023-01-01", periods=10, freq="B")
    mock_history = pd.DataFrame({
        'trading_date': dates,
        'open': np.linspace(8000, 9000, 10),
        'high': np.linspace(8100, 9100, 10),
        'low': np.linspace(7900, 8900, 10),
        'close': np.linspace(8050, 9050, 10),
        'volume': np.random.randint(1000000, 5000000, 10)
    })
    with patch("app.api.routers.stocks.fetch_stock_info_async", return_value=mock_info), \
         patch("app.api.routers.stocks.fetch_stock_history_async", return_value=mock_history):
        await client.post("/api/v1/stocks/BBCA.JK/sync")
    
    # 1. Pastikan watchlist kosong
    response = await client.get("/api/v1/stocks/watchlist", headers=headers)
    assert response.status_code == 200
    assert response.json() == []
    
    # 2. Add ke watchlist
    response = await client.post(
        "/api/v1/stocks/watchlist",
        json={"ticker": "BBCA.JK", "notes": "Saham bluechip"},
        headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["stock_ticker"] == "BBCA.JK"
    assert data["notes"] == "Saham bluechip"
    
    # 3. Add saham yang tidak ada (harus 404)
    response = await client.post(
        "/api/v1/stocks/watchlist",
        json={"ticker": "NGGA_ADA", "notes": ""},
        headers=headers
    )
    assert response.status_code == 404
    
    # 4. Add duplikat (harus 409)
    response = await client.post(
        "/api/v1/stocks/watchlist",
        json={"ticker": "BBCA.JK", "notes": "Lagi"},
        headers=headers
    )
    assert response.status_code == 409
    
    # 5. Cek list watchlist lagi
    response = await client.get("/api/v1/stocks/watchlist", headers=headers)
    data = response.json()
    assert len(data) == 1
    assert data[0]["stock_ticker"] == "BBCA.JK"
    
    # 6. Delete watchlist
    response = await client.delete("/api/v1/stocks/watchlist/BBCA.JK", headers=headers)
    assert response.status_code == 204
    
    # 7. Pastikan sudah terhapus
    response = await client.get("/api/v1/stocks/watchlist", headers=headers)
    assert response.json() == []
