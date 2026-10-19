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

import asyncio
import math
import re

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user, get_db
from app.core.config import settings
from app.core.errors import api_error
from app.core.rate_limiter import get_user_id_or_ip, limiter
from app.domain.models.models import (
    AIAnalysis,
    DailyPrice,
    Stock,
    TechnicalIndicator,
    User,
    Watchlist,
)
from app.domain.schemas.stocks import (
    DailyPriceResponse,
    PaginatedResponse,
    PaginationMeta,
    StockAnalysisLatestResponse,
    StockQuoteResponse,
    StockResponse,
    WatchlistAddRequest,
    WatchlistResponse,
    WatchlistUpdateRequest,
)
from app.infrastructure.market_data import (
    fetch_stock_history_async,
    fetch_stock_info_async,
    market_identity,
)
from app.services.indicator_engine import calculate_indicators, detect_vpa_signals
from app.services.market_metadata import as_utc, history_revision, metadata, utcnow
from app.services.pattern_engine import (
    detect_bull_flag,
    detect_confirmed_swings,
    detect_cup_and_handle,
    detect_double_bottom,
)
from app.services.smc_engine import (
    detect_fvg,
    detect_liquidity_sweep,
    detect_order_blocks,
    detect_structure_breaks,
)
from app.services.wyckoff_engine import detect_wyckoff_accumulation

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
    q: str | None = Query(None, description="Pencarian ticker atau nama perusahaan"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[StockResponse]:
    """Ambil semua saham aktif dari database dengan pagination."""
    # Build base condition
    condition = Stock.is_active.is_(True)
    if q:
        condition = condition & (Stock.ticker.ilike(f"%{q}%") | Stock.company_name.ilike(f"%{q}%"))

    # Count total
    count_stmt = select(func.count()).select_from(Stock).where(condition)
    total = await db.scalar(count_stmt)

    # Get paginated data
    offset = (page - 1) * per_page
    stmt = select(Stock).where(condition).order_by(Stock.ticker).offset(offset).limit(per_page)
    result = await db.execute(stmt)
    stocks = result.scalars().all()

    response.headers["X-Total-Count"] = str(total)

    return PaginatedResponse(
        data=[StockResponse.model_validate(s) for s in stocks],
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=math.ceil(total / per_page) if total > 0 else 1,
        ),
    )


@router.get("/recommendations", summary="Rekomendasi BUY dari seluruh saham aktif")
async def recommendations(
    db: AsyncSession = Depends(get_db), _: User = Depends(get_current_active_user)
):
    latest = (
        select(AIAnalysis.id)
        .where(
            AIAnalysis.stock_ticker == Stock.ticker,
            AIAnalysis.provenance == "real",
            AIAnalysis.data_revision == Stock.data_revision,
        )
        .order_by(AIAnalysis.generated_at.desc(), AIAnalysis.id)
        .limit(1)
        .correlate(Stock)
        .scalar_subquery()
    )
    rows = (
        await db.execute(
            select(Stock, AIAnalysis)
            .join(AIAnalysis, AIAnalysis.id == latest)
            .where(Stock.is_active.is_(True), AIAnalysis.recommendation == "BUY")
            .order_by(AIAnalysis.confidence_score.desc(), Stock.ticker)
            .limit(20)
        )
    ).all()
    return {
        "data": [
            {
                "ticker": s.ticker,
                "company_name": s.company_name,
                "recommendation": a.recommendation,
                "confidence_score": a.confidence_score,
                "analysis_date": a.analysis_date,
                "generated_at": a.generated_at,
            }
            for s, a in rows
        ],
        "ranking": "Skor model tertinggi; bukan probabilitas keuntungan",
    }


