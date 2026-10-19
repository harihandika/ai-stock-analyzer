import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import EmailStr, Field
from sqlalchemy import select, update

from app.api.dependencies import get_current_active_user, get_db
from app.core.config import settings
from app.core.rate_limiter import get_user_id_or_ip, limiter
from app.core.security import hash_password, hash_token, verify_password
from app.domain.models.models import PasswordReset, RefreshToken, User
from app.domain.schemas.auth import UserResponse
from app.domain.schemas.product import StrictInput
from app.infrastructure.email import send_password_reset
from app.services.market_metadata import utcnow
from app.services.quota import snapshot

router = APIRouter(prefix="/auth", tags=["Account"])


class ProfileUpdate(StrictInput):
    full_name: str = Field(min_length=2, max_length=255)
    notifications_enabled: bool = True


class PasswordChange(StrictInput):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)


class ResetRequest(StrictInput):
    email: EmailStr


class ResetConfirm(StrictInput):
    token: str = Field(min_length=32, max_length=200)
    new_password: str = Field(min_length=8, max_length=72)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    data: ProfileUpdate, db=Depends(get_db), user=Depends(get_current_active_user)
):
    user.full_name, user.notifications_enabled = data.full_name.strip(), data.notifications_enabled
    if len(user.full_name) < 2:
        raise HTTPException(422, "Nama minimal dua karakter.")
    await db.commit()
    return UserResponse.model_validate(user).model_copy(update=snapshot(user))


async def revoke_all(db, user_id):
    await db.execute(
        update(RefreshToken).where(RefreshToken.user_id == user_id).values(is_revoked=True)
    )
    await db.execute(
        update(PasswordReset).where(PasswordReset.user_id == user_id).values(used=True)
    )


@router.post("/change-password")
@limiter.limit("5/hour", key_func=get_user_id_or_ip)
async def change_password(
    request: Request,
    data: PasswordChange,
    db=Depends(get_db),
    user=Depends(get_current_active_user),
):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Password saat ini tidak sesuai.")
    result = await db.execute(
        update(User)
        .where(User.id == user.id, User.password_hash == user.password_hash)
        .values(password_hash=hash_password(data.new_password))
        .execution_options(synchronize_session=False)
    )
    if not result.rowcount:
        raise HTTPException(409, "Akun berubah; silakan login ulang.")
    await revoke_all(db, user.id)
    await db.commit()
    return {"message": "Password diperbarui. Semua sesi dicabut; silakan login kembali."}


@router.post("/password-reset")
@limiter.limit("3/minute")
async def request_reset(request: Request, data: ResetRequest, db=Depends(get_db)):
    if not settings.SMTP_HOST or not settings.SMTP_FROM:
        raise HTTPException(503, "Pemulihan email belum dikonfigurasi. Hubungi pengelola aplikasi.")
    user = await db.scalar(select(User).where(User.email == data.email, User.is_active.is_(True)))
    if user:
        token = secrets.token_urlsafe(32)
        await db.execute(
            update(PasswordReset).where(PasswordReset.user_id == user.id).values(used=True)
        )
        db.add(
            PasswordReset(
                user_id=user.id,
                token_hash=hash_token(token),
                expires_at=utcnow() + timedelta(minutes=30),
            )
        )
        try:
            await send_password_reset(user.email, token)
            await db.commit()
        except Exception:
            await db.rollback()
            # Same public response for existing/unknown accounts; delivery failures
            # are reported to operators as a count, never recipient or reset token.
            import logging

            logging.getLogger(__name__).error("Password reset delivery failed")
    return {
        "message": "Jika email terdaftar dan pengiriman tersedia, tautan reset akan dikirim. Periksa kotak masuk atau coba lagi nanti."
    }


@router.post("/password-reset/confirm")
@limiter.limit("5/minute")
async def confirm_reset(request: Request, data: ResetConfirm, db=Depends(get_db)):
    reset = await db.scalar(
        select(PasswordReset).where(PasswordReset.token_hash == hash_token(data.token))
    )
    if not reset:
        raise HTTPException(400, "Tautan reset tidak valid atau kedaluwarsa.")
    claimed = await db.execute(
        update(PasswordReset)
        .where(
            PasswordReset.id == reset.id,
            PasswordReset.used.is_(False),
            PasswordReset.expires_at > utcnow(),
        )
        .values(used=True)
        .execution_options(synchronize_session=False)
    )
    if not claimed.rowcount:
        raise HTTPException(400, "Tautan reset tidak valid atau kedaluwarsa.")
    await db.execute(
        update(User)
        .where(User.id == reset.user_id, User.is_active.is_(True))
        .values(password_hash=hash_password(data.new_password))
    )
    await revoke_all(db, reset.user_id)
    await db.commit()
    return {"message": "Password diperbarui. Silakan login kembali."}
