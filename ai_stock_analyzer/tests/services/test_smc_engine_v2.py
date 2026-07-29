import pandas as pd
import numpy as np
import pytest
from app.services.smc_engine import detect_order_blocks, detect_liquidity_sweep

def test_detect_order_blocks_empty():
    df = pd.DataFrame()
    res = detect_order_blocks(df)
    assert res.empty
    
def test_detect_order_blocks_bullish():
    # Setup data with a BOS uptrend
    data = {
        'open': [100, 105, 100, 95, 110, 115, 120],
        'high': [105, 110, 105, 100, 115, 120, 125],
        'low': [95, 100, 95, 90, 105, 110, 115],
        'close': [104, 108, 96, 91, 114, 118, 122], # candle 2 & 3 are bearish (close < open)
        'bos': [False, False, False, False, True, False, False] # BOS uptrend on candle 4
    }
    df = pd.DataFrame(data)
    df.index = pd.date_range(start='2026-01-01', periods=len(df))
    
    res = detect_order_blocks(df)
    
    # Candle 3 is bearish (open=95, close=91), and is the last bearish before BOS at 4
    # Note: index 3 is candle 4 in array
    assert res.loc[res.index[3], 'bullish_ob'] == True
    assert res.loc[res.index[3], 'ob_high'] == 100
    assert res.loc[res.index[3], 'ob_low'] == 90
    assert not res.loc[res.index[4], 'bullish_ob']

def test_detect_liquidity_sweep_low():
    # Setup false breakout low
    data = {
        'high': [110, 115, 110, 105, 100, 105],
        'low': [100, 105, 100, 95, 80, 90],
        'close': [105, 110, 105, 100, 102, 100],
        'swing_high': [False, True, False, False, False, False],
        'swing_low': [False, False, True, False, False, False]
        # swing_low at index 2 is 100
        # candle at index 4 drops to 80 (low < 100), but closes at 102 (close > 100) -> Liq Sweep Low!
    }
    df = pd.DataFrame(data)
    df.index = pd.date_range(start='2026-01-01', periods=len(df))
    
    res = detect_liquidity_sweep(df)
    
    assert res.loc[res.index[4], 'liq_sweep_low'] == True
    assert not res.loc[res.index[3], 'liq_sweep_low']

def test_detect_liquidity_sweep_high():
    # Setup false breakout high
    data = {
        'high': [110, 120, 110, 105, 130, 105],
        'low': [100, 105, 100, 95, 110, 90],
        'close': [105, 110, 105, 100, 115, 100],
        'swing_high': [False, True, False, False, False, False],
        'swing_low': [False, False, True, False, False, False]
        # swing_high at index 1 is 120
        # candle at index 4 goes to 130 (high > 120), but closes at 115 (close < 120) -> Liq Sweep High!
    }
    df = pd.DataFrame(data)
    df.index = pd.date_range(start='2026-01-01', periods=len(df))
    
    res = detect_liquidity_sweep(df)
    
    assert res.loc[res.index[4], 'liq_sweep_high'] == True
