import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.api.dependencies import get_current_active_user, get_db
from app.domain.models.models import AlertEvent, AlertRule, Stock
from app.domain.schemas.product import AlertCreate, AlertList, AlertResponse, AlertToggle
from app.services.alerts import rule_payload
from app.services.market_metadata import as_utc

router = APIRouter(tags=["Monitoring"])


async def owned(db, model, key, user):
    item = await db.get(model, key)
    if not item or item.user_id != user.id:
        raise HTTPException(404, "Item tidak ditemukan.")
    return item


@router.get("/alerts", response_model=AlertList)
async def list_alerts(db=Depends(get_db), user=Depends(get_current_active_user)):
    return {
        "data": [
            rule_payload(r)
            for r in (
                await db.scalars(
                    select(AlertRule)
                    .where(AlertRule.user_id == user.id)
                    .order_by(AlertRule.created_at.desc())
                )
            ).all()
        ]
    }


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
