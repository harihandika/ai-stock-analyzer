"""Atomic quota reservations and Jakarta-day accounting."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import case, or_, select, update

from app.core.errors import api_error
from app.domain.models.models import AnalysisRequest, User
from app.services.market_metadata import utcnow

JAKARTA = ZoneInfo("Asia/Jakarta")


def quota_day():
    return utcnow().astimezone(JAKARTA).date()


def snapshot(user):
    today = quota_day()
    used = user.analysis_quota_used if user.last_quota_reset == today else 0
    reserved = user.analysis_quota_reserved if user.last_quota_reset == today else 0
    limit = None if user.subscription_tier == "premium" else 3
    return {
        "analysis_quota_used": used,
        "quota_used": used,
        "quota_reserved": reserved,
        "quota_limit": limit,
        "quota_remaining": None if limit is None else max(0, limit - used - reserved),
        "quota_reset_at": datetime.combine(today + timedelta(days=1), time.min, tzinfo=JAKARTA),
    }


async def release(db, run, *, success=False):
    """Called in the same transaction as the durable terminal state/result."""
    today = quota_day()
    if run.quota_day == today:
        values = {
            "analysis_quota_reserved": case(
                (User.analysis_quota_reserved > 0, User.analysis_quota_reserved - 1), else_=0
            ),
        }
        if success:
            values["analysis_quota_used"] = User.analysis_quota_used + 1
        await db.execute(
            update(User)
            .where(User.id == run.user_id, User.last_quota_reset == today)
            .values(**values)
            .execution_options(synchronize_session=False)
        )
    run.status = "succeeded" if success else "failed"


async def reclaim_expired(db, user_id):
    rows = (
        (
            await db.execute(
                select(AnalysisRequest).where(
                    AnalysisRequest.user_id == user_id,
                    AnalysisRequest.status == "running",
                    AnalysisRequest.expires_at < utcnow(),
                )
            )
        )
        .scalars()
        .all()
    )
    for run in rows:
        claimed = await db.execute(
            update(AnalysisRequest)
            .where(AnalysisRequest.id == run.id, AnalysisRequest.status == "running")
            .values(status="failed")
            .execution_options(synchronize_session=False)
        )
        if claimed.rowcount:
            await release(db, run)
    if rows:
        await db.commit()


async def reserve(db, user_id):
    today = quota_day()
    same_day = User.last_quota_reset == today
    used = case((same_day, User.analysis_quota_used), else_=0)
    reserved = case((same_day, User.analysis_quota_reserved), else_=0)
    result = await db.execute(
        update(User)
        .where(
            User.id == user_id,
            User.is_active.is_(True),
            or_(User.subscription_tier == "premium", used + reserved < 3),
        )
        .values(
            analysis_quota_used=used,
            analysis_quota_reserved=reserved + 1,
            last_quota_reset=today,
        )
        .execution_options(synchronize_session=False)
    )
    if not result.rowcount:
        raise api_error(
            "QUOTA_EXHAUSTED",
            "Kuota analisis harian habis. Coba lagi setelah reset.",
            status=403,
            stage="quota",
        )
