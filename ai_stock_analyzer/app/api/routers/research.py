import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy import func, select

from app.api.dependencies import get_current_active_user, get_db
from app.api.routers.monitoring import owned
from app.domain.models.models import AIAnalysis, BacktestRun, SavedFilter
from app.domain.schemas.product import (
    CompareResponse,
    HistoryResponse,
    PresetCreate,
    SavedFilterList,
    SavedFilterResponse,
    ScreenCriteria,
    ScreenResult,
)
from app.services.ai_service import result_payload
from app.services.exports import analysis_pdf, csv_response
from app.services.research import screen

router = APIRouter(tags=["Research"])


@router.get("/screener", response_model=ScreenResult)
async def screener(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    user=Depends(get_current_active_user),
):
    values = {k: v for k, v in request.query_params.items() if k not in ("page", "per_page")}
    try:
        criteria = ScreenCriteria.model_validate(values)
    except ValidationError:
        raise HTTPException(
            422, "Filter screener tidak valid; periksa batas RSI dan nama parameter."
        ) from None
    return await screen(db, criteria, page, per_page)


@router.get("/screener/presets", response_model=SavedFilterList)
async def presets(db=Depends(get_db), user=Depends(get_current_active_user)):
    rows = (
        await db.scalars(
            select(SavedFilter).where(SavedFilter.user_id == user.id).order_by(SavedFilter.name)
        )
    ).all()
    return {
        "data": [
            {
                "id": str(r.id),
                "name": r.name,
                "criteria": r.criteria,
                "schema_version": r.schema_version,
            }
            for r in rows
        ]
    }


@router.post("/screener/presets", status_code=201, response_model=SavedFilterResponse)
async def save_preset(
    data: PresetCreate, db=Depends(get_db), user=Depends(get_current_active_user)
):
    if (
        await db.scalar(
            select(func.count()).select_from(SavedFilter).where(SavedFilter.user_id == user.id)
        )
        >= 100
    ):
        raise HTTPException(422, "Maksimal 100 filter tersimpan.")
    item = SavedFilter(user_id=user.id, name=data.name, criteria=data.criteria.model_dump())
    db.add(item)
    await db.commit()
    return {
        "id": str(item.id),
        "name": item.name,
        "criteria": item.criteria,
        "schema_version": item.schema_version,
    }


@router.delete("/screener/presets/{preset_id}", status_code=204)
async def delete_preset(
    preset_id: uuid.UUID, db=Depends(get_db), user=Depends(get_current_active_user)
):
    await db.delete(await owned(db, SavedFilter, preset_id, user))
    await db.commit()


