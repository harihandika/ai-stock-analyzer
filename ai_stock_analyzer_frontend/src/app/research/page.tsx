"use client";

import {
  FormEvent,
  ReactNode,
  Suspense,
  useCallback,
  useEffect,
  useState,
} from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AppLayout } from "@/components/layout/AppLayout";
import { DataStatus } from "@/components/stock/DataStatus";
import { apiClient, errorMessage } from "@/services/api";
import { downloadResult } from "@/services/download";
import { MarketMetadata, formatPrice } from "@/services/market";

const inputClass = "w-full rounded border border-slate-600 bg-slate-900 p-3";
const actionClass =
  "rounded border border-sky-500 px-4 py-2 disabled:opacity-50";
type Criteria = Record<string, string | number | boolean | null>;
type Preset = {
  id: string;
  name: string;
  criteria: Criteria;
  schema_version: number;
};
type ScreenRow = {
  ticker: string;
  company_name: string;
  exchange: string | null;
  sector: string | null;
  currency: string | null;
  close: number | null;
  rsi: number | null;
  volume: number | null;
  metadata: MarketMetadata;
};
type AnalysisRow = {
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

function Field({
  name,
  label,
  type = "text",
  defaultValue,
  required = false,
  children,
}: {
  name: string;
  label: string;
  type?: string;
  defaultValue?: string | number;
  required?: boolean;
  children?: ReactNode;
}) {
  return (
    <label className="block space-y-1">
      <span>{label}</span>
      {children || (
        <input
          name={name}
          type={type}
          defaultValue={defaultValue}
          required={required}
          step={type === "number" ? "any" : undefined}
          className={inputClass}
        />
      )}
    </label>
  );
}
function Status({ error, busy }: { error: string; busy: boolean }) {
  return (
    <>
      {busy && <p role="status">Memproses…</p>}
      {error && (
        <p role="alert" className="text-red-300">
          {error}
        </p>
      )}
    </>
  );
}
function asParams(values: Criteria) {
  return new URLSearchParams(
    Object.entries(values)
      .filter(([, v]) => v !== null && v !== "")
      .map(([k, v]) => [k, String(v)]),
  ).toString();
}
const dateLabel = (value: string) =>
  new Date(value).toLocaleString("id-ID", { timeZone: "Asia/Jakarta" }) +
  " WIB";

function Screener() {
  const [criteria, setCriteria] = useState<Criteria>({});
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<{
    data: ScreenRow[];
    pagination: { total: number; total_pages: number };
    coverage: {
      registered_active: number;
      with_aligned_data: number;
      scope: string;
    };
  } | null>(null);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [presetName, setPresetName] = useState("");
  const encoded = asParams(criteria);
  useEffect(() => {
    const c = new AbortController();
    apiClient
      .get("/screener?" + encoded + "&page=" + page + "&per_page=6", {
        signal: c.signal,
      })
      .then((r) => {
        setResult(r.data);
        setError("");
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(errorMessage(e));
      });
    return () => c.abort();
  }, [encoded, page]);
  const loadPresets = useCallback(
    () =>
      apiClient.get("/screener/presets").then((r) => setPresets(r.data.data)),
    [],
  );
  useEffect(() => {
    void loadPresets().catch((e) => setError(errorMessage(e)));
  }, [loadPresets]);
  const apply = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const values: Criteria = {};
    new FormData(e.currentTarget).forEach((v, k) => {
      if (v !== "") values[k] = String(v);
    });
    setPage(1);
    setCriteria(values);
  };
  const save = async () => {
    setBusy(true);
    setError("");
    try {
      await apiClient.post("/screener/presets", { name: presetName, criteria });
      setPresetName("");
      await loadPresets();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="space-y-5">
      <h2 className="text-2xl font-semibold">Screener saham</h2>
      <p>
        Filter memakai seluruh cakupan instrumen tersimpan dan indikator pada
        tanggal harga yang sama. Ini bukan klaim seluruh saham di bursa.
      </p>
      <form
        key={encoded}
        onSubmit={apply}
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
      >
        <Field
          name="exchange"
          label="Bursa"
          defaultValue={String(criteria.exchange || "")}
        />
        <Field
          name="sector"
          label="Sektor"
          defaultValue={String(criteria.sector || "")}
        />
        <Field
          name="min_volume"
          label="Volume minimal (lembar)"
          type="number"
          defaultValue={String(criteria.min_volume ?? "")}
        />
        <Field
          name="rsi_min"
          label="RSI minimum"
          type="number"
          defaultValue={String(criteria.rsi_min ?? "")}
        />
        <Field
          name="rsi_max"
          label="RSI maksimum"
          type="number"
          defaultValue={String(criteria.rsi_max ?? "")}
        />
        <Field
          name="wyckoff_phase"
          label="Fase Wyckoff"
          defaultValue={String(criteria.wyckoff_phase || "")}
        />
        <Field name="smc" label="Pola SMC">
          <select
            name="smc"
            defaultValue={String(criteria.smc || "")}
            className={inputClass}
          >
            <option value="">Semua pola</option>
            {[
              "bullish_fvg",
              "bearish_fvg",
              "bos",
              "choch",
              "bullish_ob",
              "bearish_ob",
            ].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </Field>
        <Field name="sort" label="Urutkan">
          <select
            name="sort"
            defaultValue={String(criteria.sort || "ticker")}
            className={inputClass}
          >
            <option value="ticker">Kode saham</option>
            <option value="volume">Volume</option>
            <option value="rsi">RSI</option>
          </select>
        </Field>
        <label className="flex gap-2 items-center">
          <input
            type="checkbox"
            name="descending"
            value="true"
            defaultChecked={String(criteria.descending) === "true"}
          />
          Menurun
        </label>
        <label className="flex gap-2 items-center">
          <input
            type="checkbox"
            name="missing_only"
            value="true"
            defaultChecked={String(criteria.missing_only) === "true"}
          />
          Hanya data belum lengkap
        </label>
        <button className={actionClass}>Terapkan filter</button>
      </form>
      <Status error={error} busy={busy} />
      {result ? (
        <>
          <p role="status">
            {result.pagination.total} hasil · cakupan{" "}
            {result.coverage.registered_active} instrumen aktif,{" "}
            {result.coverage.with_aligned_data} dengan harga/indikator selaras.
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            {result.data.map((r) => (
              <article
                key={r.ticker}
                className="rounded border border-slate-700 p-4 space-y-2"
              >
                <Link
                  className="text-xl underline"
                  href={"/stock/" + encodeURIComponent(r.ticker)}
                >
                  {r.ticker} · {r.company_name}
                </Link>
                <p>
                  {r.exchange || "Bursa belum diketahui"} ·{" "}
                  {r.sector || "Sektor belum tersedia"}
                </p>
                <p>
                  {formatPrice(r.close, r.currency)} · RSI{" "}
                  {r.rsi?.toFixed(2) ?? "Belum tersedia"} · Volume{" "}
                  {r.volume?.toLocaleString("id-ID") ?? "Belum tersedia"} lembar
                </p>
                <DataStatus metadata={r.metadata} />
              </article>
            ))}
          </div>
          {!result.data.length && (
            <p>
              Tidak ada instrumen yang cocok. Nilai kosong tidak dianggap nol;
              periksa filter dan cakupan data.
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <button
              className={actionClass}
              disabled={page === 1}
              onClick={() => setPage((v) => v - 1)}
            >
              Sebelumnya
            </button>
            <span className="self-center">
              Halaman {page} / {Math.max(1, result.pagination.total_pages)}
            </span>
            <button
              className={actionClass}
              disabled={page >= result.pagination.total_pages}
              onClick={() => setPage((v) => v + 1)}
            >
              Berikutnya
            </button>
          </div>
        </>
      ) : (
        <p role="status">Memuat screener…</p>
      )}
      <div className="space-y-3 border-t border-slate-700 pt-4">
        <label className="block">
          Nama filter tersimpan
          <input
            value={presetName}
            onChange={(e) => setPresetName(e.target.value)}
            maxLength={100}
            className={inputClass}
          />
        </label>
        <button
          className={actionClass}
          disabled={busy || !presetName.trim()}
          onClick={save}
        >
          Simpan filter aktif
        </button>
        {presets.map((p) => (
          <div key={p.id} className="flex flex-wrap gap-3 items-center">
            <button
              className={actionClass}
              disabled={p.schema_version !== 1}
              onClick={() => {
                setCriteria(p.criteria);
                setPage(1);
              }}
            >
              {p.name}
            </button>
            <button
              aria-label={"Hapus filter " + p.name}
              className={actionClass}
              onClick={async () => {
                try {
                  await apiClient.delete("/screener/presets/" + p.id);
                  await loadPresets();
                } catch (e) {
                  setError(errorMessage(e));
                }
              }}
            >
              Hapus
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}

function History({ initialTicker }: { initialTicker: string }) {
  const [ticker, setTicker] = useState(initialTicker);
  const [activeTicker, setActiveTicker] = useState(initialTicker);
  const [rows, setRows] = useState<AnalysisRow[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const [comparison, setComparison] = useState<{
    confidence_change_points: number | null;
    inputs_differ: boolean;
    explanation: string;
    first: AnalysisRow;
    second: AnalysisRow;
  } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const c = new AbortController();
    apiClient
      .get("/stocks/" + encodeURIComponent(activeTicker) + "/analyses", {
        params: { page },
        signal: c.signal,
      })
      .then((r) => {
        setRows(r.data.data);
        setTotal(r.data.pagination.total);
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(errorMessage(e));
      });
    return () => c.abort();
  }, [activeTicker, page]);
  const exportFile = async (format: "csv" | "pdf") => {
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
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold">Riwayat analisis</h2>
      <form
        className="flex flex-wrap gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setActiveTicker(ticker.toUpperCase());
          setSelected([]);
          setComparison(null);
          setPage(1);
          setError("");
        }}
      >
        <label>
          Kode saham
          <input
            value={ticker}
            required
            maxLength={20}
            onChange={(e) => setTicker(e.target.value)}
            className={inputClass}
          />
        </label>
        <button className={actionClass}>Muat riwayat</button>
      </form>
      <p>
        Skor model bukan peluang profit. Pilih dua hasil sesuai urutan
        perbandingan; ekspor memakai pilihan atau seluruh hasil bila tidak ada
        yang dipilih.
      </p>
      <Status busy={busy} error={error} />
      <p>{total} hasil tersimpan</p>
      {rows.map((r) => (
        <article
          className="rounded border border-slate-700 p-4 space-y-2"
          key={r.id}
        >
          <label className="flex gap-3">
            <input
              type="checkbox"
              checked={selected.includes(r.id)}
              onChange={(e) =>
                setSelected((s) =>
                  e.target.checked
                    ? [...s, r.id]
                    : s.filter((id) => id !== r.id),
                )
              }
            />
            Pilih {r.recommendation || "Belum tersedia"} · Skor{" "}
            {r.confidence_score ?? "—"}%
          </label>
          <p>
            {dateLabel(r.generated_at)} · Data {r.analysis_date}
          </p>
          <p>
            {r.provider_name}/{r.model_name || "Belum diketahui"} · Provenance{" "}
            {r.provenance}
          </p>
          <p>{r.ai_summary}</p>
          <p className="text-xs break-all">
            Revisi data: {r.data_revision || "Belum terverifikasi"}
          </p>
        </article>
      ))}
      {!rows.length && (
        <p>Belum ada hasil analisis tersimpan untuk saham ini.</p>
      )}
      <div className="flex flex-wrap gap-3">
        <button
          className={actionClass}
          disabled={page === 1}
          onClick={() => setPage((v) => v - 1)}
        >
          Sebelumnya
        </button>
        <span>Halaman {page}</span>
        <button
          className={actionClass}
          disabled={page * 20 >= total}
          onClick={() => setPage((v) => v + 1)}
        >
          Berikutnya
        </button>
        <button
          className={actionClass}
          disabled={selected.length !== 2 || busy}
          onClick={async () => {
            setBusy(true);
            try {
              const r = await apiClient.get("/analyses/compare", {
                params: { first: selected[0], second: selected[1] },
              });
              setComparison(r.data);
            } catch (e) {
              setError(errorMessage(e));
            } finally {
              setBusy(false);
            }
          }}
        >
          Bandingkan dua hasil
        </button>
        <button
          className={actionClass}
          disabled={busy || !total}
          onClick={() => exportFile("csv")}
        >
          Ekspor CSV
        </button>
        <button
          className={actionClass}
          disabled={busy || !total}
          onClick={() => exportFile("pdf")}
        >
          Ekspor PDF
        </button>
      </div>
      {comparison && (
        <div className="rounded border border-sky-600 p-4">
          <h3 className="font-semibold">
            {comparison.first.recommendation} →{" "}
            {comparison.second.recommendation}
          </h3>
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
          <p>{comparison.first.ai_summary}</p>
          <p>{comparison.second.ai_summary}</p>
        </div>
      )}
    </section>
  );
}

type Rule = {
  id: string;
  ticker: string;
  kind: string;
  threshold: number | null;
  signal: string | null;
  direction: string;
  enabled: boolean;
  baseline_established: boolean;
};
type Notice = {
  id: string;
  ticker: string;
  kind: string;
  value: number | string;
  market_as_of: string;
  is_read: boolean;
  href: string;
};
type Job = {
  id: string;
  ticker: string;
  status: string;
  attempts: number;
  error: { message: string } | null;
  created_at: string;
};
function Monitoring({ initialTicker }: { initialTicker: string }) {
  const [rules, setRules] = useState<Rule[]>([]);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [kind, setKind] = useState("price");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async (signal?: AbortSignal) => {
    const options = signal ? {signal, skipAuthRefresh: true} : {};
    const r = await Promise.all([
      apiClient.get("/alerts", options),
      apiClient.get("/notifications", options),
      apiClient.get("/analysis/jobs", options),
    ]);
    if (signal?.aborted) return;
    setRules(r[0].data.data);
    setNotices(r[1].data.data);
    setJobs(r[2].data.data);
  }, []);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const refresh = () => {
      if (active)
        void load(controller.signal).catch((e) => {
          if (active) setError(errorMessage(e));
        });
    };
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => {
      active = false;
      controller.abort();
      clearInterval(timer);
    };
  }, [load]);
  const act = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    try {
      await action();
      await load();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const create = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    void act(() =>
      apiClient.post("/alerts", {
        ticker: String(f.get("ticker")).toUpperCase(),
        kind,
        direction: f.get("direction"),
        threshold: kind === "signal" ? null : Number(f.get("threshold")),
        signal: kind === "signal" ? f.get("signal") : null,
      }),
    );
  };
  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold">Pemantauan EOD</h2>
      <p>
        Alert memakai penutupan harian dan worker. Evaluasi pertama membentuk
        baseline; notifikasi berikutnya hanya muncul saat kondisi bertransisi.
        Data stale atau keterkinian unknown tidak memicu alert.
      </p>
      <form onSubmit={create} className="grid gap-3 sm:grid-cols-2">
        <Field
          name="ticker"
          label="Kode saham alert"
          defaultValue={initialTicker}
          required
        />
        <Field name="kind" label="Jenis alert">
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            className={inputClass}
          >
            <option value="price">Harga penutupan</option>
            <option value="change_pct">
              Perubahan dari sesi sebelumnya (%)
            </option>
            <option value="signal">Sinyal AI baru</option>
          </select>
        </Field>
        {kind === "signal" ? (
          <Field name="signal" label="Sinyal">
            <select name="signal" className={inputClass}>
              <option>BUY</option>
              <option>HOLD</option>
              <option>WAIT</option>
            </select>
          </Field>
        ) : (
          <>
            <Field
              name="threshold"
              label={
                kind === "price"
                  ? "Ambang harga (currency instrumen)"
                  : "Ambang perubahan (%)"
              }
              type="number"
              required
            />
            <Field name="direction" label="Arah">
              <select name="direction" className={inputClass}>
                <option value="above">Naik melewati / mencapai</option>
                <option value="below">Turun melewati / mencapai</option>
              </select>
            </Field>
          </>
        )}
        <button className={actionClass} disabled={busy}>
          Simpan alert
        </button>
      </form>
      <Status error={error} busy={busy} />
      {rules.map((r) => (
        <article
          key={r.id}
          className="rounded border border-slate-700 p-4 space-y-2"
        >
          <p>
            {r.ticker} · {r.kind} · {r.direction} · {r.signal || r.threshold} ·{" "}
            {r.enabled ? "Aktif" : "Dijeda"}
          </p>
          <p>
            {r.baseline_established
              ? "Baseline tersimpan"
              : "Menunggu data lengkap dan kalender terverifikasi"}
          </p>
          <div className="flex gap-3">
            <button
              disabled={busy}
              className={actionClass}
              onClick={() =>
                act(() =>
                  apiClient.patch("/alerts/" + r.id, { enabled: !r.enabled }),
                )
              }
            >
              {r.enabled ? "Jeda" : "Aktifkan"}
            </button>
            <button
              disabled={busy}
              className={actionClass}
              onClick={() => act(() => apiClient.delete("/alerts/" + r.id))}
            >
              Hapus alert
            </button>
          </div>
        </article>
      ))}
      <h3 className="text-xl">Notifikasi</h3>
      {!notices.length && <p>Belum ada kejadian alert.</p>}
      {notices.map((n) => (
        <article key={n.id} className="border border-slate-700 rounded p-3">
          <Link className="underline" href={n.href}>
            {n.ticker} · {n.kind} · {n.value} · Data {n.market_as_of}
          </Link>
          <p>{n.is_read ? "Sudah dibaca" : "Belum dibaca"}</p>
          {!n.is_read && (
            <button
              className={actionClass}
              onClick={() =>
                act(() => apiClient.patch("/notifications/" + n.id + "/read"))
              }
            >
              Tandai dibaca
            </button>
          )}
        </article>
      ))}
      <h3 className="text-xl">Job analisis terakhir</h3>
      {!jobs.length && <p>Belum ada job. Mulai analisis dari halaman saham.</p>}
      {jobs.map((j) => (
        <article key={j.id} className="border border-slate-700 rounded p-3">
          <Link
            className="underline"
            href={"/stock/" + encodeURIComponent(j.ticker)}
          >
            {j.ticker}
          </Link>
          <p>
            {j.status} · Percobaan {j.attempts} · {dateLabel(j.created_at)}
          </p>
          {j.error && <p>{j.error.message}</p>}
        </article>
      ))}
    </section>
  );
}

type Plan = {
  id: string;
  ticker: string;
  version: number;
  needs_review: boolean;
  versions: unknown[];
  details: {
    input: Record<string, string | number>;
    calculation: {
      shares: number;
      lots: number;
      purchase_value: number;
      estimated_risk: number;
      remaining_capital: number;
      reward_risk_before_fees: number;
      limitations: string;
    };
  };
};
function Plans({ initialTicker }: { initialTicker: string }) {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [editing, setEditing] = useState<Plan | null>(null);
  const [calculation, setCalculation] = useState<
    Plan["details"]["calculation"] | null
  >(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(
    () => apiClient.get("/trade-plans").then((r) => setPlans(r.data.data)),
    [],
  );
  useEffect(() => {
    void load().catch((e) => setError(errorMessage(e)));
  }, [load]);
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body: Record<string, string | number> = {};
    const text = ["ticker", "currency", "horizon", "reason", "invalidation"];
    f.forEach((v, k) => {
      body[k] = text.includes(k) ? String(v) : Number(v);
    });
    setBusy(true);
    setError("");
    try {
      const action = (e.nativeEvent as SubmitEvent).submitter?.getAttribute(
        "value",
      );
      if (action === "calculate")
        setCalculation(
          (await apiClient.post("/trade-plans/calculate", body)).data,
        );
      else {
        if (editing)
          await apiClient.put("/trade-plans/" + editing.id, {
            ...body,
            expected_version: editing.version,
          });
        else await apiClient.post("/trade-plans", body);
        setEditing(null);
        await load();
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };
  const defaults: Record<string, string | number> = editing?.details.input || {
    ticker: initialTicker,
    currency: initialTicker.endsWith(".JK") ? "IDR" : "USD",
    lot_size: initialTicker.endsWith(".JK") ? 100 : 1,
    entry_low: "",
    entry_high: "",
    entry: "",
    stop: "",
    target: "",
    capital: 10000000,
    risk_pct: 1,
    buy_fee_bps: 0,
    sell_fee_bps: 0,
    slippage_bps: 0,
  };
  const numericFields = [
    ["entry_low", "Area entry bawah"],
    ["entry_high", "Area entry atas"],
    ["entry", "Harga entry perhitungan"],
    ["stop", "Stop"],
    ["target", "Target"],
    ["capital", "Modal"],
    ["risk_pct", "Batas risiko modal (%)"],
    ["lot_size", "Lembar per lot"],
    ["buy_fee_bps", "Fee beli (bps)"],
    ["sell_fee_bps", "Fee jual (bps)"],
    ["slippage_bps", "Slippage (bps)"],
  ];
  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold">Rencana transaksi</h2>
      <p>
        Semua angka pada formulir adalah input pengguna, bukan saran AI. Biaya
        awal 0 perlu Anda sesuaikan; 10 bps = 0,1%. Hanya simulasi long, tanpa
        pengiriman order broker.
      </p>
      <form
        key={editing?.id || "new"}
        onSubmit={submit}
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
      >
        <Field
          name="ticker"
          label="Kode saham rencana"
          defaultValue={defaults.ticker}
          required
        />
        <Field name="currency" label="Mata uang modal">
          <select
            name="currency"
            defaultValue={String(defaults.currency)}
            className={inputClass}
          >
            <option>IDR</option>
            <option>USD</option>
          </select>
        </Field>
        {numericFields.map(([name, label]) => (
          <Field
            key={name}
            name={name}
            label={label}
            type="number"
            required
            defaultValue={defaults[name]}
          />
        ))}
        {[
          ["horizon", "Horizon"],
          ["reason", "Alasan berbasis data"],
          ["invalidation", "Kondisi pembatalan"],
        ].map(([name, label]) => (
          <Field
            key={name}
            name={name}
            label={label}
            required
            defaultValue={defaults[name]}
          />
        ))}
        <button
          name="action"
          value="calculate"
          disabled={busy}
          className={actionClass}
        >
          Hitung risiko dan lot
        </button>
        <button
          name="action"
          value="save"
          disabled={busy}
          className={actionClass}
        >
          {editing ? "Simpan versi baru" : "Simpan rencana"}
        </button>
        {editing && (
          <button
            type="button"
            className={actionClass}
            onClick={() => setEditing(null)}
          >
            Batal edit
          </button>
        )}
      </form>
      <Status error={error} busy={busy} />
      {calculation && (
        <div role="status" className="border border-sky-700 rounded p-4">
          <p>
            {calculation.shares} lembar / {calculation.lots} lot · Reward/risk
            sebelum biaya {calculation.reward_risk_before_fees.toFixed(2)}:1
          </p>
          <p>
            Nilai beli termasuk estimasi biaya{" "}
            {calculation.purchase_value.toLocaleString("id-ID")} · Risiko{" "}
            {calculation.estimated_risk.toLocaleString("id-ID")} · Sisa modal{" "}
            {calculation.remaining_capital.toLocaleString("id-ID")}
          </p>
          <p>{calculation.limitations}</p>
        </div>
      )}
      {plans.map((p) => (
        <article
          key={p.id}
          className="border border-slate-700 rounded p-4 space-y-2"
        >
          <h3>
            {p.ticker} · Versi {p.version} · {p.versions.length} versi
            sebelumnya
          </h3>
          <p>
            {p.needs_review
              ? "Data berubah; tinjau rencana ini."
              : "Revisi data sesuai saat disimpan."}
          </p>
          <p>
            {p.details.calculation.shares} lembar / {p.details.calculation.lots}{" "}
            lot · Risiko{" "}
            {formatPrice(
              p.details.calculation.estimated_risk,
              String(p.details.input.currency),
            )}
          </p>
          <p>
            Entry {p.details.input.entry} · Stop {p.details.input.stop} · Target{" "}
            {p.details.input.target}
          </p>
          <p>
            {p.details.input.reason} · Batal jika:{" "}
            {p.details.input.invalidation}
          </p>
          <div className="flex gap-3">
            <button
              className={actionClass}
              onClick={() => {
                setEditing(p);
                setCalculation(null);
              }}
            >
              Edit rencana
            </button>
            <button
              className={actionClass}
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await apiClient.delete("/trade-plans/" + p.id);
                  await load();
                } catch (e) {
                  setError(errorMessage(e));
                } finally {
                  setBusy(false);
                }
              }}
            >
              Hapus rencana
            </button>
          </div>
        </article>
      ))}
    </section>
  );
}