@router.get(
    "/{ticker}/price",
    response_model=StockQuoteResponse,
    summary="Harga penutupan harian terakhir yang tersimpan",
)
async def get_realtime_price(ticker: str, db: AsyncSession = Depends(get_db)):
    stock = await db.get(Stock, ticker.upper())
    if not stock:
        raise HTTPException(status_code=404, detail="Saham tidak ditemukan.")
    prices = (
        (
            await db.execute(
                select(DailyPrice)
                .where(DailyPrice.stock_ticker == stock.ticker)
                .order_by(DailyPrice.trading_date.desc())
                .limit(2)
            )
        )
        .scalars()
        .all()
    )
    price = float(prices[0].close) if prices else None
    previous = float(prices[1].close) if len(prices) > 1 else None
    change = price - previous if price is not None and previous is not None else None
    return {
        "ticker": stock.ticker,
        "company_name": stock.company_name,
        "current_price": price,
        "previous_close": previous,
        "change": change,
        "change_percent": change / previous * 100 if change is not None and previous else None,
        "metadata": metadata(stock, prices[0].trading_date if prices else None),
    }


@router.post(
    "/{ticker}/sync",
    status_code=status.HTTP_200_OK,
    summary="Sinkronisasi data historis dan indikator (Manual/Admin)",
    description="Mengambil data dari yfinance, menghitung VPA & indikator teknikal, lalu menyimpannya ke database.",
)
@limiter.limit("20/hour", key_func=get_user_id_or_ip)
async def sync_stock_data(
    request: Request,
    ticker: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Sinkronisasi data saham manual via API."""
    try:
        return await asyncio.wait_for(do_sync_stock(ticker, db), timeout=90)
    except TimeoutError as exc:
        await db.rollback()
        raise api_error(
            "MARKET_TIMEOUT",
            "Sinkronisasi melewati batas waktu; data terakhir dipertahankan.",
            status=504,
            stage="syncing",
            retryable=True,
        ) from exc


async def do_sync_stock(ticker: str, db: AsyncSession, *, progress=None):
    """Core logic for syncing stock data, safe to call from background tasks."""
    ticker_upper = ticker.upper()

    if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.^^=\-]{0,19}", ticker_upper):
        raise HTTPException(status_code=422, detail="Kode saham tidak valid.")
    stock = await db.get(Stock, ticker_upper)
    try:
        df = await fetch_stock_history_async(ticker_upper, period="5y")
    except Exception as exc:
        raise api_error(
            "MARKET_UNAVAILABLE",
            "Sumber data pasar gagal dihubungi; data terakhir dipertahankan.",
            status=503,
            stage="syncing",
            retryable=True,
        ) from exc
    required = ["open", "high", "low", "close", "volume"]
    if df.empty or not set(["trading_date"] + required).issubset(df.columns):
        raise api_error(
            "MARKET_UNAVAILABLE",
            "Histori belum tersedia dari provider; data terakhir dipertahankan.",
            status=503,
            stage="syncing",
            retryable=True,
        )
    if (
        not np.isfinite(df[required].to_numpy(dtype=float)).all()
        or (df[["open", "high", "low", "close"]] <= 0).any().any()
        or (df["volume"] < 0).any()
        or (df["low"] > df[["open", "close"]].min(axis=1)).any()
        or (df["high"] < df[["open", "close"]].max(axis=1)).any()
        or df["trading_date"].duplicated().any()
    ):
        raise api_error(
            "MARKET_INVALID_DATA",
            "Histori provider tidak valid; data terakhir dipertahankan.",
            status=502,
            stage="syncing",
        )
    df = df.sort_values("trading_date").reset_index(drop=True)
    provenance = {
        "source": market_identity(),
        "price_adjustment": df.attrs.get("price_adjustment", "unknown"),
        "volume_adjustment": df.attrs.get("volume_adjustment", "unknown"),
    }
    revision = history_revision(df, provenance)
    try:
        info = (
            await fetch_stock_info_async(ticker_upper)
            if not stock or not stock.currency or stock.company_name == ticker_upper
            else {}
        )
    except Exception:
        info = {}  # A profile failure must not discard valid prices or invent a company name.
    if progress:
        await progress("calculating")
    if not stock:
        stock = Stock(
            ticker=ticker_upper,
            company_name=info.get("longName") or info.get("shortName") or ticker_upper,
            sector=info.get("sector"),
            exchange=info.get("exchange"),
        )
        db.add(stock)
    currency = info.get("currency")
    if isinstance(currency, str) and re.fullmatch(r"[A-Z]{3}", currency):
        stock.currency = currency
    if info.get("longName") or info.get("shortName"):
        stock.company_name = info.get("longName") or info["shortName"]
    if info.get("exchange"):
        stock.exchange = info["exchange"]
    stock.market_source = provenance["source"]
    stock.price_adjustment = provenance["price_adjustment"]
    stock.volume_adjustment = provenance["volume_adjustment"]
    stock.publication_delay_minutes = settings.EOD_PUBLICATION_DELAY_MINUTES
    stock.data_revision = revision
    stock.data_fetched_at = utcnow()
    await db.flush()

    # 3. Calculate Indicators
    df = calculate_indicators(df)
    df = detect_vpa_signals(df)

    # 4. Detect patterns (Classic, Wyckoff, SMC)
    df = detect_confirmed_swings(df, window=5)
    double_bottoms = detect_double_bottom(df)
    cup_and_handles = detect_cup_and_handle(df)
    bull_flags = detect_bull_flag(df)

    # Tandai di dataframe jika pattern selesai pada hari tersebut
    df["has_cup_and_handle"] = False
    for p in cup_and_handles:
        df.loc[df.index == p["handle_end_date"], "has_cup_and_handle"] = True

    df["has_bull_flag"] = False
    for p in bull_flags:
        df.loc[df.index == p["flag_end"], "has_bull_flag"] = True

    df = detect_liquidity_sweep(df)
    df = detect_wyckoff_accumulation(df)
    df = detect_fvg(df)
    df = detect_structure_breaks(df)
    df = detect_order_blocks(df)

    def clean_val(val):
        return None if pd.isna(val) else val

    # 4. Save to Database (DailyPrices and TechnicalIndicators)
    try:
        from sqlalchemy import delete

        await db.execute(
            delete(TechnicalIndicator).where(TechnicalIndicator.stock_ticker == ticker_upper)
        )
        await db.execute(delete(DailyPrice).where(DailyPrice.stock_ticker == ticker_upper))

        prices_to_insert = []
        indicators_to_insert = []

        for _, row in df.iterrows():
            dp = DailyPrice(
                stock_ticker=ticker_upper,
                trading_date=row["trading_date"],
                open=clean_val(row["open"]),
                high=clean_val(row["high"]),
                low=clean_val(row["low"]),
                close=clean_val(row["close"]),
                volume=int(row["volume"]),
            )
            prices_to_insert.append(dp)

            ti = TechnicalIndicator(
                stock_ticker=ticker_upper,
                trading_date=row["trading_date"],
                rsi_14=clean_val(row.get("rsi_14")),
                ema_20=clean_val(row.get("ema_20")),
                ema_50=clean_val(row.get("ema_50")),
                ema_200=clean_val(row.get("ema_200")),
                macd=clean_val(row.get("macd")),
                macd_signal=clean_val(row.get("macd_signal")),
                vwap=clean_val(row.get("vwap")),
                atr_14=clean_val(row.get("atr_14")),
                obv=int(row["obv"]) if clean_val(row.get("obv")) is not None else None,
                stopping_volume=bool(clean_val(row.get("stopping_volume")) or False),
                no_demand=bool(clean_val(row.get("no_demand")) or False),
                climactic_volume=bool(clean_val(row.get("climactic_volume")) or False),
                is_spring=bool(clean_val(row.get("is_spring")) or False),
                wyckoff_phase=clean_val(row.get("wyckoff_phase")),
                smc_patterns={
                    "bullish_fvg": bool(clean_val(row.get("bullish_fvg")) or False),
                    "bearish_fvg": bool(clean_val(row.get("bearish_fvg")) or False),
                    "fvg_size": float(clean_val(row.get("fvg_size")) or 0.0),
                    "bos": bool(clean_val(row.get("bos")) or False),
                    "choch": bool(clean_val(row.get("choch")) or False),
                    "swing_high": bool(clean_val(row.get("swing_high")) or False),
                    "swing_low": bool(clean_val(row.get("swing_low")) or False),
                    "bullish_ob": bool(clean_val(row.get("bullish_ob")) or False),
                    "bearish_ob": bool(clean_val(row.get("bearish_ob")) or False),
                    "ob_high": float(clean_val(row.get("ob_high")) or 0.0),
                    "ob_low": float(clean_val(row.get("ob_low")) or 0.0),
                    "liq_sweep_low": bool(clean_val(row.get("liq_sweep_low")) or False),
                    "liq_sweep_high": bool(clean_val(row.get("liq_sweep_high")) or False),
                    "has_cup_and_handle": bool(clean_val(row.get("has_cup_and_handle")) or False),
                    "has_bull_flag": bool(clean_val(row.get("has_bull_flag")) or False),
                },
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
        "metadata": metadata(stock, df.iloc[-1]["trading_date"]),
        "patterns_detected": {
            "double_bottoms": len(double_bottoms),
            "cup_and_handles": len(cup_and_handles),
            "bull_flags": len(bull_flags),
        },
    }


@router.get(
    "/{ticker}/chart",
    response_model=PaginatedResponse[DailyPriceResponse],
    summary="Dapatkan data harga historis OHLCV",
    description="Mengembalikan data time-series harga untuk charting, dilengkapi pagination.",
)
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
    count_stmt = (
        select(func.count())
        .select_from(DailyPrice)
        .where(DailyPrice.stock_ticker == ticker.upper())
    )
    total = await db.scalar(count_stmt)

    # Ambil data harga sesuai pagination, diurutkan desc lalu direverse
    offset = (page - 1) * per_page
    price_columns = [
        DailyPrice.trading_date,
        DailyPrice.open,
        DailyPrice.high,
        DailyPrice.low,
        DailyPrice.close,
        DailyPrice.volume,
    ]
    indicator_names = ["ema_20", "ema_50", "ema_200", "rsi_14", "macd", "macd_signal"]
    signal_names = ["stopping_volume", "no_demand", "is_spring", "climactic_volume"]
    rows = (
        (
            await db.execute(
                select(
                    *price_columns,
                    *(getattr(TechnicalIndicator, key) for key in indicator_names),
                    *(
                        func.coalesce(getattr(TechnicalIndicator, key), False).label(key)
                        for key in signal_names
                    ),
                )
                .outerjoin(
                    TechnicalIndicator,
                    (DailyPrice.stock_ticker == TechnicalIndicator.stock_ticker)
                    & (DailyPrice.trading_date == TechnicalIndicator.trading_date),
                )
                .where(DailyPrice.stock_ticker == ticker.upper())
                .order_by(desc(DailyPrice.trading_date))
                .offset(offset)
                .limit(per_page)
            )
        )
        .mappings()
        .all()
    )
    # Validate once and serialize through Pydantic's JSON serializer. Returning
    # an already validated response avoids rebuilding thousands of ORM objects
    # and a second FastAPI validation pass for concurrent five-year charts.
    result = PaginatedResponse[DailyPriceResponse](
        data=[DailyPriceResponse(**row) for row in reversed(rows)],
        metadata=metadata(stock, rows[0]["trading_date"] if rows else None),
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=math.ceil(total / per_page) if total > 0 else 1,
        ),
    )
    return Response(
        content=result.model_dump_json(),
        media_type="application/json",
        headers={"X-Total-Count": str(total)},
    )


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
    stock_result = await db.execute(select(Stock).where(Stock.ticker == ticker_upper))
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
        .where(AIAnalysis.stock_ticker == ticker_upper, AIAnalysis.provenance == "real")
        .order_by(desc(AIAnalysis.generated_at))
        .limit(1)
    )
    latest_analysis = latest_analysis_result.scalar_one_or_none()

    from app.domain.schemas.stocks import TechnicalIndicatorResponse

    return StockAnalysisLatestResponse(
        ticker=stock.ticker,
        company_name=stock.company_name,
        analysis_id=latest_analysis.id if latest_analysis else None,
        current_price=latest_price.close if latest_price else None,
        metadata=metadata(stock, latest_price.trading_date if latest_price else None),
        generated_at=as_utc(latest_analysis.generated_at) if latest_analysis else None,
        model_name=latest_analysis.model_name if latest_analysis else None,
        provider_name=latest_analysis.provider_name if latest_analysis else None,
        actual_model_name=latest_analysis.actual_model_name if latest_analysis else None,
        prompt_version=latest_analysis.prompt_version if latest_analysis else None,
        provenance=latest_analysis.provenance if latest_analysis else None,
        analysis_matches_data=bool(
            latest_analysis
            and stock.data_revision
            and latest_analysis.data_revision == stock.data_revision
        ),
        supporting_factors=(latest_analysis.details or {}).get("supporting_factors", [])
        if latest_analysis
        else [],
        opposing_factors=(latest_analysis.details or {}).get("opposing_factors", [])
        if latest_analysis
        else [],
        limitations=(latest_analysis.details or {}).get("limitations") if latest_analysis else None,
        horizon=(latest_analysis.details or {}).get("horizon") if latest_analysis else None,
        analysis_date=latest_analysis.analysis_date if latest_analysis else None,
        wyckoff_phase=latest_indicator.wyckoff_phase if latest_indicator else None,
        ai_recommendation=latest_analysis.recommendation if latest_analysis else None,
        confidence_score=latest_analysis.confidence_score if latest_analysis else None,
        ai_summary=latest_analysis.ai_summary if latest_analysis else None,
        vpa_insight=latest_analysis.vpa_insight if latest_analysis else None,
        technical_indicators=TechnicalIndicatorResponse.model_validate(latest_indicator)
        if latest_indicator
        else None,
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
        select(Watchlist, Stock)
        .join(Stock, Watchlist.stock_ticker == Stock.ticker)
        .where(Watchlist.user_id == current_user.id)
        .order_by(desc(Watchlist.added_at))
    )
    rows = result.all()

    return [
        WatchlistResponse(
            id=w.id,
            stock_ticker=w.stock_ticker,
            company_name=stock.company_name,
            exchange=stock.exchange,
            currency=stock.currency,
            notes=w.notes,
            added_at=w.added_at,
        )
        for w, stock in rows
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

    # Serialize per-user inserts to prevent duplicates from concurrent clicks.
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(analysis_quota_used=User.analysis_quota_used)
        .execution_options(synchronize_session=False)
    )
    # Cek duplikasi
    existing_result = await db.execute(
        select(Watchlist).where(
            Watchlist.user_id == current_user.id, Watchlist.stock_ticker == ticker_upper
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
            Watchlist.user_id == current_user.id, Watchlist.stock_ticker == ticker_upper
        )
    )
    watchlist_item = result.scalar_one_or_none()

    if not watchlist_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saham '{ticker_upper}' tidak ada di watchlist Anda.",
        )

    await db.delete(watchlist_item)


@router.patch("/watchlist/{ticker}", response_model=WatchlistResponse)
async def update_watchlist_notes(
    ticker: str,
    payload: WatchlistUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    item = (
        await db.execute(
            select(Watchlist).where(
                Watchlist.user_id == user.id, Watchlist.stock_ticker == ticker.upper()
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item watchlist tidak ditemukan.")
    item.notes = payload.notes
    await db.commit()
    stock = await db.get(Stock, item.stock_ticker)
    return WatchlistResponse(
        id=item.id,
        stock_ticker=item.stock_ticker,
        company_name=stock.company_name,
        notes=item.notes,
        added_at=item.added_at,
    )
