import json
from datetime import UTC, date, datetime

import httpx
import pandas as pd
import pytest

from app.core.config import settings
from app.core.errors import AnalysisError
from app.domain.models.models import Stock
from app.infrastructure.ai_client import call_analysis_model
from app.infrastructure.market_data import fetch_stock_history_async
from app.services.market_metadata import history_revision, session_status
from tests.support import MODEL_RESPONSE


def transport(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )


@pytest.mark.asyncio
async def test_gemini_schema_usage_and_actual_model(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")

    def handler(request):
        assert request.headers["x-goog-api-key"] == "test-key"
        assert "test-key" not in str(request.url)
        body = json.loads(request.content)
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        assert "recommendation" in body["generationConfig"]["responseJsonSchema"]["required"]
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {"parts": [{"text": json.dumps(MODEL_RESPONSE)}]},
                    }
                ],
                "usageMetadata": {"totalTokenCount": 123},
                "modelVersion": "pinned-model-version",
            },
        )

    transport(monkeypatch, handler)
    result = await call_analysis_model("system", "technical data")
    assert result["confidence_score"] == 0.88
    assert result["tokens_used"] == 123
    assert result["_model_name"] == "pinned-model-version"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,body,code",
    [
        (429, {}, "AI_RATE_LIMITED"),
        (200, {"candidates": [{"finishReason": "MAX_TOKENS"}]}, "AI_INVALID_RESPONSE"),
        (200, {"candidates": []}, "AI_INVALID_RESPONSE"),
        (
            200,
            {
                "candidates": [
                    {"finishReason": "STOP", "content": {"parts": [{"text": "not JSON"}]}}
                ]
            },
            "AI_INVALID_RESPONSE",
        ),
    ],
)
async def test_gemini_refusals_truncation_and_rate_limit_are_errors(
    monkeypatch, status, body, code
):
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    transport(monkeypatch, lambda request: httpx.Response(status, json=body))
    with pytest.raises(AnalysisError) as raised:
        await call_analysis_model("system", "data")
    assert raised.value.code == code


@pytest.mark.asyncio
async def test_eodhd_adjusts_each_ohlc_row_and_keeps_provider_split_volume(monkeypatch):
    monkeypatch.setattr(settings, "MARKET_DATA_PROVIDER", "eodhd")
    monkeypatch.setattr(settings, "EODHD_API_KEY", "test-key")

    def handler(request):
        assert request.url.path == "/api/eod/BBCA.JK"
        assert request.url.params["period"] == "d"
        return httpx.Response(
            200,
            json=[
                {
                    "date": "2025-01-02",
                    "open": 98,
                    "high": 102,
                    "low": 90,
                    "close": 100,
                    "adjusted_close": 50,
                    "volume": 2000,
                },
                {
                    "date": "2025-01-03",
                    "open": 50,
                    "high": 52,
                    "low": 48,
                    "close": 51,
                    "adjusted_close": 51,
                    "volume": 3000,
                },
            ],
        )

    transport(monkeypatch, handler)
    frame = await fetch_stock_history_async("BBCA.JK", "1y")
    assert list(frame["open"]) == [49, 50]
    assert list(frame["close"]) == [50, 51]
    assert list(frame["volume"]) == [2000, 3000]
    assert frame.attrs["volume_adjustment"] == "split_adjusted"


@pytest.mark.asyncio
async def test_eodhd_key_missing_and_empty_are_explicit(monkeypatch):
    monkeypatch.setattr(settings, "MARKET_DATA_PROVIDER", "eodhd")
    monkeypatch.setattr(settings, "EODHD_API_KEY", "")
    with pytest.raises(AnalysisError) as raised:
        await fetch_stock_history_async("AAPL", "1y")
    assert raised.value.code == "MARKET_NOT_CONFIGURED"
    monkeypatch.setattr(settings, "EODHD_API_KEY", "test-key")
    transport(monkeypatch, lambda request: httpx.Response(200, json=[]))
    with pytest.raises(AnalysisError) as raised:
        await fetch_stock_history_async("AAPL", "1y")
    assert raised.value.code == "MARKET_EMPTY"


def test_revision_changes_with_provider_or_adjustment():
    frame = pd.DataFrame(
        {
            "trading_date": [date(2025, 1, 2)],
            "open": [100],
            "high": [110],
            "low": [90],
            "close": [100],
            "volume": [1000],
        }
    )
    assert history_revision(frame, {"source": "A"}) != history_revision(frame, {"source": "B"})
    assert history_revision(frame, {"adjustment": "raw"}) != history_revision(
        frame, {"adjustment": "adjusted"}
    )


def test_calendar_requires_verification_and_respects_us_holiday_and_short_session(monkeypatch):
    stock = Stock(ticker="AAPL", exchange="NASDAQ", publication_delay_minutes=30)
    monkeypatch.setattr(settings, "MARKET_CALENDAR_VERIFIED", False)
    assert session_status(stock, date(2026, 11, 27))["data_state"] == "unknown"
    monkeypatch.setattr(settings, "MARKET_CALENDAR_VERIFIED", True)
    # Thanksgiving 26 Nov is closed; 27 Nov has a 13:00 New York close.
    before_publication = session_status(
        stock, date(2026, 11, 25), datetime(2026, 11, 27, 18, 15, tzinfo=UTC)
    )
    assert before_publication["data_state"] == "fresh"
    after_publication = session_status(
        stock, date(2026, 11, 25), datetime(2026, 11, 27, 18, 45, tzinfo=UTC)
    )
    assert after_publication["data_state"] == "stale"
    assert after_publication["expected_market_date"] == "2026-11-27"
    assert after_publication["market_status"] == "closed"
