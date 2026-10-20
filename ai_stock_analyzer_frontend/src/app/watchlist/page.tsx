"use client";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import {
  useUnsavedChanges,
  confirmDiscard,
} from "@/components/useUnsavedChanges";
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
  currency: string | null;
  exchange: string | null;
}
type NoteDraft = {
  value: string;
  saved: string;
  state: "saved" | "dirty" | "saving" | "failed";
  error?: string;
};
export default function WatchlistPage() {
  const { user } = useAuth();
  return (
    <Suspense fallback={<p>Memuat daftar pantauan…</p>}>
      <WatchlistWorkspace
        key={user?.id || "anonymous"}
        account={user?.id || ""}
      />
    </Suspense>
  );
}
function WatchlistWorkspace({ account }: { account: string }) {
  const [items, setItems] = useState<Item[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [notes, setNotes] = useState<Record<string, NoteDraft>>({});
  const notesRef = useRef(notes);
  const updateNotes = useCallback(
    (
      update: (value: Record<string, NoteDraft>) => Record<string, NoteDraft>,
    ) => {
      notesRef.current = update(notesRef.current);
      // Rebase low-priority server updates against the latest keystrokes.
      setNotes((previous) => update(previous));
    },
    [],
  );
  const dirty = Object.values(notes).some((n) => n.value !== n.saved);
  const beforeLeave = useUnsavedChanges(dirty);
  const params = useSearchParams();
  const rawExchange = params.get("wl_exchange") || "";
  const rawSort = params.get("wl_sort") || "name";
  const validExchange =
    !rawExchange ||
    (/^[A-Z0-9._-]{1,20}$/.test(rawExchange) &&
      (!items.length ||
        items.some(
          (item) =>
            (quotes[item.stock_ticker]?.metadata.exchange || item.exchange) ===
            rawExchange,
        )));
  const validSort = [
    "name",
    "change",
    "change_asc",
    "price_asc",
    "price_desc",
  ].includes(rawSort);
  const exchange = validExchange ? rawExchange : "";
  const sort = validSort ? rawSort : "name";
  const changeView = (key: string, value: string) => {
    const next = new URLSearchParams(params.toString());
    if (value && value !== "name") next.set(key, value);
    else next.delete(key);
    window.history.pushState(
      null,
      "",
      "/watchlist" + (next.size ? "?" + next : ""),
    );
  };
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dialogError, setDialogError] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const loadVersion = useRef(0);
  const alive = useRef(true);
  const load = useCallback(
    async (signal?: AbortSignal) => {
      const version = ++loadVersion.current;
      const current = () =>
        alive.current && version === loadVersion.current && !signal?.aborted;
      try {
        const response = await apiClient.get<Item[]>("/stocks/watchlist", {
          signal,
        });
        if (!current()) return;
        setItems(response.data);
        setError("");
        updateNotes((previous) =>
          Object.fromEntries(
            response.data.map((item) => {
              const old = previous[item.stock_ticker];
              const saved = item.notes || "";
              return [
                item.stock_ticker,
                old && (old.value !== old.saved || old.state === "saving")
                  ? {
                      ...old,
                      saved: old.state === "saving" ? old.saved : saved,
                    }
                  : { value: saved, saved, state: "saved" },
              ];
            }),
          ),
        );
        const values = await Promise.allSettled(
          response.data.map(
            async (item) =>
              (
                await apiClient.get<Quote>(
                  "/stocks/" + encodeURIComponent(item.stock_ticker) + "/price",
                  { signal },
                )
              ).data,
          ),
        );
        if (!current()) return;
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
      } catch (e) {
        if (current()) setError(errorMessage(e));
      } finally {
        if (current()) setLoading(false);
      }
    },
    [updateNotes],
  );
  const invalidate = useCallback(() => {
    alive.current = false;
    loadVersion.current++;
  }, []);
  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    void load(controller.signal);
    return () => {
      invalidate();
      controller.abort();
    };
  }, [load, invalidate]);
  useEffect(() => {
    if (loading) return;
    const saved = window.history.state?.watchlistReturn;
    if (
      saved?.account !== account ||
      saved.url !== location.pathname + location.search
    )
      return;
    const timer = setTimeout(() => {
      const anchor = document.getElementById("watch-stock-" + saved.ticker);
      if (anchor) {
        anchor.focus({ preventScroll: true });
        const container =
          document.querySelector<HTMLElement>("[data-page-scroll]");
        if (container) container.scrollTop = saved.top;
        window.history.replaceState(
          { ...window.history.state, watchlistReturn: undefined },
          "",
        );
      }
    }, 0);
    return () => clearTimeout(timer);
  }, [loading, account, items, params]);
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
    if (
      notesRef.current[ticker]?.value !== notesRef.current[ticker]?.saved &&
      !confirmDiscard()
    )
      return;
    if (!window.confirm("Hapus " + ticker + " dari watchlist?")) return;
    setBusy(true);
    try {
      await apiClient.delete("/stocks/watchlist/" + encodeURIComponent(ticker));
      if (!alive.current) return;
      loadVersion.current++;
      setLoading(false);
      setItems((prev) => prev.filter((i) => i.stock_ticker !== ticker));
      updateNotes((previous) =>
        Object.fromEntries(
          Object.entries(previous).filter(([key]) => key !== ticker),
        ),
      );
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const save = async (ticker: string) => {
    const sent = notesRef.current[ticker]?.value ?? "";
    setBusy(true);
    updateNotes((previous) => ({
      ...previous,
      [ticker]: { ...previous[ticker], state: "saving", error: "" },
    }));
    try {
      const r = await apiClient.patch<Item>(
        "/stocks/watchlist/" + encodeURIComponent(ticker),
        { notes: sent },
      );
      if (!alive.current) return;
      loadVersion.current++;
      setLoading(false);
      setItems((previous) =>
        previous.map((item) => (item.stock_ticker === ticker ? r.data : item)),
      );
      updateNotes((previous) => ({
        ...previous,
        [ticker]: {
          value: previous[ticker].value,
          saved: r.data.notes || "",
          state:
            previous[ticker].value === (r.data.notes || "") ? "saved" : "dirty",
        },
      }));
    } catch (e) {
      if (alive.current)
        updateNotes((previous) => ({
          ...previous,
          [ticker]: {
            ...previous[ticker],
            state: "failed",
            error: errorMessage(e),
          },
        }));
    } finally {
      if (alive.current) setBusy(false);
    }
  };
  const currencyOf = (item: Item) =>
    quotes[item.stock_ticker]?.metadata.currency || item.currency || "";
  const exchangeOf = (item: Item) =>
    quotes[item.stock_ticker]?.metadata.exchange || item.exchange || "";
  const sorted = items
    .filter((i) => !exchange || exchangeOf(i) === exchange)
    .sort((a, b) => {
      if (sort.startsWith("price")) {
        const currency = currencyOf(a).localeCompare(currencyOf(b));
        if (currency) return currency;
        const av = quotes[a.stock_ticker]?.current_price,
          bv = quotes[b.stock_ticker]?.current_price;
        if (av == null) return bv == null ? 0 : 1;
        if (bv == null) return -1;
        return sort === "price_asc" ? av - bv : bv - av;
      }
      if (sort.startsWith("change")) {
        const av = quotes[a.stock_ticker]?.change_percent,
          bv = quotes[b.stock_ticker]?.change_percent;
        if (av == null) return bv == null ? 0 : 1;
        if (bv == null) return -1;
        return sort === "change_asc" ? av - bv : bv - av;
      }
      return a.stock_ticker.localeCompare(b.stock_ticker);
    });
  return (
    <AppLayout beforeLeave={beforeLeave}>
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex flex-wrap justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Daftar pantauan saham</h1>
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
        <label className="block" htmlFor="watchlist-exchange">
          <span id="watchlist-exchange-label">Filter bursa</span>{" "}
          <select
            id="watchlist-exchange"
            aria-labelledby="watchlist-exchange-label"
            className="bg-slate-900 p-2 rounded"
            value={exchange}
            onChange={(e) => changeView("wl_exchange", e.target.value)}
          >
            <option value="">Semua bursa</option>
            {[...new Set(items.map(exchangeOf).filter(Boolean))]
              .sort()
              .map((v) => (
                <option key={v}>{v}</option>
              ))}
          </select>
        </label>
        <label htmlFor="watchlist-sort">
          <span id="watchlist-sort-label">Urutkan</span>{" "}
          <select
            id="watchlist-sort"
            aria-labelledby="watchlist-sort-label"
            className="bg-slate-900 p-2 rounded"
            value={sort}
            onChange={(e) => changeView("wl_sort", e.target.value)}
          >
            <option value="name">Kode saham</option>
            <option value="change">Perubahan tertinggi</option>
            <option value="change_asc">Perubahan terendah</option>
            <option value="price_asc">Harga terendah per mata uang</option>
            <option value="price_desc">Harga tertinggi per mata uang</option>
          </select>
        </label>
        <p className="text-sm">
          Harga diurutkan dalam kelompok mata uang yang sama, tanpa konversi
          IDR/USD. Nilai kosong berada di akhir kelompok.
        </p>
        {(!validSort || !validExchange) && (
          <p role="status">
            Filter URL tidak valid; pilihan default digunakan. Pilih bursa atau
            urutan lagi.
          </p>
        )}
        {loading && <p role="status">Memuat daftar pantauan…</p>}
        {error && (
          <p role="alert" className="text-red-300">
            {error}
          </p>
        )}
        {!loading && !items.length && (
          <p>
            Daftar pantauan masih kosong. Tambahkan saham dari pencarian atau
            halaman detail.
          </p>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sorted.map((i) => (
            <Card key={i.id} variant="glass">
              <CardContent>
                <Link
                  id={"watch-stock-" + i.stock_ticker}
                  onNavigate={() => {
                    const container =
                      document.querySelector<HTMLElement>("[data-page-scroll]");
                    window.history.replaceState(
                      {
                        ...window.history.state,
                        watchlistReturn: {
                          account,
                          url: location.pathname + location.search,
                          ticker: i.stock_ticker,
                          top: container?.scrollTop || 0,
                        },
                      },
                      "",
                    );
                  }}
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
                  value={notes[i.stock_ticker]?.value ?? ""}
                  onChange={(e) => {
                    const value = e.currentTarget.value;
                    updateNotes((previous) => ({
                      ...previous,
                      [i.stock_ticker]: {
                        ...previous[i.stock_ticker],
                        value,
                        state:
                          previous[i.stock_ticker]?.state === "saving"
                            ? "saving"
                            : value === previous[i.stock_ticker]?.saved
                              ? "saved"
                              : "dirty",
                        error: "",
                      },
                    }));
                  }}
                />
                <p role="status" data-note-status={i.stock_ticker}>
                  {notes[i.stock_ticker]?.state === "saving"
                    ? "Menyimpan catatan…"
                    : notes[i.stock_ticker]?.value !==
                        notes[i.stock_ticker]?.saved
                      ? "Catatan belum disimpan"
                      : "Catatan tersimpan"}
                </p>
                {notes[i.stock_ticker]?.error && (
                  <p role="alert">
                    {notes[i.stock_ticker].error} Draft tetap tersedia; coba
                    Simpan Catatan lagi.
                  </p>
                )}
                <div className="flex gap-2 mt-2">
                  <Button
                    variant="outline"
                    disabled={
                      busy ||
                      notes[i.stock_ticker]?.value ===
                        notes[i.stock_ticker]?.saved
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
            Tambah saham ke daftar pantauan
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
                  disabled={
                    busy || items.some((i) => i.stock_ticker === s.ticker)
                  }
                  className="w-full text-left border border-slate-700 rounded p-3"
                  onClick={() => add(s)}
                >
                  {s.ticker} · {s.company_name}{" "}
                  {items.some((i) => i.stock_ticker === s.ticker)
                    ? "· Sudah ditambahkan"
                    : ""}
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
