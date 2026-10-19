# Implementasi PRD 1.2 sesudah audit d17f260

Tanggal: 19 Oktober 2026, Asia/Jakarta (WIB). Acuan: [PRD 1.2](prd_perbaikan_pasca_audit_d17f260.md) dan [ringkasan audit sumber](review_audit_d17f260_2026-10-19.md). Baseline sebelum perubahan: `d17f260` pada `main` dan `work`.

## Perubahan produk

| Paket | Perilaku sesudah perubahan | Batas penerimaan |
|---|---|---|
| PA-01 / BUG-001 | Form rencana memakai draft terkontrol dan versi snapshot. Perubahan input menghapus hasil aktif; calculate/save yang terlambat tidak mengaktifkan hasil lama. Simpan memakai perhitungan respons server, edit/batal/ganti ticker membersihkan konteks, dan konflik versi memiliki tombol muat ulang. | Uji browser dan API terkontrol; rumus finansial tidak diubah. |
| PA-02 / BUG-002 | Header fleksibel, search dapat mengecil, gap/padding mobile disesuaikan dan tombol tetap 44px. Dropdown dapat ditutup dengan Escape dan fokus kembali ke pemicu. | Bounding box diperiksa pada sepuluh halaman × enam lebar; bukan hanya pemeriksaan scrollbar. Perangkat fisik tetap pending. |
| PA-03 / BUG-003 | Reset universal padding/margin dihapus; Tailwind preflight menangani reset. Padding utility kembali berlaku, tab riset berupa area klik minimal 44px, fokus summary terlihat. | Computed style pada build produksi membuktikan input 12px dan tab horizontal 16px. |
| PA-04 / BUG-004 | Panel candle tampil sebagai konten biasa, tanpa ketergantungan hover. Tanggal/OHLC/currency/volume/EMA/RSI/MACD dapat dibaca, nilai kosong tidak menjadi nol. Long press/tap, slider keyboard dan reset candle terbaru tersedia. | Chromium touch diuji; Safari/iPhone/Android fisik dan audit screen reader lengkap belum dilakukan. |
| PA-05 | Sumber/currency/bursa, tanggal penutupan dan badge keterkinian dekat harga; waktu fetch/WIB serta adjustment berada di rincian terpisah. Fetch baru tidak mengubah status stale. | Metadata diuji terkontrol. Pemahaman oleh lima peserta belum diukur. |
| PA-06 | Kalkulator dasar terpisah dari uraian rencana. Fee/slippage memiliki ringkasan selalu terlihat; area entry/horizon/alasan/pembatalan diminta saat menyimpan. | Kontrak calculate menerima payload minimal dan payload lengkap lama; simpan tetap wajib lengkap, termasuk menolak teks kosong/spasi. Pilot waktu tiga menit masih pending. |

`TradePlans` diekstrak dari halaman riset agar state formulir dan penanganan request dapat ditinjau tersendiri. Backend mengenalkan `PlanCalculationInput`; endpoint dan format hasil lama tetap tersedia. Optimasi pembacaan menambahkan migrasi `r3_read_paths`: dua indeks nonunik saham–tanggal, tanpa perubahan kolom atau penulisan ulang data. Screener memakai lookup sesi terakhir per saham; chart memvalidasi/menyerialisasi payload sekali; replay job yang sudah tersimpan tidak mengambil write lock. Backup development dibuat sebelum upgrade, dan migrasi PostgreSQL berisi 20 akun/100 saham/130.500 harga/130.500 indikator/satu watchlist/20 job mempertahankan seluruh jumlah serta catatan.

## Operasional yang disiapkan

CLI berikut berjalan dari direktori backend dengan environment/database yang sama seperti API:

```bash
# Read-only: konfigurasi berbentuk boolean, antrean, umur sesi per instrumen.
.venv/bin/python -m app.worker.market_ops status

# Opt-in: hanya universe eksplisit, tanpa AI dan tanpa kuota pengguna.
.venv/bin/python -m app.worker.market_ops ingest --tickers BBCA.JK,AAPL
```

Ingestion default **nonaktif**. Aktifkan hanya setelah provider/budget/lisensi, network, kalender dan jadwal publikasi diterima:

```dotenv
EOD_INGESTION_ENABLED=True
EOD_INGESTION_TICKERS=BBCA.JK,AAPL
MARKET_CALENDAR_VERIFIED=True
# EOD_PUBLICATION_DELAY_MINUTES harus berasal dari kontrak/jadwal provider.
```

