# Implementasi PRD tindak lanjut review pengguna

Tanggal: 19 Oktober 2026, WIB. Acuan: [PRD 1.1](prd_perbaikan_aplikasi.md), [review baseline 42d887a](review_pengguna_2026-10-19.md), dan implementasi R1 pada `541c281`.

Perubahan berikut tersedia pada branch `work`. Ini laporan implementasi dan validasi lokal; gerbang rilis publik di bagian akhir masih terbuka.

## Perilaku yang tersedia

| Paket PRD | Implementasi |
|---|---|
| B16 — Integrasi | Pilihan server `AI_PROVIDER=anthropic|gemini` dan `MARKET_DATA_PROVIDER=yahoo|eodhd`, tanpa pergantian provider diam-diam. Gemini memakai JSON schema, memeriksa finish reason, dan menyimpan penggunaan token/model aktual. EODHD memetakan IDX/AS dan menyesuaikan OHLC per bar dari adjusted_close; volume split-adjusted provider tidak disesuaikan ulang. |
| Provenance/cache | Provider/model aktual, sumber/currency/bursa/basis harga/volume serta data revision ikut disimpan. Revisi harga membedakan semantik sumber/adjustment. Metadata lama tetap unknown kecuali seri Yahoo R1 yang basisnya sudah diketahui. |
| Kalender | `exchange-calendars` menyediakan sesi XIDX dan kalender saham AS. Flag verifikasi dan delay publikasi harus dikonfigurasi; default tetap unknown. Hari libur dan sesi pendek diuji memakai kasus kalender terkontrol. Ini bukan verifikasi kontrak/jadwal provider nyata. |
| B07–B09/B11/B20 | Dashboard berhalaman, metadata perusahaan terpisah dari kegagalan AI/quote, status sudah ditambahkan, filter bursa dan sort harga per currency di watchlist. Target sentuh tombol minimal 44px, fokus terlihat, label/error input terhubung. Panduan .JK/indikator/confidence/EOD/Free/Premium dapat dibuka kembali. |
| B10 — Job | API penerimaan 202 dan status privat, antrean database, klaim atomik, TTL antrean 10 menit, deadline eksekusi 120 detik, maksimal dua attempt, dan batas retry. Frontend menampilkan tahap serta memuat job aktif setelah reload. Kuota/idempotensi HTTP dan worker memakai service yang sama. |
| B13 — Alert | Rule privat harga/persen/sinyal, pause/resume/delete, baseline awal tanpa trigger retroaktif, evaluasi sesi/revisi baru, event unik, mark-read dan badge dari jumlah aktual. Data stale/unknown tidak mengaktifkan alert. Preferensi akun dapat menjeda evaluasi. |
| B17 — Screener | Filter bursa/sektor/volume/RSI/Wyckoff/SMC, sort/pagination server pada seluruh cakupan tersimpan, tanggal indikator selaras dengan harga, penanganan null serta filter tersimpan privat. Universe tersimpan tidak dipasarkan sebagai seluruh IDX. |
| B18/B21 — Riwayat | Daftar berhalaman, perbandingan dua analisis, perubahan skor dalam poin persentase, provenance dan waktu/model/prompt asli. CSV mengekspor pilihan/seluruh hasil, PDF tersedia dengan batas eksplisit; ekspor tidak menjalankan AI dan melindungi sel CSV dari formula. |
| B19 — Rencana transaksi | Draft long dari input pengguna, area entry/entry/stop/target, modal/currency/lot, fee/slippage, horizon/alasan/pembatalan. Kalkulator membatasi lembar oleh modal dan risiko, menyimpan versi dengan optimistic concurrency, dan menandai perubahan data. Tidak mengirim order broker. |
| B15 — Backtest | Modal, lot opsional, fee beli/jual dan slippage dalam bps; arus kas dan equity setelah biaya, return bersih, total biaya, benchmark buy-and-hold. Histori tambahan dipakai untuk warm-up indikator. Run privat tersimpan dan CSV diambil dari hasil tersebut tanpa simulasi ulang. |
| B14 — Akun | Edit profil/preferensi, ubah password dengan verifikasi lama dan pencabutan semua sesi; reset lewat SMTP STARTTLS, token hash sekali pakai/30 menit, pesan publik generik, dan halaman reset dari tautan email. Kegagalan pengiriman tidak dinyatakan sebagai email berhasil terkirim. |

