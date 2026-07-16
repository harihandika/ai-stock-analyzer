import json
import pandas as pd

def build_analysis_prompt(ticker: str, df: pd.DataFrame, latest_indicators: dict) -> tuple[str, str]:
    """
    Merangkai System Prompt dan User Prompt untuk dikirim ke Claude.
    Mengubah raw DataFrame dan indicator menjadi format JSON padat agar hemat token.
    
    Args:
        ticker: Simbol saham (contoh: BBCA.JK)
        df: DataFrame harga terakhir (direkomendasikan ambil 5-10 baris terakhir saja)
        latest_indicators: Dictionary berisi Wyckoff & SMC pattern terakhir dari database
        
    Returns:
        tuple(system_prompt, user_prompt)
    """
    
    # 1. System Prompt (Instruksi Peran & Format)
    system_prompt = """You are an expert Smart Money Concept (SMC) and Volume Price Analysis (VPA) analyst for the Indonesian Stock Exchange (IDX).
Your task is to analyze the provided technical data and provide a concise, high-probability trading recommendation.
The user will provide technical data formatted as JSON.

Analyze the data based on:
1. VPA anomalies (Stopping Volume, No Demand, Climactic Volume).
2. Wyckoff Phases (Spring, SOS) - if available.
3. SMC Patterns (FVG, BOS, CHoCH) - if available.
4. Trend direction (EMA 50 vs EMA 200).

Your response MUST be ONLY a raw JSON object (without markdown code blocks) with the following structure:
{
    "wyckoff_phase": "String (e.g. 'Phase C (Spring)', 'Phase D (SOS)', or 'None')",
    "vpa_insight": "String (Brief 2-3 sentence analysis of Volume and Price action)",
    "recommendation": "String (Exactly one of: 'BUY', 'HOLD', 'WAIT')",
    "confidence_score": 0.95 (Float between 0.0 and 1.0)
}
Do NOT wrap the JSON in ```json ``` tags. Respond only with the JSON object.
Ensure output is in Bahasa Indonesia except for the recommendation standard (BUY/HOLD/WAIT)."""

    # 2. Persiapkan ringkasan data harian (Hemat token: ambil 5 hari terakhir jika lebih besar)
    df_recent = df.tail(5) if len(df) > 5 else df
    
    recent_price_action = []
    for _, row in df_recent.iterrows():
        # Gunakan atribut tanggal jika index adalah datetime
        date_str = str(row.name)[:10] if isinstance(row.name, pd.Timestamp) else str(row.get('trading_date', ''))[:10]
        
        anomalies = []
        if row.get('stopping_volume'): anomalies.append("Stopping Volume")
        if row.get('no_demand'): anomalies.append("No Demand")
        if row.get('climactic_volume'): anomalies.append("Climactic Volume")
        
        recent_price_action.append({
            "date": date_str,
            "close": round(row.get('close', 0), 2),
            "volume": int(row.get('volume', 0)),
            "rsi": round(row.get('rsi_14', 0), 1) if not pd.isna(row.get('rsi_14')) else None,
            "vpa_anomalies": anomalies
        })
        
    # Tren EMA
    last_row = df_recent.iloc[-1]
    ema_50 = last_row.get('ema_50')
    ema_200 = last_row.get('ema_200')
    if pd.isna(ema_50) or pd.isna(ema_200):
        trend = "Unknown"
    elif ema_50 > ema_200:
        trend = "Uptrend"
    else:
        trend = "Downtrend"

    # 3. User Prompt (Data Context)
    user_context = {
        "ticker": ticker,
        "current_price": recent_price_action[-1]["close"] if recent_price_action else 0,
        "macro_trend_ema50_vs_200": trend,
        "latest_smc_patterns": latest_indicators.get("smc_patterns", {}),
        "latest_wyckoff": {
            "is_spring": latest_indicators.get("is_spring", False),
            "wyckoff_phase": latest_indicators.get("wyckoff_phase", None)
        },
        "recent_5_days_price_action": recent_price_action
    }
    
    user_prompt = json.dumps(user_context, separators=(',', ':'))
    
    return system_prompt, user_prompt
