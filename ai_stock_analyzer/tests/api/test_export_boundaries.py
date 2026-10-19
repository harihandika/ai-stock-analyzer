import csv
import io
from datetime import date

import pytest
from sqlalchemy import delete, insert, select

from app.domain.models.models import AIAnalysis
from tests.support import login, seed_market


@pytest.mark.asyncio
async def test_export_limits_cover_all_records_without_rerunning_ai(client, db_session):
    await seed_market(db_session)
    headers = await login(client)
    await db_session.execute(
        insert(AIAnalysis),
        [
            {
                "stock_ticker": "BBCA.JK",
                "analysis_date": date(2026, 10, 16),
                "recommendation": "WAIT",
                "confidence_score": 0,
                "ai_summary": "=spreadsheet formula",
                "provenance": "unknown",
            }
            for _ in range(5001)
        ],
    )
    await db_session.commit()
    path = "/api/v1/stocks/BBCA.JK/analyses/export"
    assert (await client.get(path, headers=headers)).status_code == 422
    assert (await client.get(path + "?format=pdf", headers=headers)).status_code == 422
    ids = list(await db_session.scalars(select(AIAnalysis.id)))
    await db_session.execute(delete(AIAnalysis).where(AIAnalysis.id == ids.pop()))
    await db_session.commit()
    response = await client.get(path, headers=headers)
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.text.lstrip("\ufeff"))))
    assert len(rows) == 5000
    assert all(
        row["ai_summary"].startswith("'=") and row["provider_name"] == "unknown" for row in rows
    )
    await db_session.execute(delete(AIAnalysis).where(AIAnalysis.id.in_(ids[201:])))
    await db_session.commit()
    assert (await client.get(path + "?format=pdf", headers=headers)).status_code == 422
    await db_session.execute(delete(AIAnalysis).where(AIAnalysis.id == ids[200]))
    await db_session.commit()
    pdf = await client.get(path + "?format=pdf", headers=headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert (await client.get("/api/v1/auth/me", headers=headers)).json()["quota_used"] == 0
