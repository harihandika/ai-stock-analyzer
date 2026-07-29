import pandas as pd
import pytest
from app.services.pattern_engine import detect_cup_and_handle, detect_bull_flag

def test_detect_cup_and_handle_empty():
    df = pd.DataFrame()
    res = detect_cup_and_handle(df)
    assert len(res) == 0

def test_detect_bull_flag_empty():
    df = pd.DataFrame()
    res = detect_bull_flag(df)
    assert len(res) == 0

def test_detect_cup_and_handle_valid():
    # Setup data
    # Cup rim at day 0 (idx 0), price 100
    # Drops to 70 at day 15 (depth 30%)
    # Rises back to 100 at day 35 (toleransi 5%)
    # Handle drops to 90 at day 42 (10%)
    
    dates = pd.date_range(start='2026-01-01', periods=50)
    data = {
        'high': [100.0] * 50,
        'low': [98.0] * 50,
        'close': [99.0] * 50,
        'volume': [1000] * 50,
        'swing_high': [False] * 50,
        'swing_low': [False] * 50
    }
    df = pd.DataFrame(data, index=dates)
    
    # Cup rim
    df.loc[df.index[0], 'high'] = 100.0
    df.loc[df.index[0], 'swing_high'] = True
    
    # Cup bottom
    df.loc[df.index[15], 'low'] = 70.0
    
    # Cup end (return to rim)
    df.loc[df.index[35], 'high'] = 98.0 # within 5% of 100
    
    # Handle end
    df.loc[df.index[42], 'low'] = 89.0 # drop 9/98 = 9.1% -> Valid (5-10%)
    
    patterns = detect_cup_and_handle(df)
    assert len(patterns) > 0
    assert patterns[0]['depth_pct'] == 0.3

def test_detect_bull_flag_valid():
    # Setup data
    dates = pd.date_range(start='2026-01-01', periods=40)
    data = {
        'open': [10.0] * 40,
        'high': [10.5] * 40,
        'low': [9.5] * 40,
        'close': [10.0] * 40,
        'volume': [100] * 40,
    }
    df = pd.DataFrame(data, index=dates)
    
    # Setup Pole: day 20 to 30, close goes from 10 to 12 (20% gain)
    df.loc[df.index[20], 'close'] = 10.0
    df.loc[df.index[30], 'close'] = 12.0
    # High volume during pole
    df.loc[df.index[20:31], 'volume'] = 500
    
    # Setup Flag: day 30 to 38, consolidate
    df.loc[df.index[31:39], 'high'] = 12.5
    df.loc[df.index[31:39], 'low'] = 11.5 # drop max 11.5
    # Low volume during flag
    df.loc[df.index[31:39], 'volume'] = 50
    
    patterns = detect_bull_flag(df)
    assert len(patterns) > 0
    assert patterns[0]['pole_gain_pct'] == 0.2
