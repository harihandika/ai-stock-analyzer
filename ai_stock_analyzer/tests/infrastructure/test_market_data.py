import pytest
from unittest.mock import patch
import pandas as pd
import numpy as np

from app.infrastructure.market_data import fetch_stock_history_async, fetch_stock_info_async


@pytest.mark.asyncio
async def test_fetch_stock_info():
    """Test fetch stock info mengembalikan format dict yang diharapkan."""
    
    mock_info = {
        "longName": "PT Bank Central Asia Tbk",
        "symbol": "BBCA.JK",
        "sector": "Financial Services",
        "industry": "Banks - Regional"
    }
    
    with patch("yfinance.Ticker") as mock_ticker:
        mock_ticker.return_value.info = mock_info
        
        info = await fetch_stock_info_async("BBCA.JK")
        
        assert isinstance(info, dict)
        assert info["longName"] == "PT Bank Central Asia Tbk"
        assert info["sector"] == "Financial Services"


@pytest.mark.asyncio
async def test_fetch_stock_history():
    """Test fetch stock history mengembalikan DataFrame dengan format yang benar."""
    
    dates = pd.date_range(start="2023-01-01", periods=10, freq="B")
    mock_df = pd.DataFrame({
        'Open': np.linspace(8000, 8100, 10),
        'High': np.linspace(8100, 8200, 10),
        'Low': np.linspace(7900, 8000, 10),
        'Close': np.linspace(8050, 8150, 10),
        'Volume': np.random.randint(10000, 50000, 10)
    }, index=dates)
    mock_df.index.name = 'Date'
    
    with patch("yfinance.Ticker") as mock_ticker:
        mock_ticker.return_value.history.return_value = mock_df
        
        df = await fetch_stock_history_async("BBCA.JK", period="1mo")
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        # Pastikan nama kolom sudah disesuaikan ke lowercase
        assert 'trading_date' in df.columns
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns
        
        # Pastikan tidak ada index Date karena sudah di-reset
        assert df.index.name != 'Date'


@pytest.mark.asyncio
async def test_fetch_stock_history_empty():
    """Test fetch stock history saat yfinance mengembalikan DataFrame kosong."""
    
    with patch("yfinance.Ticker") as mock_ticker:
        mock_ticker.return_value.history.return_value = pd.DataFrame()
        
        df = await fetch_stock_history_async("INVALID_TICKER", period="1mo")
        
        assert isinstance(df, pd.DataFrame)
        assert df.empty
