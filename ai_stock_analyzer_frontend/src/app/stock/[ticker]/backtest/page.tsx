"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { formatWib } from "@/services/time";
import { AppLayout } from "@/components/layout/AppLayout";
import { EquityChart } from "@/components/charts/EquityChart";
import { downloadResult } from "@/services/download";
import { apiClient, runBacktest, errorMessage } from "@/services/api";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Play,
  TrendingUp,
  Target,
  AlertTriangle,
  Settings,
} from "lucide-react";
import Link from "next/link";
import clsx from "clsx";

interface TradeRecord {
  buy_date: string;
  sell_date: string;
  buy_price: number;
  sell_price: number;
  profit_pct: number;
  status: "WIN" | "LOSS" | "BREAKEVEN";
  reason: string;
  exit_reason: string;
}

interface BacktestResult {
  run_id?: string;
  created_at?: string | null;
  data_revision?: string | null;
  source?: string;
  net_return_pct: number;
  total_fees: number;
  equity_curve: { date: string; equity: number }[];
  benchmark: { net_return_pct?: number; final_equity?: number };
  ticker: string;
  period_years: number;
  total_trades: number;
  win_rate_pct: number;
  avg_profit_pct: number;
  max_drawdown_pct: number;
  trades: TradeRecord[];
  data_start: string;
  data_end: string;
  effective_parameters: {
    years: number;
    initial_capital?: number;
    lot_size?: number | null;
    target_profit_pct: number;
    stop_loss_pct: number;
  };
  assumptions: {
    entry: string;
    exit: string;
    limitations: string;
    initial_equity: number;
    max_holding_sessions: number;
    fee_bps: number | null;
    buy_fee_bps: number;
    sell_fee_bps: number;
    slippage_bps: number;
  };
}

export default function BacktestPage() {
  const params = useParams();
  const ticker = String(params.ticker).toUpperCase();

  const { user } = useAuth();
  return (
    <BacktestWorkspace
      key={`${user?.id || "anonymous"}:${ticker}`}
      ticker={ticker}
    />
  );
}

