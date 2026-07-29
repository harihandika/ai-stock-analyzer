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


def detect_cup_and_handle(df: pd.DataFrame) -> list[dict]:
    """
    Mendeteksi pola Cup & Handle.
    1. Swing high (cup rim) diikuti penurunan 15-35%.
    2. Titik terendah (cup bottom).
    3. Harga naik kembali ke level rim (±5% toleransi) dalam 30-65 hari dari awal.
    4. Koreksi kecil 5-10% (handle) selama 5-15 hari.
    """
    if 'swing_high' not in df.columns or 'swing_low' not in df.columns:
        df = detect_swing_points(df)

    patterns = []
    # Mengambil integer location dari baris yang swing_high-nya True
    swing_high_indices = np.where(df['swing_high'])[0].tolist()

    for i in range(len(swing_high_indices)):
        idx_start = swing_high_indices[i]
        start_candle = df.iloc[idx_start]
        rim_price = start_candle['high']

        # Mencari cup end di masa depan yang mendekati rim price (30-65 hari)
        for j in range(idx_start + 30, min(idx_start + 65, len(df))):
            end_candle = df.iloc[j]
            
            # Cek apakah harga kembali ke level rim (toleransi 5%)
            if abs(end_candle['high'] - rim_price) / rim_price <= 0.05:
                # Cek kedalaman cup (harus 15-35%)
                cup_df = df.iloc[idx_start:j+1]
                cup_bottom_idx = cup_df['low'].idxmin()
                
                # Cek tipe index, if datatime index, get integer loc
                # Assuming df is reset index or loc can use integer
                if isinstance(cup_bottom_idx, (int, np.integer)) and cup_bottom_idx in df.index:
                    pass
                else:
                    # if index is datetime, get position
                    cup_bottom_idx = df.index.get_loc(cup_bottom_idx)

                bottom_candle = df.iloc[cup_bottom_idx]
                depth_pct = (rim_price - bottom_candle['low']) / rim_price

                if 0.15 <= depth_pct <= 0.35:
                    # Cup valid, cari handle
                    # Handle adalah koreksi 5-10% setelah j, dalam 5-15 hari
                    handle_start_idx = j
                    for k in range(handle_start_idx + 5, min(handle_start_idx + 15, len(df))):
                        handle_end_candle = df.iloc[k]
                        handle_drop_pct = (end_candle['high'] - handle_end_candle['low']) / end_candle['high']

                        if 0.05 <= handle_drop_pct <= 0.10:
                            # Cek validitas: pastikan tidak drop lebih dalam dari handle
                            handle_df = df.iloc[handle_start_idx:k+1]
                            if handle_df['low'].min() >= end_candle['high'] * 0.85: # max 15% drop total for handle
                                patterns.append({
                                    'cup_start_date': start_candle.get('trading_date', df.index[idx_start]),
                                    'cup_bottom_date': bottom_candle.get('trading_date', df.index[cup_bottom_idx]),
                                    'cup_end_date': end_candle.get('trading_date', df.index[j]),
                                    'handle_end_date': handle_end_candle.get('trading_date', df.index[k]),
                                    'depth_pct': depth_pct
                                })
                                break # handle found
    return patterns


def detect_bull_flag(df: pd.DataFrame) -> list[dict]:
    """
    Mendeteksi pola Bull Flag.
    1. Pole: kenaikan >= 10% dalam 5-15 hari dengan volume di atas VMA.
    2. Flag: konsolidasi (lower highs + higher lows) selama 5-20 hari, volume turun.
    """
    patterns = []
    if df.empty or len(df) < 35:
        return patterns

    # Hitung VMA (Volume Moving Average)
    df['vma_20'] = df['volume'].rolling(window=20).mean()

    for i in range(20, len(df) - 5):
        # Cari pole (5-15 hari ke belakang dari i)
        for pole_len in range(5, 16):
            pole_start_idx = i - pole_len
            if pole_start_idx < 0:
                continue
                
            start_candle = df.iloc[pole_start_idx]
            end_candle = df.iloc[i]
            
            pole_gain_pct = (end_candle['close'] - start_candle['close']) / start_candle['close']
            
            # 1. Pole valid? (Kenaikan >= 10%)
            if pole_gain_pct >= 0.10:
                # Cek volume pole (avg volume pole > vma)
                pole_df = df.iloc[pole_start_idx:i+1]
                avg_pole_vol = pole_df['volume'].mean()
                if avg_pole_vol > df.iloc[i]['vma_20']:
                    
                    # 2. Cari Flag (5-20 hari ke depan)
                    for flag_len in range(5, 21):
                        flag_end_idx = i + flag_len
                        if flag_end_idx >= len(df):
                            break
                            
                        # Flag dimulai HARI SETELAH pole end (i+1)
                        flag_df = df.iloc[i+1:flag_end_idx+1]
                        
                        # Cek flag: konsolidasi
                        flag_high_max = flag_df['high'].max()
                        flag_low_min = flag_df['low'].min()
                        
                        # Flag tidak boleh jatuh melebihi 50% dari pole
                        max_drop_allowed = end_candle['close'] - (end_candle['close'] - start_candle['close']) * 0.5
                        if flag_low_min < max_drop_allowed:
                            break # Invalid flag
                            
                        # Cek volume flag menurun
                        avg_flag_vol = flag_df['volume'].mean()
                        if avg_flag_vol < avg_pole_vol:
                            patterns.append({
                                'pole_start': start_candle.get('trading_date', df.index[pole_start_idx]),
                                'pole_end': end_candle.get('trading_date', df.index[i]),
                                'flag_end': df.iloc[flag_end_idx].get('trading_date', df.index[flag_end_idx]),
                                'pole_gain_pct': pole_gain_pct,
                                'flag_tightness': (flag_high_max - flag_low_min) / flag_low_min
                            })
                            break # ketemu satu flag, stop untuk pole ini

    return patterns
