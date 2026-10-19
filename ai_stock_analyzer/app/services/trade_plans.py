from decimal import ROUND_FLOOR, Decimal


def calculate_plan(data):
    def d(key):
        return Decimal(str(getattr(data, key)))

    entry, stop, target, capital = (d(k) for k in ("entry", "stop", "target", "capital"))
    buy_fee, sell_fee, slip = (
        d(k) / 10000 for k in ("buy_fee_bps", "sell_fee_bps", "slippage_bps")
    )
    cost = entry * (1 + slip) * (1 + buy_fee)
    exit_value = stop * (1 - slip) * (1 - sell_fee)
    risk_unit = cost - exit_value
    risk_budget = capital * d("risk_pct") / 100
    units = min(capital / cost, risk_budget / risk_unit)
    lot = Decimal(data.lot_size)
    lots = (units / lot).to_integral_value(rounding=ROUND_FLOOR)
    shares = lots * lot
    return {
        "shares": int(shares),
        "lots": int(lots),
        "purchase_value": float(shares * cost),
        "estimated_risk": float(shares * risk_unit),
        "risk_budget": float(risk_budget),
        "remaining_capital": float(capital - shares * cost),
        "reward_risk_before_fees": float((target - entry) / (entry - stop)),
        "estimated_reward_after_fees": float(
            shares * (target * (1 - slip) * (1 - sell_fee) - cost)
        ),
        "origin": "input_pengguna",
        "limitations": "Simulasi long; stop tidak menjamin harga eksekusi saat gap/likuiditas rendah. Tidak mengirim order broker.",
    }
