"""API percentages are percentage points; only model output uses fractions."""

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelAnalysis(BaseModel):
    recommendation: Literal["BUY", "HOLD", "WAIT"]
    confidence_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    vpa_insight: str = Field(min_length=1, max_length=12000)
    wyckoff_phase: str = Field(min_length=1, max_length=200)
    summary: str | None = Field(default=None, max_length=12000)
    supporting_factors: list[str] = Field(default_factory=list, max_length=10)
    opposing_factors: list[str] = Field(default_factory=list, max_length=10)
    limitations: str = "Analisis teknikal harian; bukan probabilitas keuntungan terkalibrasi."
    horizon: str = "Swing trading berdasarkan data harian"
    tokens_used: int = Field(default=0, ge=0)


class BacktestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    years: int = Field(default=3, ge=1, le=5)
    target_profit_pct: float = Field(default=5, gt=0, le=20, allow_inf_nan=False)
    stop_loss_pct: float = Field(default=3, gt=0, le=10, allow_inf_nan=False)

    @model_validator(mode="before")
    @classmethod
    def legacy_decimals(cls, values):
        if not isinstance(values, dict):
            return values
        values = dict(values)
        if any(isinstance(v, bool) for v in values.values()):
            raise ValueError("Parameter backtest harus berupa angka, bukan boolean.")
        legacy = {"target_profit": "target_profit_pct", "stop_loss": "stop_loss_pct"}
        if any(k in values for k in legacy):
            if any(k in values for k in legacy.values()):
                raise ValueError("Jangan mencampur satuan legacy desimal dan persen.")
            for old, new in legacy.items():
                if old in values:
                    raw = values.pop(old)
                    if isinstance(raw, bool):
                        raise ValueError("Parameter persen harus berupa angka.")
                    values[new] = float(raw) * 100
        return values


class BacktestTrade(BaseModel):
    buy_date: date
    sell_date: date
    buy_price: float = Field(gt=0, allow_inf_nan=False)
    sell_price: float = Field(gt=0, allow_inf_nan=False)
    profit_pct: float = Field(allow_inf_nan=False)
    status: Literal["WIN", "LOSS", "BREAKEVEN"]
    exit_reason: Literal["TAKE_PROFIT", "STOP_LOSS", "TIMEOUT", "END_OF_PERIOD"]
    reason: str
    days_held: int = Field(ge=1)


class EquityPoint(BaseModel):
    date: date
    equity: float = Field(ge=0, allow_inf_nan=False)


class BacktestResult(BaseModel):
    ticker: str
    period_years: int
    requested_parameters: BacktestRequest
    effective_parameters: BacktestRequest
    data_start: date
    data_end: date
    source: str
    interval: Literal["1d"]
    strategy: str
    total_trades: int = Field(ge=0)
    win_rate_pct: float = Field(ge=0, le=100, allow_inf_nan=False)
    avg_profit_pct: float = Field(allow_inf_nan=False)
    max_drawdown_pct: float = Field(ge=0, le=100, allow_inf_nan=False)
    trades: list[BacktestTrade]
    equity_curve: list[EquityPoint]
    assumptions: dict[str, Any]


class AnalysisResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    id: uuid.UUID
    ticker: str
    recommendation: Literal["BUY", "HOLD", "WAIT"]
    confidence_score: int = Field(ge=0, le=100)
    ai_summary: str
    vpa_insight: str
    analysis_date: date
    generated_at: datetime
    data_revision: str
    model_name: str
    prompt_version: str
    provenance: Literal["real"]
    cached: bool
    supporting_factors: list[str] = Field(default_factory=list)
    opposing_factors: list[str] = Field(default_factory=list)
    limitations: str
    horizon: str
    tokens_used: int = Field(ge=0)


class AnalysisExecutionResponse(BaseModel):
    message: str
    result: AnalysisResult
