"""
AI Stock Analyzer - Rate Limiter
Menggunakan slowapi untuk membatasi jumlah request berdasarkan IP.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse

import os

# Disable rate limiting saat testing agar pytest tidak terblokir
_is_testing = os.getenv("TESTING", "").lower() in ("1", "true", "yes")

# Inisialisasi Limiter dengan fungsi untuk mendapatkan IP address client
limiter = Limiter(key_func=get_remote_address, enabled=not _is_testing)

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for RateLimitExceeded exception."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Coba lagi dalam beberapa saat."}
    )

def get_user_id_or_ip(request: Request) -> str:
    """
    Helper untuk rate limiting berbasis User ID jika memungkinkan,
    atau fallback ke IP address jika belum login.
    """
    user = getattr(request.state, "user", None)
    if user:
        return str(user.id)
    return get_remote_address(request)
