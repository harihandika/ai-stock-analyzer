import { Analysis } from "@/services/market";

const names: Record<string, string> = {
  bullish_fvg: "Fair value gap naik",
  bearish_fvg: "Fair value gap turun",
  bos: "Break of structure",
  choch: "Change of character",
  bullish_ob: "Order block naik",
  bearish_ob: "Order block turun",
};
export function PatternEvidence({
  analysis,
  canSelect,
  onSelect,
}: {
  analysis: Analysis | null;
  canSelect: boolean;
  onSelect: (date: string) => void;
}) {
  const indicators = analysis?.technical_indicators;
  const patterns = Object.entries(indicators?.smc_patterns || {}).filter(
    ([key, value]) => names[key] && value === true,
  );
  return (
    <details className="rounded border border-slate-700 p-4 space-y-3">
      <summary className="min-h-11 cursor-pointer py-2">
        Memahami indikator dan pola
      </summary>
      <p>
        RSI mengukur momentum 0–100; nilai tinggi/rendah saja tidak memastikan
        pembalikan. MACD membandingkan rata-rata bergerak. Nilai kosong berarti
        belum tersedia, termasuk histori pemanasan yang kurang.
      </p>
      {indicators ? (
        <>
          <p>
            Indikator sesi {indicators.trading_date} ·{" "}
            {analysis?.metadata.source || "Sumber belum terverifikasi"}. Tanggal
            indikator dapat berbeda dari tanggal hasil AI.
          </p>
          <p>Fase Wyckoff: {indicators.wyckoff_phase || "Belum tersedia"}.</p>
          <p>
            Pola SMC:{" "}
            {patterns.length
              ? patterns.map(([key]) => names[key]).join(", ")
              : "Belum tersedia pola terdeteksi untuk sesi ini"}
            .
          </p>
          <button
            className="border rounded p-3 disabled:opacity-50"
            disabled={!canSelect}
            onClick={() => onSelect(indicators.trading_date)}
          >
            Lihat candle sesi indikator
          </button>
          {!canSelect && (
            <p>
              Candle sesi indikator belum tersedia dalam rentang yang
              ditampilkan.
            </p>
          )}
        </>
      ) : (
        <p>Tanggal dan pola indikator belum tersedia.</p>
      )}
      <p>
        Wyckoff/SMC adalah interpretasi algoritma atas harga dan volume yang
        tersedia. Periksa tanggal konfirmasi, alasan dan keterbatasan; pola
        tidak memastikan arah harga atau profit.
      </p>
    </details>
  );
}
