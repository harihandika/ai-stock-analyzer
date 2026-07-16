"""
AI Stock Analyzer - Pattern Recognition Engine (Sprint 2)
Modul untuk mendeteksi Swing Points dan Pola Klasik (Classic Patterns)
seperti Double Bottom.
"""

import pandas as pd
import numpy as np


def detect_swing_points(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Mendeteksi Swing High dan Swing Low dalam periode tertentu.
    Swing High: Titik tertinggi di antara N hari sebelum dan sesudahnya.
    Swing Low: Titik terendah di antara N hari sebelum dan sesudahnya.
    
    Args:
        df: DataFrame OHLCV
        window: Jumlah hari untuk lookback dan lookforward
    """
    if df.empty or len(df) < (window * 2 + 1):
        df['swing_high'] = False
        df['swing_low'] = False
        return df

    # Menggunakan rolling dengan center=True berarti kita melihat ke belakang dan ke depan.
    # Nilai pada index (hari ini) dibandingkan dengan max/min pada rentang (window kiri + hari ini + window kanan).
    rolling_max = df['high'].rolling(window=window * 2 + 1, center=True).max()
    rolling_min = df['low'].rolling(window=window * 2 + 1, center=True).min()

    df['swing_high'] = df['high'] == rolling_max
    df['swing_low'] = df['low'] == rolling_min
    
    # Fill NA yang terjadi di awal dan akhir dataset akibat rolling center
    df['swing_high'] = df['swing_high'].fillna(False)
    df['swing_low'] = df['swing_low'].fillna(False)
    
    return df


def detect_double_bottom(df: pd.DataFrame) -> list[dict]:
    """
    Mendeteksi pola Double Bottom.
    
    Syarat:
    1. Ada dua titik Swing Low yang berdekatan (misal: 10 - 40 hari jaraknya).
    2. Perbedaan harga (low) antara kedua titik sangat kecil (toleransi 3%).
    3. Volume pada swing low kedua lebih rendah dari swing low pertama.
    
    Returns:
        Daftar dictionary berisi informasi kemunculan Double Bottom.
    """
    if 'swing_low' not in df.columns:
        df = detect_swing_points(df)

    double_bottoms = []
    
    # Ambil index di mana swing_low = True
    swing_low_indices = df[df['swing_low']].index.tolist()
    
    for i in range(1, len(swing_low_indices)):
        idx1 = swing_low_indices[i - 1]
        idx2 = swing_low_indices[i]
        
        low1 = df.iloc[idx1]
        low2 = df.iloc[idx2]
        
        # 1. Jarak hari (karena index merupakan urutan integer atau datetime)
        # Jika index integer (karena df.reset_index sudah dijalankan):
        time_diff = idx2 - idx1 
        
        if 10 <= time_diff <= 40:
            # 2. Perbedaan harga toleransi 3%
            price_diff_pct = abs(low2['low'] - low1['low']) / low1['low']
            if price_diff_pct <= 0.03:
                # 3. Volume confirmation (Drying selling pressure)
                if low2['volume'] < low1['volume']:
                    double_bottoms.append({
                        'first_bottom_date': low1['trading_date'],
                        'first_bottom_price': low1['low'],
                        'second_bottom_date': low2['trading_date'],
                        'second_bottom_price': low2['low'],
                        'validation_date': low2['trading_date'],
                    })
                    
    return double_bottoms
