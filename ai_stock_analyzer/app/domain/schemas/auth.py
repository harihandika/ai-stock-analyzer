"""
AI Stock Analyzer - Authentication Pydantic Schemas
Mendefinisikan skema validasi input/output untuk operasi autentikasi.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ---- Request Schemas ----

class UserRegisterRequest(BaseModel):
    """Schema untuk registrasi pengguna baru."""
    email: EmailStr = Field(..., description="Alamat email pengguna (unik)")
    password: str = Field(..., min_length=8, description="Password minimal 8 karakter")
    full_name: str = Field(..., min_length=2, max_length=255, description="Nama lengkap pengguna")


class UserLoginRequest(BaseModel):
    """Schema untuk login pengguna (OAuth2 password flow)."""
    email: EmailStr = Field(..., description="Alamat email terdaftar")
    password: str = Field(..., description="Password pengguna")


# ---- Response Schemas ----

class TokenResponse(BaseModel):
    """Response token setelah login berhasil."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str | None = Field(None, description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Tipe token")


class TokenPayload(BaseModel):
    """Payload yang tersimpan di dalam JWT token."""
    sub: str | None = None  # Subject (biasanya user_id)
    exp: datetime | None = None


class UserResponse(BaseModel):
    """Response data pengguna (tidak termasuk password)."""
    id: uuid.UUID
    email: str
    full_name: str
    subscription_tier: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RegisterResponse(BaseModel):
    """Response setelah registrasi berhasil."""
    message: str = "Registrasi berhasil. Silakan login."
    user: UserResponse
