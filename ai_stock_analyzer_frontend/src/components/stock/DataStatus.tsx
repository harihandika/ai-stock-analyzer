import { MarketMetadata } from "@/services/market";
export function DataStatus({ metadata }: { metadata?: MarketMetadata | null }) {
  if (!metadata || metadata.data_state === "unavailable")
    return <p className="text-sm text-slate-400">Data pasar belum tersedia.</p>;
  return (
    <div className="text-xs text-slate-400 space-y-1">
      <p>
        Data penutupan harian ·{" "}
        {metadata.market_as_of || "Tanggal belum diketahui"} ·{" "}
        {metadata.source || "Sumber belum terverifikasi"} ·{" "}
        {metadata.exchange || "Bursa belum terverifikasi"}
      </p>
      <p>
        {metadata.data_state === "demo"
          ? "DATA DEMO"
          : metadata.data_state === "stale"
            ? "Data lama"
            : metadata.data_state === "fresh"
              ? "Data sesuai kalender bursa"
              : "Status keterkinian belum terverifikasi terhadap kalender bursa."}
      </p>
      {metadata.price_adjustment === "split_and_dividend_adjusted" && (
        <p>Harga historis disesuaikan untuk split dan dividen.</p>
      )}
      {metadata.fetched_at && (
        <p>
          Diambil:{" "}
          {new Date(metadata.fetched_at).toLocaleString("id-ID", {
            timeZone: "Asia/Jakarta",
          })}{" "}
          WIB
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
  );
}
