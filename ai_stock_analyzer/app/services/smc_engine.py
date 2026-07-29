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


def detect_order_blocks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mendeteksi Order Blocks (OB) berdasarkan BOS (Break of Structure).
    - Bullish OB: Candle bearish terakhir sebelum BOS ke atas.
    - Bearish OB: Candle bullish terakhir sebelum BOS ke bawah.
    """
    if df.empty or 'bos' not in df.columns:
        df['bullish_ob'] = False
        df['bearish_ob'] = False
        df['ob_high'] = 0.0
        df['ob_low'] = 0.0
        return df

    df['bullish_ob'] = False
    df['bearish_ob'] = False
    df['ob_high'] = 0.0
    df['ob_low'] = 0.0

    # Lacak OB aktif
    for i in range(1, len(df)):
        if df.loc[df.index[i], 'bos']:
            # Cek arah BOS
            current_close = df.loc[df.index[i], 'close']
            previous_close = df.loc[df.index[i-1], 'close']
            
            # Asumsi: Jika close > prev_close saat BOS, ini BOS uptrend
            if current_close > previous_close:
                # Cari candle bearish (close < open) terakhir ke belakang
                for j in range(i-1, max(-1, i-10), -1):
                    if df.loc[df.index[j], 'close'] < df.loc[df.index[j], 'open']:
                        df.loc[df.index[j], 'bullish_ob'] = True
                        df.loc[df.index[j], 'ob_high'] = df.loc[df.index[j], 'high']
                        df.loc[df.index[j], 'ob_low'] = df.loc[df.index[j], 'low']
                        break
            else:
                # BOS downtrend, cari candle bullish (close > open) terakhir
                for j in range(i-1, max(-1, i-10), -1):
                    if df.loc[df.index[j], 'close'] > df.loc[df.index[j], 'open']:
                        df.loc[df.index[j], 'bearish_ob'] = True
                        df.loc[df.index[j], 'ob_high'] = df.loc[df.index[j], 'high']
                        df.loc[df.index[j], 'ob_low'] = df.loc[df.index[j], 'low']
                        break

    return df

def detect_liquidity_sweep(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mendeteksi Liquidity Sweep (False Breakout).
    - Sweep Low: Harga menembus swing low sebelumnya, tetapi close di atas swing low tersebut.
    - Sweep High: Harga menembus swing high sebelumnya, tetapi close di bawah swing high tersebut.
    """
    if df.empty or 'swing_high' not in df.columns or 'swing_low' not in df.columns:
        df['liq_sweep_low'] = False
        df['liq_sweep_high'] = False
        return df

    df['liq_sweep_low'] = False
    df['liq_sweep_high'] = False

    last_swing_high = None
    last_swing_low = None

    for i in range(len(df)):
        current_high = df.loc[df.index[i], 'high']
        current_low = df.loc[df.index[i], 'low']
        current_close = df.loc[df.index[i], 'close']

        # Cek Liquidity Sweep High
        if last_swing_high is not None:
            if current_high > last_swing_high and current_close < last_swing_high:
                df.loc[df.index[i], 'liq_sweep_high'] = True
                last_swing_high = None  # Reset setelah tersweep

        # Cek Liquidity Sweep Low
        if last_swing_low is not None:
            if current_low < last_swing_low and current_close > last_swing_low:
                df.loc[df.index[i], 'liq_sweep_low'] = True
                last_swing_low = None  # Reset setelah tersweep

        # Update swing points memory
        if df.loc[df.index[i], 'swing_high']:
            last_swing_high = current_high
        if df.loc[df.index[i], 'swing_low']:
            last_swing_low = current_low

    return df
