"""
AI Stock Analyzer - Stock & Analysis Pydantic Schemas
Mendefinisikan skema validasi input/output untuk data saham dan analisis.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field

T = TypeVar("T")

class PaginationMeta(BaseModel):
    """Metadata untuk pagination."""
    page: int
    per_page: int
    total: int
    total_pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    """Response generik untuk data berhalaman."""
    data: List[T]
    pagination: PaginationMeta


# ---- Stock Schemas ----

class StockBase(BaseModel):
    """Schema dasar untuk data emiten saham."""
    ticker: str = Field(..., max_length=20, description="Kode saham, e.g., BBCA, TLKM")
    company_name: str = Field(..., max_length=255, description="Nama perusahaan")
    sector: str | None = Field(default=None, description="Sektor industri")
    exchange: str | None = Field(default=None, description="Bursa efek, e.g., IDX, NYSE")


class StockResponse(StockBase):
    """Response data emiten saham."""
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- Daily Price Schemas ----

class DailyPriceResponse(BaseModel):
    """Response data harga OHLCV harian."""
    trading_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    model_config = {"from_attributes": True}


# ---- Technical Indicator Schemas ----

class SMCPatterns(BaseModel):
    """Pola Smart Money Concept yang terdeteksi."""
    bullish_fvg: bool = False
    bearish_fvg: bool = False
    fvg_level: Decimal | None = None
    bos_detected: bool = False
    choch_detected: bool = False
    order_block_level: Decimal | None = None


class TechnicalIndicatorResponse(BaseModel):
    """Response data indikator teknikal harian."""
    trading_date: date
    rsi_14: Decimal | None = None
    ema_20: Decimal | None = None
    ema_50: Decimal | None = None
    ema_200: Decimal | None = None
    macd: Decimal | None = None
    macd_signal: Decimal | None = None
    vwap: Decimal | None = None
    atr_14: Decimal | None = None

    # VPA Signals
    stopping_volume: bool = False
    no_demand: bool = False
    is_spring: bool = False
    climactic_volume: bool = False

    # Wyckoff
    wyckoff_phase: str | None = None

    # SMC
    smc_patterns: dict | None = None

    model_config = {"from_attributes": True}


# ---- AI Analysis Schemas ----

class AIAnalysisResponse(BaseModel):
    """Response hasil analisis AI untuk sebuah saham."""
    id: uuid.UUID
    ticker: str
    analysis_date: date
    wyckoff_phase_ai: str | None = None
    vpa_insight: str | None = None
    recommendation: str | None = None  # BUY | HOLD | WAIT
    confidence_score: int | None = None  # 1-100
    ai_summary: str | None = None
    generated_at: datetime

    model_config = {"from_attributes": True}


# ---- Combined Analysis Response ----

class StockAnalysisLatestResponse(BaseModel):
    """
    Response gabungan untuk endpoint /stocks/{ticker}/analysis/latest.
    Menggabungkan harga terkini, indikator teknikal, dan analisis AI.
    """
    ticker: str
    company_name: str
    current_price: Decimal | None = None
    analysis_date: date | None = None
    wyckoff_phase: str | None = None
    ai_recommendation: str | None = None
    confidence_score: int | None = None
    ai_summary: str | None = None
    vpa_insight: str | None = None
    technical_indicators: TechnicalIndicatorResponse | None = None


# ---- Watchlist Schemas ----

class WatchlistAddRequest(BaseModel):
    """Request untuk menambahkan saham ke watchlist."""
    ticker: str = Field(..., max_length=20, description="Kode saham yang ingin dipantau")
    notes: str | None = Field(default=None, max_length=500, description="Catatan personal")


class WatchlistResponse(BaseModel):
    """Response data watchlist pengguna."""
    id: uuid.UUID
    stock_ticker: str
    company_name: str
    notes: str | None = None
    added_at: datetime

    model_config = {"from_attributes": True}
