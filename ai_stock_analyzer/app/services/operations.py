"""Measured process liveness is separate from configuration and provider delivery."""

from datetime import timedelta

from sqlalchemy import select

from app.domain.models.models import WorkerHeartbeat
from app.services.market_metadata import as_utc, utcnow

HEARTBEAT_INTERVAL_SECONDS = 15
HEARTBEAT_STALE_SECONDS = 60


async def worker_status(db, *, now=None):
    now = now or utcnow()
    rows = (
        await db.scalars(
            select(WorkerHeartbeat).order_by(WorkerHeartbeat.heartbeat_at.desc()).limit(100)
        )
    ).all()
    live = [
        row
        for row in rows
        if not row.stopped_at
        and now - timedelta(seconds=HEARTBEAT_STALE_SECONDS) < as_utc(row.heartbeat_at) <= now
    ]
    healthy = [row for row in live if not row.error_code]
    return {
        "state": "healthy" if healthy else "degraded" if live else "unavailable",
        "healthy_instances": len(healthy),
        "live_instances": len(live),
        "last_heartbeat_at": as_utc(rows[0].heartbeat_at) if rows else None,
        "last_progress_at": max(
            (as_utc(row.progress_at) for row in rows if row.progress_at), default=None
        ),
        "stale_after_seconds": HEARTBEAT_STALE_SECONDS,
        "provider_connection": "not_verified_by_heartbeat",
    }
