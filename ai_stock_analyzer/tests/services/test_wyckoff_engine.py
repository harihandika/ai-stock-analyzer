import pandas as pd
import numpy as np
from app.services.wyckoff_engine import detect_wyckoff_accumulation


def create_mock_dataframe(rows=100):
    """Membuat dummy dataframe OHLCV untuk testing."""
    dates = pd.date_range(start="2023-01-01", periods=rows, freq="B")
    data = {
        'trading_date': dates,
        'open': np.linspace(100, 100, rows),
        'high': np.linspace(105, 105, rows),
        'low': np.linspace(95, 95, rows),
        'close': np.linspace(102, 102, rows),
        'volume': np.full(rows, 5000),
        'vma_20': np.full(rows, 5000)
    }
    return pd.DataFrame(data)


def test_detect_wyckoff_accumulation_spring():
    df = create_mock_dataframe(100)
    
    # Simulate a Spring at index 60
    # Harga jatuh mencetak rekor terendah (lowest dalam 50 hari)
    df.loc[60, 'low'] = 80  
    df.loc[60, 'high'] = 100
    df.loc[60, 'close'] = 98 # Ditarik naik ke atas (rejection)
    df.loc[60, 'volume'] = 10000 # Volume ultra high (>1.2x VMA)
    
    res_df = detect_wyckoff_accumulation(df)
    
    assert res_df.loc[60, 'is_spring'] == True
    assert res_df.loc[60, 'wyckoff_phase'] == "Phase C (Spring)"


def test_detect_wyckoff_accumulation_sos():
    df = create_mock_dataframe(100)
    
    # 1. Simulate a Spring at index 60
    df.loc[60, 'low'] = 80
    df.loc[60, 'high'] = 100
    df.loc[60, 'close'] = 98 
    df.loc[60, 'volume'] = 10000 
    
    # 2. Simulate SOS at index 65 (within 15 days of Spring)
    df.loc[64, 'close'] = 102
    df.loc[65, 'close'] = 110 # Bullish (close > prev close)
    df.loc[65, 'high'] = 112
    df.loc[65, 'low'] = 105
    df.loc[65, 'volume'] = 8000 # Volume > 1.5x VMA (5000 * 1.5 = 7500)
    
    res_df = detect_wyckoff_accumulation(df)
    
    assert res_df.loc[60, 'is_spring'] == True
    assert res_df.loc[65, 'wyckoff_phase'] == "Phase D (SOS)"


def test_detect_wyckoff_accumulation_empty():
    df = pd.DataFrame()
    res_df = detect_wyckoff_accumulation(df)
    assert res_df.empty
