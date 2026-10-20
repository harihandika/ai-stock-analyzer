import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.api.dependencies import get_current_active_user, get_db
from app.domain.models.models import AIAnalysis, AlertEvent, AlertRule, DailyPrice, Stock
from app.domain.schemas.product import AlertCreate, AlertList, AlertResponse, AlertToggle
from app.services.alerts import rule_payload
from app.services.market_metadata import as_utc, exchange_calendar, metadata
from app.services.operations import worker_status

router = APIRouter(tags=["Monitoring"])


async def owned(db, model, key, user):
    item = await db.get(model, key)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Item tidak ditemukan.")
    return item


@router.get("/alerts", response_model=AlertList)
async def list_alerts(db=Depends(get_db), user=Depends(get_current_active_user)):
    worker = await worker_status(db)
    rows = (
        await db.scalars(
            select(AlertRule)
            .where(AlertRule.user_id == user.id)
            .order_by(AlertRule.created_at.desc())
        )
    ).all()
    data, market = [], {}
    for rule in rows:
        if rule.ticker not in market:
            stock = await db.get(Stock, rule.ticker)
            days = (
                await db.scalars(
                    select(DailyPrice.trading_date)
                    .where(DailyPrice.stock_ticker == rule.ticker)
                    .order_by(DailyPrice.trading_date.desc())
                    .limit(2)
                )
            ).all()
            day = days[0] if days else None
            state = metadata(stock, day)["data_state"] if stock else "unavailable"
            signal = await db.scalar(
                select(AIAnalysis.id)
                .where(
                    AIAnalysis.stock_ticker == rule.ticker,
                    AIAnalysis.data_revision == stock.data_revision if stock else False,
                    AIAnalysis.provenance == "real",
                    AIAnalysis.recommendation.is_not(None),
                )
                .limit(1)
            )
            previous_ok = False
            if state == "fresh" and stock and len(days) > 1:
                aliases = {
                    "IDX": "XIDX",
                    "JK": "XIDX",
                    "JKT": "XIDX",
                    "NYSE": "XNYS",
                    "NASDAQ": "XNYS",
                    "US": "XNYS",
                    "NYQ": "XNYS",
                    "NMS": "XNYS",
                }
                calendar = aliases.get((stock.exchange or "").upper())
                if calendar:
                    try:
                        previous_ok = (
                            exchange_calendar(calendar, day.year).previous_session(str(day)).date()
                            == days[1]
                        )
                    except (ValueError, KeyError, IndexError):
                        pass
            market[rule.ticker] = (day, state, bool(signal), previous_ok)
        day, state, signal, previous_ok = market[rule.ticker]
        evaluation = (
            "paused"
            if not rule.enabled
            else "notifications_disabled"
            if not user.notifications_enabled
            else "waiting_for_data"
            if state != "fresh"
            else "waiting_for_analysis"
            if rule.kind == "signal" and not signal
            else "waiting_for_previous_session"
            if rule.kind == "change_pct" and not previous_ok
            else "waiting_for_worker"
            if worker["state"] != "healthy"
            else "waiting_for_baseline"
            if rule.previous_met is None
            else "ready"
        )
        data.append(
            {
                **rule_payload(rule),
                "market_as_of": day,
                "data_state": state,
                "evaluation_state": evaluation,
            }
        )
    return {"data": data, "worker": worker}


@router.post("/alerts", status_code=201, response_model=AlertResponse)
async def create_alert(
    data: AlertCreate, db=Depends(get_db), user=Depends(get_current_active_user)
):
    if not await db.get(Stock, data.ticker.upper()):
        raise HTTPException(404, "Saham belum terdaftar.")
    if (
        await db.scalar(
            select(func.count()).select_from(AlertRule).where(AlertRule.user_id == user.id)
        )
        >= 100
    ):
        raise HTTPException(422, "Maksimal 100 alert per akun.")
    rule = AlertRule(user_id=user.id, **{**data.model_dump(), "ticker": data.ticker.upper()})
    db.add(rule)
    await db.commit()
    return rule_payload(rule)


@router.patch("/alerts/{rule_id}", response_model=AlertResponse)
async def toggle_alert(
    rule_id: uuid.UUID, data: AlertToggle, db=Depends(get_db), user=Depends(get_current_active_user)
):
    rule = await owned(db, AlertRule, rule_id, user)
    rule.enabled = data.enabled
    if data.enabled:
        rule.previous_met = None
    await db.commit()
    return rule_payload(rule)


@router.delete("/alerts/{rule_id}", status_code=204)
async def delete_alert(
    rule_id: uuid.UUID, db=Depends(get_db), user=Depends(get_current_active_user)
):
    await db.delete(await owned(db, AlertRule, rule_id, user))
    await db.commit()


@router.get("/notifications")
async def notifications(db=Depends(get_db), user=Depends(get_current_active_user)):
    rows = (
        await db.scalars(
            select(AlertEvent)
            .where(AlertEvent.user_id == user.id)
            .order_by(AlertEvent.created_at.desc())
            .limit(100)
        )
    ).all()
    unread = await db.scalar(
        select(func.count())
        .select_from(AlertEvent)
        .where(AlertEvent.user_id == user.id, AlertEvent.is_read.is_(False))
    )
    return {
        "unread": unread,
        "data": [
            {
                "id": str(r.id),
                "ticker": r.ticker,
                "is_read": r.is_read,
                "created_at": as_utc(r.created_at),
                **r.details,
            }
            for r in rows
        ],
    }


@router.patch("/notifications/{event_id}/read")
async def mark_read(event_id: uuid.UUID, db=Depends(get_db), user=Depends(get_current_active_user)):
    event = await owned(db, AlertEvent, event_id, user)
    event.is_read = True
    await db.commit()
    return {"id": str(event.id), "is_read": True}