Job produk menggunakan database aplikasi sebagai antrean durable; Redis tidak diperlukan untuk antrean ini. Celery lama membaca broker/backend dari environment, tidak lagi mengunci berkas broker SQLite pada checkout. Jangan menjalankan batch Celery lama sebagai pengganti worker produk yang memiliki ownership/kuota.

## Menjalankan

1. Dari `ai_stock_analyzer`, install requirements ke `.venv`, backup database berisi data, lalu jalankan `.venv/bin/alembic upgrade head` hingga `r2_product`.
2. Jalankan backend normal: `.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
3. Pada proses terpisah dengan environment/database yang sama, jalankan `.venv/bin/python -m app.worker.product_worker`. Gunakan process supervisor untuk deployment; `--once` tersedia untuk satu siklus pemeriksaan.
4. Dari `ai_stock_analyzer_frontend`, jalankan `npm run dev`. Akses browser tetap same-origin `/api/v1`; `API_PROXY_TARGET` diatur sebelum build/dev jika backend berbeda.
5. Buka menu **Riset dan pemantauan** untuk screener, histori, alert/job, dan rencana. Backtest berbiaya berada pada halaman backtest saham, pengaturan akun pada Settings, dan panduan pada menu glosarium.

Konfigurasi ada pada [.env.example](../.env.example). Jangan menyalin nilai rahasia ke Git atau chat. Menambahkan adapter tidak membuat kunci, membayar paket, mengaktifkan lisensi display, atau mengubah izin jaringan cloud.

Untuk Gemini/EODHD, set pilihan provider dan masukkan kuncinya lewat pengaturan environment. Tujuan HTTPS yang diperlukan adalah `generativelanguage.googleapis.com` dan `eodhd.com`. Pilihan lama tetap tersedia untuk kompatibilitas. Groq, Ollama, Sectors dan Twelve Data masih kandidat kajian, bukan adapter yang diimplementasikan pada paket ini.

Kalender tetap nonaktif secara default. Tetapkan `EOD_PUBLICATION_DELAY_MINUTES` dari kontrak provider dan aktifkan `MARKET_CALENDAR_VERIFIED` hanya setelah kalender/jadwal instrumen pilot diperiksa. Nilai delay contoh pada template bukan bukti SLA provider. Adapter tetap konservatif terhadap bar sesi berjalan.

Worker mengevaluasi alert dari data baru yang sudah tersimpan. Sinkronisasi dapat dipicu dari detail/job atau scheduler pengambilan data yang dikonfigurasi operator. Worker ini tidak membuat jadwal pembelian data seluruh pasar atau menjalankan AI tanpa permintaan pengguna. Aktivasi pemantauan produksi memerlukan kebijakan ingestion EOD dan budget provider yang disepakati.

Reset email membutuhkan SMTP host/from serta jalur jaringan SMTP yang diizinkan. HTTPS allowlist saja tidak menyediakan TCP SMTP. Fitur mengembalikan pesan konfigurasi saat layanan pengirim belum tersedia; tes menggunakan transport email terkontrol.

## Validasi yang dapat diulang

~~~bash
# Dari backend; database test harus disposable, karena fixture membuat ulang tabel.
.venv/bin/python -m pytest tests/ -q
TEST_DATABASE_URL=postgresql+asyncpg://USER@HOST/TEST_DB .venv/bin/python -m pytest tests/ -q
.venv/bin/python -m scripts.export_openapi

# Dari frontend.
npm run lint
npm run build
~~~

Smoke browser menggunakan tiga proses terpisah dan database khusus:

- Backend `tests.browser_app:app`, dengan `BROWSER_SMOKE=1`, `TESTING=1`, serta DSN test yang mengandung `browser-r1`; aplikasi menolak fixture pada database normal.
- Worker `.venv/bin/python -m tests.browser_worker` dengan DSN/flag yang sama; fixture tidak dipasang pada worker normal.
- Frontend produksi yang dibangun dengan proxy menuju backend fixture. Jalankan `.venv/bin/python tests/browser_smoke.py` dengan `BROWSER_BASE_URL` dan direktori output yang sesuai.

CI diperbarui untuk menjalankan worker fixture terpisah bersama browser. Tidak ada klaim workflow GitHub sudah lulus sebelum ada hasil remote yang diperiksa.

## Gerbang yang masih terbuka

- **G1:** belum ada kunci/provider nyata, izin runtime API, hasil benchmark AI nyata, bukti adjustment/cakupan IDX+AS nyata, atau konfirmasi biaya/hak display. Gemini/EODHD diuji dengan transport terkontrol, bukan API berbayar nyata.
- **G2:** pemeriksaan browser otomatis tidak menggantikan pilot lima orang atau audit screen reader manual lengkap. Konsistensi bahasa di beberapa label lama masih perlu penyempurnaan.
- **G3:** engine dan UI alert dapat diuji lokal, tetapi aktivasi pasar nyata memerlukan kalender/jadwal dan ingestion EOD yang terverifikasi.
- **G4/G5:** API/domain/ekspor diuji terkontrol. Retensi tujuh hari, performa staging 100 ticker/lima tahun/20 pengguna, dan pengiriman email nyata belum diukur.
- Tidak ada pembayaran/upgrade mandiri, intraday, eksekusi broker, atau deployment produksi pada paket ini. Fitur tersebut tetap mengikuti ruang lingkup PRD.

## Hasil eksekusi akhir

- Regresi backend: **107 test lulus pada SQLite dan 107 pada PostgreSQL 16**, termasuk kontrak provider terkontrol, isolasi akun, retry/expiry/cancellation, kuota satu kali, dua worker, dua tab, biaya backtest dan migrasi. Setelah penyempurnaan ekspor/perbandingan, suite alur produk juga dijalankan ulang pada kedua database. Ruff pada berkas Python yang berubah lulus. Masih ada warning dependency/deprecation serta coroutine AsyncMock pada test Celery lama; hasil ini tidak membuktikan worker Celery lama siap produksi.
- Browser Chromium: **19 pemeriksaan lulus** melalui backend dan worker fixture yang terpisah. Mencakup registrasi/login, keyboard/toggle password, pagination dashboard, pencarian, sync/AI tersimpan, pemulihan job sesudah reload, backtest, notes, screener/filter tersimpan, CSV/riwayat, rencana transaksi, alert/preferensi, refresh serentak, logout, kegagalan parsial, `INVALIDXYZ`, mobile 360px/390 × 844 dan target sentuh. Provider fixture tidak menjadi data aplikasi normal.
- ESLint, TypeScript tanpa emit dan build Next produksi lulus. Build akhir memakai proxy normal ke API port 8000, bukan backend fixture.
- Migrasi SQLite fresh/legacy dan PostgreSQL fresh/legacy berisi data diuji. Database development di-backup melalui SQLite backup sebelum `alembic upgrade head`; jumlah akun/watchlist tetap sama (database development ini sebelumnya kosong). Backup lokal: `/workspace/.cloud-setup/ai-stock-analyzer/development-before-r2-20261019-053254.db`.
- API normal, worker produk dan frontend development dijalankan kembali. Smoke akun disposable memeriksa registrasi, login, tujuh pembacaan privat, logout, serta penolakan access/refresh token lama. Akun pengujian dibersihkan. Tidak memasang fixture pada ketiga proses normal tersebut.
- Log rinci dan screenshot lokal berada di `/workspace/.cloud-setup/ai-stock-analyzer/`; bukti ini tidak diklaim tersedia pada deployment atau workspace baru.

### Konfigurasi cloud yang belum tersimpan

Penyimpanan draft baru ditolak tool karena konfigurasi environment sudah berubah/dipublikasikan sejak draft sesi ini dibuat (base version stale). Membaca ulang dan mengirim draft yang sama tidak menyelesaikannya. Perubahan aplikasi tetap tersimpan dalam Git; pembaruan konfigurasi cloud **belum dikonfirmasi tersimpan atau diterapkan**.

Usulan lengkap dapat dipindahkan lewat [cloud-environment-r2-proposal.json](cloud-environment-r2-proposal.json), dengan instruksi manusia di [cloud-start-r2.md](cloud-start-r2.md). File JSON berisi instruksi startup tiga proses, tambahan domain `generativelanguage.googleapis.com`/`eodhd.com`, kebutuhan secret opsional tanpa nilai, dan referensi install script sebelumnya. Buka sesi setup baru dari pengaturan environment terkini, baca draft baru, lalu rekonsiliasi usulan sambil mempertahankan konfigurasi yang lebih baru. Setelah tersimpan, pengaturan tetap perlu disimpan/publish agar aktif. Tidak mengganti daftar repository dari draft lama.
