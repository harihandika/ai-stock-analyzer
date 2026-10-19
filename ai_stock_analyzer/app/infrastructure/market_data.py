"""
AI Stock Analyzer - Market Data Ingestion
Menyediakan wrapper untuk library yfinance guna mengunduh data OHLCV.
"""

import asyncio
import re

# Menggunakan ThreadPoolExecutor untuk menjalankan operasi I/O-bound blocking (yfinance) secara asinkron
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import httpx
import pandas as pd
import yfinance as yf

from app.core.config import settings
from app.core.errors import AnalysisError

executor = ThreadPoolExecutor(max_workers=5)


def market_identity():
    return "EODHD" if settings.MARKET_DATA_PROVIDER == "eodhd" else "Yahoo Finance"


async def _eodhd_get(path, **params):
    if not settings.EODHD_API_KEY:
        raise AnalysisError(
            "MARKET_NOT_CONFIGURED",
            "Kunci sumber data pasar belum dikonfigurasi.",
            status=503,
            stage="syncing",
        )
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            response = await client.get(
                "https://eodhd.com/api/" + path,
                params={"api_token": settings.EODHD_API_KEY, "fmt": "json", **params},
            )
        if response.status_code == 429:
            raise AnalysisError(
                "MARKET_RATE_LIMITED", "Batas provider pasar tercapai.", status=503, stage="syncing"
            )
        if response.status_code >= 300:
            raise AnalysisError(
                "MARKET_PROVIDER_ERROR",
                "Provider pasar menolak permintaan.",
                status=503,
                stage="syncing",
            )
        return response.json()
    except (httpx.HTTPError, ValueError):
        raise AnalysisError(
            "MARKET_PROVIDER_ERROR", "Data pasar tidak dapat diambil.", status=503, stage="syncing"
        ) from None


def _eodhd_symbol(ticker):
    ticker = ticker.upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]{0,19}", ticker):
        raise AnalysisError(
            "INVALID_TICKER", "Kode saham tidak valid.", status=422, stage="syncing"
        )
    if "." in ticker and not ticker.endswith((".JK", ".US")):
        raise AnalysisError(
            "UNSUPPORTED_EXCHANGE",
            "Adapter ini mendukung ticker IDX .JK dan saham AS.",
            status=422,
            stage="syncing",
        )
    return ticker if ticker.endswith((".JK", ".US")) else ticker + ".US"


async def _fetch_eodhd_history(ticker, period):
    match = re.fullmatch(r"([1-6])y|([1-9][0-9]?)mo|([1-9][0-9]{0,3})d", period)
    if not match:
        raise ValueError("Periode histori tidak didukung")
    days = int(match[1]) * 366 if match[1] else int(match[2]) * 31 if match[2] else int(match[3])
    end = datetime.now(UTC).date() - timedelta(days=1)
    rows = await _eodhd_get(
        "eod/" + _eodhd_symbol(ticker),
        **{
            "from": str(end - timedelta(days=days)),
            "to": str(end),
            "period": "d",
            "order": "a",
        },
    )
    if not isinstance(rows, list) or not rows:
        raise AnalysisError(
            "MARKET_EMPTY", "Histori belum tersedia dari provider.", status=503, stage="syncing"
        )
    frame = pd.DataFrame(rows)
    required = {"date", "open", "high", "low", "close", "adjusted_close", "volume"}
    if not required.issubset(frame.columns):
        raise AnalysisError(
            "MARKET_INVALID_DATA", "Kolom histori provider tidak lengkap.", stage="syncing"
        )
    for key in required - {"date"}:
        frame[key] = pd.to_numeric(frame[key], errors="raise")
    factor = frame["adjusted_close"] / frame["close"]
    for key in ["open", "high", "low"]:
        frame[key] *= factor
    frame["close"] = frame["adjusted_close"]
    frame["trading_date"] = pd.to_datetime(frame["date"], errors="raise").dt.date
    frame = frame[frame["trading_date"] <= end][
        ["trading_date", "open", "high", "low", "close", "volume"]
    ]
    frame.attrs = {
        "source": "EODHD",
        "price_adjustment": "split_and_dividend_adjusted",
        "volume_adjustment": "split_adjusted",
    }
    return frame


def _fetch_history_sync(ticker: str, period: str = "1y") -> pd.DataFrame:
    """
    Fungsi sinkronus untuk mengunduh data riwayat dari yfinance.
    Dijalankan di dalam executor agar tidak mem-block event loop FastAPI.
    """
    stock = yf.Ticker(ticker)

    # Ambil riwayat harga berdasarkan 'period' (misal: '1y', '6mo', '100d')
    # auto_adjust=True memastikan harga disesuaikan dengan split & dividend
    df = stock.history(period=period, auto_adjust=True, timeout=20)

    if df.empty:
        return df

    # A daily bar from today's session can still be partial. Publish completed days only.
    session_today = datetime.now(df.index.tz or UTC).date()
    df = df[df.index.date < session_today]
    if df.empty:
        return df

    # Reset index agar 'Date' menjadi kolom biasa
    df = df.reset_index()

    # Pastikan tipe kolom 'Date' adalah datetime, dan hilangkan timezone (naïve) jika ada
    if isinstance(df["Date"].dtype, pd.DatetimeTZDtype):
        df["Date"] = df["Date"].dt.tz_localize(None)

    # Hanya ambil kolom yang dibutuhkan
    columns_to_keep = ["Date", "Open", "High", "Low", "Close", "Volume"]
    # yfinance terkadang mengembalikan dataset tanpa beberapa kolom, kita cek dulu
    existing_columns = [col for col in columns_to_keep if col in df.columns]
    df = df[existing_columns]

    # Ganti nama kolom ke format lowercase standar DB kita
    df = df.rename(
        columns={
            "Date": "trading_date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )

    # Konversi trading_date ke object date python murni
    df["trading_date"] = df["trading_date"].dt.date

    # Cast tipe numerik
    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = df[col].astype(float)
    if "volume" in df.columns:
        df["volume"] = df["volume"].astype(int)

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
    if settings.MARKET_DATA_PROVIDER == "eodhd":
        return await _fetch_eodhd_history(ticker, period)
    # Jalankan _fetch_history_sync di thread terpisah (karena yfinance menggunakan requests sinkron)
    loop = asyncio.get_running_loop()
    df = await loop.run_in_executor(executor, _fetch_history_sync, ticker, period)
    df.attrs = {
        "source": "Yahoo Finance",
        "price_adjustment": "split_and_dividend_adjusted",
        "volume_adjustment": "provider_reported",
    }
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
    if settings.MARKET_DATA_PROVIDER == "eodhd":
        symbol = _eodhd_symbol(ticker)
        exchange = "JK" if symbol.endswith(".JK") else "US"
        # The exchange listing is included in the EOD plan, unlike fundamentals.
        rows = await _eodhd_get("exchange-symbol-list/" + exchange)
        if not isinstance(rows, list):
            return {}
        code = symbol.rsplit(".", 1)[0]
        item = next((r for r in rows if r.get("Code") == code), {})
        return {
            "longName": item.get("Name"),
            "currency": item.get("Currency"),
            "exchange": "IDX" if exchange == "JK" else item.get("Exchange", "US"),
        }
    loop = asyncio.get_running_loop()
    info = await loop.run_in_executor(executor, _fetch_info_sync, ticker)
    return info