function BacktestWorkspace({ ticker }: { ticker: string }) {
  // Form State
  const [years, setYears] = useState(3);
  const [targetProfit, setTargetProfit] = useState(10);
  const [stopLoss, setStopLoss] = useState(5);

  // Execution State
  const [costs, setCosts] = useState({
    initial_capital: ticker.endsWith(".JK") ? 10000000 : 10000,
    lot_size: ticker.endsWith(".JK") ? 100 : 1,
    buy_fee_bps: 0,
    sell_fee_bps: 0,
    slippage_bps: 0,
  });
  const [runs, setRuns] = useState<
    { id: string; ticker: string; created_at: string }[]
  >([]);
  const [selected, setSelected] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState("");
  const [result, setResult] = useState<BacktestResult | null>(null);
  const generation = useRef(0);
  const historyGeneration = useRef(0);
  const alive = useRef(true);
  const request = useRef<AbortController | null>(null);
  const loadRuns = useCallback(
    async (signal?: AbortSignal) => {
      const revision = ++historyGeneration.current;
      try {
        const response = await apiClient.get("/backtests", { signal });
        if (
          alive.current &&
          revision === historyGeneration.current &&
          !signal?.aborted
        ) {
          setRuns(
            response.data.data.filter(
              (r: { ticker: string }) => r.ticker === ticker,
            ),
          );
          setHistoryError("");
        }
      } catch (e) {
        if (
          alive.current &&
          revision === historyGeneration.current &&
          !signal?.aborted
        )
          setHistoryError("Riwayat belum dapat diperbarui. " + errorMessage(e));
      }
    },
    [ticker],
  );
  const invalidate = useCallback(() => {
    alive.current = false;
    generation.current++;
    historyGeneration.current++;
    request.current?.abort();
  }, []);
  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    void Promise.resolve().then(() => {
      if (!controller.signal.aborted) return loadRuns(controller.signal);
    });
    return () => {
      controller.abort();
      invalidate();
    };
  }, [loadRuns, invalidate]);

  async function execute(runId?: string) {
    const current = ++generation.current;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    const active = () => alive.current && generation.current === current;
    setSelected(runId || "");
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = runId
        ? await apiClient.get<BacktestResult>(
            "/backtests/" + encodeURIComponent(runId),
            { signal: controller.signal },
          )
        : await runBacktest(
            ticker,
            {
              years,
              target_profit_pct: targetProfit,
              stop_loss_pct: stopLoss,
              ...costs,
            },
            controller.signal,
          );
      if (!active()) return;
      const value = response.data as BacktestResult;
      if (
        !value.run_id ||
        value.ticker !== ticker ||
        (runId && value.run_id !== runId)
      )
        throw new Error(
          "Identitas hasil berbeda dari run yang dipilih. Coba muat ulang riwayat.",
        );
      setResult(value);
      setSelected(value.run_id);
      if (!runId) void loadRuns();
    } catch (e) {
      if (active() && !controller.signal.aborted) setError(errorMessage(e));
    } finally {
      if (active()) setLoading(false);
    }
  }
  const handleRunBacktest = (e: React.FormEvent) => {
    e.preventDefault();
    void execute();
  };

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto py-8">
        <div className="flex items-center mb-6">
          <Link
            href={`/stock/${ticker}`}
            className="text-gray-400 hover:text-white transition-colors mr-4"
          >
            <ArrowLeft width={24} height={24} />
          </Link>
          <h1 className="text-3xl font-bold">Backtest Teknikal: {ticker}</h1>
        </div>

        {!!runs.length && (
          <label className="block mb-6" htmlFor="backtest-run">
            <span id="backtest-run-label">
              Buka run tersimpan tanpa simulasi ulang
            </span>
            <select
              id="backtest-run"
              aria-labelledby="backtest-run-label"
              className="block w-full bg-slate-900 rounded p-3"
              value={selected}
              onChange={(e) => {
                if (e.target.value) void execute(e.target.value);
              }}
            >
              <option value="">Pilih run</option>
              {selected && !runs.some((run) => run.id === selected) && (
                <option value={selected}>
                  {formatWib(result?.created_at)} · {selected.slice(0, 8)}
                </option>
              )}
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {formatWib(r.created_at)} · {r.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </label>
        )}
        {historyError && (
          <p role="status">
            {historyError}{" "}
            <button className="underline" onClick={() => void loadRuns()}>
              Muat ulang riwayat
            </button>
          </p>
        )}
        {loading && <p role="status">Memuat hasil pilihan terkini…</p>}
        {error && selected && (
          <button
            className="underline min-h-11"
            onClick={() => void execute(selected)}
          >
            Coba muat run lagi
          </button>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Pengaturan simulasi Form */}
          <div className="lg:col-span-1">
            <div className="bg-dark-800/50 backdrop-blur-md border border-dark-600 rounded-xl p-6 sticky top-24">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <Settings width={20} height={20} className="text-primary-400" />
                Pengaturan simulasi
              </h2>

              <form onSubmit={handleRunBacktest} className="space-y-6">
                <div>
                  <label
                    htmlFor="backtest-years"
                    className="block text-sm font-medium text-gray-300 mb-2"
                  >
                    Periode (tahun): {years}
                  </label>
                  <input
                    id="backtest-years"
                    type="range"
                    min="1"
                    max="5"
                    value={years}
                    onChange={(e) => setYears(parseInt(e.target.value))}
                    className="w-full accent-primary-500"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>1Y</span>
                    <span>5Y</span>
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="backtest-target"
                    className="block text-sm font-medium text-gray-300 mb-2 flex items-center gap-2"
                  >
                    <Target width={16} height={16} className="text-green-400" />
                    Target keuntungan (%)
                  </label>
                  <input
                    id="backtest-target"
                    type="number"
                    min="0.1"
                    max="20"
                    step="0.1"
                    value={targetProfit}
                    onChange={(e) =>
                      setTargetProfit(parseFloat(e.target.value))
                    }
                    className="w-full bg-dark-700 border border-dark-500 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary-500"
                  />
                </div>

                <div>
                  <label
                    htmlFor="backtest-stop"
                    className="block text-sm font-medium text-gray-300 mb-2 flex items-center gap-2"
                  >
                    <AlertTriangle
                      width={16}
                      height={16}
                      className="text-red-400"
                    />
                    Batas kerugian (%)
                  </label>
                  <input
                    id="backtest-stop"
                    type="number"
                    min="0.1"
                    max="10"
                    step="0.1"
                    value={stopLoss}
                    onChange={(e) => setStopLoss(parseFloat(e.target.value))}
                    className="w-full bg-dark-700 border border-dark-500 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-red-500"
                  />
                </div>

                <p className="text-sm text-slate-400">
                  Modal memakai currency instrumen. Biaya 0 adalah asumsi awal;
                  1 bps = 0,01%; 10 bps = 0,1%. Lot mengikuti input.
                </p>
                <details className="text-sm text-slate-300 space-y-2">
                  <summary className="cursor-pointer min-h-11 py-2">
                    Memahami hasil dan biaya
                  </summary>
                  <p>
                    Tingkat kemenangan adalah persentase transaksi yang untung.
                    Rata-rata hasil mencakup seluruh transaksi. Penurunan modal
                    maksimum mengukur turunnya equity dari puncaknya, bukan
                    hanya kerugian satu transaksi.
                  </p>
                  <p>
                    Fee adalah biaya transaksi; slippage adalah asumsi selisih
                    harga eksekusi. Hasil historis tidak menjamin profit di masa
                    depan.
                  </p>
                </details>
                {(
                  [
                    ["initial_capital", "Modal awal"],
                    ["lot_size", "Lembar per lot"],
                    ["buy_fee_bps", "Fee beli (bps)"],
                    ["sell_fee_bps", "Fee jual (bps)"],
                    ["slippage_bps", "Slippage (bps)"],
                  ] as const
                ).map(([key, label]) => (
                  <label key={key} className="block">
                    {label}
                    <input
                      type="number"
                      step="any"
                      min={
                        key === "initial_capital" || key === "lot_size" ? 1 : 0
                      }
                      max={key.endsWith("bps") ? 1000 : undefined}
                      required
                      value={costs[key]}
                      onChange={(e) =>
                        setCosts((v) => ({
                          ...v,
                          [key]: Number(e.target.value),
                        }))
                      }
                      className="w-full rounded bg-slate-900 border border-slate-600 p-3"
                    />
                  </label>
                ))}
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
                      Jalankan backtest
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>

          {/* Results Area */}
          <div className="lg:col-span-2">
            {error && (
              <div
                role="alert"
                className="bg-red-500/10 border border-red-500/50 text-red-500 p-4 rounded-lg mb-6"
              >
                {error}
              </div>
            )}

            {!result && !loading && !error && (
              <div className="bg-dark-800/30 border border-dark-600 border-dashed rounded-xl p-12 text-center text-gray-400 flex flex-col items-center justify-center h-full min-h-[400px]">
                <TrendingUp
                  width={48}
                  height={48}
                  className="text-dark-500 mb-4 opacity-50"
                />
                <p className="text-lg">
                  Atur parameter strategi lalu jalankan backtest untuk melihat
                  hasil.
                </p>
              </div>
            )}

            {result && (
              <div
                role="region"
                aria-label="Hasil backtest aktif"
                className="animate-in fade-in slide-in-from-bottom-4 duration-500"
              >
                <div className="rounded border border-sky-700 p-4 mb-5 space-y-2 break-words">
                  <h2 className="text-xl">Hasil tersimpan: {result.ticker}</h2>
                  <p>
                    ID run: <span className="break-all">{result.run_id}</span>
                  </p>
                  <p>Dibuat: {formatWib(result.created_at)}</p>
                  <p>
                    Sumber: {result.source || "Belum tersedia"} · Revisi:{" "}
                    <span className="break-all">
                      {result.data_revision || "Belum tersedia"}
                    </span>
                  </p>
                  <p>
                    Lot:{" "}
                    {result.effective_parameters.lot_size ?? "Belum tersedia"}{" "}
                    lembar. Parameter di bawah milik hasil ini; form di samping
                    menyiapkan simulasi berikutnya.
                  </p>
                </div>
                <div className="text-sm text-slate-400 mb-6 space-y-2">
                  <p>
                    Simulasi strategi teknikal harian, bukan rekam jejak
                    rekomendasi AI.
                  </p>
                  <p>
                    Data aktual: {result.data_start} sampai {result.data_end}.
                    Periode diminta: {result.effective_parameters.years} tahun.
                  </p>
                  <p>
                    Parameter efektif: target{" "}
                    {result.effective_parameters.target_profit_pct}% · stop{" "}
                    {result.effective_parameters.stop_loss_pct}%.
                  </p>
                  <p>
                    {result.assumptions.entry}. {result.assumptions.exit}.
                  </p>
                  <p>
                    Modal awal {result.assumptions.initial_equity}; alokasi
                    100%, compounding. Maksimum{" "}
                    {result.assumptions.max_holding_sessions} sesi.
                  </p>
                  <p>
                    Fee beli: {result.assumptions.buy_fee_bps} bps; fee jual:{" "}
                    {result.assumptions.sell_fee_bps} bps; slippage:{" "}
                    {result.assumptions.slippage_bps} bps.{" "}
                    {result.assumptions.limitations}
                  </p>
                  <p>
                    Return bersih terhadap modal awal:{" "}
                    {result.net_return_pct.toFixed(2)}% · Total fee{" "}
                    {result.total_fees.toLocaleString("id-ID")}. Buy-and-hold
                    pada periode/asumsi sama:{" "}
                    {result.benchmark.net_return_pct?.toFixed(2) ??
                      "Belum tersedia"}
                    %.
                  </p>
                  {result.run_id && (
                    <button
                      className="rounded border border-sky-600 p-3"
                      onClick={async () => {
                        const current = generation.current;
                        try {
                          await downloadResult(
                            "/backtests/" + result.run_id + "/export",
                            `backtest-${ticker}-${result.run_id}.csv`,
                            {
                              signal: request.current?.signal,
                              isCurrent: () =>
                                alive.current && current === generation.current,
                            },
                          );
                        } catch (e) {
                          if (alive.current && current === generation.current)
                            setError(errorMessage(e));
                        }
                      }}
                    >
                      Ekspor seluruh transaksi CSV
                    </button>
                  )}
                  <EquityChart points={result.equity_curve} />
                </div>
                {/* Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                  <div className="bg-dark-800/50 backdrop-blur-md border border-dark-600 rounded-xl p-4">
                    <p className="text-sm text-gray-400 mb-1">
                      Tingkat kemenangan
                    </p>
                    <p
                      className={clsx(
                        "text-2xl font-bold",
                        result.win_rate_pct >= 50
                          ? "text-green-400"
                          : "text-red-400",
                      )}
                    >
                      {result.win_rate_pct.toFixed(1)}%
                    </p>
                  </div>
                  <div className="bg-dark-800/50 backdrop-blur-md border border-dark-600 rounded-xl p-4">
                    <p className="text-sm text-gray-400 mb-1">
                      Jumlah transaksi
                    </p>
                    <p className="text-2xl font-bold">{result.total_trades}</p>
                  </div>
                  <div className="bg-dark-800/50 backdrop-blur-md border border-dark-600 rounded-xl p-4">
                    <p className="text-sm text-gray-400 mb-1">
                      Rata-rata hasil
                    </p>
                    <p
                      className={clsx(
                        "text-2xl font-bold",
                        result.avg_profit_pct > 0
                          ? "text-green-400"
                          : "text-red-400",
                      )}
                    >
                      {result.avg_profit_pct.toFixed(2)}%
                    </p>
                  </div>
                  <div className="bg-dark-800/50 backdrop-blur-md border border-dark-600 rounded-xl p-4">
                    <p className="text-sm text-gray-400 mb-1">
                      Penurunan modal maksimum
                    </p>
                    <p className="text-2xl font-bold text-red-400">
                      {result.max_drawdown_pct.toFixed(2)}%
                    </p>
                  </div>
                </div>

                {/* Riwayat transaksi */}
                <h3 className="text-xl font-semibold mb-4">
                  Riwayat transaksi
                </h3>
                <div className="bg-dark-800/50 backdrop-blur-md border border-dark-600 rounded-xl overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-dark-700/50 text-gray-300 text-sm border-b border-dark-600">
                          <th className="p-4 font-medium">Tanggal beli</th>
                          <th className="p-4 font-medium">Tanggal jual</th>
                          <th className="p-4 font-medium text-right">
                            Hasil (%)
                          </th>
                          <th className="p-4 font-medium text-center">
                            Status
                          </th>
                          <th className="p-4 font-medium">Alasan keluar</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-dark-600/50">
                        {result.trades.length > 0 ? (
                          result.trades.map((trade, idx) => (
                            <tr
                              key={idx}
                              className="hover:bg-dark-700/30 transition-colors"
                            >
                              <td className="p-4 text-sm">{trade.buy_date}</td>
                              <td className="p-4 text-sm">{trade.sell_date}</td>
                              <td
                                className={clsx(
                                  "p-4 text-sm text-right font-medium",
                                  trade.profit_pct > 0
                                    ? "text-green-400"
                                    : "text-red-400",
                                )}
                              >
                                {trade.profit_pct.toFixed(2)}%
                              </td>
                              <td className="p-4 text-center">
                                <span
                                  className={clsx(
                                    "inline-flex items-center justify-center px-2 py-1 rounded text-xs font-bold w-16",
                                    trade.status === "WIN"
                                      ? "bg-green-500/20 text-green-400 border border-green-500/30"
                                      : "bg-red-500/20 text-red-400 border border-red-500/30",
                                  )}
                                >
                                  {trade.status === "WIN"
                                    ? "Untung"
                                    : trade.status === "BREAKEVEN"
                                      ? "Impas"
                                      : "Rugi"}
                                </span>
                              </td>
                              <td className="p-4 text-sm text-gray-400">
                                {trade.exit_reason}: {trade.reason}
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td
                              colSpan={5}
                              className="p-8 text-center text-gray-500"
                            >
                              Tidak ada transaksi yang memenuhi strategi ini.
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
