"""
AI Stock Analyzer - FastAPI Dependencies
Menyediakan dependency injections untuk:
- Database session (per-request async session)
- Autentikasi pengguna saat ini (get_current_user)
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.domain.models.models import RefreshToken, User
from app.infrastructure.database import AsyncSessionLocal

# OAuth2 scheme: membaca token dari header Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency untuk mendapatkan sesi database async per request.
    Sesi akan ditutup secara otomatis setelah request selesai.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency untuk mendapatkan pengguna yang sedang login dari JWT token.
    Digunakan pada endpoint yang membutuhkan autentikasi.

    Raises:
        HTTPException 401: Jika token tidak valid atau kedaluwarsa.
        HTTPException 401: Jika pengguna tidak ditemukan di database.
        HTTPException 400: Jika akun pengguna tidak aktif.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau sudah kedaluwarsa. Silakan login kembali.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Akun pengguna tidak aktif.",
        )

    try:
        session_id = uuid.UUID(payload.get("sid", ""))
    except (ValueError, TypeError):
        raise credentials_exception
    session = await db.get(RefreshToken, session_id)
    if not session or session.user_id != user.id or session.is_revoked:
        raise credentials_exception
    expiry = session.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    if expiry <= datetime.now(UTC):
        raise credentials_exception
    request.state.user = user
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Alias dependency yang memastikan pengguna aktif.
    Gunakan dependency ini di endpoint yang membutuhkan user aktif terautentikasi.
    """
    return current_user
