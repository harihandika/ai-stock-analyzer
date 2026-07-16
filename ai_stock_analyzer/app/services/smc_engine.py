"""
AI Stock Analyzer - SMC Engine (Sprint 3)
Modul untuk mendeteksi pola Smart Money Concepts (FVG, BOS, CHoCH).
"""

import pandas as pd
import numpy as np


def detect_fvg(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mendeteksi Fair Value Gap (FVG).
    Bullish FVG: Low candle(t) > High candle(t-2)
    Bearish FVG: High candle(t) < Low candle(t-2)
    """
    if df.empty or len(df) < 3:
        df['bullish_fvg'] = False
        df['bearish_fvg'] = False
        df['fvg_size'] = 0.0
        return df

    # Inisialisasi default
    df['bullish_fvg'] = False
    df['bearish_fvg'] = False
    df['fvg_size'] = 0.0

    # Bullish FVG: Harga Low hari ini lebih tinggi dari harga High lusa kemarin
    df['bullish_fvg'] = df['low'] > df['high'].shift(2)
    
    # Bearish FVG: Harga High hari ini lebih rendah dari harga Low lusa kemarin
    df['bearish_fvg'] = df['high'] < df['low'].shift(2)

    # Menghitung ukuran gap (absolute)
    df.loc[df['bullish_fvg'], 'fvg_size'] = df['low'] - df['high'].shift(2)
    df.loc[df['bearish_fvg'], 'fvg_size'] = df['low'].shift(2) - df['high']

    return df


def detect_structure_breaks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mendeteksi BOS (Break of Structure) dan CHoCH (Change of Character).
    Memerlukan Swing Points (dijalankan dari pattern_engine).
    """
    if df.empty or 'swing_high' not in df.columns or 'swing_low' not in df.columns:
        # Jika belum ada swing points, kembalikan data apa adanya dengan kolom kosong
        df['bos'] = False
        df['choch'] = False
        return df

    df['bos'] = False
    df['choch'] = False

    # Ekstrak data swing high dan low terakhir
    last_swing_high = None
    last_swing_low = None
    
    # State tren saat ini (1: Uptrend, -1: Downtrend, 0: Sideways)
    # Pendekatan sederhana menggunakan SMA atau perbandingan awal
    current_trend = 0 

    for i in range(len(df)):
        # Update swing points memory
        if df.loc[df.index[i], 'swing_high']:
            last_swing_high = df.loc[df.index[i], 'high']
        if df.loc[df.index[i], 'swing_low']:
            last_swing_low = df.loc[df.index[i], 'low']

        # Logika BOS & CHoCH (Versi Simplifikasi untuk MVP)
        # 1. Break of Structure (BOS) Uptrend: Harga close memecahkan last_swing_high
        if last_swing_high is not None and df.loc[df.index[i], 'close'] > last_swing_high:
            if current_trend == 1:
                df.loc[df.index[i], 'bos'] = True # Melanjutkan Uptrend
            else:
                df.loc[df.index[i], 'choch'] = True # Dari downtrend/sideways menjadi Uptrend
                current_trend = 1
            # Reset last_swing_high agar tidak memicu terus menerus
            last_swing_high = None 
            
        # 2. Break of Structure (BOS) Downtrend: Harga close memecahkan last_swing_low
        elif last_swing_low is not None and df.loc[df.index[i], 'close'] < last_swing_low:
            if current_trend == -1:
                df.loc[df.index[i], 'bos'] = True # Melanjutkan Downtrend
            else:
                df.loc[df.index[i], 'choch'] = True # Dari uptrend/sideways menjadi Downtrend
                current_trend = -1
            # Reset last_swing_low agar tidak memicu terus menerus
            last_swing_low = None

    return df
