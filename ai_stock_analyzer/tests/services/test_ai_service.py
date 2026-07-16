import pytest
from unittest.mock import patch, MagicMock
from app.services.ai_service import run_ai_analysis
from app.domain.models.models import DailyPrice, TechnicalIndicator, AIAnalysis
from sqlalchemy.ext.asyncio import AsyncSession
import datetime

@pytest.mark.asyncio
@patch("app.services.ai_service.call_claude_sonnet")
async def test_run_ai_analysis(mock_call_claude):
    mock_call_claude.return_value = {
        "wyckoff_phase": "Phase C (Spring)",
        "vpa_insight": "Test insight",
        "recommendation": "BUY",
        "confidence_score": 0.85
    }
    
    mock_db = MagicMock(spec=AsyncSession)
    
    # Mock result for DailyPrice
    mock_price = MagicMock(spec=DailyPrice)
    mock_price.trading_date = datetime.date(2026, 7, 10)
    mock_price.open = 100
    mock_price.high = 110
    mock_price.low = 90
    mock_price.close = 105
    mock_price.volume = 1000
    
    # Mock result for TechnicalIndicator
    mock_tech = MagicMock(spec=TechnicalIndicator)
    mock_tech.trading_date = datetime.date(2026, 7, 10)
    mock_tech.is_spring = True
    mock_tech.wyckoff_phase = "Phase C (Spring)"
    mock_tech.smc_patterns = {}
    mock_tech.ema_50 = 100.0
    mock_tech.ema_200 = 90.0
    mock_tech.rsi_14 = 55.0
    mock_tech.stopping_volume = False
    mock_tech.no_demand = False
    mock_tech.climactic_volume = False
    
    # We will mock the execute method to return sequences
    async def mock_execute(*args, **kwargs):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_price] if "daily_prices" in str(args[0]) else [mock_tech]
        mock_result.scalars.return_value.first.return_value = None # AIAnalysis existing
        return mock_result
        
    async def mock_commit():
        pass
        
    mock_db.execute = mock_execute
    mock_db.commit = mock_commit
    
    result = await run_ai_analysis("BBCA.JK", mock_db)
    
    assert result["recommendation"] == "BUY"
    mock_db.add.assert_called_once()
