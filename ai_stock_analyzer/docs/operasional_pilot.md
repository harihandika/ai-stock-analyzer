# Runbook pilot dan penerimaan operasional

Tanggal: 20 Oktober 2026, Asia/Jakarta (WIB). Acuan: [PRD 1.3](prd_kesiapan_pilot_8d9645d.md). Perintah dijalankan dari backend `ai_stock_analyzer`, kecuali yang menyebut direktori frontend. Konfigurasi berisi secret disediakan operator melalui environment; jangan menaruh nilainya pada command, log, Git atau laporan.

## Proses dan migrasi

Gunakan satu kandidat aplikasi yang sama untuk frontend/API/worker. Backup dahulu; uji upgrade `r3_read_paths` → `r4_operations` pada salinan berisi data. Migrasi baru hanya menambah tabel `worker_heartbeats` dan `ingestion_runs` beserta indeks, tanpa mengubah data finansial/akun.

```bash
.venv/bin/python -m scripts.sqlite_snapshot backup --target /PRIVATE_STORAGE/before-r4.db
.venv/bin/alembic upgrade head
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# Proses terpisah, environment/database sama:
.venv/bin/python -m app.worker.product_worker
# Dari ai_stock_analyzer_frontend, sesudah npm ci dan npm run build:
npm run start -- --hostname 127.0.0.1 --port 3000
```

Perintah backup di atas khusus SQLite. Penggunaan PostgreSQL mengikuti bagian backup di bawah. Semua proses deployment harus dimiliki supervisor yang ditetapkan operator; contoh unit worker Linux berikut adalah template, belum diinstal pada staging/produksi:

```ini
[Unit]
Description=AI Stock Analyzer product worker
After=network-online.target

[Service]
Type=simple
User=stock-analyzer
WorkingDirectory=/srv/ai-stock-analyzer/ai_stock_analyzer
EnvironmentFile=/etc/stock-analyzer/runtime.env
ExecStart=/srv/ai-stock-analyzer/ai_stock_analyzer/.venv/bin/python -m app.worker.product_worker
Restart=always
RestartSec=5
KillSignal=SIGTERM
TimeoutStopSec=150
UMask=0077

[Install]
WantedBy=multi-user.target
```

API memakai `ExecStart` Uvicorn di atas dan frontend memakai Node/Next dari direktori frontend; gunakan unit terpisah dengan Restart dan private environment file yang sama prinsipnya. Sesuaikan user/path, reverse proxy HTTPS, resource dan dependensi database dengan deployment nyata sebelum pemasangan. Template ini tidak menggantikan verifikasi supervisor/reboot pada staging. Worker Celery lama bukan pengganti product worker.

## Status yang benar-benar diukur

```bash
.venv/bin/python -m app.worker.market_ops status
```

Output read-only memuat konfigurasi berbentuk boolean, jumlah/umur antrean, job overdue, sesi sumber per saham, heartbeat/progres dan 20 run ingestion terbaru. Command tidak melakukan probe berbayar atau mengirim email. Panggil dari konteks operator, jangan mempublikasikan seluruh daftar job atau run ke akun pengguna lain.

- Worker menulis heartbeat melalui task/session terpisah setiap 15 detik, termasuk selama menunggu provider. Setelah 60 detik tanpa heartbeat, worker tidak dianggap tersedia. Progres main loop dicatat terpisah; heartbeat hidup tidak membuktikan job maju, provider terhubung atau alert pasti terkirim.
- Error siklus worker membuat status degraded dan hanya mencatat kode; supervisor tetap diperlukan untuk restart proses yang keluar. Pemeriksaan provider/job deadline harus terpisah dari liveness. Heartbeat lama dibersihkan setelah tujuh hari saat worker baru dimulai.
- UI alert membedakan dijeda, notifikasi akun nonaktif, menunggu data/analisis/sesi sebelumnya/worker/baseline, serta siap dievaluasi. Baseline awal tidak menyalakan notifikasi historis.
- Run ingestion dicatat sebelum pengambilan, lalu menyimpan hasil tersanitasi, waktu, expected/actual session dan attempt per ticker. Run blocked/failed juga disimpan. Proses mati dapat meninggalkan running; CLI menandainya overdue setelah `120 × jumlah ticker + 30` detik. Jangan mengubahnya menjadi success tanpa bukti.
- Riwayat ingestion berumur lebih dari 30 hari dibersihkan pada run berikutnya. Tetapkan arsip privat terpisah bila kebutuhan operator lebih lama. Status heartbeat pada API hanya agregat, tanpa identitas host, isi job atau secret.

Rehearsal operator: hentikan worker milik deployment → pastikan unavailable dalam 60 detik → restart → periksa heartbeat dan progres baru → pastikan job melewati deadline dilepas sesuai kontrak. Jangan menganggap satu pemeriksaan status membuktikan seluruh rehearsal selesai.

