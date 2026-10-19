"""Provenance is explicit; an unavailable exchange calendar is never guessed."""

import hashlib
import json
from datetime import UTC, datetime
from functools import lru_cache

import pandas as pd

from app.core.config import settings


def history_revision(frame: pd.DataFrame, provenance: dict | None = None) -> str:
    cols = ["trading_date", "open", "high", "low", "close", "volume"]
    data = frame[cols].sort_values("trading_date").copy()
    data["trading_date"] = pd.to_datetime(data["trading_date"]).dt.strftime("%Y-%m-%d")
    payload = data.to_json(orient="records", double_precision=10) + json.dumps(
        provenance or {}, sort_keys=True
    )
    return hashlib.sha256(payload.encode()).hexdigest()


@lru_cache(maxsize=8)
def exchange_calendar(name, year):
    import exchange_calendars as xc

    return xc.get_calendar(name, start=f"{year - 2}-01-01", end=f"{year + 1}-12-31")


def session_status(stock, market_date, now=None):
    result = {
        "data_state": "unknown" if market_date else "unavailable",
        "market_status": "unknown",
        "session_timezone": None,
        "expected_market_date": None,
    }
    aliases = {
        "IDX": ("XIDX", "Asia/Jakarta"),
        "JK": ("XIDX", "Asia/Jakarta"),
        "JKT": ("XIDX", "Asia/Jakarta"),
        "NYSE": ("XNYS", "America/New_York"),
        "NASDAQ": ("XNYS", "America/New_York"),
        "NYQ": ("XNYS", "America/New_York"),
        "NMS": ("XNYS", "America/New_York"),
        "US": ("XNYS", "America/New_York"),
    }
    exchange = aliases.get((stock.exchange or "").upper())
    if not exchange:
        return result
    result["session_timezone"] = exchange[1]
    delay = stock.publication_delay_minutes
    if not settings.MARKET_CALENDAR_VERIFIED or delay is None or delay < 0:
        return result
    now = pd.Timestamp(now or utcnow())
    try:
        cal = exchange_calendar(exchange[0], now.year)
        schedule = cal.schedule.loc[
            (now - pd.Timedelta(days=30)).date().isoformat() : now.date().isoformat()
        ]
        mature = schedule[schedule["close"] + pd.Timedelta(minutes=delay) <= now]
        if mature.empty:
            return result
        expected = mature.index[-1].date()
        result.update(
            expected_market_date=expected.isoformat(),
            market_status="open" if cal.is_open_on_minute(now.floor("min")) else "closed",
        )
        if market_date:
            result["data_state"] = (
                "fresh"
                if market_date == expected
                else "stale"
                if market_date < expected
                else "unknown"
            )
        return result
    except (ValueError, KeyError, IndexError):
        return result


def metadata(stock, market_date=None) -> dict:
    # Calendar-aware freshness is unknown until a verified exchange calendar is configured.
    return {
        "source": stock.market_source,
        "currency": stock.currency,
        "exchange": stock.exchange,
        "interval": "1d",
        "market_as_of": market_date.isoformat() if market_date else None,
        "fetched_at": as_utc(stock.data_fetched_at),
        "data_revision": stock.data_revision,
        **session_status(stock, market_date),
        "publication_delay_minutes": stock.publication_delay_minutes,
        "calendar_verified": settings.MARKET_CALENDAR_VERIFIED,
        "price_adjustment": stock.price_adjustment or "unknown",
        "volume_adjustment": stock.volume_adjustment or "unknown",
    }


def utcnow():
    return datetime.now(UTC)


def as_utc(value):
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
