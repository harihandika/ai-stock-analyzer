"""AI Stock Analyzer - Domain schemas module init."""
from app.domain.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    RegisterResponse,
)
from app.domain.schemas.stocks import (
    StockResponse,
    DailyPriceResponse,
    TechnicalIndicatorResponse,
    AIAnalysisResponse,
    StockAnalysisLatestResponse,
    WatchlistAddRequest,
    WatchlistResponse,
)

__all__ = [
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "UserResponse",
    "RegisterResponse",
    "StockResponse",
    "DailyPriceResponse",
    "TechnicalIndicatorResponse",
    "AIAnalysisResponse",
    "StockAnalysisLatestResponse",
    "WatchlistAddRequest",
    "WatchlistResponse",
]
