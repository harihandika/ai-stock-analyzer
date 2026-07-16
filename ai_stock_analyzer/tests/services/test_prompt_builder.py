import json
import pandas as pd
from app.services.prompt_builder import build_analysis_prompt

def test_build_analysis_prompt():
    df = pd.DataFrame([
        {
            "trading_date": pd.Timestamp("2026-07-10"),
            "close": 1000,
            "volume": 5000,
            "rsi_14": 40.5,
            "ema_50": 980,
            "ema_200": 950,
            "stopping_volume": True,
            "no_demand": False,
            "climactic_volume": False
        }
    ])
    df.set_index("trading_date", inplace=True)
    
    latest_ind = {
        "smc_patterns": {"bos": True},
        "is_spring": True,
        "wyckoff_phase": "Phase C (Spring)"
    }
    
    sys_prompt, user_prompt = build_analysis_prompt("BBCA.JK", df, latest_ind)
    
    assert "BBCA.JK" in user_prompt
    assert "Uptrend" in user_prompt
    
    # Verify user_prompt is valid JSON
    parsed = json.loads(user_prompt)
    assert parsed["ticker"] == "BBCA.JK"
    assert parsed["recent_5_days_price_action"][0]["vpa_anomalies"] == ["Stopping Volume"]
    assert parsed["latest_wyckoff"]["wyckoff_phase"] == "Phase C (Spring)"
