# UX & FEATURE RECOMMENDATIONS — 8d9645d

## Perbaikan UX fitur yang sudah ada

Dasar rekomendasi adalah journey yang benar-benar dijalankan; bukan usulan membangun ulang fitur yang sudah tersedia. Perbaikan bug dipisahkan dari fitur baru.

| Kondisi sekarang | Masalah pengguna | Usulan desain/workflow | Alur sekarang | Alur usulan | Manfaat | Kesulitan | Prioritas |
|---|---|---|---|---|---|---|---|
| Konteks screener hilang saat Back (BUG-007) | Investor harus mengisi filter lagi untuk setiap kandidat. | Letakkan kriteria/sort/page diURL, lalu pulihkan kartu dan posisi scroll. | Terapkan→buka saham→Back→isi ulang | Terapkan→buka saham→Back→lanjut kandidat berikutnya | Mempercepat pemilihan beberapa kandidat. | Sedang | P2 |
| Compare lama dapat muncul pada ticker baru (BUG-005) | Investor berisiko membaca analisis saham berbeda. | Guard snapshot request, batalkan requestlama dan cantumkan ticker/tanggal/model pada panel. | Bandingkan BBCA→muat AAPL→panel BBCA menyusul | Ganti saham→compare lama dibatalkan→hanya data saham aktif | Mengembalikan kepercayaan konteks analisis. | Rendah–sedang | P1 |
| Alert sinyal gagal dengan pesan above/below (BUG-006) | Pengguna tidak dapat memperbaiki form yang tidak memiliki arah. | Payload berbeda per jenis alert dan pesan validasi berbahasa pengguna. | Pilih sinyal→Simpan→error teknis | Pilih sinyal→Simpan→rule/status tersimpan | Monitoring sinyal dapat digunakan. | Rendah | P2 |
| Badge belum langsung mengikuti mark-read (B03) | Status Belum dibaca terlihat bertentangan dengan event yang sudah dibaca. | Invalidasi cache/count atau kirim event state bersama sesudah mark-read. | Tandai dibaca→badge lama→tunggu polling | Tandai dibaca→event dan badge berubah bersama | Mengurangi kebingungan serta pengecekan ulang. | Rendah | P3 |
| Bahasa backtest campuran (J13) | Pemula perlu menerjemahkan Configuration, Trade History, Avg Profit. | Gunakan bahasa Indonesia konsisten dengan penjelasan singkat win rate, drawdown, bps. | Baca label English→buka panduan | Baca label lokal→bantuan kontekstual bila perlu | Hasil simulasi lebih mudah dipahami tanpa menjanjikan profit. | Rendah | P3 |
| Pengguna baru belum diarahkan ke tugas pertama (J02) | Dashboard berfungsi tetapi pemula harus menebak langkah awal. | Tampilkan jalur singkat cari saham→lihat tanggal/sinkronkan→simpanwatchlist, dapatditutup. | Login→eksplorasi menu | Login→pilih tugas pertama→mulai riset | Mempercepat orientasi awal. | Rendah–sedang | P3 |
| Arti unknown dan kesiapan alert masih teknis (J12/B01/G03) | Rule aktif mudah dianggap sudah memantau pasar walau belum ada data eligible. | Tampilkan status menunggu-data, sesi terakhir dan penjelasan sumber/kalender/worker yang dapatdiverifikasi; jangan mengklaim heartbeat bila tidak diukur. | Buat rule→baca penjelasan teknis | Buat rule→lihat status dan syarat aktivasi yang jelas | Ekspektasi monitoring lebih akurat. | Sedang | P2 |
| Wyckoff/SMC sulit ditelusuri pada fixture detail (J04/T04) | Trader sulit menghubungkan pola dengan candle dan alasan AI. | Tampilkan penjelasan pola yang benar-benar terdeteksi besertatanggal; beri Belum tersedia bila tidak ada. Jangan membuatlabel pengganti. | Lihat indikator→cari interpretasi di panduan | Pilih pola yang tersedia→lihat candle/alasan/limitasi | Memperjelas riset teknikal tanpa menambah sinyal buatan. | Sedang | P3 |

## Peningkatan yang sudah terbukti dan perlu dipertahankan

- Panel candle tekstual tanpa hover, sliderkeyboard dan reset candle terbaru.
- Input kalkulator dasar terpisah dari uraian lengkap rencana; asumsi biaya tetap terlihat.
- Hasil kalkulator diinvalidasi ketika input berubah dan terlindungi dari responsrencana lama.
- Header320 px utuh, padding 12 px dan tab44 px pada build produksi.
- Tanggal penutupan, sumber, currency dan badge dibedakan dari waktu fetch.
- Watchlist notes, sorting/filter, preset, history, CSV/PDF, alert harga dan versioning rencana sudah ada. Jangan mengusulkan fitur tersebut sebagai penambahan dari nol.

## Fitur tambahan baru (tiga usulan, sesudah stabilisasi)

