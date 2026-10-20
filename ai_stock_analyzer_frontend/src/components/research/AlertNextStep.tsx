import Link from "next/link";

const guidance: Record<
  string,
  {
    text: string;
    destination?: "stock" | "settings" | "monitoring";
    action?: string;
  }
> = {
  paused: {
    text: "Aturan dijeda. Gunakan Aktifkan jika ingin melanjutkan evaluasi EOD.",
  },
  notifications_disabled: {
    text: "Aktifkan preferensi notifikasi akun untuk menerima kejadian berikutnya.",
    destination: "settings",
    action: "Buka preferensi notifikasi",
  },
  waiting_for_data: {
    text: "Periksa sumber dan sesi data saham. Jika kalender belum terverifikasi, operator perlu memverifikasinya; tombol pengguna tidak dapat menandai data sebagai fresh.",
    destination: "stock",
    action: "Periksa data saham",
  },
  waiting_for_analysis: {
    text: "Buka saham dan jalankan analisis setelah data tersedia. Analisis harus sesuai revisi data terkini.",
    destination: "stock",
    action: "Buka saham untuk analisis",
  },
  waiting_for_previous_session: {
    text: "Data sesi pembanding belum lengkap. Periksa histori; operator perlu melengkapi ingestion yang memenuhi syarat.",
    destination: "stock",
    action: "Periksa histori saham",
  },
  waiting_for_worker: {
    text: "Operator perlu memeriksa atau menjalankan kembali worker. Pengguna dapat meninjau status pekerjaan; menyimpan ulang alert tidak memulihkan worker.",
    destination: "monitoring",
    action: "Lihat status pekerjaan",
  },
  waiting_for_baseline: {
    text: "Tunggu evaluasi pertama yang memenuhi syarat. Baseline awal tidak mengirim notifikasi historis.",
  },
  ready: {
    text: "Aturan menunggu perubahan pada sesi EOD berikutnya yang memenuhi syarat. Ini bukan pemantauan harga realtime.",
  },
};
export function AlertNextStep({
  state,
  ticker,
}: {
  state: string;
  ticker: string;
}) {
  const item = guidance[state] || {
    text: "Kesiapan belum diketahui. Periksa status layanan bersama operator sebelum mengandalkan alert.",
  };
  const href =
    item.destination === "stock"
      ? "/stock/" + encodeURIComponent(ticker)
      : item.destination === "settings"
        ? "/settings#notification-preferences"
        : "#monitoring-jobs";
  return (
    <div className="text-sm space-y-2">
      <p>{item.text}</p>
      {item.destination && (
        <Link
          className="inline-flex min-h-11 items-center underline"
          href={href}
        >
          {item.action}
        </Link>
      )}
    </div>
  );
}
