# VPA & Wyckoff Algorithm Engine

Dalam *Clean Architecture*, engine ini berada di layer *Application Services*. Karena model AI cukup mahal untuk menganalisis data riwayat harga dari 0, kita menggunakan *rule-based engine* di Python untuk mendeteksi anomali (VPA) dan Fase Wyckoff. Hasil ini baru dikirim ke AI.

## 1. Volume Price Analysis (VPA)
VPA mencari anomali hubungan antara pergerakan harga (*Spread* candle) dan jumlah Volume.

**Logika Dasar**:
1. Hitung *Volume Moving Average* (VMA) 20 hari.
2. Volume disebut **High/Climactic** jika > 200% dari VMA.
3. *Spread* (Tinggi - Rendah) disebut **Wide** jika lebih besar dari *Average True Range* (ATR).
4. Sinyal VPA:
   - *Stopping Volume*: Down-trend, Wide Spread, Close di tengah/atas, Volume Ultra High (Sinyal Smart Money membeli).
   - *No Demand*: Up-trend, Narrow Spread, Volume sangat rendah (Sinyal uptrend kehabisan tenaga).

**Snippet Kode Python (Pandas)**:
```python
import pandas as pd
import pandas_ta as ta

def detect_vpa_signals(df: pd.DataFrame):
    # Hitung VMA dan ATR
    df['VMA_20'] = ta.sma(df['Volume'], length=20)
    df['ATR_14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    # Hitung Spread dan Posisi Close
    df['Spread'] = df['High'] - df['Low']
    df['Close_Pos'] = (df['Close'] - df['Low']) / df['Spread'] # 0 = bottom, 1 = top
    
    # Deteksi Stopping Volume (Smart Money Buying)
    df['Stopping_Volume'] = (
        (df['Close'] < df['Close'].shift(1)) &     # Downward trend
        (df['Volume'] > df['VMA_20'] * 2) &        # Ultra high volume
        (df['Spread'] > df['ATR_14']) &            # Wide spread
        (df['Close_Pos'] > 0.5)                    # Rejection at bottom (pin bar)
    )
    return df
```

## 2. Wyckoff Phase Engine
Wyckoff membagi pasar menjadi: Accumulation, Markup, Distribution, Markdown.

**Logika Dasar Accumulation (A - E)**:
1. **Phase A (Stop of downtrend)**: Didahului downtrend, ditandai dengan munculnya *Selling Climax* (SC) -> mirip *Stopping Volume* di atas.
2. **Phase B (Building a cause)**: Harga bergerak *sideways* (Ranging). Volume menurun drastis.
3. **Phase C (Test/Spring)**: Harga menembus *Support* (membentuk *Lower Low*) tapi segera ditarik naik dengan volume tinggi (*Shakeout/Spring*).
4. **Phase D (Sign of Strength - SOS)**: Harga memantul dari support dengan volume naik tajam dan menembus resistance.
5. **Phase E (Markup)**: Tren naik terkonfirmasi, moving average berbalik naik.

**Snippet Kode Python (Pandas)**:
```python
def detect_wyckoff_accumulation(df: pd.DataFrame):
    # Syarat Phase C (Spring):
    # 1. Harga membuat harga terendah baru dalam 50 hari terakhir
    df['Lowest_50'] = df['Low'].rolling(50).min()
    df['Is_New_Low'] = df['Low'] == df['Lowest_50']
    
    # 2. Rejection tajam ke atas (Close jauh dari Low) dengan Volume naik
    df['Is_Spring'] = (
        df['Is_New_Low'] & 
        (df['Close_Pos'] > 0.6) & 
        (df['Volume'] > df['VMA_20'] * 1.5)
    )
    
    # 3. Sign of Strength (SOS) menyusul Spring
    df['SOS'] = (df['Close'] > df['Close'].shift(1)) & (df['Volume'] > df['VMA_20'] * 1.2)
    
    # Simpel pelabelan: Jika ada Spring, saham masuk Phase C. Jika setelah Spring ada SOS beruntun, masuk Phase D.
    return df
```
Catatan: Algoritma penuh akan menggunakan array *peak/trough* detection (seperti `scipy.signal.find_peaks`) untuk mendeteksi *Support* dan *Resistance* secara dinamis.
