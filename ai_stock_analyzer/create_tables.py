import sys, os
sys.path.insert(0, os.path.abspath("."))
import asyncio
from app.infrastructure.database import engine, Base
import app.domain.models.models

async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(create())
