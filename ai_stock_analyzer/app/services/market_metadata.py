"""Provenance is explicit; an unavailable exchange calendar is never guessed."""

import hashlib
from datetime import UTC, datetime

import pandas as pd


def history_revision(frame: pd.DataFrame) -> str:
    cols = ["trading_date", "open", "high", "low", "close", "volume"]
    data = frame[cols].sort_values("trading_date").copy()
    data["trading_date"] = pd.to_datetime(data["trading_date"]).dt.strftime("%Y-%m-%d")
    return hashlib.sha256(data.to_json(orient="records", double_precision=10).encode()).hexdigest()


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
        "data_state": "unknown" if market_date else "unavailable",
        "price_adjustment": "split_and_dividend_adjusted" if stock.market_source else "unknown",
    }


def utcnow():
    return datetime.now(UTC)


def as_utc(value):
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