@router.get("/stocks/{ticker}/analyses", response_model=HistoryResponse)
async def history(
    ticker: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    user=Depends(get_current_active_user),
):
    condition = AIAnalysis.stock_ticker == ticker.upper()
    total = await db.scalar(select(func.count()).select_from(AIAnalysis).where(condition))
    rows = (
        await db.scalars(
            select(AIAnalysis)
            .where(condition)
            .order_by(AIAnalysis.generated_at.desc(), AIAnalysis.id)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).all()
    return {
        "data": [analysis_view(r) for r in rows],
        "pagination": {"page": page, "per_page": per_page, "total": total},
    }


def analysis_view(record):
    if record.provenance == "real" and record.model_name and record.data_revision:
        return result_payload(record)
    return {
        "id": str(record.id),
        "ticker": record.stock_ticker,
        "recommendation": record.recommendation,
        "confidence_score": record.confidence_score,
        "ai_summary": record.ai_summary,
        "analysis_date": record.analysis_date,
        "generated_at": record.generated_at,
        "provenance": "unknown",
        "model_name": record.model_name,
        "provider_name": "unknown",
        "data_revision": record.data_revision,
    }


@router.get("/analyses/compare", response_model=CompareResponse)
async def compare(
    first: uuid.UUID, second: uuid.UUID, db=Depends(get_db), user=Depends(get_current_active_user)
):
    a, b = await db.get(AIAnalysis, first), await db.get(AIAnalysis, second)
    if not a or not b:
        raise HTTPException(404, "Analisis tidak ditemukan.")
    if a.stock_ticker != b.stock_ticker:
        raise HTTPException(422, "Pilih dua hasil untuk saham yang sama.")
    return {
        "first": analysis_view(a),
        "second": analysis_view(b),
        "confidence_change_points": b.confidence_score - a.confidence_score
        if a.confidence_score is not None and b.confidence_score is not None
        else None,
        "inputs_differ": (
            a.data_revision,
            a.provider_name,
            a.model_name,
            a.actual_model_name,
            a.prompt_version,
        )
        != (b.data_revision, b.provider_name, b.model_name, b.actual_model_name, b.prompt_version),
        "explanation": "Perubahan skor dalam poin persentase, bukan return atau peluang profit; hasil dibandingkan sesuai urutan yang dipilih.",
    }


@router.get("/stocks/{ticker}/analyses/export")
async def export_history(
    ticker: str,
    format: Literal["csv", "pdf"] = "csv",
    ids: str | None = Query(None, max_length=7500),
    db=Depends(get_db),
    user=Depends(get_current_active_user),
):
    query = select(AIAnalysis).where(AIAnalysis.stock_ticker == ticker.upper())
    if ids:
        try:
            selected = [uuid.UUID(v) for v in ids.split(",")]
        except ValueError:
            raise HTTPException(422, "ID ekspor tidak valid.") from None
        query = query.where(AIAnalysis.id.in_(selected))
    count = await db.scalar(select(func.count()).select_from(query.subquery()))
    if count > (200 if format == "pdf" else 5000):
        raise HTTPException(422, "Pilih maksimal 200 hasil untuk PDF atau 5.000 hasil untuk CSV.")
    rows = (await db.scalars(query.order_by(AIAnalysis.generated_at.desc()))).all()
    if format == "pdf":
        return analysis_pdf(rows, ticker.upper())
    fields = [
        "id",
        "ticker",
        "analysis_date",
        "generated_at",
        "provider_name",
        "model_name",
        "actual_model_name",
        "prompt_version",
        "data_revision",
        "provenance",
        "recommendation",
        "confidence_score",
        "ai_summary",
        "limitations",
        "source",
        "currency",
        "exchange",
        "price_adjustment",
        "volume_adjustment",
    ]
    return csv_response(
        [{**analysis_view(r), **(r.details or {}).get("input_metadata", {})} for r in rows],
        fields,
        "analyses.csv",
    )


@router.get("/backtests")
async def backtest_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    user=Depends(get_current_active_user),
):
    condition = BacktestRun.user_id == user.id
    total = await db.scalar(select(func.count()).select_from(BacktestRun).where(condition))
    rows = (
        await db.scalars(
            select(BacktestRun)
            .where(condition)
            .order_by(BacktestRun.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).all()
    return {
        "data": [
            {
                "id": str(r.id),
                "ticker": r.ticker,
                "created_at": r.created_at,
                "parameters": r.result.get("effective_parameters"),
                "total_trades": r.result.get("total_trades"),
                "net_return_pct": r.result.get("net_return_pct"),
                "data_revision": r.data_revision,
            }
            for r in rows
        ],
        "pagination": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/backtests/{run_id}")
async def backtest_detail(
    run_id: uuid.UUID, db=Depends(get_db), user=Depends(get_current_active_user)
):
    run = await owned(db, BacktestRun, run_id, user)
    return {**run.result, "run_id": str(run.id)}


@router.get("/backtests/{run_id}/export")
async def backtest_csv(
    run_id: uuid.UUID, db=Depends(get_db), user=Depends(get_current_active_user)
):
    run = await owned(db, BacktestRun, run_id, user)
    result = run.result
    common = {
        "run_id": str(run.id),
        "ticker": run.ticker,
        "strategy": result.get("strategy"),
        "data_revision": run.data_revision,
        "data_start": result.get("data_start"),
        "data_end": result.get("data_end"),
        "source": result.get("source"),
        "price_adjustment": result.get("assumptions", {}).get("price_adjustment"),
        **result.get("effective_parameters", {}),
    }
    rows = [
        {
            **common,
            "row_type": "summary",
            "net_return_pct": result.get("net_return_pct"),
            "total_fees": result.get("total_fees"),
        }
    ]
    rows.extend({**common, "row_type": "trade", **trade} for trade in result.get("trades", []))
    return csv_response(
        rows,
        [
            "row_type",
            *common.keys(),
            "net_return_pct",
            "total_fees",
            "buy_date",
            "sell_date",
            "buy_price",
            "sell_price",
            "quantity",
            "fees",
            "profit_pct",
            "gross_profit_pct",
            "status",
            "exit_reason",
            "days_held",
            "reason",
        ],
        "backtest.csv",
    )