Instrumen harus aktif dan sudah terdaftar dengan bursa yang dikenal. CLI menolak universe kosong/tidak valid/lebih dari 20 ticker, kalender yang belum diverifikasi dan kredensial EODHD yang belum tersedia. Ia melewati sesi yang sudah sesuai sumber/konfigurasi, melakukan maksimal dua attempt dalam 120 detik per ticker, mempertahankan transaksi data saat gagal, dan mengembalikan status incomplete/nonzero jika data masih menunggu atau gagal. `--refresh` tersedia untuk koreksi data yang disengaja dan dapat menambah biaya provider.

Satu host scheduler memakai file lock nonblocking berdasarkan identitas database agar run cron tidak tumpang tindih. Ini bukan koordinasi scheduler multi-host. Gunakan satu scheduler yang ditunjuk; product worker tetap proses terpisah untuk job pengguna dan evaluasi alert. Status CLI tidak membuktikan heartbeat worker atau koneksi provider; periksa supervisor/PID dan bukti request nyata secara terpisah.

Contoh template cron Linux setelah jadwal diverifikasi operator (01:15 UTC = 08:15 WIB, **bukan SLA provider yang sudah diterima**):

```cron
15 1 * * * cd /srv/ai-stock-analyzer/ai_stock_analyzer && .venv/bin/python -m app.worker.market_ops ingest >> /var/log/stock-eod.jsonl 2>> /var/log/stock-eod.err
```

Template ini tidak dipasang pada environment sekarang. Operator menyesuaikan path, zona cron, jadwal publikasi, rotasi log dan budget. Adapter tetap konservatif terhadap sesi berjalan; output awaiting_fresh_data tidak dianggap sukses. Koreksi corporate action dan pencocokan kalender/provider nyata tetap gerbang penerimaan.

## Bukti pengujian

Regresi backend akhir: **114 test lulus pada SQLite dan 114 pada PostgreSQL 16**. Sesudah optimasi baca, browser produksi kembali lulus **72 pemeriksaan pasca-audit dan 19 alur smoke**. Pengujian 200% memakai pembesaran root text; bukan klaim seluruh variasi zoom browser/perangkat fisik. Masih ada warning dependency/deprecation dan AsyncMock pada test Celery lama; hasil ini tidak menyatakan worker Celery lama siap produksi. Lint, TypeScript, build frontend produksi dan Ruff berkas yang berubah lulus. Log/screenshot lokal berada di `/workspace/.cloud-setup/ai-stock-analyzer/` dan tidak diasumsikan ikut tersedia pada workspace/deployment lain.

Database development kosong sebelum migrasi; backup SQLite dibuat pada `development-before-r3-20261019-221301-WIB.db` di direktori log tersebut (izin 0600). Seluruh jumlah baris tetap nol sesudah upgrade. Bukti PostgreSQL berisi data berasal dari database benchmark disposable, bukan database produksi. Build akhir menggunakan proxy normal port 8000; API, worker produk dan frontend development normal dijalankan kembali. Proses fixture/benchmark dibersihkan sesudah pengujian.

- `tests/browser_post_audit.py` mempertahankan reproduksi empat bug: input berubah/response terlambat, 60 geometri header, padding aktual, long press 900ms tanpa hover, pembacaan Close terhadap API candle, keyboard dan badge stale. Screenshot tidak berisi kredensial.
- `tests/browser_smoke.py` tetap mencakup 19 alur aplikasi sebelumnya; langkah formulir menyesuaikan bagian rencana yang dapat dibuka.
- Unit/API baru memeriksa payload calculate minimal, simpan wajib lengkap, batas CSV 5.000/PDF 200 dan penolakan di atasnya, formula CSV, quota serta ingestion opt-in/retry/lock/readiness.
- Workflow GitHub menjalankan kedua script browser bersama backend/worker fixture terpisah. Hasil lokal tidak disebut sebagai hasil workflow remote.
- OpenAPI diekspor dari runtime baru. Lint, tipe dan build diperiksa; pemeriksaan provider nyata tidak digantikan fixture.

### Benchmark lokal yang dapat diulang

`scripts/benchmark_product.py` membuat **100 ticker, histori lima tahun dan 20 akun** pada database kosong disposable yang namanya mengandung `benchmark`, dengan `BENCHMARK_SETUP=1`. Jalankan API terpisah memakai database tersebut dan `TESTING=1`; tidak menjalankan worker atau memanggil provider.

