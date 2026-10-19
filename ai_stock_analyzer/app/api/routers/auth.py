"""
AI Stock Analyzer - Authentication Router
Menyediakan endpoint untuk registrasi dan login pengguna.

Endpoints:
- POST /auth/register - Registrasi pengguna baru
- POST /auth/token   - Login dan dapatkan JWT access token
- GET  /auth/me      - Data pengguna yang sedang login
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user, get_db
from app.core.config import settings
from app.core.rate_limiter import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.domain.models.models import RefreshToken, User
from app.domain.schemas.auth import (
    RegisterResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrasi pengguna baru",
    description="Mendaftarkan akun pengguna baru. Email harus unik.",
)
@limiter.limit("3/minute")
async def register(
    request: Request,
    user_request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """
    Registrasi pengguna baru ke sistem.
    - Cek apakah email sudah terdaftar
    - Hash password sebelum disimpan
    - Return data user (tanpa password)
    """
    # 1. Cek apakah email sudah terdaftar
    result = await db.execute(select(User).where(User.email == user_request.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{user_request.email}' sudah terdaftar. Gunakan email lain atau login.",
        )

    # 2. Buat user baru dengan password yang di-hash
    new_user = User(
        email=user_request.email,
        password_hash=hash_password(user_request.password),
        full_name=user_request.full_name,
        subscription_tier="free",
        is_active=True,
    )
    db.add(new_user)
    await db.flush()  # Dapatkan ID sebelum commit
    await db.refresh(new_user)

    return RegisterResponse(
        message="Registrasi berhasil. Silakan login untuk mendapatkan token akses.",
        user=UserResponse.model_validate(new_user),
    )


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Login dan dapatkan JWT Access Token",
    description="Autentikasi pengguna dengan email dan password. Mengembalikan JWT token.",
)
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request,
    user_request: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Login pengguna dan menghasilkan JWT access token.
    Token ini harus disertakan di header Authorization: Bearer <token>
    untuk semua endpoint yang membutuhkan autentikasi.
    """
    # 1. Cari user berdasarkan email
    result = await db.execute(select(User).where(User.email == user_request.email))
    user = result.scalar_one_or_none()

    # 2. Verifikasi password (gunakan pesan error generik untuk keamanan)
    if not user or not verify_password(user_request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Cek status akun
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Akun Anda tidak aktif. Hubungi administrator.",
        )

    # 4. Buat JWT token dengan subject = user ID
    session_id = uuid.uuid4()
    access_token = create_access_token(subject=str(user.id), session_id=str(session_id))
    refresh_token = create_refresh_token(subject=str(user.id))

    # 5. Simpan hash refresh_token ke DB
    hashed_rt = hash_token(refresh_token)
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    rt_record = RefreshToken(
        id=session_id,
        user_id=user.id,
        token_hash=hashed_rt,
        expires_at=expires_at,
        is_revoked=False,
    )
    db.add(rt_record)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Dapatkan Access Token baru menggunakan Refresh Token",
    description="Menghasilkan JWT access token baru menggunakan refresh token yang valid.",
)
@limiter.limit("5/minute")
async def refresh_token(
    request: Request,
    refresh_request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Menggunakan refresh token untuk mendapatkan access token baru."""
    payload = decode_refresh_token(refresh_request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token tidak valid atau sudah kedaluwarsa.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Refresh token tidak valid.")

    import uuid

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Refresh token tidak valid.")

    # Validasi refresh token dari DB
    hashed_rt = hash_token(refresh_request.refresh_token)
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == hashed_rt, RefreshToken.is_revoked.is_(False)
    )
    result_rt = await db.execute(stmt)
    rt_record = result_rt.scalar_one_or_none()

    if not rt_record or rt_record.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token tidak valid atau sudah kedaluwarsa.",
        )

    record_expires_at = rt_record.expires_at
    if record_expires_at.tzinfo is None:
        record_expires_at = record_expires_at.replace(tzinfo=UTC)

    if record_expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token tidak valid atau sudah kedaluwarsa.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pengguna tidak valid atau akun tidak aktif.",
        )

    # Compare-and-set ensures concurrent rotations cannot consume the same token twice.
    consumed = await db.execute(
        update(RefreshToken)
        .where(RefreshToken.id == rt_record.id, RefreshToken.is_revoked.is_(False))
        .values(is_revoked=True)
        .execution_options(synchronize_session=False)
    )
    if not consumed.rowcount:
        raise HTTPException(status_code=401, detail="Refresh token sudah digunakan.")

    # Buat token baru
    session_id = uuid.uuid4()
    access_token = create_access_token(subject=str(user.id), session_id=str(session_id))
    new_refresh_token = create_refresh_token(subject=str(user.id))

    # Simpan token baru ke DB
    new_hashed_rt = hash_token(new_refresh_token)
    new_expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    new_rt_record = RefreshToken(
        id=session_id,
        user_id=user.id,
        token_hash=new_hashed_rt,
        expires_at=new_expires_at,
        is_revoked=False,
    )
    db.add(new_rt_record)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


class LogoutResponse(BaseModel):
    message: str


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Logout pengguna",
    description="Me-revoke refresh token sehingga tidak bisa digunakan lagi.",
)
async def logout(
    request: Request,
    refresh_request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    """Logout dengan me-revoke refresh token di database."""
    hashed_rt = hash_token(refresh_request.refresh_token)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == hashed_rt)
        .values(is_revoked=True)
        .execution_options(synchronize_session=False)
    )
    await db.commit()

    return LogoutResponse(message="Logout berhasil.")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Dapatkan data pengguna yang sedang login",
    description="Mengembalikan profil pengguna yang terautentikasi berdasarkan JWT token.",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Endpoint untuk mendapatkan profil pengguna yang sedang login.
    Membutuhkan JWT token yang valid di header Authorization.
    """
    from app.services.quota import reclaim_expired, snapshot

    await reclaim_expired(db, current_user.id)
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user).model_copy(update=snapshot(current_user))
