import pandas as pd
import numpy as np
from app.services.smc_engine import detect_fvg, detect_structure_breaks


def test_detect_bullish_fvg():
    # Setup data dimana candle 3 low > candle 1 high
    data = {
        'high': [100, 110, 120, 125],
        'low': [90, 105, 115, 120]
    }
    df = pd.DataFrame(data)
    
    res = detect_fvg(df)
    
    # Candle index 2 (ke-3) memilik Low (115) > High candle index 0 (100)
    assert res.loc[2, 'bullish_fvg'] == True
    assert res.loc[2, 'fvg_size'] == 15.0 # 115 - 100
    
    assert res.loc[2, 'bearish_fvg'] == False


def test_detect_bearish_fvg():
    # Setup data dimana candle 3 high < candle 1 low
    data = {
        'high': [100, 95, 80, 75],
        'low': [90, 85, 70, 65]
    }
    df = pd.DataFrame(data)
    
    res = detect_fvg(df)
    
    # Candle index 2 (ke-3) memilik High (80) < Low candle index 0 (90)
    assert res.loc[2, 'bearish_fvg'] == True
    assert res.loc[2, 'fvg_size'] == 10.0 # 90 - 80
    
    assert res.loc[2, 'bullish_fvg'] == False


def test_detect_structure_breaks():
    data = {
        'high': [100, 120, 110, 130, 125],
        'low': [90, 110, 100, 120, 115],
        'close': [95, 115, 105, 125, 120],
        'swing_high': [False, True, False, False, False],
        'swing_low': [False, False, True, False, False]
    }
    df = pd.DataFrame(data)
    
    # Tren diasumsikan mulai dari sideways (0) lalu menembus swing_high di candle ke-3
    res = detect_structure_breaks(df)
    
    # Pada index 1: terjadi swing_high = 120
    # Pada index 3: close(125) > last_swing_high(120). current_trend=0, maka CHoCH terpicu
    assert res.loc[3, 'choch'] == True
    assert res.loc[3, 'bos'] == False
    
    # Jika kita punya candle ke-5 menembus high lagi, maka akan menjadi BOS
    # Tapi last_swing_high direset setelah break, jadi untuk test ini cukup memvalidasi logic di atas
