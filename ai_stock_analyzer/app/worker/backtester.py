"""Causal daily technical strategy. Decisions at close, executions at next open."""

import argparse
import asyncio

import numpy as np
import pandas as pd

from app.infrastructure.market_data import fetch_stock_history_async
from app.services.indicator_engine import calculate_indicators, detect_vpa_signals
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
        self, ticker: str, years: int, target_profit: float = 0.05, stop_loss: float = 0.03
    ):
        if not 1 <= years <= 5 or not 0 < target_profit <= 0.20 or not 0 < stop_loss <= 0.10:
            raise ValueError("Parameter backtest di luar batas.")
        self.ticker = ticker.upper()
        self.years = years
        self.period = str(years) + "y"
        self.target_profit = target_profit
        self.stop_loss = stop_loss
        self.trades = []
        self.equity_curve = []
        self.df = pd.DataFrame()

    async def _fetch_and_prepare_data(self):
        frame = await fetch_stock_history_async(self.ticker, period=self.period)
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
        self.df = prepare_signals(frame)
        return True

    @staticmethod
    def entry_signal(row):
        if bool(row.get("is_spring", False)) and bool(row.get("stopping_volume", False)):
            return "Wyckoff Spring + Stopping Volume"
        if bool(row.get("bullish_fvg", False)) and bool(row.get("choch", False)):
            return "SMC Bullish FVG + confirmed CHoCH"
        return None

    def run_simulation(self):
        self.trades, self.equity_curve = [], []
        cash, units = 100.0, 0.0
        entry = None
        pending_entry, pending_exit = None, None
        for i, row in self.df.iterrows():
            exited_today = False
            if pending_exit and entry:
                sell = float(row["open"])
                cash = units * sell
                self._record_trade(
                    entry["date"],
                    row["trading_date"],
                    entry["price"],
                    sell,
                    pending_exit,
                    sell / entry["price"] - 1,
                    i - entry["index"] + 1,
                    entry["reason"],
                )
                units, entry, pending_exit = 0.0, None, None
                exited_today = True
            if pending_entry and not entry and not exited_today:
                buy = float(row["open"])
                units, cash = cash / buy, 0.0
                entry = {
                    "date": row["trading_date"],
                    "price": buy,
                    "reason": pending_entry,
                    "index": i,
                }
            pending_entry = None
            final_day = i == len(self.df) - 1
            if final_day and entry:
                sell = float(row["close"])
                cash = units * sell
                self._record_trade(
                    entry["date"],
                    row["trading_date"],
                    entry["price"],
                    sell,
                    "END_OF_PERIOD",
                    sell / entry["price"] - 1,
                    i - entry["index"] + 1,
                    entry["reason"],
                )
                units, entry = 0.0, None
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
            elif not exited_today and i >= 50:
                pending_entry = self.entry_signal(row)

    def _record_trade(
        self, buy_date, sell_date, buy_price, sell_price, exit_reason, profit, days_held, reason
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
            }
        )

    def get_results_dict(self):
        total = len(self.trades)
        wins = sum(t["status"] == "WIN" for t in self.trades)
        peak, drawdown = 100.0, 0.0
        for point in self.equity_curve:
            peak = max(peak, point["equity"])
            drawdown = max(drawdown, (peak - point["equity"]) / peak * 100)
        params = {
            "years": self.years,
            "target_profit_pct": self.target_profit * 100,
            "stop_loss_pct": self.stop_loss * 100,
        }
        return {
            "ticker": self.ticker,
            "period_years": self.years,
            "requested_parameters": params,
            "effective_parameters": params,
            "data_start": str(self.df.iloc[0]["trading_date"]) if not self.df.empty else None,
            "data_end": str(self.df.iloc[-1]["trading_date"]) if not self.df.empty else None,
            "source": "Yahoo Finance",
            "interval": "1d",
            "strategy": "technical_daily_v1",
            "total_trades": total,
            "win_rate_pct": round(wins / total * 100, 6) if total else 0,
            "avg_profit_pct": round(sum(t["profit_pct"] for t in self.trades) / total, 6)
            if total
            else 0,
            "max_drawdown_pct": round(drawdown, 6),
            "trades": self.trades,
            "equity_curve": self.equity_curve,
            "assumptions": {
                "initial_equity": 100,
                "allocation_pct": 100,
                "compounding": True,
                "entry": "Keputusan close; entry open sesi berikutnya",
                "exit": "Evaluasi TP/SL pada close; exit open berikutnya termasuk gap",
                "max_holding_sessions": 30,
                "final_position": "Tutup pada close akhir periode",
                "price_adjustment": "split_and_dividend_adjusted",
                "fee_bps": 0,
                "slippage_bps": 0,
                "limitations": "Simulasi strategi teknikal, bukan rekam jejak AI. Ukuran lot dan likuiditas belum dimodelkan; biaya/slippage diasumsikan nol. TP/SL bukan jaminan harga eksekusi intraday.",
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
