"use client";

import {
  cloneElement,
  isValidElement,
  FormEvent,
  ReactElement,
  ReactNode,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { AnalysisHistory } from "@/components/research/AnalysisHistory";
import {
  Criteria,
  readScreener,
  screenerParams,
} from "@/services/screener-state";
import { AlertNextStep } from "@/components/research/AlertNextStep";
import { patternLabels } from "@/services/labels";
import { publishUnread } from "@/services/notifications";
import { TradePlans } from "@/components/TradePlans";
import { AppLayout } from "@/components/layout/AppLayout";
import { DataStatus } from "@/components/stock/DataStatus";
import { apiClient, errorMessage } from "@/services/api";
import { MarketMetadata, formatPrice } from "@/services/market";

const inputClass = "w-full rounded border border-slate-600 bg-slate-900 p-3";
const actionClass =
  "inline-flex min-h-11 items-center justify-center rounded border border-sky-500 px-4 py-2 disabled:opacity-50";
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
  const id = "research-field-" + name;
  const labelId = id + "-label";
  return (
    <label className="block space-y-1" htmlFor={id}>
      <span id={labelId}>{label}</span>
      {isValidElement(children) ? (
        cloneElement(
          children as ReactElement<{
            id: string;
            name: string;
            "aria-labelledby": string;
          }>,
          { id, name, "aria-labelledby": labelId },
        )
      ) : (
        <input
          id={id}
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
  const params = useSearchParams();
  const { user } = useAuth();
  const {
    criteria,
    page,
    error: urlError,
  } = readScreener(new URLSearchParams(params.toString()));
  const [loaded, setResult] = useState<{
    requestKey: string;
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
  const [notice, setNotice] = useState("");
  const restored = useRef("");
  const encoded = asParams(criteria);
  const requestKey = (user?.id || "") + ":" + encoded + "&page=" + page;
  const result = !urlError && loaded?.requestKey === requestKey ? loaded : null;
  const navigate = (values: Criteria, nextPage = 1) => {
    const next = screenerParams(
      new URLSearchParams(params.toString()),
      values,
      nextPage,
    );
    const checked = readScreener(next);
    if (checked.error) {
      setError(checked.error);
      return;
    }
    setError("");
    setNotice("");
    window.history.pushState(null, "", "?" + next.toString());
  };
  useEffect(() => {
    const c = new AbortController();
    if (urlError) return () => c.abort();
    apiClient
      .get("/screener?" + encoded + "&page=" + page + "&per_page=6", {
        signal: c.signal,
      })
      .then((r) => {
        if (c.signal.aborted) return;
        const last = Math.max(1, r.data.pagination.total_pages);
        if (page > last) {
          setNotice(
            "Cakupan data berubah; halaman disesuaikan ke hasil yang tersedia.",
          );
          const next = screenerParams(
            new URLSearchParams(window.location.search),
            Object.fromEntries(new URLSearchParams(encoded)),
            last,
          );
          window.history.replaceState(null, "", "?" + next.toString());
          return;
        }
        setResult({ ...r.data, requestKey });
        setError("");
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(errorMessage(e));
      });
    return () => c.abort();
  }, [encoded, page, requestKey, urlError]);
  useEffect(() => {
    if (!result || restored.current === requestKey) return;
    const saved = window.history.state?.stockScreenerReturn;
    if (!saved || saved.query !== requestKey || saved.user !== user?.id) return;
    const frame = requestAnimationFrame(() => {
      const anchor = document.getElementById("screener-" + saved.anchor);
      const container =
        document.querySelector<HTMLElement>("[data-page-scroll]");
      if (anchor) {
        anchor.querySelector("a")?.focus({ preventScroll: true });
        if (container && Number.isFinite(saved.top))
          container.scrollTop = saved.top;
      } else
        setNotice(
          "Kandidat sebelumnya tidak ada dalam hasil terbaru. Filter tetap dipertahankan.",
        );
      restored.current = requestKey;
    });
    return () => cancelAnimationFrame(frame);
  }, [result, requestKey, user?.id]);
  const loadPresets = useCallback(
    () =>
      apiClient.get("/screener/presets").then((r) => setPresets(r.data.data)),
    [setPresets],
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
    navigate(values);
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
              <option key={v} value={v}>
                {patternLabels[v] || v}
              </option>
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
        <button
          type="button"
          className={actionClass}
          onClick={() => navigate({})}
        >
          Reset filter
        </button>
      </form>
      <Status error={urlError || error} busy={busy} />
      {notice && <p role="status">{notice}</p>}
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
                id={"screener-" + r.ticker}
                className="rounded border border-slate-700 p-4 space-y-2"
              >
                <Link
                  className="text-xl underline"
                  href={"/stock/" + encodeURIComponent(r.ticker)}
                  onNavigate={() => {
                    const container =
                      document.querySelector<HTMLElement>("[data-page-scroll]");
                    window.history.replaceState(
                      {
                        ...window.history.state,
                        stockScreenerReturn: {
                          query: requestKey,
                          user: user?.id,
                          anchor: r.ticker,
                          top: container?.scrollTop || 0,
                        },
                      },
                      "",
                      window.location.href,
                    );
                  }}
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
              onClick={() => navigate(criteria, page - 1)}
            >
              Sebelumnya
            </button>
            <span className="self-center">
              Halaman {page} / {Math.max(1, result.pagination.total_pages)}
            </span>
            <button
              className={actionClass}
              disabled={page >= result.pagination.total_pages}
              onClick={() => navigate(criteria, page + 1)}
            >
              Berikutnya
            </button>
          </div>
        </>
      ) : (
        !urlError && !error && <p role="status">Memuat screener…</p>
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
                navigate(p.criteria);
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

type Rule = {
  id: string;
  ticker: string;
  kind: string;
  threshold: number | null;
  signal: string | null;
  direction: string;
  enabled: boolean;
  baseline_established: boolean;
  evaluation_state: string;
  market_as_of: string | null;
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
  const { user } = useAuth();
  const [rules, setRules] = useState<Rule[]>([]);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [kind, setKind] = useState("price");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [worker, setWorker] = useState<{
    state: string;
    last_heartbeat_at: string | null;
  } | null>(null);
  const loadVersion = useRef(0);
  const load = useCallback(
    async (signal?: AbortSignal) => {
      const version = ++loadVersion.current;
      const current = () => !signal?.aborted && version === loadVersion.current;
      const options = signal ? { signal, skipAuthRefresh: true } : {};
      const r = await Promise.allSettled([
        apiClient.get("/alerts", options).then((response) => {
          if (current()) {
            setRules(response.data.data);
            setWorker(response.data.worker);
          }
        }),
        apiClient.get("/notifications", options).then((response) => {
          if (current()) {
            setNotices(response.data.data);
            publishUnread(user?.id, response.data.unread);
          }
        }),
        apiClient.get("/analysis/jobs", options).then((response) => {
          if (current()) setJobs(response.data.data);
        }),
      ]);
      if (!current()) return;
      const failed = r.find((item) => item.status === "rejected");
      if (failed?.status === "rejected")
        throw new Error(
          "Sebagian data pemantauan belum diperbarui. " +
            errorMessage(failed.reason),
        );
    },
    [user?.id],
  );
  const invalidateLoad = useCallback(() => {
    loadVersion.current++;
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
      invalidateLoad();
      controller.abort();
      clearInterval(timer);
    };
  }, [load, invalidateLoad]);
  const act = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    let persisted = false;
    try {
      await action();
      persisted = true;
      await load();
    } catch (e) {
      setError((persisted ? "Perubahan tersimpan. " : "") + errorMessage(e));
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
        ...(kind === "signal"
          ? { signal: f.get("signal") }
          : {
              direction: f.get("direction"),
              threshold: Number(f.get("threshold")),
            }),
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
      <p>
        Worker:{" "}
        {worker?.state === "healthy"
          ? "Heartbeat terukur"
          : worker?.state === "degraded"
            ? "Proses hidup, evaluasi mengalami kegagalan"
            : "Belum tersedia heartbeat aktif"}
        .
        {worker?.last_heartbeat_at && (
          <> Terakhir {dateLabel(worker.last_heartbeat_at)}.</>
        )}{" "}
        Heartbeat tidak membuktikan koneksi provider atau ketersediaan data
        pasar terbaru.
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
            {r.ticker} ·{" "}
            {r.kind === "signal"
              ? "Sinyal " + r.signal
              : (r.kind === "price" ? "Harga " : "Perubahan (%) ") +
                (r.direction === "above"
                  ? "naik mencapai "
                  : "turun mencapai ") +
                r.threshold}{" "}
            · {r.enabled ? "Aktif" : "Dijeda"}
          </p>
          <p>
            {(
              {
                paused: "Dijeda",
                notifications_disabled: "Notifikasi akun dinonaktifkan",
                waiting_for_data:
                  "Menunggu data lengkap dan kalender terverifikasi",
                waiting_for_analysis:
                  "Menunggu analisis yang sesuai revisi data",
                waiting_for_previous_session:
                  "Menunggu data sesi bursa sebelumnya",
                waiting_for_worker: "Menunggu worker dengan heartbeat sehat",
                waiting_for_baseline:
                  "Menunggu evaluasi pertama untuk membentuk baseline",
                ready:
                  "Baseline tersimpan; siap untuk evaluasi sesi berikutnya",
              } as Record<string, string>
            )[r.evaluation_state] || "Kesiapan evaluasi belum terverifikasi"}
            {r.market_as_of && <> · Sesi data {r.market_as_of}</>}
          </p>
          <AlertNextStep state={r.evaluation_state} ticker={r.ticker} />
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
      <h3 id="monitoring-jobs" tabIndex={-1} className="text-xl">
        Pekerjaan analisis terakhir
      </h3>
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
              href={(() => {
                const next = new URLSearchParams(params.toString());
                next.set("tab", key);
                next.set("ticker", ticker);
                return "/research?" + next.toString();
              })()}
            >
              {label}
            </Link>
          ))}
        </nav>
        <div key={tab + ticker}>
          {tab === "history" ? (
            <AnalysisHistory initialTicker={ticker} />
          ) : tab === "monitoring" ? (
            <Monitoring initialTicker={ticker} />
          ) : tab === "plans" ? (
            <TradePlans initialTicker={ticker} />
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
