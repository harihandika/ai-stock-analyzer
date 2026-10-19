"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AppLayout } from "@/components/layout/AppLayout";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { DataStatus } from "@/components/stock/DataStatus";
import { apiClient, errorMessage } from "@/services/api";
import { Quote, Stock, formatPrice } from "@/services/market";
interface Item {
  id: string;
  stock_ticker: string;
  company_name: string;
  notes: string | null;
}
export default function WatchlistPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [sort, setSort] = useState("name");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dialogError, setDialogError] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const load = useCallback((signal?: AbortSignal) => {
    return apiClient
      .get<Item[]>("/stocks/watchlist", { signal })
      .then(async (response) => {
        if (signal?.aborted) return;
        setItems(response.data);
        setError("");
        setNotes(
          Object.fromEntries(
            response.data.map((i) => [i.stock_ticker, i.notes || ""]),
          ),
        );
        const values = await Promise.allSettled(
          response.data.map(
            async (i) =>
              (
                await apiClient.get<Quote>(
                  "/stocks/" + encodeURIComponent(i.stock_ticker) + "/price",
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
          setError(
            "Sebagian harga gagal diperbarui; data terakhir yang tersedia tetap ditampilkan.",
          );
      })
      .catch((e) => {
        if (!signal?.aborted) setError(errorMessage(e));
      })
      .finally(() => {
        if (!signal?.aborted) setLoading(false);
      });
  }, []);
  useEffect(() => {
    const c = new AbortController();
    void load(c.signal);
    return () => c.abort();
  }, [load]);
  useEffect(() => {
    const c = new AbortController();
    const timer = setTimeout(async () => {
      if (query.trim().length < 2) {
        setResults([]);
        return;
      }
      try {
        const r = await apiClient.get("/stocks", {
          params: { q: query, per_page: 10 },
          signal: c.signal,
        });
        if (!c.signal.aborted) setResults(r.data.data);
      } catch (e) {
        if (!c.signal.aborted) setDialogError(errorMessage(e));
      }
    }, 300);
    return () => {
      clearTimeout(timer);
      c.abort();
    };
  }, [query]);
  const add = async (stock: Stock) => {
    setBusy(true);
    setDialogError("");
    try {
      await apiClient.post("/stocks/watchlist", { ticker: stock.ticker });
      dialog.current?.close();
      setQuery("");
      await load();
    } catch (e) {
      setDialogError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const remove = async (ticker: string) => {
    if (!window.confirm("Hapus " + ticker + " dari watchlist?")) return;
    setBusy(true);
    try {
      await apiClient.delete("/stocks/watchlist/" + encodeURIComponent(ticker));
      setItems((prev) => prev.filter((i) => i.stock_ticker !== ticker));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const save = async (ticker: string) => {
    setBusy(true);
    setError("");
    try {
      const r = await apiClient.patch<Item>(
        "/stocks/watchlist/" + encodeURIComponent(ticker),
        { notes: notes[ticker] },
      );
      setItems((prev) =>
        prev.map((i) => (i.stock_ticker === ticker ? r.data : i)),
      );
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const sorted = [...items].sort((a, b) =>
    sort === "change"
      ? (quotes[b.stock_ticker]?.change_percent ?? -Infinity) -
        (quotes[a.stock_ticker]?.change_percent ?? -Infinity)
      : a.stock_ticker.localeCompare(b.stock_ticker),
  );
  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex flex-wrap justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Watchlist Saham</h1>
            <p>Harga penutupan harian dan catatan pribadi.</p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => {
                setDialogError("");
                dialog.current?.showModal();
              }}
            >
              Tambah Saham
            </Button>
            <Button
              variant="outline"
              disabled={loading || busy}
              onClick={() => {
                setLoading(true);
                void load();
              }}
            >
              Muat Ulang
            </Button>
          </div>
        </header>
        <label>
          Urutkan{" "}
          <select
            className="bg-slate-900 p-2 rounded"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="name">Kode saham</option>
            <option value="change">Perubahan tertinggi</option>
          </select>
        </label>
        {loading && <p role="status">Memuat watchlist…</p>}
        {error && (
          <p role="alert" className="text-red-300">
            {error}
          </p>
        )}
        {!loading && !items.length && (
          <p>
            Watchlist masih kosong. Tambahkan saham dari pencarian atau halaman
            detail.
          </p>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sorted.map((i) => (
            <Card key={i.id} variant="glass">
              <CardContent>
                <Link
                  className="text-xl font-semibold underline"
                  href={"/stock/" + encodeURIComponent(i.stock_ticker)}
                >
                  {i.stock_ticker}
                </Link>
                <p>{i.company_name}</p>
                <p className="text-2xl mt-3">
                  {formatPrice(
                    quotes[i.stock_ticker]?.current_price,
                    quotes[i.stock_ticker]?.metadata.currency,
                  )}
                </p>
                <p>
                  Perubahan:{" "}
                  {quotes[i.stock_ticker]?.change_percent == null
                    ? "Belum tersedia"
                    : quotes[i.stock_ticker].change_percent?.toFixed(2) + "%"}
                </p>
                <DataStatus metadata={quotes[i.stock_ticker]?.metadata} />
                <label className="block mt-4" htmlFor={"notes-" + i.id}>
                  Catatan pribadi
                </label>
                <textarea
                  id={"notes-" + i.id}
                  className="w-full rounded bg-slate-900 border border-slate-700 p-2"
                  maxLength={500}
                  value={notes[i.stock_ticker] || ""}
                  onChange={(e) =>
                    setNotes((prev) => ({
                      ...prev,
                      [i.stock_ticker]: e.target.value,
                    }))
                  }
                />
                <div className="flex gap-2 mt-2">
                  <Button
                    variant="outline"
                    disabled={
                      busy || (notes[i.stock_ticker] || "") === (i.notes || "")
                    }
                    onClick={() => save(i.stock_ticker)}
                  >
                    Simpan Catatan
                  </Button>
                  <Button
                    variant="outline"
                    disabled={busy}
                    onClick={() => remove(i.stock_ticker)}
                  >
                    Hapus
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        <dialog
          ref={dialog}
          aria-labelledby="watchlist-dialog-title"
          className="rounded-xl bg-slate-900 text-white p-6 border border-slate-600 w-[min(90vw,520px)] backdrop:bg-black/60"
        >
          <h2 id="watchlist-dialog-title" className="text-xl mb-4">
            Tambah Saham ke Watchlist
          </h2>
          <label htmlFor="watchlist-query">
            Cari kode atau nama perusahaan
          </label>
          <input
            id="watchlist-query"
            className="w-full p-3 rounded bg-slate-800 mt-2"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
          />
          {dialogError && (
            <p role="alert" className="text-red-300">
              {dialogError}
            </p>
          )}
          <ul className="my-4 space-y-2">
            {results.map((s) => (
              <li key={s.ticker}>
                <button
                  disabled={busy}
                  className="w-full text-left border border-slate-700 rounded p-3"
                  onClick={() => add(s)}
                >
                  {s.ticker} · {s.company_name}
                  <span className="block text-xs text-slate-400">
                    {s.exchange || "Bursa belum diketahui"} ·{" "}
                    {s.currency || "Mata uang belum diketahui"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {query.length >= 2 && !results.length && (
            <p>
              Belum ditemukan. Sinkronkan instrumen pada halaman detail terlebih
              dahulu.
            </p>
          )}
          <Button variant="outline" onClick={() => dialog.current?.close()}>
            Tutup
          </Button>
        </dialog>
      </div>
    </AppLayout>
  );
}
