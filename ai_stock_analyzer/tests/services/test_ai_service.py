from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.domain.models.models import AIAnalysis
from app.services.ai_service import run_ai_analysis
from tests.support import seed_market


@pytest.mark.asyncio
async def test_run_ai_analysis(db_session, monkeypatch):
    await seed_market(db_session)
    provider = AsyncMock(
        return_value={
            "wyckoff_phase": "Phase C",
            "vpa_insight": "Test insight",
            "recommendation": "BUY",
            "confidence_score": 0.85,
        }
    )
    monkeypatch.setattr("app.services.ai_service.call_claude_sonnet", provider)
    result = await run_ai_analysis("BBCA.JK", db_session)
    assert result["recommendation"] == "BUY"
    assert result["confidence_score"] == 85
    record = (await db_session.execute(select(AIAnalysis))).scalar_one()
    assert record.ai_summary == "Test insight"
    assert record.provenance == "real"
    assert record.data_revision == "revision-1"
    cached = await run_ai_analysis("BBCA.JK", db_session)
    assert cached["cached"] is True
    assert provider.await_count == 1
