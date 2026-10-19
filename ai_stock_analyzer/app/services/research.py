"""Screen across the stored universe, with indicators aligned to each price session."""

import math

from sqlalchemy import and_, func, select

from app.domain.models.models import DailyPrice, Stock, TechnicalIndicator
from app.services.market_metadata import metadata


async def screen(db, criteria, page=1, per_page=20):
    # Probe each stock's ordered composite index instead of aggregating the
    # entire multi-year price table for every filter/count/page request.
    latest_day = (
        select(DailyPrice.trading_date)
        .where(DailyPrice.stock_ticker == Stock.ticker)
        .order_by(DailyPrice.trading_date.desc())
        .limit(1)
        .correlate(Stock)
        .scalar_subquery()
    )
    query = (
        select(Stock, DailyPrice, TechnicalIndicator)
        .outerjoin(
            DailyPrice,
            and_(DailyPrice.stock_ticker == Stock.ticker, DailyPrice.trading_date == latest_day),
        )
        .outerjoin(
            TechnicalIndicator,
            and_(
                TechnicalIndicator.stock_ticker == Stock.ticker,
                TechnicalIndicator.trading_date == DailyPrice.trading_date,
            ),
        )
        .where(Stock.is_active.is_(True))
    )
    valid = and_(
        DailyPrice.id.is_not(None),
        TechnicalIndicator.id.is_not(None),
        Stock.data_revision.is_not(None),
        Stock.market_source.is_not(None),
    )
    universe = await db.scalar(
        select(func.count()).select_from(Stock).where(Stock.is_active.is_(True))
    )
    covered = await db.scalar(select(func.count()).select_from(query.where(valid).subquery()))
    if criteria.exchange:
        query = query.where(func.upper(Stock.exchange) == criteria.exchange.upper())
    if criteria.sector:
        query = query.where(func.lower(Stock.sector) == criteria.sector.lower())
    query = query.where(~valid if criteria.missing_only else valid)
    if criteria.min_volume is not None:
        query = query.where(DailyPrice.volume >= criteria.min_volume)
    if criteria.rsi_min is not None:
        query = query.where(TechnicalIndicator.rsi_14 >= criteria.rsi_min)
    if criteria.rsi_max is not None:
        query = query.where(TechnicalIndicator.rsi_14 <= criteria.rsi_max)
    if criteria.wyckoff_phase:
        query = query.where(TechnicalIndicator.wyckoff_phase == criteria.wyckoff_phase)
    if criteria.smc:
        query = query.where(TechnicalIndicator.smc_patterns[criteria.smc].as_boolean().is_(True))
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    column = {
        "ticker": Stock.ticker,
        "volume": DailyPrice.volume,
        "rsi": TechnicalIndicator.rsi_14,
    }[criteria.sort]
    query = query.order_by(
        (column.desc() if criteria.descending else column.asc()).nulls_last(), Stock.ticker
    )
    rows = (await db.execute(query.offset((page - 1) * per_page).limit(per_page))).all()
    data = []
    for stock, price, tech in rows:
        data.append(
            {
                "ticker": stock.ticker,
                "company_name": stock.company_name,
                "sector": stock.sector,
                "exchange": stock.exchange,
                "currency": stock.currency,
                "close": float(price.close) if price else None,
                "volume": price.volume if price else None,
                "rsi": float(tech.rsi_14) if tech and tech.rsi_14 is not None else None,
                "wyckoff_phase": tech.wyckoff_phase if tech else None,
                "smc_patterns": tech.smc_patterns if tech else None,
                "metadata": metadata(stock, price.trading_date if price else None),
            }
        )
    return {
        "data": data,
        "criteria": criteria.model_dump(),
        "coverage": {
            "registered_active": universe,
            "with_aligned_data": covered,
            "scope": "Instrumen aktif tersimpan; tidak menyatakan seluruh bursa.",
        },
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": math.ceil(total / per_page),
        },
    }
