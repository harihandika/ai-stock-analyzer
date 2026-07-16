"""
AI Stock Analyzer - SQLAlchemy ORM Models
Mendefinisikan semua entitas database sesuai dengan ERD di database_design.md
"""

import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class User(Base):
    """
    Entitas pengguna aplikasi.
    Menyimpan informasi akun dan tier langganan.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subscription_tier: Mapped[str] = mapped_column(
        String(50), nullable=False, default="free"  # free | premium
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    watchlists: Mapped[list["Watchlist"]] = relationship("Watchlist", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"


class Stock(Base):
    """
    Entitas emiten saham yang didukung oleh aplikasi.
    """
    __tablename__ = "stocks"

    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(50), nullable=True)  # IDX, NYSE, NASDAQ
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    daily_prices: Mapped[list["DailyPrice"]] = relationship("DailyPrice", back_populates="stock")
    technical_indicators: Mapped[list["TechnicalIndicator"]] = relationship(
        "TechnicalIndicator", back_populates="stock"
    )
    ai_analyses: Mapped[list["AIAnalysis"]] = relationship("AIAnalysis", back_populates="stock")
    watchlists: Mapped[list["Watchlist"]] = relationship("Watchlist", back_populates="stock")

    def __repr__(self) -> str:
        return f"<Stock(ticker='{self.ticker}', company='{self.company_name}')>"


class DailyPrice(Base):
    """
    Data harga OHLCV (Open, High, Low, Close, Volume) harian per saham.
    Tabel ini direncanakan untuk dipartisi secara bulanan/tahunan di production
    menggunakan PostgreSQL Table Partitioning.
    """
    __tablename__ = "daily_prices"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    stock_ticker: Mapped[str] = mapped_column(
        String(20), ForeignKey("stocks.ticker", ondelete="CASCADE"), nullable=False, index=True
    )
    trading_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Relationships
    stock: Mapped["Stock"] = relationship("Stock", back_populates="daily_prices")

    def __repr__(self) -> str:
        return f"<DailyPrice(ticker='{self.stock_ticker}', date='{self.trading_date}', close={self.close})>"


class TechnicalIndicator(Base):
    """
    Hasil kalkulasi indikator teknikal untuk setiap saham per hari.
    Data ini diisi oleh background worker setelah data harga harian tersedia.
    Kolom smc_patterns menggunakan JSONB untuk fleksibilitas menyimpan berbagai pola SMC.
    """
    __tablename__ = "technical_indicators"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    stock_ticker: Mapped[str] = mapped_column(
        String(20), ForeignKey("stocks.ticker", ondelete="CASCADE"), nullable=False, index=True
    )
    trading_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Indikator Dasar
    rsi_14: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    ema_20: Mapped[Decimal | None] = mapped_column(Numeric(15, 4), nullable=True)
    ema_50: Mapped[Decimal | None] = mapped_column(Numeric(15, 4), nullable=True)
    ema_200: Mapped[Decimal | None] = mapped_column(Numeric(15, 4), nullable=True)
    macd: Mapped[Decimal | None] = mapped_column(Numeric(15, 6), nullable=True)
    macd_signal: Mapped[Decimal | None] = mapped_column(Numeric(15, 6), nullable=True)
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(15, 4), nullable=True)
    atr_14: Mapped[Decimal | None] = mapped_column(Numeric(15, 4), nullable=True)
    obv: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # VPA Signals
    stopping_volume: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    no_demand: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_spring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    climactic_volume: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Wyckoff Phase Detection
    wyckoff_phase: Mapped[str | None] = mapped_column(
        String(20), nullable=True  # Phase_A, Phase_B, Phase_C, Phase_D, Phase_E, Distribution
    )

    # SMC Patterns (JSON) - FVG, BOS, CHoCH, Order Block
    smc_patterns: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    stock: Mapped["Stock"] = relationship("Stock", back_populates="technical_indicators")

    def __repr__(self) -> str:
        return f"<TechnicalIndicator(ticker='{self.stock_ticker}', date='{self.trading_date}', wyckoff='{self.wyckoff_phase}')>"


class AIAnalysis(Base):
    """
    Hasil analisis yang dihasilkan oleh AI (Claude Sonnet).
    Diisi oleh background worker harian setelah kalkulasi indikator selesai.
    Data ini bersifat statis/immutable setelah di-generate.
    """
    __tablename__ = "ai_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    stock_ticker: Mapped[str] = mapped_column(
        String(20), ForeignKey("stocks.ticker", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(
        String(10), nullable=True  # BUY | HOLD | WAIT
    )
    vpa_insight: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-100
    wyckoff_phase_ai: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Track token cost
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    stock: Mapped["Stock"] = relationship("Stock", back_populates="ai_analyses")

    def __repr__(self) -> str:
        return f"<AIAnalysis(ticker='{self.stock_ticker}', date='{self.analysis_date}', rec='{self.recommendation}')>"


class Watchlist(Base):
    """
    Daftar saham pantau milik pengguna.
    Pengguna bisa mendapatkan notifikasi jika ada anomali volume pada saham di watchlist-nya.
    """
    __tablename__ = "watchlists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    stock_ticker: Mapped[str] = mapped_column(
        String(20), ForeignKey("stocks.ticker", ondelete="CASCADE"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="watchlists")
    stock: Mapped["Stock"] = relationship("Stock", back_populates="watchlists")

    def __repr__(self) -> str:
        return f"<Watchlist(user_id={self.user_id}, ticker='{self.stock_ticker}')>"
