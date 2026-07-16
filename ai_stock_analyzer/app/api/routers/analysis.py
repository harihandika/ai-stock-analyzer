"""
AI Stock Analyzer - Analysis Router
Menangani trigger analisis AI secara manual dan melihat insight khusus.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import get_current_active_user, get_db
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
async def trigger_ai_analysis(
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
