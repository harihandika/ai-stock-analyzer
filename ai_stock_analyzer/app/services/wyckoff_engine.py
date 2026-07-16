"""
AI Stock Analyzer - Wyckoff Phase Engine (Sprint 3)
Modul untuk mendeteksi Fase Akumulasi Wyckoff (Phase C: Spring & Phase D: Sign of Strength).
"""

import pandas as pd
import numpy as np


def detect_wyckoff_accumulation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mendeteksi Fase Akumulasi Wyckoff, berfokus pada Phase C (Spring) 
    dan Phase D (Sign of Strength / SOS).
    
    Args:
        df: DataFrame OHLCV yang sudah memiliki VMA_20.
    """
    if df.empty or len(df) < 50:
        df['is_spring'] = False
        df['wyckoff_phase'] = None
        return df

    # Pastikan VMA_20 tersedia (dari indicator_engine)
    if 'vma_20' not in df.columns:
        # Fallback hitung sederhana jika belum ada
        df['vma_20'] = df['volume'].rolling(20).mean()

    # 1. Hitung titik terendah dalam 50 hari terakhir
    df['lowest_50'] = df['low'].rolling(50, min_periods=20).min()
    df['is_new_low'] = df['low'] <= df['lowest_50']

    # 2. Hitung Close Position (0 = bottom, 1 = top)
    df['spread'] = df['high'] - df['low']
    df['close_pos'] = np.where(df['spread'] > 0, (df['close'] - df['low']) / df['spread'], 0.5)

    # ==========================================
    # PHASE C: THE SPRING (Shakeout)
    # ==========================================
    # Syarat Phase C (Spring):
    # - Harga membuat rekor terendah baru (atau setara terendah).
    # - Terjadi rejection kuat: harga ditarik naik menjauhi 'low' (close_pos > 0.5).
    # - Volume di atas rata-rata (menandakan Smart Money menyerap kepanikan).
    df['is_spring'] = (
        df['is_new_low'] & 
        (df['close_pos'] > 0.5) & 
        (df['volume'] > df['vma_20'] * 1.2)
    )

    # ==========================================
    # PHASE D: SIGN OF STRENGTH (SOS)
    # ==========================================
    # Syarat Sign of Strength:
    # - Candle bullish (close hari ini > close kemarin).
    # - Volume melonjak tajam (Demand > Supply).
    df['is_sos'] = (
        (df['close'] > df['close'].shift(1)) & 
        (df['volume'] > df['vma_20'] * 1.5) &
        (df['close_pos'] > 0.6)  # Ditutup mendekati high
    )

    # Inisialisasi kolom label fase
    df['wyckoff_phase'] = None

    # Logika pelabelan State Machine sederhana untuk Accumulation
    # Jika terdeteksi Spring -> Phase C
    # Jika terdeteksi SOS dalam 10 hari setelah Spring -> Phase D
    
    # Track indeks Spring terakhir
    last_spring_idx = -100 # Inisialisasi jauh di masa lalu
    
    for i in range(len(df)):
        if df.loc[df.index[i], 'is_spring']:
            df.loc[df.index[i], 'wyckoff_phase'] = "Phase C (Spring)"
            last_spring_idx = i
        elif df.loc[df.index[i], 'is_sos']:
            # Cek apakah SOS ini terjadi setelah Phase C (maksimal 15 hari setelahnya)
            if (i - last_spring_idx) <= 15 and last_spring_idx >= 0:
                df.loc[df.index[i], 'wyckoff_phase'] = "Phase D (SOS)"

    # Membersihkan kolom bantuan
    df = df.drop(columns=['lowest_50', 'is_new_low', 'is_sos'], errors='ignore')

    return df