function Workbench() {
  const params = useSearchParams();
  const tab = params.get("tab") || "screener";
  const ticker = (params.get("ticker") || "BBCA.JK").toUpperCase();
  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto space-y-6 pb-12">
        <h1 className="text-3xl font-bold">Riset dan pemantauan</h1>
        <nav aria-label="Bagian riset" className="flex flex-wrap gap-3">
          {[
            ["screener", "Screener"],
            ["history", "Riwayat AI"],
            ["monitoring", "Alert dan job"],
            ["plans", "Rencana transaksi"],
          ].map(([key, label]) => (
            <Link
              className={actionClass + (tab === key ? " bg-sky-900" : "")}
              aria-current={tab === key ? "page" : undefined}
              key={key}
              href={
                "/research?tab=" + key + "&ticker=" + encodeURIComponent(ticker)
              }
            >
              {label}
            </Link>
          ))}
        </nav>
        <div key={tab + ticker}>
          {tab === "history" ? (
            <History initialTicker={ticker} />
          ) : tab === "monitoring" ? (
            <Monitoring initialTicker={ticker} />
          ) : tab === "plans" ? (
            <Plans initialTicker={ticker} />
          ) : (
            <Screener />
          )}
        </div>
      </div>
    </AppLayout>
  );
}
export default function ResearchPage() {
  return (
    <Suspense fallback={<p role="status">Memuat ruang riset…</p>}>
      <Workbench />
    </Suspense>
  );
}
