"""Validated, revisioned analysis results. Database results are the shared cache."""

from decimal import Decimal

import pandas as pd
from pydantic import ValidationError
from sqlalchemy import select

from app.core.errors import AnalysisError
from app.domain.models.models import AIAnalysis, DailyPrice, Stock, TechnicalIndicator
from app.domain.schemas.analysis import ModelAnalysis
from app.infrastructure.ai_client import ai_identity
from app.infrastructure.ai_client import call_analysis_model as call_claude_sonnet
from app.services.market_metadata import as_utc, utcnow
from app.services.prompt_builder import build_analysis_prompt

PROMPT_VERSION = "technical-r1-v1"


def result_payload(record, *, cached=False):
    return {
        **(record.details or {}),
        "id": str(record.id),
        "ticker": record.stock_ticker,
        "recommendation": record.recommendation,
        "confidence_score": record.confidence_score,
        "ai_summary": record.ai_summary,
        "vpa_insight": record.vpa_insight,
        "analysis_date": record.analysis_date.isoformat(),
        "generated_at": as_utc(record.generated_at).isoformat(),
        "data_revision": record.data_revision,
        "model_name": record.model_name,
        "provider_name": record.provider_name,
        "actual_model_name": record.actual_model_name,
        "prompt_version": record.prompt_version,
        "provenance": record.provenance,
        "cached": cached,
    }


async def cached_analysis(db, ticker, revision):
    if not revision:
        return None
    return (
        await db.execute(
            select(AIAnalysis)
            .where(
                AIAnalysis.stock_ticker == ticker,
                AIAnalysis.data_revision == revision,
                AIAnalysis.model_name == ai_identity()[1],
                AIAnalysis.provider_name == ai_identity()[0],
                AIAnalysis.prompt_version == PROMPT_VERSION,
                AIAnalysis.provenance == "real",
            )
            .order_by(AIAnalysis.generated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def run_ai_analysis(ticker, db, analyzed_by=None, *, commit=True):
    stock = await db.get(Stock, ticker)
    if not stock or not stock.data_revision or not stock.market_source:
        raise AnalysisError(
            "DATA_UNVERIFIED",
            "Sinkronkan data pasar sebelum menjalankan AI.",
            status=409,
            stage="data",
        )
    cached = await cached_analysis(db, ticker, stock.data_revision)
    if cached:
        return result_payload(cached, cached=True)
    prices = list(
        reversed(
            (
                await db.execute(
                    select(DailyPrice)
                    .where(DailyPrice.stock_ticker == ticker)
                    .order_by(DailyPrice.trading_date.desc())
                    .limit(10)
                )
            )
            .scalars()
            .all()
        )
    )
    techs = list(
        reversed(
            (
                await db.execute(
                    select(TechnicalIndicator)
                    .where(TechnicalIndicator.stock_ticker == ticker)
                    .order_by(TechnicalIndicator.trading_date.desc())
                    .limit(5)
                )
            )
            .scalars()
            .all()
        )
    )
    if (
        len(prices) < 5
        or not techs
        or techs[-1].trading_date != prices[-1].trading_date
        or techs[-1].rsi_14 is None
        or techs[-1].ema_50 is None
    ):
        raise AnalysisError(
            "DATA_INSUFFICIENT",
            "Data harga/indikator belum cukup atau tidak selaras.",
            status=409,
            stage="data",
        )
    revision = stock.data_revision
    input_metadata = {
        "source": stock.market_source,
        "currency": stock.currency,
        "exchange": stock.exchange,
        "price_adjustment": stock.price_adjustment,
        "volume_adjustment": stock.volume_adjustment,
    }
    tech_map = {t.trading_date: t for t in techs}
    data = []
    for p in prices:
        row = {"trading_date": p.trading_date, "volume": p.volume}
        row.update({k: float(getattr(p, k)) for k in ["open", "high", "low", "close"]})
        for k in [
            "rsi_14",
            "ema_50",
            "ema_200",
            "stopping_volume",
            "no_demand",
            "climactic_volume",
        ]:
            value = getattr(tech_map.get(p.trading_date), k, None)
            row[k] = float(value) if isinstance(value, Decimal) else value
        data.append(row)
    latest = techs[-1]
    system, prompt = build_analysis_prompt(
        ticker,
        pd.DataFrame(data),
        {
            "smc_patterns": latest.smc_patterns,
            "is_spring": latest.is_spring,
            "wyckoff_phase": latest.wyckoff_phase,
        },
    )
    raw = await call_claude_sonnet(system, prompt)
    try:
        validated = ModelAnalysis.model_validate(raw)
    except ValidationError as exc:
        raise AnalysisError(
            "AI_INVALID_RESPONSE", "Respons AI tidak memenuhi kontrak analisis."
        ) from exc
    # Do not label a result against a newer data revision if sync happened during the call.
    await db.refresh(stock)
    if stock.data_revision != revision:
        raise AnalysisError(
            "DATA_CHANGED", "Data berubah selama analisis. Silakan jalankan ulang.", status=409
        )
    record = AIAnalysis(
        stock_ticker=ticker,
        analysis_date=latest.trading_date,
        ai_summary=validated.summary or validated.vpa_insight,
        vpa_insight=validated.vpa_insight,
        recommendation=validated.recommendation,
        confidence_score=round(validated.confidence_score * 100),
        wyckoff_phase_ai=validated.wyckoff_phase,
        tokens_used=validated.tokens_used,
        analyzed_by=analyzed_by,
        generated_at=utcnow(),
        provenance="real",
        data_revision=revision,
        model_name=ai_identity()[1],
        provider_name=ai_identity()[0],
        actual_model_name=raw.get("_model_name", ai_identity()[1]),
        prompt_version=PROMPT_VERSION,
        details={
            **validated.model_dump(exclude={"confidence_score", "recommendation"}),
            "input_metadata": input_metadata,
        },
    )
    db.add(record)
    await db.flush()
    if commit:
        await db.commit()
    return result_payload(record)