```bash
# Setelah database disposable dibuat dan alembic upgrade head:
BENCHMARK_SETUP=1 DATABASE_URL=postgresql+asyncpg://USER@HOST/APP_benchmark \
SYNC_DATABASE_URL=postgresql://USER@HOST/APP_benchmark \
.venv/bin/python -m scripts.benchmark_product --base http://127.0.0.1:8002
```

Script menolak database berisi akun/stocks dan target non-localhost. Ukuran workload dicatat pada JSON hasil: putaran pertama terpisah, lalu tiga putaran 20 request serentak per endpoint daftar/harga/chart lima tahun/screener/job admission. Login di luar waktu pengukuran, rate limit dinonaktifkan hanya pada API uji terpisah, dan semua job tetap queued. Hasil tidak mengukur durasi AI, biaya provider, throughput produksi, retensi, atau keberhasilan job worker.

Hasil [JSON benchmark sebelum/sesudah](benchmark_pasca_audit_20261019.json) tersedia di repository. Dataset masing-masing 100 ticker × 1.305 bar (18 Oktober 2021–16 Oktober 2026), 20 pengguna, PostgreSQL 16 lokal. Run awal satu worker; run akhir empat worker Uvicorn dengan indeks/query/serialisasi baru. Karena konfigurasi worker dan kode berubah bersama, selisih ini bukan eksperimen terisolasi tentang dampak indeks saja. Resource cloud dipakai bersama; hasil harus diterima ulang pada staging dengan resource produksi yang ditetapkan.

| Endpoint | p95 awal, 1 worker | p95 akhir, 4 worker | Error akhir |
|---|---:|---:|---:|
| Daftar | 0,9431 dtk | 0,1845 dtk | 0 |
| Harga | 0,1011 dtk | 0,2385 dtk | 0 |
| Chart lima tahun | 3,1558 dtk | 0,6927 dtk | 0 |
| Screener | 6,2256 dtk | 0,4534 dtk | 0 |
| Penerimaan/replay job | 3,3920 dtk | 0,2922 dtk | 0 |

Seluruh p95 warm run akhir berada di bawah target lokal satu detik (60 sampel per endpoint). Maksimum putaran pertama tercatat terpisah pada JSON; putaran pertama tidak menjamin cache storage benar-benar dingin. Penerimaan pertama job maksimum 0,489 detik, sedangkan putaran warm memakai idempotent replay. Tidak menjalankan worker AI pada workload ini. Untuk mengulang konfigurasi akhir, jalankan API disposable dengan `--workers 4` dan script dengan `--server-workers 4` sebagai label konfigurasi yang dicatat, bukan pengaturan server otomatis.

## Gerbang yang tetap terbuka

| Paket | Kesiapan yang benar-benar diamati | Yang masih diperlukan |
|---|---|---|
| PA-07 / G1 | Anthropic/Gemini/EODHD key tidak tersedia; runtime tidak memiliki domain provider tambahan. Adapter lama tetap tersedia. | Secret/network aktif, provider IDX+AS nyata, budget dan lisensi display, rekonsiliasi OHLCV/adjustment, dua hasil AI nyata. |
| PA-08 / G3 | CLI/status dan kebijakan ingestion disiapkan, default nonaktif; kalender runtime belum terverifikasi. | Jadwal/scheduler yang diterima, ingestion sesi baru nyata, corporate action/kalender, trigger alert nyata tanpa duplikasi. |
| PA-09 / akun | SMTP host/from belum dikonfigurasi. Alur reset/token/revoke yang ada diuji terkontrol. Tidak ada email nyata dikirim. | Pengirim/TLS/egress/inbox milik tim dan alur reset valid lewat email nyata. |
| PA-10 / publik | Regresi lokal, browser produksi dan alat benchmark disiapkan. | CI remote pada commit kandidat, staging sebenarnya, lima peserta/perangkat fisik/screen reader dan pengamatan tujuh hari, penerimaan backup/restore serta operator deployment. |

Konfigurasi cloud lama tetap berstatus draft stale; penyimpanan sebelumnya ditolak karena base version berubah. [File usulan](cloud-environment-r2-proposal.json) dapat direkonsiliasi dari sesi setup baru memakai pengaturan environment terkini. Paket ini tidak menyatakan konfigurasi tersebut tersimpan/diterapkan.

Tidak membeli layanan, mengganti provider default, mengaktifkan jadwal pengambilan pasar nyata, memodifikasi database produksi atau melakukan deployment. Gerbang eksternal/manual tersebut tetap tercatat pending; hasil pengujian tidak diubah menjadi bukti layanan nyata.
