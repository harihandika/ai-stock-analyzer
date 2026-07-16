"""
AI Stock Analyzer - Backtesting Engine
CLI script untuk menguji efektivitas algoritma VPA + SMC pada data historis.
"""

import argparse
import asyncio
import pandas as pd
from rich.console import Console
from rich.table import Table
from typing import List, Dict

from app.infrastructure.market_data import fetch_stock_history_async
from app.services.indicator_engine import calculate_indicators, detect_vpa_signals
from app.services.pattern_engine import detect_swing_points, detect_double_bottom
from app.services.wyckoff_engine import detect_wyckoff_accumulation
from app.services.smc_engine import detect_fvg, detect_structure_breaks

console = Console()

class Backtester:
    def __init__(self, ticker: str, years: int, target_profit: float = 0.05, stop_loss: float = 0.03):
        self.ticker = ticker.upper()
        self.period = f"{years}y"
        self.target_profit = target_profit
        self.stop_loss = stop_loss
        
        self.trades: List[Dict] = []
        self.df = pd.DataFrame()

    async def _fetch_and_prepare_data(self):
        console.print(f"[cyan]Mengambil data {self.ticker} selama {self.period} terakhir...[/cyan]")
        df = await fetch_stock_history_async(self.ticker, period=self.period)
        
        if df.empty:
            console.print(f"[red]Error: Data untuk {self.ticker} tidak ditemukan.[/red]")
            return False
            
        console.print(f"[cyan]Menghitung indikator teknikal untuk {len(df)} baris data...[/cyan]")
        df = calculate_indicators(df)
        df = detect_vpa_signals(df)
        df = detect_swing_points(df, window=5)
        df = detect_wyckoff_accumulation(df)
        df = detect_fvg(df)
        df = detect_structure_breaks(df)
        
        self.df = df
        return True

    def run_simulation(self):
        console.print("[cyan]Memulai simulasi time-stepping (berjalan dari masa lalu ke masa kini)...[/cyan]")
        
        in_position = False
        buy_price = 0
        buy_date = None
        buy_reason = ""
        days_held = 0
        MAX_HOLD_DAYS = 30
        
        # Simulasi berjalan dari hari pertama yang punya indikator komplit
        for idx in range(50, len(self.df)):
            row = self.df.iloc[idx]
            current_date = row['trading_date']
            current_close = row['close']
            
            # Cek Exit (Jika sedang punya posisi)
            if in_position:
                days_held += 1
                profit_pct = (current_close - buy_price) / buy_price
                
                # Exit condition: Take profit, Stop Loss, atau Timeout
                if profit_pct >= self.target_profit:
                    self._record_trade(buy_date, current_date, buy_price, current_close, "WIN (Take Profit)", profit_pct, days_held, buy_reason)
                    in_position = False
                elif profit_pct <= -self.stop_loss:
                    self._record_trade(buy_date, current_date, buy_price, current_close, "LOSS (Stop Loss)", profit_pct, days_held, buy_reason)
                    in_position = False
                elif days_held >= MAX_HOLD_DAYS:
                    status = "WIN (Timeout)" if profit_pct > 0 else "LOSS (Timeout)"
                    self._record_trade(buy_date, current_date, buy_price, current_close, status, profit_pct, days_held, buy_reason)
                    in_position = False
                continue
            
            # Cek Entry (Jika tidak punya posisi)
            # Syarat Entry: 
            # 1. Wyckoff Spring + VPA Stopping Volume ATAU
            # 2. Bullish FVG + CHoCH (Pembalikan arah tren)
            
            is_spring = row.get('is_spring', False)
            stopping_vol = row.get('stopping_volume', False)
            bullish_fvg = row.get('bullish_fvg', False)
            choch = row.get('choch', False)
            
            if is_spring and stopping_vol:
                in_position = True
                buy_price = current_close
                buy_date = current_date
                buy_reason = "Wyckoff Spring + Stopping Vol"
                days_held = 0
            elif bullish_fvg and choch:
                in_position = True
                buy_price = current_close
                buy_date = current_date
                buy_reason = "SMC Bullish FVG + CHoCH"
                days_held = 0
                
    def _record_trade(self, buy_date, sell_date, buy_price, sell_price, status, profit_pct, days_held, reason):
        self.trades.append({
            "buy_date": buy_date,
            "sell_date": sell_date,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "status": status,
            "profit_pct": profit_pct * 100,
            "days_held": days_held,
            "reason": reason
        })
        
    def get_results_dict(self) -> dict:
        total_trades = len(self.trades)
        if total_trades == 0:
            return {
                "ticker": self.ticker,
                "period": self.period,
                "total_trades": 0,
                "win_rate": 0.0,
                "avg_profit_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "recent_trades": []
            }
            
        wins = [t for t in self.trades if "WIN" in t["status"]]
        losses = [t for t in self.trades if "LOSS" in t["status"]]
        
        win_rate = (len(wins) / total_trades) * 100
        avg_profit = sum([t["profit_pct"] for t in self.trades]) / total_trades
        max_drawdown = min([t["profit_pct"] for t in self.trades]) if losses else 0
        
        return {
            "ticker": self.ticker,
            "period": self.period,
            "total_trades": total_trades,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 2),
            "avg_profit_pct": round(avg_profit, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "recent_trades": self.trades[-10:]
        }
        
    def print_results(self):
        total_trades = len(self.trades)
        if total_trades == 0:
            console.print("[yellow]Tidak ada sinyal entry yang terdeteksi selama periode ini.[/yellow]")
            return
            
        wins = [t for t in self.trades if "WIN" in t["status"]]
        losses = [t for t in self.trades if "LOSS" in t["status"]]
        
        win_rate = (len(wins) / total_trades) * 100
        avg_profit = sum([t["profit_pct"] for t in self.trades]) / total_trades
        max_drawdown = min([t["profit_pct"] for t in self.trades]) if losses else 0
        
        console.print("\n[bold green]=== HASIL BACKTESTING ===[/bold green]")
        console.print(f"Ticker: {self.ticker}")
        console.print(f"Periode: {self.period}")
        console.print(f"Total Trade: {total_trades}")
        console.print(f"Win Rate: {win_rate:.2f}% ({len(wins)} Win / {len(losses)} Loss)")
        console.print(f"Avg Profit/Trade: {avg_profit:.2f}%")
        console.print(f"Max Drawdown: {max_drawdown:.2f}%")
        
        # Print Table
        table = Table(title="Daftar Transaksi (Sampel max 10 terakhir)")
        table.add_column("Buy Date", style="cyan")
        table.add_column("Sell Date", style="cyan")
        table.add_column("Reason", style="magenta")
        table.add_column("Hold", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("Profit %", justify="right")
        
        for t in self.trades[-10:]:
            color = "green" if "WIN" in t["status"] else "red"
            table.add_row(
                str(t["buy_date"])[:10],
                str(t["sell_date"])[:10],
                t["reason"],
                f"{t['days_held']} hari",
                f"[{color}]{t['status']}[/{color}]",
                f"[{color}]{t['profit_pct']:.2f}%[/{color}]"
            )
            
        console.print(table)


async def main():
    parser = argparse.ArgumentParser(description="AI Stock Analyzer - Backtesting Engine")
    parser.add_argument("--ticker", type=str, required=True, help="Simbol saham (contoh: BBCA.JK)")
    parser.add_argument("--years", type=int, default=3, help="Periode backtest dalam tahun (default: 3)")
    parser.add_argument("--tp", type=float, default=0.05, help="Target profit dalam desimal (default: 0.05 = 5%)")
    parser.add_argument("--sl", type=float, default=0.03, help="Stop loss dalam desimal (default: 0.03 = 3%)")
    
    args = parser.parse_args()
    
    backtester = Backtester(args.ticker, args.years, args.tp, args.sl)
    success = await backtester._fetch_and_prepare_data()
    
    if success:
        backtester.run_simulation()
        backtester.print_results()

if __name__ == "__main__":
    asyncio.run(main())
