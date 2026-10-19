"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { apiClient, errorMessage } from "@/services/api";
import { formatPrice } from "@/services/market";

type Calculation = {
  shares: number;
  lots: number;
  purchase_value: number;
  estimated_risk: number;
  remaining_capital: number;
  reward_risk_before_fees: number;
  estimated_reward_after_fees: number;
  limitations: string;
};
type Plan = {
  id: string;
  ticker: string;
  version: number;
  needs_review: boolean;
  versions: unknown[];
  details: { input: Record<string, string | number>; calculation: Calculation };
};
type Draft = Record<string, string>;
const inputClass =
  "w-full min-w-0 rounded border border-slate-600 bg-slate-900 p-3";
const actionClass =
  "rounded border border-sky-500 px-4 py-2 disabled:opacity-50";
const basicFields = [
  ["entry", "Harga entry perhitungan"],
  ["stop", "Stop"],
  ["target", "Target"],
  ["capital", "Modal"],
  ["risk_pct", "Batas risiko modal (%)"],
  ["lot_size", "Lembar per lot"],
] as const;
const fees = [
  ["buy_fee_bps", "Fee beli (bps)"],
  ["sell_fee_bps", "Fee jual (bps)"],
  ["slippage_bps", "Slippage (bps)"],
] as const;
const fullFields = [
  ["entry_low", "Area entry bawah"],
  ["entry_high", "Area entry atas"],
  ["horizon", "Horizon"],
  ["reason", "Alasan berbasis data"],
  ["invalidation", "Kondisi pembatalan"],
] as const;
const textFields = new Set([
  "ticker",
  "currency",
  "horizon",
  "reason",
  "invalidation",
]);
const defaults = (ticker: string): Draft => ({
  ticker,
  currency: ticker.endsWith(".JK") ? "IDR" : "USD",
  lot_size: ticker.endsWith(".JK") ? "100" : "1",
  entry: "",
  stop: "",
  target: "",
  capital: "10000000",
  risk_pct: "1",
  buy_fee_bps: "0",
  sell_fee_bps: "0",
  slippage_bps: "0",
  entry_low: "",
  entry_high: "",
  horizon: "",
  reason: "",
  invalidation: "",
});

