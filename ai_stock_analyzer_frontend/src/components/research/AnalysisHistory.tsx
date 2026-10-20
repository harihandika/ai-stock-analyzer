"use client";

import { useEffect, useRef, useState } from "react";
import { apiClient, errorMessage } from "@/services/api";
import { downloadResult } from "@/services/download";

type Analysis = {
  id: string;
  ticker: string;
  generated_at: string;
  analysis_date: string;
  recommendation: string | null;
  confidence_score: number | null;
  ai_summary: string | null;
  provider_name: string;
  model_name: string | null;
  data_revision: string | null;
  provenance: string;
};
type Comparison = {
  first: Analysis;
  second: Analysis;
  confidence_change_points: number | null;
  inputs_differ: boolean;
  explanation: string;
};
const action =
  "inline-flex min-h-11 items-center justify-center rounded border border-sky-500 px-4 py-2 disabled:opacity-50";
const date = (value: string) =>
  new Date(value).toLocaleString("id-ID", { timeZone: "Asia/Jakarta" }) +
  " WIB";

function Identity({ record }: { record: Analysis }) {
  return (
    <div className="text-sm space-y-1 break-words">
      <p>
        <strong>{record.ticker}</strong> · Hasil {record.id}
      </p>
      <p>
        Data {record.analysis_date} · Hasil {date(record.generated_at)}
      </p>
      <p>
        {record.provider_name}/{record.model_name || "Belum diketahui"} ·
        Provenance {record.provenance}
      </p>
      <p className="break-all">
        Revisi data: {record.data_revision || "Belum terverifikasi"}
      </p>
    </div>
  );
}

