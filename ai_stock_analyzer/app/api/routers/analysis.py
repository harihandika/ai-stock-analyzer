"""
AI Stock Analyzer - Analysis Router
Menangani trigger analisis AI secara manual dan melihat insight khusus.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import get_current_active_user, get_db
from app.core.rate_limiter import limiter
from app.domain.models.models import User, Stock
from app.services.ai_service import run_ai_analysis

router = APIRouter(prefix="/analysis", tags=["Analysis"])

@router.get(
    "/health",
    summary="Health check untuk Analysis engine",
    description="Memverifikasi bahwa modul analisis siap digunakan.",
)
async def analysis_health_check(
    _: User = Depends(get_current_active_user),
) -> dict:
    """Health check endpoint untuk engine analisis."""
    return {
        "status": "ok",
        "message": "Analysis engine siap dan online.",
        "available_engines": [
            "VPA Engine (Sprint 3)",
            "Wyckoff Engine (Sprint 3)",
            "SMC Engine (Sprint 3)",
            "AI Claude Sonnet Engine (Sprint 4)",
        ],
    }

@router.post(
    "/{ticker}",
    summary="Jalankan analisis AI manual",
    description="Memaksa jalannya analisis AI Claude Sonnet untuk ticker tertentu. Hati-hati penggunaan token (Rate Limit).",
)
@limiter.limit("10/hour")
async def trigger_ai_analysis(
    request: Request,
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """Trigger manual analisis AI (Hanya untuk Admin/Premium)."""
    ticker_upper = ticker.upper()
    
    # Cek ketersediaan saham
    stock_result = await db.execute(select(Stock).where(Stock.ticker == ticker_upper))
    stock = stock_result.scalar_one_or_none()
    
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saham '{ticker_upper}' tidak ditemukan. Lakukan /sync terlebih dahulu."
        )

    # --- Tier Access Control ---
    from datetime import date
    today = date.today()
    
    if current_user.subscription_tier == "free":
        # Reset quota jika hari sudah berganti
        if current_user.last_quota_reset != today:
            current_user.analysis_quota_used = 0
            current_user.last_quota_reset = today
            
        if current_user.analysis_quota_used >= 3:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Batas harian analisis AI (3/hari) telah tercapai untuk akun free. Silakan upgrade ke premium."
            )
            
        # Increment quota
        current_user.analysis_quota_used += 1
        db.add(current_user)
        # Akan ter-commit bersamaan dengan run_ai_analysis
    # ---------------------------
        
    try:
        response = await run_ai_analysis(ticker_upper, db)
        return {
            "message": f"AI Analysis untuk {ticker_upper} selesai dijalankan.",
            "result": response
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memproses AI Analysis: {str(e)}"
        )

from app.worker.backtester import Backtester
from pydantic import BaseModel

class BacktestRequest(BaseModel):
    years: int = 3
    target_profit: float = 0.05
    stop_loss: float = 0.03

@router.post(
    "/{ticker}/backtest",
    summary="Jalankan backtesting untuk saham tertentu",
    description="Menjalankan simulasi trading berdasarkan sinyal teknikal (Wyckoff & SMC) menggunakan data historis.",
)
@limiter.limit("10/hour")
async def run_backtest(
    request: Request,
    ticker: str,
    params: BacktestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """Endpoint untuk menjalankan backtesting strategi."""
    # Khusus premium atau free dengan kuota tertentu, tapi untuk sekarang kita samakan ratelimit
    
    backtester = Backtester(ticker, params.years, params.target_profit, params.stop_loss)
    success = await backtester._fetch_and_prepare_data()
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data untuk {ticker} tidak ditemukan atau gagal diambil."
        )
        
    backtester.run_simulation()
    result = backtester.get_results_dict()
    
    return result
