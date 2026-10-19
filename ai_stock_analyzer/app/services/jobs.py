"""Database-backed jobs: committed acceptance, bounded leases and atomic claims."""

import asyncio
import hashlib
import uuid
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.core.errors import AnalysisError, api_error
from app.domain.models.models import AnalysisJob, User
from app.infrastructure.ai_client import ai_identity
from app.services.ai_service import PROMPT_VERSION
from app.services.market_metadata import as_utc, utcnow

ACTIVE = ("syncing", "calculating", "analyzing", "persisting")


def job_payload(job):
    return {
        "id": str(job.id),
        "ticker": job.ticker,
        "status": job.status,
        "attempts": job.attempts,
        "result_id": str(job.result_id) if job.result_id else None,
        "error": job.error,
        "created_at": as_utc(job.created_at),
        "updated_at": as_utc(job.updated_at),
        "deadline": as_utc(job.deadline),
        "expires_at": as_utc(job.expires_at),
    }


async def submit(db, user, data):
    from app.core.config import settings

    ticker = data.ticker.upper()
    fingerprint = hashlib.sha256(
        (ticker + ":".join(ai_identity()) + settings.MARKET_DATA_PROVIDER + PROMPT_VERSION).encode()
    ).hexdigest()
    key = hashlib.sha256(data.idempotency_key.encode()).hexdigest()
    # Committed idempotent replays do not need a write lock or another commit.
    # New acceptances still recheck after the per-user lock below.
    existing = await db.scalar(
        select(AnalysisJob).where(AnalysisJob.user_id == user.id, AnalysisJob.request_key == key)
    )
    if existing:
        if existing.fingerprint != fingerprint:
            raise api_error(
                "IDEMPOTENCY_CONFLICT",
                "Kunci job sudah dipakai untuk input lain.",
                status=409,
                stage="queued",
            )
        return existing
    # Serialize acceptance per account, including requests with different keys.
    # A read-then-insert check alone can admit duplicate jobs from two tabs.
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(analysis_quota_used=User.analysis_quota_used)
        .execution_options(synchronize_session=False)
    )
    existing = await db.scalar(
        select(AnalysisJob).where(AnalysisJob.user_id == user.id, AnalysisJob.request_key == key)
    )
    if existing:
        if existing.fingerprint != fingerprint:
            raise api_error(
                "IDEMPOTENCY_CONFLICT",
                "Kunci job sudah dipakai untuk input lain.",
                status=409,
                stage="queued",
            )
        return existing
    pending = await db.scalar(
        select(AnalysisJob.id).where(
            AnalysisJob.user_id == user.id,
            AnalysisJob.ticker == ticker,
            AnalysisJob.status.in_(("queued", *ACTIVE)),
        )
    )
    if pending:
        raise api_error(
            "JOB_ALREADY_RUNNING",
            "Analisis saham ini masih dalam antrean.",
            status=409,
            stage="queued",
        )
    now = utcnow()
    job = AnalysisJob(
        user_id=user.id,
        ticker=ticker,
        request_key=key,
        fingerprint=fingerprint,
        status="queued",
        available_at=now,
        expires_at=now + timedelta(minutes=10),
    )
    db.add(job)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        job = await db.scalar(
            select(AnalysisJob).where(
                AnalysisJob.user_id == user.id, AnalysisJob.request_key == key
            )
        )
        if not job or job.fingerprint != fingerprint:
            raise api_error(
                "IDEMPOTENCY_CONFLICT",
                "Job bersamaan memiliki input berbeda.",
                status=409,
                stage="queued",
            ) from None
    return job


