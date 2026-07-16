# Backtesting Engine

Sistem rekomendasi investasi tidak lengkap tanpa fitur backtesting untuk memvalidasi *win-rate* dan parameter algoritma (VPA/SMC/Wyckoff).

## 1. Arsitektur Backtesting
Backtesting Engine bukan bagian dari API yang diakses user secara live, melainkan modul internal (biasanya dijalankan sebagai CLI script di `app/worker/backtester.py`) yang berguna untuk mengaudit akurasi logika Python dan AI Prompt.

- **Data Source**: Menggunakan data historis 5-10 tahun ke belakang.
- **Simulasi Waktu (*Time-Stepping*)**: Script memotong DataFrame harga (OHLCV) saham *seolah-olah* hari ini adalah tanggal X di masa lalu.
- **Kondisi Pengujian**: Hanya menggunakan algoritma deterministik (Pandas VPA & Wyckoff) untuk menghemat biaya (jangan menembak AI API untuk proses backtesting ribuan baris, sangat mahal). AI (Claude) hanya dipercaya jika *rule-based* Python kita akurat.

## 2. Metrik Keberhasilan (KPI)
Script akan mengukur:
1. **Win Rate**: Persentase *Buy Signal* (Fase C/D Spring + Stopping Volume) yang menghasilkan profit > 5% dalam waktu maksimal 30 hari.
2. **Maximum Drawdown (MDD)**: Penurunan maksimal portofolio dari sinyal rekomendasi.
3. **Risk/Reward Ratio (RR)**.

## 3. Snippet Kode Backtesting Sederhana

```python
import pandas as pd
from app.services.wyckoff_engine import detect_wyckoff_accumulation
from app.services.indicator_engine import detect_vpa_signals

def run_backtest(df_history: pd.DataFrame):
    # 1. Jalankan deteksi indikator pada seluruh dataset
    df = detect_vpa_signals(df_history)
    df = detect_wyckoff_accumulation(df)
    
    trades = []
    
    # 2. Iterasi hari demi hari untuk simulasi eksekusi
    for i in range(50, len(df)):
        current_day = df.iloc[i]
        
        # Kondisi Buy: Ada Spring & Stopping Volume
        if current_day['Is_Spring'] and current_day['Stopping_Volume']:
            buy_price = current_day['Close']
            buy_date = current_day.name
            
            # 3. Cek hasil 30 hari ke depan
            future_df = df.iloc[i+1 : i+31]
            if future_df.empty:
                continue
                
            max_future_price = future_df['High'].max()
            profit_pct = (max_future_price - buy_price) / buy_price
            
            # Jika profit lebih dari 5%, dianggap win
            is_win = profit_pct >= 0.05
            
            trades.append({
                "buy_date": buy_date,
                "buy_price": buy_price,
                "profit_pct": profit_pct,
                "is_win": is_win
            })
            
    # Hitung Statistik
    total_trades = len(trades)
    wins = len([t for t in trades if t['is_win']])
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
    
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}%")
```

Setelah script di atas memberikan win-rate di atas 60-70%, kita tahu bahwa data ringkasan (*flags*) yang dikirim ke **Claude Sonnet** valid dan berkualitas tinggi.
