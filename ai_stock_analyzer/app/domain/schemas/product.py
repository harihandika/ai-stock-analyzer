"""Explicit public contracts for persistent research and monitoring workflows."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.schemas.stocks import MarketDataMetadata


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JobCreate(StrictInput):
    ticker: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9.\-]{0,19}$")
    idempotency_key: str = Field(min_length=8, max_length=100)


class AlertCreate(StrictInput):
    ticker: str = Field(min_length=1, max_length=20)
    kind: Literal["price", "change_pct", "signal"]
    direction: Literal["above", "below"] = "above"
    threshold: float | None = Field(default=None, allow_inf_nan=False)
    signal: Literal["BUY", "HOLD", "WAIT"] | None = None

    @model_validator(mode="after")
    def coherent(self):
        if self.kind == "signal":
            if self.signal is None or self.threshold is not None:
                raise ValueError("Alert sinyal memerlukan sinyal dan tidak memakai ambang harga.")
        elif (
            self.threshold is None
            or self.signal is not None
            or (self.kind == "price" and self.threshold <= 0)
        ):
            raise ValueError("Ambang harga/persen tidak valid.")
        return self


class AlertToggle(StrictInput):
    enabled: bool


class ScreenCriteria(StrictInput):
    exchange: str | None = Field(default=None, max_length=50)
    sector: str | None = Field(default=None, max_length=100)
    min_volume: int | None = Field(default=None, ge=0)
    rsi_min: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    rsi_max: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    wyckoff_phase: str | None = Field(default=None, max_length=20)
    smc: (
        Literal["bullish_fvg", "bearish_fvg", "bos", "choch", "bullish_ob", "bearish_ob"] | None
    ) = None
    missing_only: bool = False
    sort: Literal["ticker", "volume", "rsi"] = "ticker"
    descending: bool = False

    @model_validator(mode="after")
    def bounds(self):
        if self.rsi_min is not None and self.rsi_max is not None and self.rsi_min > self.rsi_max:
            raise ValueError("RSI minimum melebihi maksimum.")
        return self


class PresetCreate(StrictInput):
    name: str = Field(min_length=1, max_length=100)
    criteria: ScreenCriteria


class PlanInput(StrictInput):
    ticker: str = Field(min_length=1, max_length=20)
    currency: Literal["IDR", "USD"]
    entry_low: float = Field(gt=0, allow_inf_nan=False)
    entry_high: float = Field(gt=0, allow_inf_nan=False)
    entry: float = Field(gt=0, allow_inf_nan=False)
    stop: float = Field(gt=0, allow_inf_nan=False)
    target: float = Field(gt=0, allow_inf_nan=False)
    capital: float = Field(gt=0, le=1e15, allow_inf_nan=False)
    risk_pct: float = Field(gt=0, le=100, allow_inf_nan=False)
    lot_size: int = Field(ge=1, le=100000)
    buy_fee_bps: float = Field(default=0, ge=0, le=1000, allow_inf_nan=False)
    sell_fee_bps: float = Field(default=0, ge=0, le=1000, allow_inf_nan=False)
    slippage_bps: float = Field(default=0, ge=0, le=1000, allow_inf_nan=False)
    horizon: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)
    invalidation: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def prices(self):
        if not (
            self.entry_low <= self.entry <= self.entry_high and self.stop < self.entry < self.target
        ):
            raise ValueError("Gunakan stop < entry < target dan entry di dalam area entry.")
        return self


class PlanUpdate(PlanInput):
    expected_version: int = Field(ge=1)


class JobError(BaseModel):
    code: str
    message: str
    stage: str | None = None
    retryable: bool = False


class JobResponse(BaseModel):
    id: UUID
    ticker: str
    status: Literal[
        "queued", "syncing", "calculating", "analyzing", "persisting", "succeeded", "failed"
    ]
    attempts: int = Field(ge=0)
    result_id: UUID | None
    error: JobError | None
    created_at: datetime
    updated_at: datetime
    deadline: datetime | None
    expires_at: datetime


class JobList(BaseModel):
    data: list[JobResponse]


class AlertResponse(AlertCreate):
    id: UUID
    enabled: bool
    last_market_date: date | None
    baseline_established: bool


class AlertList(BaseModel):
    data: list[AlertResponse]


class ScreenRow(BaseModel):
    ticker: str
    company_name: str
    sector: str | None
    exchange: str | None
    currency: str | None
    close: float | None
    volume: int | None
    rsi: float | None
    wyckoff_phase: str | None
    smc_patterns: dict | None
    metadata: MarketDataMetadata


class ScreenCoverage(BaseModel):
    registered_active: int
    with_aligned_data: int
    scope: str


class PageMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int | None = None


class ScreenResult(BaseModel):
    data: list[ScreenRow]
    criteria: ScreenCriteria
    coverage: ScreenCoverage
    pagination: PageMeta


class SavedFilterResponse(PresetCreate):
    id: UUID
    schema_version: int


class SavedFilterList(BaseModel):
    data: list[SavedFilterResponse]


class HistoryItem(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    id: UUID
    ticker: str
    recommendation: str | None
    confidence_score: int | None
    ai_summary: str | None
    analysis_date: date
    generated_at: datetime
    provider_name: str
    model_name: str | None
    actual_model_name: str | None = None
    prompt_version: str | None = None
    data_revision: str | None
    provenance: Literal["real", "unknown"]
    supporting_factors: list[str] = Field(default_factory=list)
    opposing_factors: list[str] = Field(default_factory=list)
    limitations: str | None = None
    horizon: str | None = None
    tokens_used: int = 0
    input_metadata: dict | None = None


class HistoryResponse(BaseModel):
    data: list[HistoryItem]
    pagination: PageMeta


class CompareResponse(BaseModel):
    first: HistoryItem
    second: HistoryItem
    confidence_change_points: int | None
    inputs_differ: bool
    explanation: str


class PlanResponse(BaseModel):
    id: UUID
    ticker: str
    version: int
    details: dict
    versions: list[dict]
    data_revision: str | None
    needs_review: bool
    created_at: datetime
    updated_at: datetime


class PlanList(BaseModel):
    data: list[PlanResponse]
