"""Causal daily technical strategy. Decisions at close, executions at next open."""

import argparse
import asyncio

import numpy as np
import pandas as pd

from app.infrastructure.market_data import fetch_stock_history_async, market_identity
from app.services.indicator_engine import calculate_indicators, detect_vpa_signals
from app.services.market_metadata import history_revision
from app.services.pattern_engine import detect_confirmed_swings
from app.services.smc_engine import detect_fvg, detect_structure_breaks
from app.services.wyckoff_engine import detect_wyckoff_accumulation


def prepare_signals(frame):
    frame = frame.sort_values("trading_date").reset_index(drop=True).copy()
    frame = calculate_indicators(frame)
    frame = detect_vpa_signals(frame)
    frame = detect_confirmed_swings(frame)
    frame = detect_wyckoff_accumulation(frame)
    frame = detect_fvg(frame)
    return detect_structure_breaks(frame)


class Backtester:
    def __init__(
        self,
        ticker: str,
        years: int,
        target_profit: float = 0.05,
        stop_loss: float = 0.03,
        *,
        initial_capital=100,
        lot_size=None,
        buy_fee_bps=0,
        sell_fee_bps=0,
        slippage_bps=0,
    ):
        if not 1 <= years <= 5 or not 0 < target_profit <= 0.20 or not 0 < stop_loss <= 0.10:
            raise ValueError("Parameter backtest di luar batas.")
        if not 0 < initial_capital <= 1e15 or any(
            not np.isfinite(v) or not 0 <= v <= 1000
            for v in (buy_fee_bps, sell_fee_bps, slippage_bps)
        ):
            raise ValueError("Modal/biaya tidak valid.")
        self.initial_capital, self.lot_size = initial_capital, lot_size
        self.buy_fee, self.sell_fee, self.slip = (
            buy_fee_bps / 10000,
            sell_fee_bps / 10000,
            slippage_bps / 10000,
        )
        self.source, self.price_adjustment, self.data_revision = market_identity(), "unknown", None
        self.ticker = ticker.upper()
        self.years = years
        self.period = str(years) + "y"
        self.target_profit = target_profit
        self.stop_loss = stop_loss
        self.trades = []
        self.equity_curve = []
        self.df = pd.DataFrame()

    async def _fetch_and_prepare_data(self):
        frame = await fetch_stock_history_async(self.ticker, period=str(self.years + 1) + "y")
        required = ["open", "high", "low", "close", "volume"]
        if frame.empty or len(frame) < 60 or not set(required + ["trading_date"]).issubset(frame):
            return False
        values = frame[required].to_numpy(dtype=float)
        if (
            not np.isfinite(values).all()
            or (frame[required[:4]] <= 0).any().any()
            or frame["trading_date"].duplicated().any()
            or (frame["low"] > frame[["open", "close"]].min(axis=1)).any()
            or (frame["high"] < frame[["open", "close"]].max(axis=1)).any()
            or (frame["volume"] < 0).any()
        ):
            raise ValueError("Data OHLCV tidak valid.")
        self.source = frame.attrs.get("source", market_identity())
        self.price_adjustment = frame.attrs.get("price_adjustment", "unknown")
        prepared = prepare_signals(frame)
        cutoff = pd.Timestamp(prepared.iloc[-1]["trading_date"]) - pd.DateOffset(years=self.years)
        self.df = prepared[pd.to_datetime(prepared["trading_date"]) >= cutoff].reset_index(
            drop=True
        )
        self.data_revision = history_revision(
            self.df, {"source": self.source, "price_adjustment": self.price_adjustment}
        )
        return len(self.df) >= 60

    @staticmethod
    def entry_signal(row):
        if bool(row.get("is_spring", False)) and bool(row.get("stopping_volume", False)):
            return "Wyckoff Spring + Stopping Volume"
        if bool(row.get("bullish_fvg", False)) and bool(row.get("choch", False)):
            return "SMC Bullish FVG + confirmed CHoCH"
        return None

    def quantity(self, cash, price):
        units = cash / (price * (1 + self.buy_fee))
        return np.floor(units / self.lot_size) * self.lot_size if self.lot_size else units

    def run_simulation(self):
        self.trades, self.equity_curve = [], []
        cash, units = float(self.initial_capital), 0.0
        entry = None
        pending_entry, pending_exit = None, None

        def close_position(row, raw_price, reason, index):
            nonlocal cash, units, entry
            sell = raw_price * (1 - self.slip)
            fee = units * sell * self.sell_fee
            proceeds = units * sell - fee
            cash += proceeds
            self._record_trade(
                entry["date"],
                row["trading_date"],
                entry["price"],
                sell,
                reason,
                proceeds / entry["cost"] - 1,
                index - entry["index"] + 1,
                entry["reason"],
                quantity=float(units),
                fees=entry["fee"] + fee,
                gross_profit_pct=(raw_price / entry["raw_price"] - 1) * 100,
            )
            units, entry = 0.0, None

        for i, row in self.df.iterrows():
            exited_today = False
            if pending_exit and entry:
                close_position(row, float(row["open"]), pending_exit, i)
                pending_exit = None
                exited_today = True
            if pending_entry and not entry and not exited_today:
                raw_price = float(row["open"])
                buy = raw_price * (1 + self.slip)
                units = float(self.quantity(cash, buy))
                if units > 0:
                    fee = units * buy * self.buy_fee
                    cost = units * buy + fee
                    cash -= cost
                    entry = {
                        "date": row["trading_date"],
                        "price": buy,
                        "raw_price": raw_price,
                        "reason": pending_entry,
                        "index": i,
                        "fee": fee,
                        "cost": cost,
                    }
            pending_entry = None
            final_day = i == len(self.df) - 1
            if final_day and entry:
                close_position(row, float(row["close"]), "END_OF_PERIOD", i)
            equity = cash + units * float(row["close"])
            self.equity_curve.append({"date": str(row["trading_date"]), "equity": round(equity, 8)})
            if final_day:
                continue
            if entry:
                profit = float(row["close"]) / entry["price"] - 1
                if profit >= self.target_profit:
                    pending_exit = "TAKE_PROFIT"
                elif profit <= -self.stop_loss:
                    pending_exit = "STOP_LOSS"
                elif i - entry["index"] + 1 >= 30:
                    pending_exit = "TIMEOUT"
            elif not exited_today:
                pending_entry = self.entry_signal(row)

    def benchmark_result(self):
        if self.df.empty:
            return {}
        first, last = self.df.iloc[0], self.df.iloc[-1]
        buy = float(first["open"]) * (1 + self.slip)
        sell = float(last["close"]) * (1 - self.slip)
        units = float(self.quantity(self.initial_capital, buy))
        entry_cost = units * buy * (1 + self.buy_fee)
        fees = units * buy * self.buy_fee + units * sell * self.sell_fee
        final = self.initial_capital - entry_cost + units * sell * (1 - self.sell_fee)
        return {
            "strategy": "buy_and_hold",
            "quantity": units,
            "data_start": str(first["trading_date"]),
            "data_end": str(last["trading_date"]),
            "final_equity": final,
            "net_return_pct": (final / self.initial_capital - 1) * 100,
            "total_fees": fees,
            "remaining_cash": self.initial_capital - entry_cost,
        }

    def _record_trade(
        self,
        buy_date,
        sell_date,
        buy_price,
        sell_price,
        exit_reason,
        profit,
        days_held,
        reason,
        **details,
    ):
        self.trades.append(
            {
                "buy_date": str(buy_date),
                "sell_date": str(sell_date),
                "buy_price": buy_price,
                "sell_price": sell_price,
                "profit_pct": round(profit * 100, 6),
                "status": "WIN" if profit > 0 else "LOSS" if profit < 0 else "BREAKEVEN",
                "exit_reason": exit_reason,
                "reason": reason,
                "days_held": days_held,
                **details,
            }
        )

    def get_results_dict(self):
        total = len(self.trades)
        wins = sum(t["status"] == "WIN" for t in self.trades)
        peak, drawdown = float(self.initial_capital), 0.0
        for point in self.equity_curve:
            peak = max(peak, point["equity"])
            drawdown = max(drawdown, (peak - point["equity"]) / peak * 100)
        params = {
            "years": self.years,
            "target_profit_pct": self.target_profit * 100,
            "stop_loss_pct": self.stop_loss * 100,
            "initial_capital": self.initial_capital,
            "lot_size": self.lot_size,
            "buy_fee_bps": self.buy_fee * 10000,
            "sell_fee_bps": self.sell_fee * 10000,
            "slippage_bps": self.slip * 10000,
        }
        return {
            "ticker": self.ticker,
            "period_years": self.years,
            "requested_parameters": params,
            "effective_parameters": params,
            "data_start": str(self.df.iloc[0]["trading_date"]) if not self.df.empty else None,
            "data_end": str(self.df.iloc[-1]["trading_date"]) if not self.df.empty else None,
            "source": self.source,
            "data_revision": self.data_revision,
            "net_return_pct": ((self.equity_curve[-1]["equity"] / self.initial_capital - 1) * 100)
            if self.equity_curve
            else 0,
            "total_fees": sum(t.get("fees", 0) for t in self.trades),
            "benchmark": self.benchmark_result(),
            "interval": "1d",
            "strategy": "technical_daily_v2",
            "total_trades": total,
            "win_rate_pct": round(wins / total * 100, 6) if total else 0,
            "avg_profit_pct": round(sum(t["profit_pct"] for t in self.trades) / total, 6)
            if total
            else 0,
            "max_drawdown_pct": round(drawdown, 6),
            "trades": self.trades,
            "equity_curve": self.equity_curve,
            "assumptions": {
                "initial_equity": self.initial_capital,
                "lot_size": self.lot_size,
                "allocation_pct": 100,
                "compounding": True,
                "entry": "Keputusan close; entry open sesi berikutnya",
                "exit": "Evaluasi TP/SL pada close; exit open berikutnya termasuk gap",
                "max_holding_sessions": 30,
                "final_position": "Tutup pada close akhir periode",
                "price_adjustment": self.price_adjustment,
                "fee_bps": None,
                "buy_fee_bps": self.buy_fee * 10000,
                "sell_fee_bps": self.sell_fee * 10000,
                "slippage_bps": self.slip * 10000,
                "limitations": "Simulasi strategi teknikal, bukan rekam jejak AI. Lot sesuai parameter; lot null memakai lembar pecahan ternormalisasi. Likuiditas belum dimodelkan; biaya/slippage mengikuti input. Histori pemanasan tidak ditampilkan sebagai bagian periode simulasi. TP/SL bukan jaminan harga eksekusi intraday.",
            },
        }

    def print_results(self):
        import json

        print(json.dumps(self.get_results_dict(), indent=2))


async def main():
    parser = argparse.ArgumentParser(description="Backtest strategi teknikal harian")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--tp", type=float, default=0.05, help="Target sebagai desimal")
    parser.add_argument("--sl", type=float, default=0.03, help="Stop sebagai desimal")
    args = parser.parse_args()
    engine = Backtester(args.ticker, args.years, args.tp, args.sl)
    if not await engine._fetch_and_prepare_data():
        raise SystemExit("Data historis belum cukup atau tidak tersedia.")
    engine.run_simulation()
    engine.print_results()


if __name__ == "__main__":
    asyncio.run(main())
