"use client";
import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AppLayout } from "@/components/layout/AppLayout";
import { AIReportCard } from "@/components/stock/AIReportCard";
import { DataStatus } from "@/components/stock/DataStatus";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { ChartData } from "@/components/charts/StockChart";
import { apiClient, errorMessage } from "@/services/api";
import {
  Analysis,
  Stock,
  Quote,
  formatPrice,
  MarketMetadata,
} from "@/services/market";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";
const StockChart = dynamic(
  () => import("@/components/charts/StockChart").then((m) => m.StockChart),
  { ssr: false },
);
interface PriceRow {
  trading_date: string;
  open: string | number;
  high: string | number;
  low: string | number;
  close: string | number;
  volume: number;
  ema_20: string | number | null;
  ema_50: string | number | null;
  ema_200: string | number | null;
  rsi_14: string | number | null;
  macd: string | number | null;
  macd_signal: string | number | null;
}
const numeric = (v: string | number | null) => (v == null ? null : Number(v));
export default function StockDetailPage() {
  const ticker = String(useParams().ticker).toUpperCase();
  return <StockDetail key={ticker} ticker={ticker} />;
}
function StockDetail({ ticker }: { ticker: string }) {
  const { fetchUser } = useAuth();
  const { addToast } = useToast();
  const [chart, setChart] = useState<ChartData[]>([]);
  const [metadata, setMetadata] = useState<MarketMetadata | null>(null);
  const [profile, setProfile] = useState<Stock | null>(null);
  const [watched, setWatched] = useState(false);
  const [job, setJob] = useState<{
    id: string;
    status: string;
    error: { message: string } | null;
  } | null>(null);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [actionError, setActionError] = useState("");
  const [errors, setErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [stage, setStage] = useState("");
  const [range, setRange] = useState("1Y");
  const [adding, setAdding] = useState(false);
  const load = useCallback(
    (signal?: AbortSignal) => {
      return Promise.allSettled([
        apiClient.get(
          "/stocks/" + encodeURIComponent(ticker) + "/chart?per_page=1825",
          { signal },
        ),
        apiClient.get<Quote>(
          "/stocks/" + encodeURIComponent(ticker) + "/price",
          { signal },
        ),
        apiClient.get<Analysis>(
          "/stocks/" + encodeURIComponent(ticker) + "/analysis/latest",
          { signal },
        ),
      ]).then(async (results) => {
        if (signal?.aborted) return;
        const failures: string[] = [];
        const c = results[0];
        if (c.status === "fulfilled") {
          setMetadata(c.value.data.metadata);
          setChart(
            c.value.data.data.map((p: PriceRow) => ({
              time: p.trading_date,
              open: Number(p.open),
              high: Number(p.high),
              low: Number(p.low),
              close: Number(p.close),
              volume: p.volume,
              ema20: numeric(p.ema_20),
              ema50: numeric(p.ema_50),
              ema200: numeric(p.ema_200),
              rsi: numeric(p.rsi_14),
              macd: numeric(p.macd),
              macdSignal: numeric(p.macd_signal),
            })),
          );
        } else failures.push("Grafik: " + errorMessage(c.reason));
        const q = results[1];
        if (q.status === "fulfilled") setQuote(q.value.data);
        else failures.push("Harga: " + errorMessage(q.reason));
        const a = results[2];
        if (a.status === "fulfilled") setAnalysis(a.value.data);
        else failures.push("Analisis: " + errorMessage(a.reason));
        setErrors(failures);
        setLoading(false);
      });
    },
    [ticker],
  );
  useEffect(() => {
    const c = new AbortController();
    apiClient
      .get("/stocks", {
        params: { q: ticker, per_page: 100 },
        signal: c.signal,
      })
      .then((r) =>
        setProfile(r.data.data.find((s: Stock) => s.ticker === ticker) || null),
      )
      .catch(() => undefined);
    apiClient
      .get("/stocks/watchlist", { signal: c.signal })
      .then((r) =>
        setWatched(
          r.data.some(
            (i: { stock_ticker: string }) => i.stock_ticker === ticker,
          ),
        ),
      )
      .catch(() => undefined);
    apiClient
      .get("/analysis/jobs", {
        signal: c.signal,
        params: { ticker, active: true },
      })
      .then((r) => {
        if (r.data.data[0]) setJob(r.data.data[0]);
      })
      .catch(() => undefined);
    return () => c.abort();
  }, [ticker]);
  const jobId = job?.id;
  const pendingJob = job && !["succeeded", "failed"].includes(job.status);
  useEffect(() => {
    if (!jobId || !pendingJob) return;
    const c = new AbortController();
    const timer = setInterval(async () => {
      try {
        const r = await apiClient.get("/analysis/jobs/" + jobId, {
          signal: c.signal, skipAuthRefresh: true,
        });
        if (c.signal.aborted) return;
        if (r.data.status === "failed")
          setActionError(r.data.error?.message || "Job gagal; coba lagi.");
        if (["succeeded", "failed"].includes(r.data.status)) {
          await load(c.signal);
          await fetchUser().catch(() => undefined);
        }
        if (!c.signal.aborted) setJob(r.data);
      } catch (e) {
        if (!c.signal.aborted) setActionError(errorMessage(e));
      }
    }, 1500);
    return () => {
      c.abort();
      clearInterval(timer);
    };
  }, [jobId, pendingJob, load, fetchUser]);
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);
  const sync = async (withAI: boolean) => {
    setActionError("");
    if (withAI) {
      setStage("Mengantrekan analisis…");
      try {
        const response = await apiClient.post("/analysis/jobs", {
          ticker,
          idempotency_key: crypto.randomUUID(),
        });
        setJob(response.data);
      } catch (e) {
        setActionError(errorMessage(e));
      } finally {
        setStage("");
      }
      return;
    }
    setStage("Menyinkronkan data pasar dan indikator…");
    try {
      await apiClient.post("/stocks/" + encodeURIComponent(ticker) + "/sync");
      addToast("success", "Data pasar dan indikator berhasil disinkronkan.");
    } catch (error) {
      const message = errorMessage(error);
      setActionError(message);
      addToast("error", message);
    } finally {
      await load();
      await fetchUser().catch(() => undefined);
      setStage("");
    }
  };
  const add = async () => {
    setAdding(true);
    try {
      await apiClient.post("/stocks/watchlist", { ticker });
      setWatched(true);
      addToast("success", "Saham ditambahkan ke watchlist.");
    } catch (error) {
      addToast("error", errorMessage(error));
    } finally {
      setAdding(false);
    }
  };
  const cutoff = new Date(chart.at(-1)?.time || "1970-01-01");
  cutoff.setUTCMonth(
    cutoff.getUTCMonth() -
      ({ "1M": 1, "3M": 3, "6M": 6, "1Y": 12 }[range] || 12),
  );
  const visible = chart.filter((p) => new Date(p.time) >= cutoff);
  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto space-y-6 pb-12">
        <header className="flex flex-wrap justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">{ticker}</h1>
            <p>
              {profile?.company_name ||
                quote?.company_name ||
                "Informasi instrumen belum tersedia"}
            </p>
            <p className="text-2xl mt-2">
              {formatPrice(quote?.current_price, quote?.metadata.currency)}
            </p>
            <p>
              Perubahan antar penutupan:{" "}
              {quote?.change_percent == null
                ? "Belum tersedia"
                : quote.change_percent.toFixed(2) + "%"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2 items-start">
            <Link href={"/stock/" + encodeURIComponent(ticker) + "/backtest"}>
              <Button variant="outline">Backtest teknikal</Button>
            </Link>
            <Button
              variant="outline"
              onClick={add}
              isLoading={adding}
              disabled={watched}
            >
              {watched ? "Sudah ditambahkan" : "Tambah Watchlist"}
            </Button>
            <Button
              variant="outline"
              disabled={!!stage || !!pendingJob}
              onClick={() => sync(false)}
            >
              Sinkronkan Data
            </Button>
            <Button
              disabled={!!stage || !!pendingJob}
              onClick={() => sync(true)}
            >
              Analisis Ulang AI
            </Button>
          </div>
        </header>
        <div className="flex flex-wrap gap-3">
          {[
            ["history", "Riwayat AI"],
            ["plans", "Rencana transaksi"],
            ["monitoring", "Alert dan job"],
          ].map(([tab, label]) => (
            <Link
              className="underline p-2"
              key={tab}
              href={
                "/research?tab=" + tab + "&ticker=" + encodeURIComponent(ticker)
              }
            >
              {label}
            </Link>
          ))}
        </div>
        {job && (
          <p role="status" aria-live="polite">
            Job analisis:{" "}
            {(
              {
                queued: "Dalam antrean; Anda dapat meninggalkan halaman",
                syncing: "Mengambil data pasar",
                calculating: "Menghitung indikator",
                analyzing: "Menjalankan AI",
                persisting: "Menyimpan hasil",
                succeeded: "Hasil berhasil disimpan",
                failed: "Gagal; hasil terakhir dipertahankan",
              } as Record<string, string>
            )[job.status] || job.status}
            .{" "}
            <Link className="underline" href="/research?tab=monitoring">
              Lihat status job
            </Link>
          </p>
        )}
        <DataStatus metadata={quote?.metadata || metadata} />
        {stage && (
          <p role="status" aria-live="polite">
            {stage}
          </p>
        )}
        {(!!errors.length || !!actionError) && (
          <div
            role="alert"
            className="rounded-xl p-4 bg-red-950/40 text-red-300"
          >
            <p>
              Pembaruan belum berhasil. Data terakhir yang tersedia tetap
              ditampilkan.
            </p>
            {actionError && <p>{actionError}</p>}
            {errors.map((e, i) => (
              <p key={i}>{e}</p>
            ))}
            <button className="underline" onClick={() => load()}>
              Coba muat ulang
            </button>
          </div>
        )}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 min-w-0">
            <Card variant="glass">
              <CardContent>
                <div
                  className="flex flex-wrap gap-2 mb-4"
                  aria-label="Rentang grafik harian"
                >
                  {["1M", "3M", "6M", "1Y"].map((r) => (
                    <button
                      key={r}
                      aria-pressed={range === r}
                      className="border border-slate-600 rounded px-3 py-2"
                      onClick={() => setRange(r)}
                    >
                      {r}
                    </button>
                  ))}
                </div>
                <p className="text-sm text-slate-400 mb-4">
                  Candle harian. Rentang aktual: {visible[0]?.time || "—"}{" "}
                  sampai {visible.at(-1)?.time || "—"}. Indikator kosong berarti
                  histori belum cukup.
                </p>
                {loading ? (
                  <p role="status">Memuat grafik…</p>
                ) : visible.length ? (
                  <StockChart data={visible} />
                ) : (
                  <p>
                    Data historis belum tersedia. Sinkronkan data untuk memulai.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
          <AIReportCard analysis={analysis} />
        </div>
      </div>
    </AppLayout>
  );
}
