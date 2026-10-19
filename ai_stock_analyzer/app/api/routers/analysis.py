"""Authenticated analysis and technical backtest endpoints."""

import asyncio
import hashlib
from datetime import UTC, timedelta

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user, get_db
from app.core.config import settings
from app.core.errors import AnalysisError, api_error
from app.core.rate_limiter import get_user_id_or_ip, limiter
from app.domain.models.models import AIAnalysis, AnalysisRequest, Stock, User
from app.domain.schemas.analysis import AnalysisExecutionResponse, BacktestRequest, BacktestResult
from app.services.ai_service import PROMPT_VERSION, cached_analysis, result_payload, run_ai_analysis
from app.services.market_metadata import utcnow
from app.services.quota import quota_day, reclaim_expired, release, reserve
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
        "ai_configured": bool(settings.ANTHROPIC_API_KEY),
        "provider_validation": "not_checked",
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
    user_id = current_user.id
    ticker = ticker.upper()
    stock = await db.get(Stock, ticker)
    if not stock:
        raise api_error(
            "STOCK_NOT_FOUND",
            "Saham belum terdaftar. Sinkronkan terlebih dahulu.",
            status=404,
            stage="data",
        )
    if not stock.data_revision:
        raise api_error(
            "DATA_UNVERIFIED", "Sinkronkan data pasar terlebih dahulu.", status=409, stage="data"
        )
    revision = hashlib.sha256(
        (stock.data_revision + settings.AI_MODEL_OPERATIONAL + PROMPT_VERSION).encode()
    ).hexdigest()
    key = hashlib.sha256((idempotency_key or (ticker + revision)).encode()).hexdigest()
    await reclaim_expired(db, user_id)
    run = (
        await db.execute(
            select(AnalysisRequest).where(
                AnalysisRequest.user_id == user_id, AnalysisRequest.request_key == key
            )
        )
    ).scalar_one_or_none()
    if run and run.input_revision != revision:
        raise api_error(
            "IDEMPOTENCY_CONFLICT",
            "Kunci permintaan sudah digunakan untuk input lain.",
            status=409,
            stage="quota",
        )
    if run and run.status == "succeeded":
        return {
            "message": "Hasil analisis tersimpan digunakan kembali.",
            "result": result_payload(await db.get(AIAnalysis, run.result_id), cached=True),
        }
    if run and run.status == "running":
        raise api_error(
            "ANALYSIS_RUNNING",
            "Analisis yang sama sedang berjalan. Coba lagi sebentar.",
            status=409,
            stage="analyzing",
            retryable=True,
        )
    cached = await cached_analysis(db, ticker, stock.data_revision)
    if cached:
        # Even a shared-cache response binds the key to its original input.
        if not run:
            run = AnalysisRequest(
                user_id=user_id, request_key=key, input_revision=revision,
                status="succeeded", quota_day=quota_day(),
                expires_at=utcnow(), result_id=cached.id,
            )
            db.add(run)
        else:
            run.status, run.result_id = "succeeded", cached.id
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise api_error(
                "ANALYSIS_RUNNING", "Permintaan yang sama sedang diproses.",
                status=409, stage="quota", retryable=True,
            ) from exc
        return {
            "message": "Hasil analisis tersimpan digunakan kembali; kuota tidak berkurang.",
            "result": result_payload(cached, cached=True),
        }
    deadline = utcnow() + timedelta(seconds=120)
    try:
        if run:
            claimed = await db.execute(
                update(AnalysisRequest)
                .where(AnalysisRequest.id == run.id, AnalysisRequest.status == "failed")
                .values(status="running", expires_at=deadline, quota_day=quota_day())
                .execution_options(synchronize_session=False)
            )
            if not claimed.rowcount:
                raise api_error(
                    "ANALYSIS_RUNNING",
                    "Permintaan sedang diproses.",
                    status=409,
                    stage="quota",
                    retryable=True,
                )
            await db.refresh(run)
        else:
            run = AnalysisRequest(
                user_id=user_id,
                request_key=key,
                input_revision=revision,
                status="running",
                quota_day=quota_day(),
                expires_at=deadline,
            )
            db.add(run)
            await db.flush()
        await reserve(db, user_id)
        run_id = run.id
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise api_error(
            "ANALYSIS_RUNNING",
            "Permintaan yang sama sedang diproses.",
            status=409,
            stage="quota",
            retryable=True,
        ) from exc
    try:
        result = await asyncio.wait_for(
            run_ai_analysis(ticker, db, analyzed_by=user_id, commit=False), timeout=90
        )
        await db.refresh(run)
        if run.status != "running" or run.expires_at.replace(tzinfo=UTC) != deadline:
            raise AnalysisError(
                "RESERVATION_EXPIRED", "Permintaan kedaluwarsa; silakan coba lagi.", status=409
            )
        from uuid import UUID

        run.result_id = UUID(result["id"])
        await release(db, run, success=not result.get("cached", False))
        run.status = "succeeded"
        await db.commit()
        return {"message": "Analisis AI berhasil disimpan.", "result": result}
    except Exception as exc:
        await db.rollback()
        run = await db.get(AnalysisRequest, run_id)
        if run and run.status == "running" and run.expires_at.replace(tzinfo=UTC) == deadline:
            await release(db, run)
            await db.commit()
        if isinstance(exc, AnalysisError):
            raise api_error(
                exc.code,
                exc.message,
                status=exc.status,
                stage=exc.stage,
                retryable=exc.status >= 500,
            ) from exc
        if isinstance(exc, TimeoutError):
            raise api_error(
                "AI_TIMEOUT",
                "Analisis melewati batas waktu.",
                status=504,
                stage="analyzing",
                retryable=True,
            ) from exc
        raise api_error(
            "ANALYSIS_FAILED",
            "Analisis gagal; hasil terakhir dipertahankan.",
            status=500,
            stage="persisting",
            retryable=True,
        ) from exc


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
        ticker, params.years, params.target_profit_pct / 100, params.stop_loss_pct / 100
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
    return backtester.get_results_dict()
