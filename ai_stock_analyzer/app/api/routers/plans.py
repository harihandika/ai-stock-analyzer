import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update

from app.api.dependencies import get_current_active_user, get_db
from app.api.routers.monitoring import owned
from app.domain.models.models import Stock, TradePlan
from app.domain.schemas.product import PlanInput, PlanList, PlanResponse, PlanUpdate
from app.services.market_metadata import as_utc, utcnow
from app.services.trade_plans import calculate_plan

router = APIRouter(prefix="/trade-plans", tags=["Trade plans"])


async def validate_instrument(db, data):
    stock = await db.get(Stock, data.ticker.upper())
    if not stock:
        raise HTTPException(404, "Saham belum terdaftar.")
    if stock.currency != data.currency:
        raise HTTPException(
            422, "Mata uang modal/rencana harus sama dengan instrumen; tidak ada konversi otomatis."
        )
    expected_lot = (
        100
        if stock.exchange in ("IDX", "JK", "JKT")
        else 1
        if stock.currency == "USD" and stock.exchange in ("NASDAQ", "NYSE", "NMS", "NYQ", "US")
        else None
    )
    if expected_lot is None or data.lot_size != expected_lot:
        raise HTTPException(
            422,
            "Aturan lot instrumen belum diketahui atau tidak sesuai; fractional share tidak didukung.",
        )
    return stock


def payload(plan, stock):
    return {
        "id": str(plan.id),
        "ticker": plan.ticker,
        "version": plan.version,
        "details": plan.details,
        "versions": plan.versions,
        "data_revision": plan.data_revision,
        "needs_review": stock is None
        or not plan.data_revision
        or stock.data_revision != plan.data_revision,
        "created_at": as_utc(plan.created_at),
        "updated_at": as_utc(plan.updated_at),
    }


@router.get("", response_model=PlanList)
async def list_plans(db=Depends(get_db), user=Depends(get_current_active_user)):
    rows = (
        await db.execute(
            select(TradePlan, Stock)
            .join(Stock, Stock.ticker == TradePlan.ticker)
            .where(TradePlan.user_id == user.id)
            .order_by(TradePlan.updated_at.desc())
            .limit(100)
        )
    ).all()
    return {"data": [payload(p, s) for p, s in rows]}


@router.post("/calculate")
async def calculate(data: PlanInput, db=Depends(get_db), user=Depends(get_current_active_user)):
    await validate_instrument(db, data)
    return calculate_plan(data)


@router.post("", status_code=201, response_model=PlanResponse)
async def create(data: PlanInput, db=Depends(get_db), user=Depends(get_current_active_user)):
    stock = await validate_instrument(db, data)
    plan = TradePlan(
        user_id=user.id,
        ticker=stock.ticker,
        details={
            "input": data.model_dump(),
            "calculation": calculate_plan(data),
            "saved_at": utcnow().isoformat(),
        },
        data_revision=stock.data_revision,
    )
    db.add(plan)
    await db.commit()
    return payload(plan, stock)


@router.put("/{plan_id}", response_model=PlanResponse)
async def edit(
    plan_id: uuid.UUID, data: PlanUpdate, db=Depends(get_db), user=Depends(get_current_active_user)
):
    plan = await owned(db, TradePlan, plan_id, user)
    stock = await validate_instrument(db, data)
    if stock.ticker != plan.ticker:
        raise HTTPException(422, "Buat rencana baru untuk saham lain.")
    details = {
        "input": data.model_dump(exclude={"expected_version"}),
        "calculation": calculate_plan(data),
        "saved_at": utcnow().isoformat(),
    }
    result = await db.execute(
        update(TradePlan)
        .where(TradePlan.id == plan.id, TradePlan.version == data.expected_version)
        .values(
            version=data.expected_version + 1,
            details=details,
            versions=[
                *(plan.versions or []),
                {
                    "version": plan.version,
                    "details": plan.details,
                    "data_revision": plan.data_revision,
                },
            ],
            data_revision=stock.data_revision,
        )
        .execution_options(synchronize_session=False)
    )
    if not result.rowcount:
        raise HTTPException(409, "Rencana sudah berubah; muat versi terbaru sebelum mengedit.")
    await db.commit()
    await db.refresh(plan)
    return payload(plan, stock)


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: uuid.UUID, db=Depends(get_db), user=Depends(get_current_active_user)
):
    await db.delete(await owned(db, TradePlan, plan_id, user))
    await db.commit()