export function TradePlans({ initialTicker }: { initialTicker: string }) {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [editing, setEditing] = useState<Plan | null>(null);
  const [draft, setDraft] = useState<Draft>(() => defaults(initialTicker));
  const [calculation, setCalculation] = useState<{
    version: number;
    value: Calculation;
  } | null>(null);
  const version = useRef(0);
  const context = useRef(0);
  const alive = useRef(true);
  const request = useRef<AbortController | null>(null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [invalid, setInvalid] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [completeOpen, setCompleteOpen] = useState(false);
  const load = useCallback(async (signal?: AbortSignal) => {
    const result = await apiClient.get<{ data: Plan[] }>("/trade-plans", {
      signal,
    });
    if (!signal?.aborted && alive.current) setPlans(result.data.data);
    return result.data.data;
  }, []);
  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    void load(controller.signal).catch((e) => {
      if (!controller.signal.aborted) setError(errorMessage(e));
    });
    return () => {
      alive.current = false;
      controller.abort();
      request.current?.abort();
    };
  }, [load]);

  function update(name: string, value: string) {
    version.current += 1;
    if (name === "ticker") {
      context.current += 1;
      setEditing(null);
    }
    setDraft((previous) => ({ ...previous, [name]: value }));
    setCalculation(null);
    setDirty(true);
    setNotice("");
    setInvalid(null);
  }
  function select(plan: Plan | null) {
    version.current += 1;
    context.current += 1;
    setEditing(plan);
    setDraft(
      plan
        ? Object.fromEntries(
            Object.entries(plan.details.input).map(([k, v]) => [k, String(v)]),
          )
        : defaults(initialTicker),
    );
    setCalculation(null);
    setDirty(false);
    setNotice("");
    setError("");
    setConflict(false);
    setInvalid(null);
    setCompleteOpen(Boolean(plan));
  }
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const save =
      (e.nativeEvent as SubmitEvent).submitter?.getAttribute("value") ===
      "save";
    if (save) {
      const missing = fullFields.find(([name]) => !draft[name]?.trim());
      if (missing) {
        setCompleteOpen(true);
        setInvalid(missing[0]);
        setError(
          "Lengkapi " + missing[1].toLowerCase() + " untuk menyimpan rencana.",
        );
        requestAnimationFrame(() =>
          document.getElementById("plan-" + missing[0])?.focus(),
        );
        return;
      }
    }
    const keys = [
      "ticker",
      "currency",
      ...basicFields.map(([k]) => k),
      ...fees.map(([k]) => k),
      ...(save ? fullFields.map(([k]) => k) : []),
    ];
    const body = Object.fromEntries(
      keys.map((key) => [
        key,
        textFields.has(key) ? draft[key].trim() : Number(draft[key]),
      ]),
    );
    body.ticker = String(body.ticker).toUpperCase();
    const snapshotVersion = version.current;
    const snapshotContext = context.current;
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError("");
    setNotice("");
    setConflict(false);
    // Never keep a prior result active when a new request fails or is superseded.
    setCalculation(null);
    try {
      if (!save) {
        const result = await apiClient.post<Calculation>(
          "/trade-plans/calculate",
          body,
          { signal: controller.signal },
        );
        if (alive.current && version.current === snapshotVersion) {
          setCalculation({ version: snapshotVersion, value: result.data });
          setDirty(false);
        }
      } else {
        const response = editing
          ? await apiClient.put<Plan>(
              "/trade-plans/" + editing.id,
              { ...body, expected_version: editing.version },
              { signal: controller.signal },
            )
          : await apiClient.post<Plan>("/trade-plans", body, {
              signal: controller.signal,
            });
        if (!alive.current) return;
        // Inputs may be edited while saving. Keep that newer draft, but use the
        // newly committed version for its next save to avoid an artificial 409.
        if (context.current === snapshotContext) setEditing(response.data);
        if (version.current === snapshotVersion) {
          setCalculation({
            version: snapshotVersion,
            value: response.data.details.calculation,
          });
          setDirty(false);
          setNotice("Rencana disimpan. Hasil sesuai input yang dikirim.");
        } else
          setNotice(
            "Versi yang dikirim sudah disimpan. Input terbaru belum dihitung ulang.",
          );
        await load(controller.signal);
      }
    } catch (err) {
      if (!controller.signal.aborted && alive.current) {
        setError(errorMessage(err));
        setConflict(axios.isAxiosError(err) && err.response?.status === 409);
      }
    } finally {
      if (alive.current) setBusy(false);
    }
  }

  function field(
    name: string,
    label: string,
    type = "number",
    required = false,
  ) {
    return (
      <label
        key={name}
        htmlFor={"plan-" + name}
        className="block min-w-0 space-y-1"
      >
        <span>{label}</span>
        <input
          id={"plan-" + name}
          name={name}
          type={type}
          step={type === "number" ? "any" : undefined}
          required={required}
          value={draft[name] || ""}
          onChange={(e) => update(name, e.target.value)}
          aria-invalid={invalid === name || undefined}
          className={inputClass}
        />
      </label>
    );
  }
  const result = calculation?.value || null;
  return (
    <section className="space-y-5">
      <h2 className="text-2xl font-semibold">Rencana transaksi</h2>
      <p>
        Angka adalah input pengguna, bukan saran AI. Simulasi long, tanpa
        pengiriman order broker.
      </p>
      <form onSubmit={submit} className="space-y-5">
        <fieldset className="grid min-w-0 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <legend className="mb-3 text-lg font-semibold">
            1. Hitung ukuran posisi
          </legend>
          {field("ticker", "Kode saham rencana", "text", true)}
          <label className="block min-w-0 space-y-1" htmlFor="plan-currency">
            <span>Mata uang modal</span>
            <select
              id="plan-currency"
              name="currency"
              value={draft.currency}
              className={inputClass}
              onChange={(e) => update("currency", e.target.value)}
            >
              <option>IDR</option>
              <option>USD</option>
            </select>
          </label>
          {basicFields.map(([name, label]) =>
            field(name, label, "number", true),
          )}
        </fieldset>
        <p className="text-sm text-slate-300" data-testid="plan-fee-summary">
          Asumsi biaya: beli {draft.buy_fee_bps} bps · jual {draft.sell_fee_bps}{" "}
          bps · slippage {draft.slippage_bps} bps. 10 bps = 0,1%. Biaya awal 0
          perlu disesuaikan.
        </p>
        <details className="rounded border border-slate-700 p-4">
          <summary className="cursor-pointer min-h-11 py-2">
            Biaya dan slippage
          </summary>
          <div className="grid gap-4 mt-3 sm:grid-cols-3">
            {fees.map(([name, label]) => field(name, label, "number", true))}
          </div>
        </details>
        <button
          name="action"
          value="calculate"
          disabled={busy}
          className={actionClass}
        >
          Hitung risiko dan lot
        </button>
        <details
          open={completeOpen}
          onToggle={(e) => setCompleteOpen(e.currentTarget.open)}
          className="rounded border border-slate-700 p-4"
        >
          <summary className="cursor-pointer min-h-11 py-2">
            2. Lengkapi rencana untuk disimpan
          </summary>
          <p className="my-3 text-sm text-slate-300">
            Field berikut wajib saat menyimpan. Kalkulator dapat dicoba tanpa
            uraian rencana.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            {fullFields.map(([name, label]) =>
              field(name, label, name.startsWith("entry_") ? "number" : "text"),
            )}
          </div>
        </details>
        <div className="flex flex-wrap gap-3">
          <button
            name="action"
            value="save"
            disabled={busy}
            className={actionClass}
          >
            {editing ? "Simpan versi baru" : "Simpan rencana"}
          </button>
          <button
            type="button"
            disabled={busy}
            className={actionClass}
            onClick={() => select(null)}
          >
            {editing ? "Batal edit" : "Rencana baru"}
          </button>
        </div>
      </form>
      {busy && <p role="status">Memproses snapshot input yang dikirim…</p>}
      {dirty && !result && <p role="status">Input berubah — hitung ulang.</p>}
      {!dirty && !result && !busy && (
        <p>Belum dihitung. Isi harga dan modal, lalu hitung risiko dan lot.</p>
      )}
      {error && (
        <p role="alert" className="text-red-300">
          {error}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      {conflict && (
        <button
          type="button"
          className={actionClass}
          onClick={async () => {
            try {
              const rows = await load();
              const stored = rows.find((p) => p.id === editing?.id);
              if (stored) select(stored);
            } catch (e) {
              setError(errorMessage(e));
            }
          }}
        >
          Muat ulang versi tersimpan
        </button>
      )}
      {result && (
        <div
          role="status"
          aria-label="Hasil kalkulator terkini"
          className="border border-sky-700 rounded p-4 space-y-2"
        >
          <p>
            {result.shares} lembar / {result.lots} lot · Reward/risk sebelum
            biaya {result.reward_risk_before_fees.toFixed(2)}:1
          </p>
          <p>
            Nilai beli termasuk estimasi biaya{" "}
            {formatPrice(result.purchase_value, draft.currency)} · Risiko{" "}
            {formatPrice(result.estimated_risk, draft.currency)} · Sisa modal{" "}
            {formatPrice(result.remaining_capital, draft.currency)}
          </p>
          {result.lots === 0 && (
            <p>
              Modal atau batas risiko belum cukup untuk satu lot sesuai input.
            </p>
          )}
          <p>{result.limitations}</p>
        </div>
      )}
      {plans.map((p) => (
        <article
          key={p.id}
          className="border border-slate-700 rounded p-4 space-y-3"
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
          <div className="flex flex-wrap gap-3">
            <button
              className={actionClass}
              disabled={busy}
              onClick={() => select(p)}
            >
              Edit rencana
            </button>
            <button
              className={actionClass}
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setError("");
                try {
                  await apiClient.delete("/trade-plans/" + p.id);
                  if (editing?.id === p.id) select(null);
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