async def claim_next(db):
    now = utcnow()
    # An interrupted process cannot retain a lease forever. Its AI reservation is
    # recovered by the shared quota policy when that user executes again.
    await db.execute(
        update(AnalysisJob)
        .where(AnalysisJob.status.in_(ACTIVE), AnalysisJob.deadline <= now)
        .values(
            status="failed",
            error={
                "code": "JOB_INTERRUPTED",
                "message": "Worker terhenti atau deadline terlampaui. Jalankan ulang.",
                "retryable": True,
            },
            lease_token=None,
        )
        .execution_options(synchronize_session=False)
    )
    await db.execute(
        update(AnalysisJob)
        .where(AnalysisJob.status == "queued", AnalysisJob.expires_at <= now)
        .values(
            status="failed",
            error={
                "code": "QUEUE_EXPIRED",
                "message": "Antrean kedaluwarsa; periksa worker lalu coba lagi.",
                "retryable": True,
            },
        )
        .execution_options(synchronize_session=False)
    )
    job = await db.scalar(
        select(AnalysisJob)
        .where(
            AnalysisJob.status == "queued",
            AnalysisJob.available_at <= now,
            AnalysisJob.expires_at > now,
        )
        .order_by(AnalysisJob.created_at, AnalysisJob.id)
        .limit(1)
    )
    if not job:
        await db.commit()
        return None
    token = str(uuid.uuid4())
    result = await db.execute(
        update(AnalysisJob)
        .where(AnalysisJob.id == job.id, AnalysisJob.status == "queued")
        .values(
            status="syncing",
            lease_token=token,
            attempts=AnalysisJob.attempts + 1,
            deadline=job.deadline or now + timedelta(seconds=120),
        )
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    if not result.rowcount:
        return None
    await db.refresh(job)
    return job


async def process_one(factory):
    from app.api.routers.stocks import do_sync_stock
    from app.services.analysis_execution import execute_analysis

    async with factory() as db:
        job = await claim_next(db)
        if not job:
            return False
        job_id, token, deadline = job.id, job.lease_token, as_utc(job.deadline)

        async def stage(value):
            result = await db.execute(
                update(AnalysisJob)
                .where(
                    AnalysisJob.id == job_id,
                    AnalysisJob.lease_token == token,
                    AnalysisJob.deadline > utcnow(),
                )
                .values(status=value)
                .execution_options(synchronize_session=False)
            )
            if not result.rowcount:
                raise AnalysisError("JOB_LEASE_EXPIRED", "Job kedaluwarsa.", status=409)
            await db.commit()

        try:
            from app.core.config import settings

            expected = hashlib.sha256(
                (
                    job.ticker
                    + ":".join(ai_identity())
                    + settings.MARKET_DATA_PROVIDER
                    + PROMPT_VERSION
                ).encode()
            ).hexdigest()
            if expected != job.fingerprint:
                raise AnalysisError(
                    "PROVIDER_CHANGED", "Konfigurasi provider berubah; buat job baru.", status=409
                )
            async with asyncio.timeout(max(0, (deadline - utcnow()).total_seconds())):
                user = await db.get(User, job.user_id)
                if not user or not user.is_active:
                    raise AnalysisError("ACCOUNT_INACTIVE", "Akun tidak aktif.", status=403)
                await do_sync_stock(job.ticker, db, progress=stage)
                await stage("analyzing")
                result = await execute_analysis(job.ticker, db, user, "job-" + str(job.id))
                await stage("persisting")
                await db.execute(
                    update(AnalysisJob)
                    .where(AnalysisJob.id == job_id, AnalysisJob.lease_token == token)
                    .values(
                        status="succeeded",
                        result_id=uuid.UUID(result["result"]["id"]),
                        error=None,
                        lease_token=None,
                    )
                    .execution_options(synchronize_session=False)
                )
                await db.commit()
        except Exception as exc:
            await db.rollback()
            job = await db.get(AnalysisJob, job_id)
            if not job or job.lease_token != token:
                return True
            if isinstance(exc, HTTPException):
                error = (
                    exc.detail
                    if isinstance(exc.detail, dict)
                    else {
                        "code": "JOB_FAILED",
                        "message": "Analisis gagal; silakan periksa data/provider.",
                        "retryable": exc.status_code >= 500,
                    }
                )
            elif isinstance(exc, AnalysisError):
                error = {"code": exc.code, "message": exc.message, "retryable": exc.status >= 500}
            else:
                error = {
                    "code": "JOB_TIMEOUT" if isinstance(exc, TimeoutError) else "JOB_FAILED",
                    "message": "Analisis belum selesai; data tersimpan dipertahankan.",
                    "retryable": True,
                }
            can_retry = (
                error.get("retryable", False)
                and job.attempts < 2
                and deadline > utcnow() + timedelta(seconds=10)
            )
            job.status = "queued" if can_retry else "failed"
            job.error, job.lease_token = error, None
            job.available_at = utcnow() + timedelta(seconds=5)
            await db.commit()
        return True
