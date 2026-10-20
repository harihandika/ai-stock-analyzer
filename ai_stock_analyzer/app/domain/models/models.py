"""
AI Stock Analyzer - SQLAlchemy ORM Models
Mendefinisikan semua entitas database sesuai dengan ERD di database_design.md
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.infrastructure.database import Base


class User(Base):
    """
    Entitas pengguna aplikasi.
    Menyimpan informasi akun dan tier langganan.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subscription_tier: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="free",  # free | premium
    )
    analysis_quota_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_quota_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_quota_reset: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    watchlists: Mapped[list["Watchlist"]] = relationship("Watchlist", back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

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
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    price_adjustment: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    volume_adjustment: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    publication_delay_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    data_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

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
    __table_args__ = (Index("ix_daily_prices_stock_date", "stock_ticker", "trading_date"),)

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
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
    __table_args__ = (Index("ix_technical_indicators_stock_date", "stock_ticker", "trading_date"),)

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
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
        String(20),
        nullable=True,  # Phase_A, Phase_B, Phase_C, Phase_D, Phase_E, Distribution
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stock_ticker: Mapped[str] = mapped_column(
        String(20), ForeignKey("stocks.ticker", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,  # BUY | HOLD | WAIT
    )
    vpa_insight: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-100
    wyckoff_phase_ai: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Track token cost
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    analyzed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    provenance: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, default="anthropic")
    actual_model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stock_ticker: Mapped[str] = mapped_column(
        String(20), ForeignKey("stocks.ticker", ondelete="CASCADE"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="watchlists")
    stock: Mapped["Stock"] = relationship("Stock", back_populates="watchlists")

    def __repr__(self) -> str:
        return f"<Watchlist(user_id={self.user_id}, ticker='{self.stock_ticker}')>"


class RefreshToken(Base):
    """
    Menyimpan hash dari refresh token untuk mendukung revokasi (logout)
    dan mencegah token reuse.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return f"<RefreshToken(user_id={self.user_id}, is_revoked={self.is_revoked})>"


class AnalysisRequest(Base):
    """Durable idempotency and quota reservation; not a background-job queue."""

    __tablename__ = "analysis_requests"
    __table_args__ = (UniqueConstraint("user_id", "request_key", name="uq_analysis_request_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    request_key: Mapped[str] = mapped_column(String(64), nullable=False)
    input_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    quota_day: Mapped[date] = mapped_column(Date, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_analyses.id"), nullable=True
    )


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (UniqueConstraint("user_id", "request_key", name="uq_job_request"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    request_key: Mapped[str] = mapped_column(String(64), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[str | None] = mapped_column(String(36))
    result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_analyses.id")
    )
    error: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AlertRule(Base):
    __tablename__ = "alert_rules"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    ticker: Mapped[str] = mapped_column(String(20), ForeignKey("stocks.ticker"), index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), default="above")
    threshold: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    signal: Mapped[str | None] = mapped_column(String(10))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    previous_met: Mapped[bool | None] = mapped_column(Boolean)
    last_market_date: Mapped[date | None] = mapped_column(Date)
    last_analysis_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlertEvent(Base):
    __tablename__ = "alert_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_key: Mapped[str] = mapped_column(String(160), unique=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SavedFilter(Base):
    __tablename__ = "saved_filters"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    criteria: Mapped[dict] = mapped_column(JSON, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)


class TradePlan(Base):
    __tablename__ = "trade_plans"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    ticker: Mapped[str] = mapped_column(String(20), ForeignKey("stocks.ticker"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    versions: Mapped[list] = mapped_column(JSON, default=list)
    data_revision: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    data_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordReset(Base):
    __tablename__ = "password_resets"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    progress_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(40))


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    tickers: Mapped[list] = mapped_column(JSON, nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON)
