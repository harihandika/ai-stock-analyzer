"""Shared transactional quota/idempotency policy for HTTP and durable workers."""

import asyncio
import hashlib
from datetime import UTC, timedelta

from anyio import CancelScope
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.core.errors import AnalysisError, api_error
from app.domain.models.models import AIAnalysis, AnalysisRequest, Stock
from app.infrastructure.ai_client import ai_identity
from app.services.ai_service import PROMPT_VERSION, cached_analysis, result_payload, run_ai_analysis
from app.services.market_metadata import utcnow
from app.services.quota import quota_day, reclaim_expired, release, reserve


async def execute_analysis(ticker, db, current_user, idempotency_key=None):
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
        (stock.data_revision + ":".join(ai_identity()) + PROMPT_VERSION).encode()
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
                user_id=user_id,
                request_key=key,
                input_revision=revision,
                status="succeeded",
                quota_day=quota_day(),
                expires_at=utcnow(),
                result_id=cached.id,
            )
            db.add(run)
        else:
            run.status, run.result_id = "succeeded", cached.id
        try:
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
    except BaseException as exc:
        with CancelScope(shield=True):
            await db.rollback()
            run = await db.get(AnalysisRequest, run_id)
            if run and run.status == "running" and run.expires_at.replace(tzinfo=UTC) == deadline:
                await release(db, run)
                await db.commit()
        if not isinstance(exc, Exception):
            raise
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
