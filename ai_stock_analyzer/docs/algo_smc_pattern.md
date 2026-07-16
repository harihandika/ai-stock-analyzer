# SMC & Pattern Recognition Engine

Sama halnya dengan VPA, Smart Money Concepts (SMC) sangat mengandalkan struktur harga (*Price Action*). Deteksi pola ini secara sistematis sangat menghemat beban AI (Claude).

## 1. Smart Money Concepts (SMC)
Fokus kita adalah mendeteksi *Break of Structure* (BOS), *Change of Character* (CHoCH), dan *Fair Value Gap* (FVG).

### Fair Value Gap (FVG)
FVG terjadi saat ada pergerakan harga tajam dalam 3 candle, sehingga terdapat "celah" antara candle 1 dan candle 3 yang belum terisi. *Smart Money* biasanya akan kembali ke celah ini (sebagai magnet harga).

**Snippet Kode Python (Pandas)**:
```python
import pandas as pd

def detect_fvg(df: pd.DataFrame):
    # Bullish FVG: Low candle ke-3 lebih tinggi dari High candle ke-1
    df['Bullish_FVG'] = df['Low'] > df['High'].shift(2)
    
    # Bearish FVG: High candle ke-3 lebih rendah dari Low candle ke-1
    df['Bearish_FVG'] = df['High'] < df['Low'].shift(2)
    
    # Gap size
    df['FVG_Size'] = 0.0
    df.loc[df['Bullish_FVG'], 'FVG_Size'] = df['Low'] - df['High'].shift(2)
    df.loc[df['Bearish_FVG'], 'FVG_Size'] = df['Low'].shift(2) - df['High']
    
    return df
```

### BOS & CHoCH (Structure)
- **BOS (Break of Structure)**: Melanjutkan tren. Jika uptrend menembus puncak (*High*) sebelumnya.
- **CHoCH (Change of Character)**: Berbalik tren. Jika downtrend menembus puncak terakhir, mengindikasikan pembalikan arah menjadi uptrend (awal akumulasi).

Deteksi ini memerlukan deteksi *Swing High* dan *Swing Low*.
```python
def detect_swing_points(df: pd.DataFrame, window=5):
    # Swing High: Titik tertinggi dalam 'window' hari ke kiri dan ke kanan
    df['Swing_High'] = df['High'] == df['High'].rolling(window=window*2+1, center=True).max()
    df['Swing_Low'] = df['Low'] == df['Low'].rolling(window=window*2+1, center=True).min()
    return df
```

## 2. Pattern Recognition (Pola Klasik)
Pola klasik (seperti *Double Bottom* atau *Cup and Handle*) dicari dari titik-titik Swing yang sudah didapatkan dari algoritma SMC di atas.

**Double Bottom Detection**:
1. Cari 2 *Swing Low* yang terjadi berdekatan (misal dalam jarak 10-30 hari).
2. Perbedaan harga antara kedua *Swing Low* sangat kecil (toleransi 2-3%).
3. Volume pada *Swing Low* kedua harus lebih rendah dari *Swing Low* pertama (menandakan *Selling Pressure* mengering).

**Snippet Pseudocode Python**:
```python
def detect_double_bottom(df: pd.DataFrame):
    swing_lows = df[df['Swing_Low'] == True]
    
    # Iterasi mencari pasangan Swing Low berdekatan
    for i in range(1, len(swing_lows)):
        low1 = swing_lows.iloc[i-1]
        low2 = swing_lows.iloc[i]
        
        time_diff = (low2.name - low1.name).days # Assuming datetime index
        price_diff = abs(low2['Low'] - low1['Low']) / low1['Low']
        
        if 10 <= time_diff <= 40 and price_diff <= 0.03:
            if low2['Volume'] < low1['Volume']:
                # Valid Double Bottom potential
                pass
```
Catatan: Semua deteksi pola ini menghasilkan *flag* (boolean/enum) di baris tabel, yang nantinya akan dibaca oleh Claude AI untuk dirangkai menjadi sebuah cerita analisis.
