"""
AI Stock Analyzer - Stocks Router
Menyediakan endpoint untuk daftar saham, data chart OHLCV, dan watchlist.

Endpoints:
- GET  /stocks                        - Daftar semua saham yang didukung
- GET  /stocks/{ticker}/chart         - Data harga historis OHLCV
- GET  /stocks/{ticker}/analysis/latest - Hasil analisis AI terbaru
- POST /stocks/watchlist              - Tambah saham ke watchlist
- GET  /stocks/watchlist              - Daftar watchlist pengguna
- DELETE /stocks/watchlist/{ticker}   - Hapus saham dari watchlist
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request, Response
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_active_user
from app.core.rate_limiter import limiter
from app.domain.models.models import (
    Stock, DailyPrice, TechnicalIndicator, AIAnalysis, Watchlist, User
)
from app.domain.schemas.stocks import (
    StockResponse,
    DailyPriceResponse,
    StockAnalysisLatestResponse,
    WatchlistAddRequest,
    WatchlistResponse,
    PaginatedResponse,
    PaginationMeta,
)
import pandas as pd
from app.infrastructure.market_data import fetch_stock_history_async, fetch_stock_info_async
from app.services.indicator_engine import calculate_indicators, detect_vpa_signals
from app.services.pattern_engine import detect_double_bottom, detect_swing_points
from app.services.wyckoff_engine import detect_wyckoff_accumulation
from app.services.smc_engine import detect_fvg, detect_structure_breaks
import math

router = APIRouter(prefix="/stocks", tags=["Stocks"])


@router.get(
    "",
    response_model=PaginatedResponse[StockResponse],
    summary="Dapatkan daftar saham yang didukung",
    description="Mengembalikan semua emiten saham yang aktif di database.",
)
async def list_stocks(
    response: Response,
    page: int = Query(1, ge=1, description="Nomor halaman"),
    per_page: int = Query(20, ge=1, le=100, description="Jumlah item per halaman"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[StockResponse]:
    """Ambil semua saham aktif dari database dengan pagination."""
    # Count total
    count_stmt = select(func.count()).select_from(Stock).where(Stock.is_active == True)
    total = await db.scalar(count_stmt)
    
    # Get paginated data
    offset = (page - 1) * per_page
    stmt = select(Stock).where(Stock.is_active == True).order_by(Stock.ticker).offset(offset).limit(per_page)
    result = await db.execute(stmt)
    stocks = result.scalars().all()
    
    response.headers["X-Total-Count"] = str(total)
    
    return PaginatedResponse(
        data=[StockResponse.model_validate(s) for s in stocks],
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=math.ceil(total / per_page) if total > 0 else 1
        )
    )


@router.post(
    "/{ticker}/sync",
    status_code=status.HTTP_200_OK,
    summary="Sinkronisasi data historis dan indikator (Manual/Admin)",
    description="Mengambil data dari yfinance, menghitung VPA & indikator teknikal, lalu menyimpannya ke database.",
)
@limiter.limit("20/hour")
async def sync_stock_data(
    request: Request,
    ticker: str,
    db: AsyncSession = Depends(get_db),
    # _: User = Depends(get_current_active_user), # Uncomment to secure
):
    """Sinkronisasi data saham manual via API."""
    return await do_sync_stock(ticker, db)

async def do_sync_stock(ticker: str, db: AsyncSession):
    """Core logic for syncing stock data, safe to call from background tasks."""
    ticker_upper = ticker.upper()
    
    # 1. Pastikan stock ada di master
    stock_result = await db.execute(select(Stock).where(Stock.ticker == ticker_upper))
    stock = stock_result.scalar_one_or_none()
    
    if not stock:
        # Auto create stock jika belum ada
        info = await fetch_stock_info_async(ticker_upper)
        company_name = info.get("longName") or info.get("shortName") or ticker_upper
        stock = Stock(
            ticker=ticker_upper,
            company_name=company_name,
            sector=info.get("sector"),
            exchange=info.get("exchange")
        )
        db.add(stock)
        await db.commit()
        await db.refresh(stock)

    # 2. Fetch History Data
    df = await fetch_stock_history_async(ticker_upper, period="1y")
    if df.empty:
        raise HTTPException(status_code=404, detail="Data riwayat tidak ditemukan di yfinance.")

    # 3. Calculate Indicators
    df = calculate_indicators(df)
    df = detect_vpa_signals(df)
    
    # 4. Detect patterns (Classic, Wyckoff, SMC)
    df = detect_swing_points(df, window=5)
    double_bottoms = detect_double_bottom(df)
    df = detect_wyckoff_accumulation(df)
    df = detect_fvg(df)
    df = detect_structure_breaks(df)

    def clean_val(val):
        return None if pd.isna(val) else val

    # 4. Save to Database (DailyPrices and TechnicalIndicators)
    try:
        from sqlalchemy import delete
        await db.execute(delete(TechnicalIndicator).where(TechnicalIndicator.stock_ticker == ticker_upper))
        await db.execute(delete(DailyPrice).where(DailyPrice.stock_ticker == ticker_upper))
        
        prices_to_insert = []
        indicators_to_insert = []
        
        for _, row in df.iterrows():
            dp = DailyPrice(
                stock_ticker=ticker_upper,
                trading_date=row['trading_date'],
                open=clean_val(row['open']),
                high=clean_val(row['high']),
                low=clean_val(row['low']),
                close=clean_val(row['close']),
                volume=clean_val(row['volume'])
            )
            prices_to_insert.append(dp)
            
            ti = TechnicalIndicator(
                stock_ticker=ticker_upper,
                trading_date=row['trading_date'],
                rsi_14=clean_val(row.get('rsi_14')),
                ema_20=clean_val(row.get('ema_20')),
                ema_50=clean_val(row.get('ema_50')),
                ema_200=clean_val(row.get('ema_200')),
                macd=clean_val(row.get('macd')),
                macd_signal=clean_val(row.get('macd_signal')),
                vwap=clean_val(row.get('vwap')),
                atr_14=clean_val(row.get('atr_14')),
                obv=clean_val(row.get('obv')),
                stopping_volume=bool(clean_val(row.get('stopping_volume')) or False),
                no_demand=bool(clean_val(row.get('no_demand')) or False),
                climactic_volume=bool(clean_val(row.get('climactic_volume')) or False),
                is_spring=bool(clean_val(row.get('is_spring')) or False),
                wyckoff_phase=clean_val(row.get('wyckoff_phase')),
                smc_patterns={
                    "bullish_fvg": bool(clean_val(row.get('bullish_fvg')) or False),
                    "bearish_fvg": bool(clean_val(row.get('bearish_fvg')) or False),
                    "fvg_size": float(clean_val(row.get('fvg_size')) or 0.0),
                    "bos": bool(clean_val(row.get('bos')) or False),
                    "choch": bool(clean_val(row.get('choch')) or False),
                    "swing_high": bool(clean_val(row.get('swing_high')) or False),
                    "swing_low": bool(clean_val(row.get('swing_low')) or False)
                }
            )
            indicators_to_insert.append(ti)
            
        db.add_all(prices_to_insert)
        db.add_all(indicators_to_insert)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database transaction failed: {str(e)}")
    
    return {
        "message": f"Sinkronisasi berhasil untuk {ticker_upper}",
        "total_days_synced": len(df),
        "patterns_detected": {
            "double_bottoms": len(double_bottoms)
        }
    }


from fastapi_cache.decorator import cache

@router.get(
    "/{ticker}/chart",
    response_model=PaginatedResponse[DailyPriceResponse],
    summary="Dapatkan data harga historis OHLCV",
    description="Mengembalikan data time-series harga untuk charting, dilengkapi pagination.",
)
@cache(expire=3600)  # Cache 1 jam
async def get_stock_chart(
    ticker: str,
    response: Response,
    page: int = Query(1, ge=1, description="Nomor halaman"),
    per_page: int = Query(100, ge=1, le=1825, description="Jumlah data per halaman"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[DailyPriceResponse]:
    """Ambil data harga OHLCV historis untuk saham tertentu."""
    # Cek apakah saham ada
    stock_result = await db.execute(select(Stock).where(Stock.ticker == ticker.upper()))
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saham dengan ticker '{ticker}' tidak ditemukan.",
        )

    # Count total prices for this ticker
    count_stmt = select(func.count()).select_from(DailyPrice).where(DailyPrice.stock_ticker == ticker.upper())
    total = await db.scalar(count_stmt)

    # Ambil data harga sesuai pagination, diurutkan desc lalu direverse
    offset = (page - 1) * per_page
    prices_result = await db.execute(
        select(DailyPrice)
        .where(DailyPrice.stock_ticker == ticker.upper())
        .order_by(desc(DailyPrice.trading_date))
        .offset(offset)
        .limit(per_page)
    )
    prices = prices_result.scalars().all()
    
    response.headers["X-Total-Count"] = str(total)

    # Kembalikan dalam urutan kronologis (ascending) untuk chart
    return PaginatedResponse(
        data=[DailyPriceResponse.model_validate(p) for p in reversed(prices)],
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=math.ceil(total / per_page) if total > 0 else 1
        )
    )


@router.get(
    "/{ticker}/analysis/latest",
    response_model=StockAnalysisLatestResponse,
    summary="Dapatkan hasil analisis AI terbaru",
    description="Mengembalikan analisis VPA/Wyckoff dan rekomendasi AI terkini untuk sebuah saham.",
)
@cache(expire=86400) # Cache 24 jam
async def get_latest_analysis(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),  # Endpoint ini butuh autentikasi
) -> StockAnalysisLatestResponse:
    """Ambil analisis AI terbaru untuk saham tertentu."""
    ticker_upper = ticker.upper()

    # Cek apakah saham ada
    stock_result = await db.execute(
        select(Stock).where(Stock.ticker == ticker_upper)
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saham dengan ticker '{ticker}' tidak ditemukan.",
        )

    # Ambil harga terbaru
    latest_price_result = await db.execute(
        select(DailyPrice)
        .where(DailyPrice.stock_ticker == ticker_upper)
        .order_by(desc(DailyPrice.trading_date))
        .limit(1)
    )
    latest_price = latest_price_result.scalar_one_or_none()

    # Ambil indikator teknikal terbaru
    latest_indicator_result = await db.execute(
        select(TechnicalIndicator)
        .where(TechnicalIndicator.stock_ticker == ticker_upper)
        .order_by(desc(TechnicalIndicator.trading_date))
        .limit(1)
    )
    latest_indicator = latest_indicator_result.scalar_one_or_none()

    # Ambil analisis AI terbaru
    latest_analysis_result = await db.execute(
        select(AIAnalysis)
        .where(AIAnalysis.stock_ticker == ticker_upper)
        .order_by(desc(AIAnalysis.analysis_date))
        .limit(1)
    )
    latest_analysis = latest_analysis_result.scalar_one_or_none()

    from app.domain.schemas.stocks import TechnicalIndicatorResponse
    return StockAnalysisLatestResponse(
        ticker=stock.ticker,
        company_name=stock.company_name,
        current_price=latest_price.close if latest_price else None,
        analysis_date=latest_analysis.analysis_date if latest_analysis else None,
        wyckoff_phase=latest_indicator.wyckoff_phase if latest_indicator else None,
        ai_recommendation=latest_analysis.recommendation if latest_analysis else None,
        confidence_score=latest_analysis.confidence_score if latest_analysis else None,
        ai_summary=latest_analysis.ai_summary if latest_analysis else None,
        vpa_insight=latest_analysis.vpa_insight if latest_analysis else None,
        technical_indicators=TechnicalIndicatorResponse.model_validate(latest_indicator) if latest_indicator else None,
    )


@router.get(
    "/watchlist",
    response_model=list[WatchlistResponse],
    summary="Dapatkan daftar watchlist pengguna",
    description="Mengembalikan semua saham yang dipantau oleh pengguna yang sedang login.",
)
async def get_watchlist(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[WatchlistResponse]:
    """Ambil semua item watchlist milik pengguna yang sedang login."""
    result = await db.execute(
        select(Watchlist, Stock.company_name)
        .join(Stock, Watchlist.stock_ticker == Stock.ticker)
        .where(Watchlist.user_id == current_user.id)
        .order_by(desc(Watchlist.added_at))
    )
    rows = result.all()

    return [
        WatchlistResponse(
            id=w.id,
            stock_ticker=w.stock_ticker,
            company_name=company_name,
            notes=w.notes,
            added_at=w.added_at,
        )
        for w, company_name in rows
    ]


@router.post(
    "/watchlist",
    response_model=WatchlistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tambah saham ke watchlist",
    description="Menambahkan emiten saham ke daftar pantau pengguna yang sedang login.",
)
async def add_to_watchlist(
    request: WatchlistAddRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> WatchlistResponse:
    """Tambah saham ke watchlist pengguna."""
    ticker_upper = request.ticker.upper()

    # Cek apakah saham ada
    stock_result = await db.execute(select(Stock).where(Stock.ticker == ticker_upper))
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saham '{ticker_upper}' tidak ditemukan.",
        )

    # Cek duplikasi
    existing_result = await db.execute(
        select(Watchlist).where(
            Watchlist.user_id == current_user.id,
            Watchlist.stock_ticker == ticker_upper
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Saham '{ticker_upper}' sudah ada di watchlist Anda.",
        )

    # Tambah ke watchlist
    new_item = Watchlist(
        user_id=current_user.id,
        stock_ticker=ticker_upper,
        notes=request.notes,
    )
    db.add(new_item)
    await db.flush()
    await db.refresh(new_item)

    return WatchlistResponse(
        id=new_item.id,
        stock_ticker=new_item.stock_ticker,
        company_name=stock.company_name,
        notes=new_item.notes,
        added_at=new_item.added_at,
    )


@router.delete(
    "/watchlist/{ticker}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus saham dari watchlist",
    description="Menghapus emiten saham dari daftar pantau pengguna yang sedang login.",
)
async def remove_from_watchlist(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Hapus saham dari watchlist pengguna."""
    ticker_upper = ticker.upper()

    result = await db.execute(
        select(Watchlist).where(
            Watchlist.user_id == current_user.id,
            Watchlist.stock_ticker == ticker_upper
        )
    )
    watchlist_item = result.scalar_one_or_none()

    if not watchlist_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saham '{ticker_upper}' tidak ada di watchlist Anda.",
        )

    await db.delete(watchlist_item)
