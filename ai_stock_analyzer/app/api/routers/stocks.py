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

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_active_user
from app.domain.models.models import (
    Stock, DailyPrice, TechnicalIndicator, AIAnalysis, Watchlist, User
)
from app.domain.schemas.stocks import (
    StockResponse,
    DailyPriceResponse,
    StockAnalysisLatestResponse,
    WatchlistAddRequest,
    WatchlistResponse,
)
import pandas as pd
from app.infrastructure.market_data import fetch_stock_history_async, fetch_stock_info_async
from app.services.indicator_engine import calculate_indicators, detect_vpa_signals
from app.services.pattern_engine import detect_double_bottom, detect_swing_points
from app.services.wyckoff_engine import detect_wyckoff_accumulation
from app.services.smc_engine import detect_fvg, detect_structure_breaks

router = APIRouter(prefix="/stocks", tags=["Stocks"])


@router.get(
    "",
    response_model=list[StockResponse],
    summary="Dapatkan daftar saham yang didukung",
    description="Mengembalikan semua emiten saham yang aktif di database.",
)
async def list_stocks(
    db: AsyncSession = Depends(get_db),
) -> list[StockResponse]:
    """Ambil semua saham aktif dari database."""
    result = await db.execute(
        select(Stock).where(Stock.is_active == True).order_by(Stock.ticker)
    )
    stocks = result.scalars().all()
    return [StockResponse.model_validate(s) for s in stocks]


@router.post(
    "/{ticker}/sync",
    status_code=status.HTTP_200_OK,
    summary="Sinkronisasi data historis dan indikator (Manual/Admin)",
    description="Mengambil data dari yfinance, menghitung VPA & indikator teknikal, lalu menyimpannya ke database.",
)
async def sync_stock_data(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    # _: User = Depends(get_current_active_user), # Uncomment to secure
):
    """Sinkronisasi data saham manual."""
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
    
    return {
        "message": f"Sinkronisasi berhasil untuk {ticker_upper}",
        "total_days_synced": len(df),
        "patterns_detected": {
            "double_bottoms": len(double_bottoms)
        }
    }


@router.get(
    "/{ticker}/chart",
    response_model=list[DailyPriceResponse],
    summary="Dapatkan data harga historis OHLCV",
    description="Mengembalikan data time-series harga untuk charting.",
)
async def get_stock_chart(
    ticker: str,
    days: int = Query(default=100, ge=1, le=1825, description="Jumlah hari ke belakang (max 5 tahun)"),
    db: AsyncSession = Depends(get_db),
) -> list[DailyPriceResponse]:
    """Ambil data harga OHLCV historis untuk saham tertentu."""
    # Cek apakah saham ada
    stock_result = await db.execute(select(Stock).where(Stock.ticker == ticker.upper()))
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saham dengan ticker '{ticker}' tidak ditemukan.",
        )

    # Ambil data harga terbaru sejumlah 'days'
    prices_result = await db.execute(
        select(DailyPrice)
        .where(DailyPrice.stock_ticker == ticker.upper())
        .order_by(desc(DailyPrice.trading_date))
        .limit(days)
    )
    prices = prices_result.scalars().all()

    # Kembalikan dalam urutan kronologis (ascending)
    return [DailyPriceResponse.model_validate(p) for p in reversed(prices)]


@router.get(
    "/{ticker}/analysis/latest",
    response_model=StockAnalysisLatestResponse,
    summary="Dapatkan hasil analisis AI terbaru",
    description="Mengembalikan analisis VPA/Wyckoff dan rekomendasi AI terkini untuk sebuah saham.",
)
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
