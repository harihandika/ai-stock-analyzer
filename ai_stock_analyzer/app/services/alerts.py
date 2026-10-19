"""Evaluate new complete sessions only; event insertion and rule advancement are atomic."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domain.models.models import AIAnalysis, AlertEvent, AlertRule, DailyPrice, Stock, User
from app.services.market_metadata import metadata, utcnow


async def evaluate_alerts(db):
    rule_ids = (
        await db.scalars(
            select(AlertRule.id)
            .join(User, User.id == AlertRule.user_id)
            .where(
                AlertRule.enabled.is_(True),
                User.notifications_enabled.is_(True),
                User.is_active.is_(True),
            )
        )
    ).all()
    for rule_id in rule_ids:
        rule = await db.get(AlertRule, rule_id, populate_existing=True)
        if not rule or not rule.enabled:
            continue
        stock = await db.get(Stock, rule.ticker, populate_existing=True)
        prices = (
            await db.scalars(
                select(DailyPrice)
                .where(DailyPrice.stock_ticker == rule.ticker)
                .order_by(DailyPrice.trading_date.desc())
                .limit(2)
            )
        ).all()
        if (
            not stock
            or not prices
            or metadata(stock, prices[0].trading_date)["data_state"] != "fresh"
        ):
            continue
        day = prices[0].trading_date
        analysis = None
        if rule.kind == "signal":
            analysis = await db.scalar(
                select(AIAnalysis)
                .where(
                    AIAnalysis.stock_ticker == rule.ticker,
                    AIAnalysis.data_revision == stock.data_revision,
                    AIAnalysis.provenance == "real",
                )
                .order_by(AIAnalysis.generated_at.desc())
                .limit(1)
            )
            if not analysis or rule.last_analysis_id == str(analysis.id):
                continue
            value = analysis.recommendation
            met = value == rule.signal
            key = f"{rule.id}:{analysis.id}"
        else:
            if rule.last_market_date and day <= rule.last_market_date:
                continue
            if rule.kind == "change_pct":
                if len(prices) < 2:
                    continue
                from app.services.market_metadata import exchange_calendar

                aliases = "XIDX" if stock.exchange in ("IDX", "JK", "JKT") else "XNYS"
                try:
                    previous = (
                        exchange_calendar(aliases, day.year).previous_session(str(day)).date()
                    )
                except (ValueError, KeyError):
                    continue
                if prices[1].trading_date != previous:
                    continue
                value = (float(prices[0].close) / float(prices[1].close) - 1) * 100
            else:
                value = float(prices[0].close)
            met = (
                value >= float(rule.threshold)
                if rule.direction == "above"
                else value <= float(rule.threshold)
            )
            key = f"{rule.id}:{day}"
        # The first evaluation establishes a baseline; creating an alert never
        # pretends that a crossing occurred before the user subscribed.
        should_fire = rule.previous_met is False and met
        try:
            async with db.begin_nested():
                if should_fire:
                    db.add(
                        AlertEvent(
                            user_id=rule.user_id,
                            rule_id=rule.id,
                            event_key=key,
                            ticker=rule.ticker,
                            details={
                                "kind": rule.kind,
                                "direction": rule.direction,
                                "threshold": float(rule.threshold)
                                if rule.threshold is not None
                                else None,
                                "signal": rule.signal,
                                "value": value,
                                "market_as_of": str(day),
                                "evaluated_at": utcnow().isoformat(),
                                "source": stock.market_source,
                                "data_revision": stock.data_revision,
                                "analysis_id": str(analysis.id) if analysis else None,
                                "href": "/stock/" + rule.ticker,
                            },
                        )
                    )
                    await db.flush()
                rule.previous_met, rule.last_market_date = met, day
                rule.last_analysis_id = str(analysis.id) if analysis else rule.last_analysis_id
            await db.commit()
        except IntegrityError:
            await db.rollback()  # Another worker already inserted this exact event.


def rule_payload(rule):
    return {
        "id": str(rule.id),
        "ticker": rule.ticker,
        "kind": rule.kind,
        "direction": rule.direction,
        "threshold": float(rule.threshold) if rule.threshold is not None else None,
        "signal": rule.signal,
        "enabled": rule.enabled,
        "last_market_date": rule.last_market_date,
        "baseline_established": rule.previous_met is not None,
    }
