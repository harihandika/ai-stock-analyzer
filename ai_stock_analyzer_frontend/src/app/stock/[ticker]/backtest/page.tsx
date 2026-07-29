'use client';

import { useState } from 'react';
import AppLayout from '@/components/layout/AppLayout';
import { runBacktest } from '@/services/api';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Play, TrendingUp, TrendingDown, Target, AlertTriangle } from 'lucide-react';
import Link from 'next/link';
import clsx from 'clsx';

interface TradeRecord {
  buy_date: string;
  sell_date: string;
  buy_price: number;
  sell_price: number;
  profit_pct: number;
  status: 'WIN' | 'LOSS';
  reason: string;
}

interface BacktestResult {
  ticker: string;
  period_years: number;
  total_trades: number;
  win_rate: number;
  avg_profit_pct: number;
  max_drawdown_pct: number;
  trades: TradeRecord[];
}

export default function BacktestPage() {
  const params = useParams();
  const ticker = params.ticker as string;
  const router = useRouter();

  // Form State
  const [years, setYears] = useState(3);
  const [targetProfit, setTargetProfit] = useState(10);
  const [stopLoss, setStopLoss] = useState(5);
  
  // Execution State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BacktestResult | null>(null);

  const handleRunBacktest = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await runBacktest(ticker, {
        years,
        target_profit_pct: targetProfit,
        stop_loss_pct: stopLoss
      });
      setResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to run backtest. Make sure data is synced.');
      if (err.response?.status === 401) {
        router.push('/login');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto py-8">
        <div className="flex items-center mb-6">
          <Link href={`/stock/${ticker}`} className="text-gray-400 hover:text-white transition-colors mr-4">
            <ArrowLeft width={24} height={24} />
          </Link>
          <h1 className="text-3xl font-bold">Strategy Backtest: {ticker}</h1>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Configuration Form */}
          <div className="lg:col-span-1">
            <div className="bg-dark-800/50 backdrop-blur-md border border-dark-600 rounded-xl p-6 sticky top-24">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <Settings width={20} height={20} className="text-primary-400" />
                Configuration
              </h2>
              
              <form onSubmit={handleRunBacktest} className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Period (Years): {years}
                  </label>
                  <input 
                    type="range" 
                    min="1" max="5" 
                    value={years} 
                    onChange={(e) => setYears(parseInt(e.target.value))}
                    className="w-full accent-primary-500"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>1Y</span><span>5Y</span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center gap-2">
                    <Target width={16} height={16} className="text-green-400" />
                    Target Profit (%)
                  </label>
                  <input 
                    type="number" 
                    min="1" max="100" 
                    value={targetProfit}
                    onChange={(e) => setTargetProfit(parseFloat(e.target.value))}
                    className="w-full bg-dark-700 border border-dark-500 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center gap-2">
                    <AlertTriangle width={16} height={16} className="text-red-400" />
                    Stop Loss (%)
                  </label>
                  <input 
                    type="number" 
                    min="1" max="100" 
                    value={stopLoss}
                    onChange={(e) => setStopLoss(parseFloat(e.target.value))}
                    className="w-full bg-dark-700 border border-dark-500 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-red-500"
                  />
                </div>

                <button 
                  type="submit" 
                  disabled={loading}
                  className="w-full bg-primary-600 hover:bg-primary-500 text-white font-medium py-3 rounded-lg flex justify-center items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  ) : (
                    <>
                      <Play width={18} height={18} />
                      Run Backtest
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>

          {/* Results Area */}
          <div className="lg:col-span-2">
            {error && (
              <div className="bg-red-500/10 border border-red-500/50 text-red-500 p-4 rounded-lg mb-6">
                {error}
              </div>
            )}
            
            {!result && !loading && !error && (
              <div className="bg-dark-800/30 border border-dark-600 border-dashed rounded-xl p-12 text-center text-gray-400 flex flex-col items-center justify-center h-full min-h-[400px]">
                <TrendingUp width={48} height={48} className="text-dark-500 mb-4 opacity-50" />
                <p className="text-lg">Configure your strategy parameters and run the backtest to see the results.</p>
              </div>
            )}

            {result && (
              <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                {/* Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                  <div className="bg-dark-800/50 backdrop-blur-md border border-dark-600 rounded-xl p-4">
                    <p className="text-sm text-gray-400 mb-1">Win Rate</p>
                    <p className={clsx("text-2xl font-bold", result.win_rate >= 50 ? "text-green-400" : "text-red-400")}>
                      {(result.win_rate * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div className="bg-dark-800/50 backdrop-blur-md border border-dark-600 rounded-xl p-4">
                    <p className="text-sm text-gray-400 mb-1">Total Trades</p>
                    <p className="text-2xl font-bold">{result.total_trades}</p>
                  </div>
                  <div className="bg-dark-800/50 backdrop-blur-md border border-dark-600 rounded-xl p-4">
                    <p className="text-sm text-gray-400 mb-1">Avg Profit</p>
                    <p className={clsx("text-2xl font-bold", result.avg_profit_pct > 0 ? "text-green-400" : "text-red-400")}>
                      {(result.avg_profit_pct * 100).toFixed(2)}%
                    </p>
                  </div>
                  <div className="bg-dark-800/50 backdrop-blur-md border border-dark-600 rounded-xl p-4">
                    <p className="text-sm text-gray-400 mb-1">Max Drawdown</p>
                    <p className="text-2xl font-bold text-red-400">
                      -{(result.max_drawdown_pct * 100).toFixed(2)}%
                    </p>
                  </div>
                </div>

                {/* Trade History */}
                <h3 className="text-xl font-semibold mb-4">Trade History</h3>
                <div className="bg-dark-800/50 backdrop-blur-md border border-dark-600 rounded-xl overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-dark-700/50 text-gray-300 text-sm border-b border-dark-600">
                          <th className="p-4 font-medium">Buy Date</th>
                          <th className="p-4 font-medium">Sell Date</th>
                          <th className="p-4 font-medium text-right">Profit %</th>
                          <th className="p-4 font-medium text-center">Status</th>
                          <th className="p-4 font-medium">Reason</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-dark-600/50">
                        {result.trades.length > 0 ? (
                          result.trades.map((trade, idx) => (
                            <tr key={idx} className="hover:bg-dark-700/30 transition-colors">
                              <td className="p-4 text-sm">{trade.buy_date}</td>
                              <td className="p-4 text-sm">{trade.sell_date}</td>
                              <td className={clsx("p-4 text-sm text-right font-medium", trade.profit_pct > 0 ? "text-green-400" : "text-red-400")}>
                                {(trade.profit_pct * 100).toFixed(2)}%
                              </td>
                              <td className="p-4 text-center">
                                <span className={clsx(
                                  "inline-flex items-center justify-center px-2 py-1 rounded text-xs font-bold w-16",
                                  trade.status === 'WIN' ? "bg-green-500/20 text-green-400 border border-green-500/30" : "bg-red-500/20 text-red-400 border border-red-500/30"
                                )}>
                                  {trade.status}
                                </span>
                              </td>
                              <td className="p-4 text-sm text-gray-400">{trade.reason}</td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={5} className="p-8 text-center text-gray-500">
                              No trades executed based on this strategy.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
