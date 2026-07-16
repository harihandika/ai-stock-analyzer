"""
AI Stock Analyzer - Market Data Ingestion
Menyediakan wrapper untuk library yfinance guna mengunduh data OHLCV.
"""

import asyncio
from datetime import datetime, date, timedelta
import pandas as pd
import yfinance as yf

# Menggunakan ThreadPoolExecutor untuk menjalankan operasi I/O-bound blocking (yfinance) secara asinkron
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=5)


def _fetch_history_sync(ticker: str, period: str = "1y") -> pd.DataFrame:
    """
    Fungsi sinkronus untuk mengunduh data riwayat dari yfinance.
    Dijalankan di dalam executor agar tidak mem-block event loop FastAPI.
    """
    stock = yf.Ticker(ticker)
    
    # Ambil riwayat harga berdasarkan 'period' (misal: '1y', '6mo', '100d')
    # auto_adjust=True memastikan harga disesuaikan dengan split & dividend
    df = stock.history(period=period, auto_adjust=True)
    
    if df.empty:
        return df

    # Reset index agar 'Date' menjadi kolom biasa
    df = df.reset_index()

    # Pastikan tipe kolom 'Date' adalah datetime, dan hilangkan timezone (naïve) jika ada
    if pd.api.types.is_datetime64tz_dtype(df['Date']):
        df['Date'] = df['Date'].dt.tz_localize(None)

    # Hanya ambil kolom yang dibutuhkan
    columns_to_keep = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    # yfinance terkadang mengembalikan dataset tanpa beberapa kolom, kita cek dulu
    existing_columns = [col for col in columns_to_keep if col in df.columns]
    df = df[existing_columns]

    # Ganti nama kolom ke format lowercase standar DB kita
    df = df.rename(columns={
        'Date': 'trading_date',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    })

    # Konversi trading_date ke object date python murni
    df['trading_date'] = df['trading_date'].dt.date
    
    # Cast tipe numerik
    for col in ['open', 'high', 'low', 'close']:
        if col in df.columns:
            df[col] = df[col].astype(float)
    if 'volume' in df.columns:
        df['volume'] = df['volume'].astype(int)

    return df


async def fetch_stock_history_async(ticker: str, period: str = "1y") -> pd.DataFrame:
    """
    Mengambil data riwayat saham (OHLCV) secara asinkronus menggunakan yfinance.
    
    Args:
        ticker: Simbol saham (contoh: "BBCA.JK", "AAPL")
        period: Periode riwayat (contoh: "1y", "6mo", "100d")
        
    Returns:
        DataFrame Pandas berisi data harga. Kolom: trading_date, open, high, low, close, volume.
    """
    # Jalankan _fetch_history_sync di thread terpisah (karena yfinance menggunakan requests sinkron)
    loop = asyncio.get_running_loop()
    df = await loop.run_in_executor(executor, _fetch_history_sync, ticker, period)
    return df


def _fetch_info_sync(ticker: str) -> dict:
    """Fungsi sinkronus mengambil informasi profil saham (nama perusahaan, dll)."""
    try:
        stock = yf.Ticker(ticker)
        return stock.info
    except Exception:
        return {}


async def fetch_stock_info_async(ticker: str) -> dict:
    """Mengambil metadata informasi perusahaan secara asinkronus."""
    loop = asyncio.get_running_loop()
    info = await loop.run_in_executor(executor, _fetch_info_sync, ticker)
    return info
