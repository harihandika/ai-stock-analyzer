"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AppLayout } from "@/components/layout/AppLayout";
import { Card, CardContent } from "@/components/ui/Card";
import { DataStatus } from "@/components/stock/DataStatus";
import { useAuth } from "@/contexts/AuthContext";
import { FirstSteps } from "@/components/FirstSteps";
import { apiClient, errorMessage } from "@/services/api";
import { Quote, Stock, formatPrice } from "@/services/market";
interface Pick {
  ticker: string;
  company_name: string;
  recommendation: string;
  confidence_score: number | null;
  analysis_date: string;
}
export default function DashboardPage() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [total, setTotal] = useState<number | null>(null);
  const [count, setCount] = useState<number | null>(null);
  const [picks, setPicks] = useState<Pick[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const load = useCallback(
    (signal?: AbortSignal) => {
      return Promise.allSettled([
        apiClient.get("/stocks/watchlist", { signal }),
        apiClient.get("/stocks?per_page=6&page=" + page, { signal }),
        apiClient.get("/stocks/recommendations", { signal }),
      ]).then(async (results) => {
        if (signal?.aborted) return;
        const issues: string[] = [];
        const w = results[0];
        if (w.status === "fulfilled") setCount(w.value.data.length);
        else issues.push("Watchlist: " + errorMessage(w.reason));
        const s = results[1];
        if (s.status === "fulfilled") {
          setStocks(s.value.data.data);
          setTotal(s.value.data.pagination.total);
          const values = await Promise.allSettled(
            (s.value.data.data as Stock[]).map(
              async (stock) =>
                (
                  await apiClient.get<Quote>(
                    "/stocks/" + encodeURIComponent(stock.ticker) + "/price",
                    { signal },
                  )
                ).data,
            ),
          );
          if (signal?.aborted) return;
          setQuotes((previous) => ({
            ...previous,
            ...Object.fromEntries(
              values.flatMap((v) =>
                v.status === "fulfilled" ? [[v.value.ticker, v.value]] : [],
              ),
            ),
          }));
          if (values.some((v) => v.status === "rejected"))
            issues.push(
              "Sebagian harga gagal dimuat; nilai yang tersedia ditampilkan.",
            );
        } else issues.push("Daftar saham: " + errorMessage(s.reason));
        const a = results[2];
        if (a.status === "fulfilled") setPicks(a.value.data.data);
        else issues.push("Rekomendasi: " + errorMessage(a.reason));
        setErrors(issues);
        setLoading(false);
      });
    },
    [page],
  );
  useEffect(() => {
    const c = new AbortController();
    void load(c.signal);
    return () => c.abort();
  }, [load]);
  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto space-y-6">
        <header>
          <h1 className="text-3xl font-bold">
            Selamat Datang, {user?.full_name?.split(" ")[0]}
          </h1>
          <p className="text-slate-400">
            Pantau harga penutupan harian dan analisis teknikal saham.
          </p>
        </header>
        <FirstSteps />
        <button
          className="underline"
          onClick={() => {
            setLoading(true);
            void load();
          }}
          disabled={loading}
        >
          Muat ulang dashboard
        </button>
        {loading && <p role="status">Memuat dashboard…</p>}
        {!!errors.length && (
          <div role="alert" className="text-red-300">
            {errors.map((e) => (
              <p key={e}>{e}</p>
            ))}
          </div>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <CardContent>
              <p>Saham Pantauan</p>
              <strong className="text-2xl">{count ?? "Belum tersedia"}</strong>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <p>Total Saham Tersedia</p>
              <strong className="text-2xl">{total ?? "Belum tersedia"}</strong>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <p>Sisa Kuota AI</p>
              <strong className="text-2xl">
                {user?.quota_limit == null
                  ? "Tidak terbatas"
                  : user.quota_remaining}
              </strong>
            </CardContent>
          </Card>
        </div>
        <section className="space-y-3">
          <h2 className="text-xl font-semibold">Rekomendasi BUY</h2>
          <p className="text-sm text-slate-400">
            Hasil terverifikasi dari seluruh daftar saham, diurutkan menurut
            skor model. Bukan probabilitas keuntungan.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {picks.map((p) => (
              <Link
                key={p.ticker}
                href={"/stock/" + encodeURIComponent(p.ticker)}
              >
                <Card variant="glass">
                  <CardContent>
                    <h3 className="font-bold">{p.ticker}</h3>
                    <p>{p.company_name}</p>
                    <p className="text-emerald-400">
                      {p.recommendation} · Skor{" "}
                      {p.confidence_score == null
                        ? "belum tersedia"
                        : p.confidence_score + "%"}
                    </p>
                    <p className="text-xs text-slate-400">
                      Data: {p.analysis_date}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
          {!loading && !picks.length && (
            <p>
              Belum ada rekomendasi BUY yang cocok dengan revisi data terkini.
              Periksa status pemuatan di atas jika ada kegagalan.
            </p>
          )}
        </section>
        <section className="space-y-3">
          <h2 className="text-xl font-semibold">Ringkasan Saham</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {stocks.map((s) => (
              <Link
                key={s.ticker}
                href={"/stock/" + encodeURIComponent(s.ticker)}
              >
                <Card variant="glass">
                  <CardContent>
                    <h3 className="font-bold">{s.ticker}</h3>
                    <p>{s.company_name}</p>
                    <p className="text-lg my-2">
                      {formatPrice(
                        quotes[s.ticker]?.current_price,
                        quotes[s.ticker]?.metadata.currency,
                      )}
                    </p>
                    <DataStatus metadata={quotes[s.ticker]?.metadata} />
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
          <nav
            aria-label="Halaman daftar saham"
            className="flex flex-wrap gap-3 items-center"
          >
            <button
              className="border rounded p-2"
              disabled={loading || page === 1}
              onClick={() => {
                setLoading(true);
                setPage((v) => v - 1);
              }}
            >
              Saham sebelumnya
            </button>
            <span>
              Halaman {page} / {Math.max(1, Math.ceil((total || 0) / 6))}
            </span>
            <button
              className="border rounded p-2"
              disabled={loading || page * 6 >= (total || 0)}
              onClick={() => {
                setLoading(true);
                setPage((v) => v + 1);
              }}
            >
              Saham berikutnya
            </button>
            <Link className="underline p-2" href="/research">
              Buka screener
            </Link>
          </nav>
          {!loading && total === 0 && (
            <p>
              Belum ada saham tersimpan. Cari ticker lalu sinkronkan data pada
              halaman detail.
            </p>
          )}
        </section>
      </div>
    </AppLayout>
  );
}
