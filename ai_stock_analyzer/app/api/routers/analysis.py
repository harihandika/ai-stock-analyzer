"""Authenticated analysis and technical backtest endpoints."""

import asyncio

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user, get_db
from app.core.config import settings
from app.core.errors import api_error
from app.core.rate_limiter import get_user_id_or_ip, limiter
from app.domain.models.models import User
from app.domain.schemas.analysis import AnalysisExecutionResponse, BacktestRequest, BacktestResult
from app.infrastructure.ai_client import ai_configured, ai_identity
from app.worker.backtester import Backtester

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get(
    "/health",
    summary="Health check untuk Analysis engine",
    description="Memverifikasi bahwa modul analisis siap digunakan.",
)
async def analysis_health_check(
    _: User = Depends(get_current_active_user),
) -> dict:
    """Health check endpoint untuk engine analisis."""
    return {
        "status": "ok",
        "message": "Modul analisis tersedia; konfigurasi provider dilaporkan terpisah.",
        "ai_configured": ai_configured(),
        "provider_validation": "not_checked",
        "provider": ai_identity()[0],
        "model": ai_identity()[1],
        "market_provider": settings.MARKET_DATA_PROVIDER,
        "available_engines": [
            "VPA Engine (Sprint 3)",
            "Wyckoff Engine (Sprint 3)",
            "SMC Engine (Sprint 3)",
            "AI Claude Sonnet Engine (Sprint 4)",
        ],
    }


@router.post(
    "/{ticker}",
    response_model=AnalysisExecutionResponse,
    summary="Jalankan analisis AI dari data tersinkronisasi",
)
@limiter.limit("10/hour", key_func=get_user_id_or_ip)
async def trigger_ai_analysis(
    request: Request,
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    idempotency_key: str | None = Header(default=None, max_length=200),
) -> dict:
    from app.services.analysis_execution import execute_analysis

    return await execute_analysis(ticker, db, current_user, idempotency_key)


@router.post(
    "/{ticker}/backtest", response_model=BacktestResult, summary="Backtest strategi teknikal harian"
)
@limiter.limit("10/hour", key_func=get_user_id_or_ip)
async def run_backtest(
    request: Request,
    ticker: str,
    params: BacktestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    backtester = Backtester(
        ticker,
        params.years,
        params.target_profit_pct / 100,
        params.stop_loss_pct / 100,
        initial_capital=params.initial_capital,
        lot_size=params.lot_size,
        buy_fee_bps=params.buy_fee_bps,
        sell_fee_bps=params.sell_fee_bps,
        slippage_bps=params.slippage_bps,
    )
    try:
        success = await asyncio.wait_for(backtester._fetch_and_prepare_data(), timeout=60)
    except Exception as exc:
        raise api_error(
            "MARKET_DATA_FAILED",
            "Data historis tidak valid atau melewati batas waktu.",
            status=503,
            stage="data",
            retryable=True,
        ) from exc
    if not success:
        raise api_error(
            "DATA_INSUFFICIENT",
            "Histori tidak tersedia atau belum cukup untuk simulasi.",
            status=422,
            stage="data",
        )
    backtester.run_simulation()
    from app.domain.models.models import BacktestRun
    from app.services.market_metadata import history_revision

    result = backtester.get_results_dict()
    run = BacktestRun(
        user_id=current_user.id,
        ticker=ticker.upper(),
        result=result,
        data_revision=backtester.data_revision or history_revision(backtester.df),
    )
    db.add(run)
    await db.commit()
    from app.services.backtest_records import run_payload

    return run_payload(run)