export function AnalysisHistory({ initialTicker }: { initialTicker: string }) {
  const [ticker, setTicker] = useState(initialTicker);
  const [activeTicker, setActiveTicker] = useState(initialTicker);
  const [rows, setRows] = useState<Analysis[]>([]);
  const [page, setPage] = useState(1);
  const [reload, setReload] = useState(0);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const version = useRef(0);
  const request = useRef<AbortController | null>(null);
  const listing = useRef<AbortController | null>(null);

  const invalidate = () => {
    version.current++;
    request.current?.abort();
    setComparison(null);
    setError("");
    setBusy(false);
  };
  useEffect(
    () => () => {
      version.current++;
      request.current?.abort();
      listing.current?.abort();
    },
    [],
  );
  useEffect(() => {
    const controller = new AbortController();
    listing.current = controller;
    apiClient
      .get("/stocks/" + encodeURIComponent(activeTicker) + "/analyses", {
        params: { page },
        signal: controller.signal,
      })
      .then(({ data }) => {
        if (controller.signal.aborted) return;
        setRows(data.data);
        setTotal(data.pagination.total);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(errorMessage(e));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [activeTicker, page, reload]);

  const compare = async () => {
    invalidate();
    const snapshot = {
      ticker: activeTicker,
      ids: [...selected],
      version: version.current,
    };
    if (snapshot.ids.length !== 2) return;
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    const current = () =>
      !controller.signal.aborted && snapshot.version === version.current;
    try {
      const { data } = await apiClient.get<Comparison>("/analyses/compare", {
        params: { first: snapshot.ids[0], second: snapshot.ids[1] },
        signal: controller.signal,
      });
      if (!current()) return;
      if (
        data.first.ticker !== snapshot.ticker ||
        data.second.ticker !== snapshot.ticker ||
        data.first.id !== snapshot.ids[0] ||
        data.second.id !== snapshot.ids[1]
      )
        throw new Error(
          "Identitas hasil tidak sesuai pilihan. Muat ulang riwayat dan coba kembali.",
        );
      setComparison(data);
    } catch (e) {
      if (current()) setError(errorMessage(e));
    } finally {
      if (current()) setBusy(false);
    }
  };
  const exportFile = async (format: "csv" | "pdf") => {
    const snapshot = version.current;
    setError("");
    setBusy(true);
    try {
      await downloadResult(
        "/stocks/" +
          encodeURIComponent(activeTicker) +
          "/analyses/export?format=" +
          format +
          (selected.length ? "&ids=" + selected.join(",") : ""),
        "analyses." + format,
      );
    } catch (e) {
      if (version.current === snapshot) setError(errorMessage(e));
    } finally {
      if (version.current === snapshot) setBusy(false);
    }
  };
  const changePage = (next: number) => {
    invalidate();
    listing.current?.abort();
    setRows([]);
    setLoading(true);
    setPage(next);
  };
  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold">Riwayat analisis</h2>
      <form
        className="flex flex-wrap gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          invalidate();
          listing.current?.abort();
          setActiveTicker(ticker.trim().toUpperCase());
          setSelected([]);
          setRows([]);
          setTotal(0);
          setLoading(true);
          setPage(1);
          setReload((n) => n + 1);
        }}
      >
        <label>
          Kode saham
          <input
            value={ticker}
            required
            maxLength={20}
            pattern="[A-Za-z0-9][A-Za-z0-9.\-]{0,19}"
            onChange={(e) => setTicker(e.target.value)}
            className="w-full rounded border border-slate-600 bg-slate-900 p-3"
          />
        </label>
        <button className={action}>Muat riwayat</button>
      </form>
      <p aria-label="Saham riwayat aktif">
        Riwayat aktif: <strong>{activeTicker}</strong>
      </p>
      <p>
        Skor model bukan peluang profit. Pilih dua hasil sesuai urutan
        perbandingan; ekspor memakai pilihan atau seluruh hasil bila tidak ada
        yang dipilih.
      </p>
      {(busy || loading) && <p role="status">Memproses…</p>}
      {error && (
        <p role="alert" className="text-red-300">
          {error}
        </p>
      )}
      <p>{total} hasil tersimpan</p>
      {rows.map((record) => (
        <article
          key={record.id}
          className="rounded border border-slate-700 p-4 space-y-2"
        >
          <label className="flex gap-3">
            <input
              type="checkbox"
              checked={selected.includes(record.id)}
              onChange={(e) => {
                invalidate();
                setSelected((ids) =>
                  e.target.checked
                    ? [...ids, record.id]
                    : ids.filter((id) => id !== record.id),
                );
              }}
            />
            Pilih {record.recommendation || "Belum tersedia"} · Skor{" "}
            {record.confidence_score ?? "—"}%
          </label>
          <Identity record={record} />
          <p>{record.ai_summary}</p>
        </article>
      ))}
      {!loading && !rows.length && (
        <p>Belum ada hasil analisis tersimpan untuk saham ini.</p>
      )}
      <div className="flex flex-wrap gap-3">
        <button
          className={action}
          disabled={page === 1 || loading}
          onClick={() => changePage(page - 1)}
        >
          Sebelumnya
        </button>
        <span>Halaman {page}</span>
        <button
          className={action}
          disabled={page * 20 >= total || loading}
          onClick={() => changePage(page + 1)}
        >
          Berikutnya
        </button>
        <button
          className={action}
          disabled={selected.length !== 2 || busy || loading}
          onClick={compare}
        >
          Bandingkan dua hasil
        </button>
        <button
          className={action}
          disabled={busy || !total}
          onClick={() => exportFile("csv")}
        >
          Ekspor CSV
        </button>
        <button
          className={action}
          disabled={busy || !total}
          onClick={() => exportFile("pdf")}
        >
          Ekspor PDF
        </button>
      </div>
      {comparison && (
        <div
          className="rounded border border-sky-600 p-4 space-y-3"
          role="region"
          aria-label="Perbandingan analisis"
        >
          <h3 className="font-semibold">
            {comparison.first.ticker}:{" "}
            {comparison.first.recommendation || "Belum tersedia"} →{" "}
            {comparison.second.recommendation || "Belum tersedia"}
          </h3>
          <div className="grid gap-4 md:grid-cols-2">
            {[comparison.first, comparison.second].map((record, index) => (
              <div key={record.id}>
                <h4>Hasil {index + 1}</h4>
                <Identity record={record} />
                <p>{record.ai_summary}</p>
              </div>
            ))}
          </div>
          <p>
            Perubahan skor:{" "}
            {comparison.confidence_change_points ?? "Belum tersedia"} poin
            persentase.
          </p>
          <p>
            Input/model/prompt berbeda:{" "}
            {comparison.inputs_differ ? "Ya" : "Tidak"}.
          </p>
          <p>{comparison.explanation}</p>
        </div>
      )}
    </section>
  );
}
