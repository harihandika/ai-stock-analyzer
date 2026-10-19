"""
AI Stock Analyzer - Stock & Analysis Pydantic Schemas
Mendefinisikan skema validasi input/output untuk data saham dan analisis.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class MarketDataMetadata(BaseModel):
    source: str | None
    currency: str | None
    exchange: str | None
    market_as_of: date | None
    fetched_at: datetime | None
    interval: Literal["1d"]
    data_revision: str | None
    data_state: Literal["fresh", "stale", "unavailable", "demo", "unknown"]
    price_adjustment: str


class StockQuoteResponse(BaseModel):
    ticker: str
    company_name: str
    current_price: float | None
    previous_close: float | None
    change: float | None
    change_percent: float | None
    metadata: MarketDataMetadata


class PaginationMeta(BaseModel):
    """Metadata untuk pagination."""

    page: int
    per_page: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Response generik untuk data berhalaman."""

    data: list[T]
    pagination: PaginationMeta
    metadata: MarketDataMetadata | None = None


# ---- Stock Schemas ----


class StockBase(BaseModel):
    """Schema dasar untuk data emiten saham."""

    ticker: str = Field(..., max_length=20, description="Kode saham, e.g., BBCA, TLKM")
    company_name: str = Field(..., max_length=255, description="Nama perusahaan")
    sector: str | None = Field(default=None, description="Sektor industri")
    exchange: str | None = Field(default=None, description="Bursa efek, e.g., IDX, NYSE")


class StockResponse(StockBase):
    """Response data emiten saham."""

    currency: str | None = None
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
    ema_20: Decimal | None = None
    ema_50: Decimal | None = None
    ema_200: Decimal | None = None
    rsi_14: Decimal | None = None
    macd: Decimal | None = None
    macd_signal: Decimal | None = None

    stopping_volume: bool | None = False
    no_demand: bool | None = False
    is_spring: bool | None = False
    climactic_volume: bool | None = False

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
    model_config = {"protected_namespaces": ()}
    """
    Response gabungan untuk endpoint /stocks/{ticker}/analysis/latest.
    Menggabungkan harga terkini, indikator teknikal, dan analisis AI.
    """
    ticker: str
    company_name: str
    analysis_id: uuid.UUID | None = None
    current_price: Decimal | None = None
    metadata: MarketDataMetadata | None = None
    generated_at: datetime | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    provenance: str | None = None
    analysis_matches_data: bool = False
    supporting_factors: list[str] = []
    opposing_factors: list[str] = []
    limitations: str | None = None
    horizon: str | None = None
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


class WatchlistUpdateRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=500)
    model_config = {"extra": "forbid"}
