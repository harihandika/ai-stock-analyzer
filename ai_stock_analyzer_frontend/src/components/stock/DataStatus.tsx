import { MarketMetadata } from "@/services/market";

export function DataStatus({ metadata }: { metadata?: MarketMetadata | null }) {
  if (!metadata || metadata.data_state === "unavailable")
    return <p className="text-sm text-slate-400">Data pasar belum tersedia.</p>;
  const state = metadata.data_state;
  const badge =
    state === "demo"
      ? "DATA DEMO"
      : state === "stale"
        ? "Data lama"
        : state === "fresh"
          ? "Data sesuai kalender bursa"
          : "Keterkinian belum terverifikasi";
  const style =
    state === "fresh"
      ? "border-emerald-700 text-emerald-200"
      : state === "stale" || state === "demo"
        ? "border-amber-600 text-amber-200"
        : "border-slate-500 text-slate-200";
  return (
    <div
      className="text-sm text-slate-300 space-y-2 break-words"
      data-testid="market-data-status"
    >
      <p>
        <strong>Penutupan pasar:</strong>{" "}
        {metadata.market_as_of || "Tanggal belum diketahui"} · Candle harian
      </p>
      <p>
        {metadata.source || "Sumber belum terverifikasi"} ·{" "}
        {metadata.exchange || "Bursa belum terverifikasi"} ·{" "}
        {metadata.currency || "Currency belum terverifikasi"}
      </p>
      <p>
        <span className={"inline-block rounded border px-2 py-1 " + style}>
          {badge}
        </span>
      </p>
      <details>
        <summary className="cursor-pointer min-h-11 py-2">
          Rincian sumber dan waktu
        </summary>
        <div className="mt-2 space-y-2">
          {state === "unknown" && (
            <p>
              Status keterkinian belum terverifikasi terhadap kalender bursa.
            </p>
          )}
          {metadata.fetched_at && (
            <p>
              Diambil:{" "}
              {new Date(metadata.fetched_at).toLocaleString("id-ID", {
                timeZone: "Asia/Jakarta",
              })}{" "}
              WIB. Waktu pengambilan tidak mengubah tanggal penutupan harga.
            </p>
          )}
          <p>
            Zona sesi: {metadata.session_timezone || "Belum diketahui"} · Status
            pasar:{" "}
            {metadata.market_status === "open"
              ? "Buka"
              : metadata.market_status === "closed"
                ? "Tutup"
                : "Belum terverifikasi"}
            .
          </p>
          {metadata.publication_delay_minutes != null && (
            <p>
              Delay publikasi yang dikonfigurasi:{" "}
              {metadata.publication_delay_minutes} menit.
            </p>
          )}
          {metadata.price_adjustment === "split_and_dividend_adjusted" && (
            <p>Harga historis disesuaikan untuk split dan dividen.</p>
          )}
          {metadata.volume_adjustment &&
            metadata.volume_adjustment !== "unknown" && (
              <p>
                Volume:{" "}
                {metadata.volume_adjustment === "split_adjusted"
                  ? "disesuaikan split oleh provider"
                  : "sesuai laporan provider"}
                .
              </p>
            )}
        </div>
      </details>
    </div>
  );
}
