"""
AI Stock Analyzer - Indicator Engine (Sprint 2)
Menggunakan pandas-ta untuk menghitung indikator dasar dan algoritma rule-based
untuk deteksi anomali Volume Price Analysis (VPA).
"""

import pandas as pd
import pandas_ta as ta
import numpy as np


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Menghitung indikator teknikal dasar menggunakan pandas-ta.
    Fungsi ini dipanggil setelah data harian diambil dari market_data.

    Syarat Input:
    DataFrame dengan kolom (minimal): open, high, low, close, volume (lowercase).
    """
    if df.empty or len(df) < 50:
        # Kembalikan dataframe jika datanya terlalu sedikit untuk kalkulasi MA
        return df

    # Pastikan data diurutkan dari terlama ke terbaru
    if 'trading_date' in df.columns:
        df = df.sort_values('trading_date').reset_index(drop=True)

    # ==== Indikator Trend (Moving Averages) ====
    df['ema_20'] = ta.ema(df['close'], length=20)
    df['ema_50'] = ta.ema(df['close'], length=50)
    df['ema_200'] = ta.ema(df['close'], length=200)

    # ==== Indikator Momentum (RSI & MACD) ====
    df['rsi_14'] = ta.rsi(df['close'], length=14)
    
    macd_res = ta.macd(df['close'], fast=12, slow=26, signal=9)
    if macd_res is not None and not macd_res.empty:
        # MACD returns multiple columns: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
        df['macd'] = macd_res.iloc[:, 0]
        df['macd_signal'] = macd_res.iloc[:, 2]
    else:
        df['macd'] = np.nan
        df['macd_signal'] = np.nan

    # ==== Indikator Volatilitas (ATR) ====
    df['atr_14'] = ta.atr(df['high'], df['low'], df['close'], length=14)

    # ==== Indikator Volume (VWAP & OBV) ====
    # pandas-ta VWAP requires high, low, close, volume, and an anchor or index. 
    # For a simple daily VWAP approximation over the whole dataset or rolling:
    # Here we use On-Balance Volume (OBV)
    df['obv'] = ta.obv(df['close'], df['volume'])
    
    # Simple VWAP (Cumulative Price * Volume / Cumulative Volume)
    # Ini adalah anchored VWAP sejak bar pertama di dataframe
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()

    return df


def detect_vpa_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mendeteksi sinyal anomali Volume Price Analysis (VPA).
    - Stopping Volume
    - No Demand
    - Climactic Volume
    """
    if df.empty or 'volume' not in df.columns or len(df) < 20:
        return df

    # 1. Hitung Volume Moving Average (VMA) 20 hari
    df['vma_20'] = ta.sma(df['volume'], length=20)
    
    # 2. Hitung atribut candle
    df['spread'] = df['high'] - df['low']
    # Handle pembagian nol jika high == low
    df['close_pos'] = np.where(df['spread'] > 0, (df['close'] - df['low']) / df['spread'], 0.5)

    # Inisialisasi kolom sinyal (False default)
    df['stopping_volume'] = False
    df['no_demand'] = False
    df['climactic_volume'] = False

    # === Kondisi 1: Climactic Volume ===
    # Volume lebih besar dari 2x (200%) VMA 20
    df['climactic_volume'] = df['volume'] > (df['vma_20'] * 2)

    # === Kondisi 2: Stopping Volume (Smart Money Buying) ===
    # - Terjadi saat Downtrend (close hari ini < close kemarin)
    # - Spread lebar (spread > atr_14)
    # - Volume Ultra High (climactic)
    # - Penutupan (Close) berada di area tengah ke atas (close_pos > 0.5) -> Rejection ekor panjang di bawah
    
    # (Gunakan atr_14 jika sudah dikalkulasi, jika belum, aproksimasi pakai simple moving average spread)
    if 'atr_14' not in df.columns:
        df['atr_14'] = df['spread'].rolling(14).mean()

    # Shift(1) = data kemarin
    is_downtrend = df['close'] < df['close'].shift(1)
    is_wide_spread = df['spread'] > df['atr_14']
    rejection_bottom = df['close_pos'] > 0.5

    df['stopping_volume'] = is_downtrend & df['climactic_volume'] & is_wide_spread & rejection_bottom

    # === Kondisi 3: No Demand (Smart Money tidak tertarik memompa harga lebih tinggi) ===
    # - Terjadi saat Uptrend (close hari ini > close kemarin)
    # - Spread sempit (spread < 0.5 * atr_14)
    # - Volume sangat rendah (volume < 0.5 * vma_20)
    is_uptrend = df['close'] > df['close'].shift(1)
    is_narrow_spread = df['spread'] < (0.5 * df['atr_14'])
    is_low_volume = df['volume'] < (0.5 * df['vma_20'])

    df['no_demand'] = is_uptrend & is_narrow_spread & is_low_volume

    return df
