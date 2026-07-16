"""
AI Stock Analyzer - Database Infrastructure
Menyediakan engine SQLAlchemy async, sesi database, dan base model.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ---- Async Engine ----
# Pool size dan max_overflow bisa diatur sesuai kebutuhan production
engine_kwargs = {
    "echo": settings.DEBUG,
}
if "sqlite" not in settings.DATABASE_URL:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

# ---- Async Session Factory ----
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,    # Cegah lazy-loading error setelah commit
    autocommit=False,
    autoflush=False,
)


# ---- Declarative Base ----
class Base(DeclarativeBase):
    """
    Base class untuk semua ORM Model di aplikasi ini.
    Semua model harus mewarisi class ini.
    """
    pass
