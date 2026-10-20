import Link from "next/link";
import { AppLayout } from "@/components/layout/AppLayout";

const glossary = [
  [
    "Ticker .JK",
    "Akhiran .JK menunjukkan saham Indonesia pada aplikasi, misalnya BBCA.JK. Instrumen AS menggunakan ticker dan currency USD; aplikasi tidak mengonversi harga secara otomatis.",
  ],
  [
    "EOD dan waktu data",
    "Harga penutupan harian berbeda dari harga real-time. Tanggal sesi, waktu pengambilan, sumber, dan zona waktu memiliki makna berbeda. Status unknown berarti keterkinian belum dapat diverifikasi.",
  ],
  [
    "BUY / HOLD / WAIT",
    "Label analisis teknikal tersimpan. Data atau analisis yang belum tersedia tidak otomatis berarti HOLD. Periksa alasan pendukung, penyangkal, horizon, serta keterbatasannya.",
  ],
  [
    "Confidence",
    "Skor dari model, bukan probabilitas profit atau janji akurasi. Perubahan 80 menjadi 60 adalah -20 poin persentase, bukan return -20%.",
  ],
  [
    "RSI",
    "Indikator momentum pada skala 0–100. RSI tinggi/rendah saja tidak memastikan harga akan berbalik. Nilai kosong berarti indikator belum tersedia.",
  ],
  [
    "EMA dan MACD",
    "EMA merangkum harga historis dengan bobot lebih besar pada data baru; MACD membandingkan rata-rata bergerak. Histori pemanasan dibutuhkan dan sinyal tetap dapat salah.",
  ],
  [
    "VPA, Wyckoff, SMC",
    "Kerangka teknikal untuk membaca hubungan harga/volume, fase pasar dan struktur harga. Pola yang memerlukan konfirmasi baru boleh dipakai setelah data konfirmasinya tersedia.",
  ],
  [
    "Alert EOD",
    "Notifikasi dari transisi kondisi pada sesi lengkap yang terverifikasi. Worker harus berjalan. Data stale atau unknown tidak memicu alert. Notifikasi bukan order otomatis.",
  ],
  [
    "Risiko dan lot",
    "Kalkulator membatasi lembar oleh modal dan risiko per rencana. IDX memakai lot 100 lembar; AS pada versi ini memakai lembar utuh. Gap, biaya, slippage dan likuiditas dapat membuat kerugian melebihi perhitungan stop.",
  ],
  [
    "Backtest",
    "Simulasi strategi teknikal pada histori, bukan rekam jejak keputusan AI. Keputusan close dieksekusi pada open berikutnya; TP/SL tidak menjamin harga fill. Periksa seluruh transaksi, equity, biaya, dan pembanding buy-and-hold.",
  ],
];

export default function Guide() {
  return (
    <AppLayout>
      <article className="max-w-4xl mx-auto space-y-6 pb-12">
        <h1 className="text-3xl font-bold">Panduan dan glosarium</h1>
        <p>
          Mulai dari pencarian nama/kode, buka detail, periksa sumber dan
          tanggal, lalu simpan ke daftar pantauan. Jalankan AI setelah data
          tersedia; status job dapat dibuka kembali dari halaman riset.
        </p>
        <Link
          className="inline-block p-3 rounded border border-sky-600"
          href="/research"
        >
          Buka riset dan pemantauan
        </Link>
        <section className="rounded border border-slate-700 p-5 space-y-2">
          <h2 className="text-xl">Free dan Premium</h2>
          <p>
            Free: maksimal tiga analisis baru yang berhasil per hari. Cache hit
            dan kegagalan tidak mengurangi kuota. Reservasi yang sedang diproses
            ditampilkan terpisah; reset pukul 00.00 WIB.
          </p>
          <p>
            Premium: aplikasi saat ini menampilkan kuota harian tidak terbatas
            untuk akun dengan tier premium, tetap mengikuti rate limit dan
            ketersediaan provider. Pengaturan akun menunjukkan entitlement dari
            server.
          </p>
          <p>
            Pembayaran dan upgrade mandiri belum tersedia. Halaman ini tidak
            mengaktifkan langganan atau menjanjikan layanan yang belum
            dikonfigurasi.
          </p>
          <Link className="underline inline-block p-2" href="/settings">
            Lihat kuota akun
          </Link>
        </section>
        {glossary.map(([term, explanation]) => (
          <section key={term} className="space-y-2">
            <h2 className="text-xl font-semibold">{term}</h2>
            <p>{explanation}</p>
          </section>
        ))}
      </article>
    </AppLayout>
  );
}
