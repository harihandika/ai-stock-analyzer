"""Durable database worker. Run separately: python -m app.worker.product_worker."""

import argparse
import asyncio
import logging

from app.infrastructure.database import AsyncSessionLocal, engine
from app.services.jobs import process_one


async def main(once=False):
    try:
        while True:
            processed = await process_one(AsyncSessionLocal)
            from app.services.alerts import evaluate_alerts

            async with AsyncSessionLocal() as db:
                await evaluate_alerts(db)
            if once:
                return
            await asyncio.sleep(1 if processed else 5)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main(args.once))
