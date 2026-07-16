"""
AI Stock Analyzer - Security Utilities
Menangani enkripsi password (bcrypt) dan JWT token (pembuatan & verifikasi).
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ---- Password Hashing ----
# Menggunakan bcrypt sebagai algoritma hashing yang aman dan lambat (resistant to brute-force)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash password plaintext menggunakan bcrypt."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifikasi password plaintext terhadap hash yang tersimpan di database."""
    return pwd_context.verify(plain_password, hashed_password)


# ---- JWT Token ----

def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """
    Membuat JWT access token.

    Args:
        subject: Payload data (biasanya user_id atau email).
        expires_delta: Override default expiry time. Jika None, menggunakan setting default.

    Returns:
        JWT token string yang ditandatangani (signed).
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    """
    Mendekode dan memverifikasi JWT access token.

    Args:
        token: JWT token string.

    Returns:
        Dictionary payload jika token valid, None jika tidak valid/kedaluwarsa.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
