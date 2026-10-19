from datetime import date, timedelta

from app.domain.models.models import DailyPrice, Stock, TechnicalIndicator
from app.services.market_metadata import utcnow


async def seed_market(db, ticker="BBCA.JK", revision="revision-1", currency="IDR"):
    stock = Stock(
        ticker=ticker,
        company_name="Bank Test",
        exchange="IDX",
        currency=currency,
        market_source="Yahoo Finance",
        data_revision=revision,
        data_fetched_at=utcnow(),
    )
    db.add(stock)
    for i in range(60):
        day = date(2025, 1, 1) + timedelta(days=i)
        db.add(
            DailyPrice(
                stock_ticker=ticker,
                trading_date=day,
                open=100,
                high=120,
                low=90,
                close=100 + i / 10,
                volume=1000,
            )
        )
        db.add(
            TechnicalIndicator(
                stock_ticker=ticker,
                trading_date=day,
                rsi_14=55,
                ema_50=100,
                ema_200=None,
                stopping_volume=False,
                no_demand=False,
                climactic_volume=False,
                is_spring=False,
                wyckoff_phase="Phase C",
                smc_patterns={},
            )
        )
    await db.commit()
    return stock


async def login(client, email="r1@example.com"):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "test-password-123", "full_name": "R1 Tester"},
    )
    assert response.status_code == 201
    response = await client.post(
        "/api/v1/auth/token", json={"email": email, "password": "test-password-123"}
    )
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


MODEL_RESPONSE = {
    "recommendation": "BUY",
    "confidence_score": 0.88,
    "vpa_insight": "Volume mendukung akumulasi.",
    "wyckoff_phase": "Phase C",
    "summary": "Ringkasan aktual berdasarkan indikator.",
    "supporting_factors": ["Volume meningkat"],
    "opposing_factors": ["Histori terbatas"],
}