## Ingestion dan penerimaan provider

Ingestion tetap opt-in; CLI tidak memasang cron atau mengaktifkan sendiri. Tetapkan satu scheduler, universe maksimal 20 ticker, budget/hak display, kalender dan delay publikasi sebelum aktivasi.

```bash
.venv/bin/python -m app.worker.market_ops ingest --tickers BBCA.JK,AAPL
```

Tanpa konfigurasi yang diterima, hasil blocked/nonzero adalah perilaku yang benar. `--refresh` memaksa fetch ulang dan dapat menambah biaya. Lock hanya menghindari run bertumpuk pada satu host; jangan menjalankan scheduler di beberapa host sebelum koordinasinya dirancang.

Operator harus menerima jadwal publikasi IDX/AS, hari libur, sesi pendek dan DST, lalu memeriksa apakah delay global saat ini cukup untuk kedua bursa. Bila berbeda, tambahkan kebijakan per bursa sebelum mengaktifkan jadwal tersebut. Harga lama yang baru diambil tetap stale/unknown. Rule signal memerlukan analisis yang sesuai revisi data; heartbeat tidak menghapus syarat itu.

Paket penerimaan nyata mencatat BBCA.JK/AAPL, sumber, OHLCV/adjustment, rentang histori, currency/bursa, model aktual/token/biaya, hasil tersimpan dan request tersanitasi. Kalender/alert/SMTP/perangkat fisik tetap gerbang tersendiri. Status configured maupun fixture tidak menutupnya.

## Backup, restore dan rollback

Snapshot mengandung data akun. Simpan privat, izin minimum 0600, retensi sesuai keputusan operator. Jangan mengunggah snapshot atau log berisi token ke repository. Target pilot yang perlu dibuktikan: backup setidaknya harian, RPO ≤24 jam dan RTO ≤60 menit; ini bukan hasil pengukuran produksi sekarang.

SQLite memakai online backup yang mencakup WAL, verifikasi quick_check dan revision:

```bash
.venv/bin/python -m scripts.sqlite_snapshot backup --target /PRIVATE_STORAGE/pilot-backup.db
.venv/bin/python -m scripts.sqlite_snapshot restore --source /PRIVATE_STORAGE/pilot-backup.db --target /PRIVATE_STORAGE/rehearsal-new.db
```

Tool menolak target yang sudah ada atau database aktif yang dikonfigurasi. Restore selalu ke file baru. Setelah verifikasi login/ownership/watchlist/versi rencana pada environment rehearsal, operator dapat merencanakan cutover terpisah. Tool tidak menimpa aplikasi aktif.

Untuk PostgreSQL, pakai tool PostgreSQL dengan versi yang cocok. Gunakan profil/environment/pgpass privat yang telah dikonfigurasi, bukan DSN dengan password pada argumen:

```bash
umask 077
pg_dump --format=custom --file=/PRIVATE_STORAGE/pilot-backup.dump
# PGDATABASE untuk proses restore harus menunjuk database rehearsal BARU.
# Verifikasi target sebelum menjalankan; --clean tidak digunakan.
pg_restore --exit-on-error --no-owner --dbname=NEW_REHEARSAL_DATABASE /PRIVATE_STORAGE/pilot-backup.dump
```

Ukur waktu, verifikasi revision/jumlah dan isi contoh privat yang dipilih operator, lalu ulangi login/ownership/catatan/rencana. Restore database disposable lokal membuktikan mekanisme pada sampel tersebut; belum membuktikan pemulihan staging sesungguhnya. Rollback aplikasi dilakukan pada kandidat kompatibel setelah menghentikan proses baru. Downgrade r4 menghapus riwayat operasi/heartbeat; ekspor arsip privat jika diperlukan sebelum downgrade. Jangan downgrade database produksi hanya untuk menguji runbook.

## Bukti kandidat dan pilot

Catat SHA, URL CI remote, resource/API worker/database, dataset, putaran awal/warm dan error terpisah. Script benchmark yang sudah ada memakai 100 ticker/lima tahun/20 akun pada database disposable; jangan menjalankannya pada database pengguna. Panggilan provider dan durasi penyelesaian AI tidak dicampur dengan admission/replay job.

Perangkat fisik, Firefox/WebKit, screen reader, lima peserta dan observasi tujuh hari memerlukan lingkungan/responden yang sesuai. Jangan menyamakan emulasi, tes unit atau skor auditor dengan bukti tersebut. Pemilik produk/operator menetapkan lanjut/perbaiki berdasarkan gerbang PRD, dengan hasil blocked/not-tested tetap terlihat.