| Usulan | Kebutuhan yang terlihat | Yang sudah ada dan batasnya | Nilai tambahan | Kesulitan dan dependensi |
|---|---|---|---|---|
| Perbandingan2–3 saham | Journey screener mengharuskan membuka kandidat satu per satu. | Compare saat ini membandingkan dua analisis untuk satu ticker. | Tampilan sejajar indikator, tanggal, sektor, sumber dan risiko beberapa kandidat. Harga beda currency harus tetap diberi unit; tanpa konversi otomatis yang tidak terverifikasi. | Sedang; memerlukan perbaikan konteks compare dan metadata konsisten. |
| Jurnal evaluasi rencana dengan input manual | Rencana dapat disimpan dan diedit tetapi pengguna belum dapat mengevaluasi apa yang terjadi sesudahnya. | Notes watchlist dan versi rencana mencatat alasan/input, bukan evaluasi hasil. | Catat keputusan manual, hasil/kondisi pembatalan dan pelajaran dari rencana; tidak mengirim order dan tidak mengklaim hasil broker. | Sedang; definisikan status/hak edit dan bedakan catatan pengguna dari data pasar. |
| Ringkasan perubahan watchlist sejak kunjungan terakhir | Pengguna memeriksa beberapa saham dan alert terpisah. | Dashboard, watchlist dan alert sudah ada; belum ada ringkasan perubahan relatif ke kunjungan pengguna. | Sorot perubahan tanggal data, harga atau rekomendasi yang baru, dengan sumber dan ketidaktersediaan yang jelas. | Sedang–tinggi; memerlukan snapshot kunjungan dan ingestion yang sah. Jangan menyebutnya realtime. |

## Sepuluh prioritas perbaikan

| Urutan | Prioritas | Pekerjaan | Kriteria selesai |
|---|---|---|---|
| 1 | P1 | Perbaiki respons compare yang melintasi ticker | N05 tidak boleh menampilkan panel BBCA pada AAPL, termasuk responslambat dan Back/Forward. |
| 2 | P2 | Benahi payload alert sinyal | BUY/HOLD/WAIT dapat disimpan dari UI; field arah tidak relevan tidak menghasilkan422. |
| 3 | P2 | Pertahankan konteks screener | Kriteria, page, sort dan posisi kembali sesudah detail, Back, Forward danrefresh. |
| 4 | P2 | Perjelas identitas record dalam panel perbandingan | Ticker, tanggal data, waktu hasil danmodel tercantum untukkedua sisi. |
| 5 | P3 | Sinkronkan badge dan event sesudah mark-read | UnreadAPI dan badge berubah bersama tanpa menunggu polling 30 detik. |
| 6 | P3 | Konsistenkan bahasa dan pesan validasi | Label danerror terkait backtest/alert memakai bahasa yang dapatdipahami pengguna. |
| 7 | P3 | Tambahkan orientasi tugas pertama yang ringkas | Pengguna dapat memulai cari/detail/watchlist tanpa menebak menu; validasi dengan peserta manusia. |
| 8 | P3 | Perjelas interpretasi indikator yang tersedia | Bantuan RSI/MACD/Wyckoff/SMC menautkan tanggal dan sumber tanpa mengisi nilai kosong. |
| 9 | P2 gate | Terima readiness monitoring dan data nyata | Kalender, ingestion, sumber serta status worker yang terukur dibuktikan sebelum aktivasi alert nyata. |
| 10 | Release gate | Selesaikan penerimaan layanan dan pilot lapangan | ProviderIDX+AS/AI dan SMTP nyata, perangkat fisik, pilot manusia serta staging/retensi dibuktikan sesuai cakupan rilis. |

## Penilaian dan keputusan

| Dimensi | Skor 0–10 | Dasar |
|---|---:|---|
| Ease of Use | 7,5 | Register, pencarian dan kalkulator bertahap mudah dijalankan; kosakata teknis, bahasa campuran dan hilangnya filter masih menghambat. |
| Feature Usability | 7 | Watchlist, preset, rencana, ekspor dan alert harga bekerja; alert sinyal gagal dari UI dan perbandingan memiliki masalah konteks. |
| Financial Data Trustworthiness | 6 | Angka fixture konsisten dan oracle biaya cocok; bug perbandingan beda ticker berisiko menyesatkan. Provider/adjustment nyata belum diterima. |
| Desktop UX | 8 | Spacing dan hierarki tanggal lebih jelas pada build produksi; konteks screener dan perbandingan perlu diperbaiki. |
| Mobile UX | 8 | Enam lebar, header, dialog, sentuhan, slider, hitung/simpan rencana dan backtest dapat digunakan. Perangkat fisik belum diuji. |
| Stability | 7 | Tidak ada pageerrorJS pada suite journey/negative/mobile; recovery503 dan request rencana lambat bekerja. Race pada perbandingan masih terbuka. |
| Overall Product Quality | 7,5 | Peningkatan nyata terhadap d17f260, tetapi tiga bug baru dan gerbang provider/operasional menahan rilis publik. |

**Belum siap rilis publik untuk investor nyata.** Perubahan8d9645d layak diteruskan ke pilot internal setelah P1 ditutup. Peningkatan skor mobile/desktop tidak menutup gerbang integrasi nyata. Tiga usulan fitur baru tidak mendahului perbaikan bug dan pembuktian layanan.
