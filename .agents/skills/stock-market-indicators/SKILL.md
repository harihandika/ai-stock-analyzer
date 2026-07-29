---
name: stock-market-indicators
description: Panduan algoritma dan perhitungan indikator teknikal serta analisis saham (RSI, MACD, Moving Averages, Bollinger Bands). Gunakan skill ini saat membuat service analisis teknikal atau algoritma komputasi data saham.
---

# Indikator Analisis Saham (Technical Analysis Standards)

## 1. Moving Averages (MA)
- **SMA (Simple Moving Average)**: Rata-rata aritmatika harga penutupan selama periode $N$ hari.
- **EMA (Exponential Moving Average)**: Bobot lebih tinggi pada data harga terbaru. Formula: $EMA_{today} = (Price_{today} \times k) + (EMA_{yesterday} \times (1 - k))$ di mana $k = 2 / (N + 1)$.

## 2. RSI (Relative Strength Index)
- Periode standar: 14 hari.
- Formula RS: $RS = \text{Average Gain} / \text{Average Loss}$.
- Formula RSI: $RSI = 100 - (100 / (1 + RS))$.
- Signal: $RSI > 70$ (Overbought), $RSI < 30$ (Oversold).

## 3. MACD (Moving Average Convergence Divergence)
- **MACD Line**: $EMA(12) - EMA(26)$.
- **Signal Line**: $EMA(9)$ dari MACD Line.
- **Histogram**: $MACD Line - Signal Line$.

## 4. Bollinger Bands
- **Middle Band**: $SMA(20)$.
- **Upper Band**: $SMA(20) + (2 \times \text{StdDev}(20))$.
- **Lower Band**: $SMA(20) - (2 \times \text{StdDev}(20))$.
