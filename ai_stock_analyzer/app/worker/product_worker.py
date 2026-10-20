"""Durable database worker. Run separately: python -m app.worker.product_worker."""

import argparse
import asyncio
import logging
import uuid
from datetime import timedelta

from sqlalchemy import delete, update

from app.domain.models.models import WorkerHeartbeat
from app.infrastructure.database import AsyncSessionLocal, engine
from app.services.alerts import evaluate_alerts
from app.services.jobs import process_one
from app.services.market_metadata import utcnow
from app.services.operations import HEARTBEAT_INTERVAL_SECONDS


async def run(
    factory, *, once=False, heartbeat_interval=HEARTBEAT_INTERVAL_SECONDS, instance_id=None
):
    """A separate task/session keeps liveness advancing during slow AI calls.

    Progress is updated only by the main loop. A supervisor should restart an
    exited process; heartbeat does not turn a stuck/deadline job into success.
    """
    instance_id = instance_id or str(uuid.uuid4())
    started = utcnow()
    async with factory() as db:
        await db.execute(
            delete(WorkerHeartbeat).where(
                WorkerHeartbeat.heartbeat_at < started - timedelta(days=7)
            )
        )
        db.add(WorkerHeartbeat(id=instance_id, started_at=started, heartbeat_at=started))
        await db.commit()
    stop = asyncio.Event()

    async def update_state(**values):
        async with factory() as db:
            await db.execute(
                update(WorkerHeartbeat).where(WorkerHeartbeat.id == instance_id).values(**values)
            )
            await db.commit()

    async def heartbeat():
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=heartbeat_interval)
            except TimeoutError:
                try:
                    await update_state(heartbeat_at=utcnow())
                except Exception:
                    logging.getLogger(__name__).error("WORKER_HEARTBEAT_FAILED")

    pulse = asyncio.create_task(heartbeat())
    try:
        while True:
            try:
                processed = await process_one(factory)
                async with factory() as db:
                    await evaluate_alerts(db)
                await update_state(progress_at=utcnow(), error_code=None)
            except Exception:
                # Exception text may include provider URLs or user input.
                logging.getLogger(__name__).error("WORKER_CYCLE_FAILED")
                await update_state(error_code="WORKER_CYCLE_FAILED")
                if once:
                    raise RuntimeError("WORKER_CYCLE_FAILED") from None
                processed = False
            if once:
                return
            await asyncio.sleep(1 if processed else 5)
    finally:
        stop.set()
        await pulse
        await update_state(stopped_at=utcnow())


async def main(once=False):
    try:
        await run(AsyncSessionLocal, once=once)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main(args.once))
