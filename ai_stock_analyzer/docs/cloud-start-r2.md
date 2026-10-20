# Startup cloud sesudah implementasi PRD

Gunakan checkout `/workspace/ai-stock-analyzer`. Periksa `git status` dan pertahankan perubahan pengguna. Cloud task sudah terisolasi; jangan membuat worktree kecuali diminta. Baca PRD 1.4, `docs/operasional_pilot.md`, serta laporan implementasi sebelum mengubah setup.

Python 3.12, backend `.venv`, Node 24, dan dependency npm sudah terpasang. Install script sebelumnya memasang requirements dan menjalankan Alembic. Database development telah di-backup sebelum migrasi `r2_product`; backup berada di `/workspace/.cloud-setup/ai-stock-analyzer`. Jangan stamp database tanpa versi secara otomatis: periksa schema dan ikuti laporan migrasi. Jangan menjalankan fixture pytest pada database development/produksi karena fixture membuat ulang tabel. Hentikan proses frontend milik task sebelum `npm ci`, kemudian jalankan kembali.

Jalankan tiga proses terpisah setelah environment direstore:

1. API, cwd `/workspace/ai-stock-analyzer/ai_stock_analyzer`:

   ```bash
   .venv/bin/alembic upgrade head
   .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

2. Worker produk, cwd backend dan environment/database yang sama:

   ```bash
   .venv/bin/python -m app.worker.product_worker
   ```

3. Frontend, cwd `/workspace/ai-stock-analyzer/ai_stock_analyzer_frontend`:

   ```bash
   NEXT_TELEMETRY_DISABLED=1 npm run dev -- --hostname 127.0.0.1 --port 3000
   ```

Job produk memakai database sebagai antrean durable dan tidak memerlukan Redis. Jangan menjalankan worker batch Celery lama terhadap `celery_broker.sqlite` tracked. Redis opsional untuk cache/rate limit lokal. Frontend memakai same-origin `/api/v1` ke `API_PROXY_TARGET`, default `http://127.0.0.1:8000`; tetapkan sebelum build/dev jika backend berbeda. `NEXT_PUBLIC_API_URL` hanya untuk konfigurasi cross-origin yang disengaja. Jangan membuat tautan preview localhost.

Periksa API `/health`, `/openapi.json`, frontend `/login`, `/register`. Uji registrasi/login JSON, `/auth/me`, daftar job privat dan logout dengan refresh token memakai akun disposable; jangan mencetak password, token atau key. Token sesi lama mungkin membutuhkan login kembali. Worker `--once` dapat dipakai untuk readiness saat tidak ada worker kontinu yang berjalan.

Pilihan provider di server: `AI_PROVIDER=anthropic|gemini` dan `MARKET_DATA_PROVIDER=yahoo|eodhd`. Default kompatibel tetap Anthropic/Yahoo. Jangan berganti diam-diam atau memakai fallback data contoh. Secret opsional melalui pengaturan environment: `ANTHROPIC_API_KEY` untuk `api.anthropic.com`, `GEMINI_API_KEY` untuk `generativelanguage.googleapis.com`, dan `EODHD_API_KEY` untuk `eodhd.com`. Pilih provider yang memiliki kredensial, periksa grant runtime sebelum menguji, dan jangan meminta nilainya di chat. Draft konfigurasi tidak menyediakan kredensial ataupun menerapkan izin jaringan. Integrasi nyata dan lisensi display belum diterima.

Freshness tetap unknown sampai `MARKET_CALENDAR_VERIFIED` dan `EOD_PUBLICATION_DELAY_MINUTES` diatur berdasarkan perilaku bursa/provider yang diverifikasi. Alert hanya mengevaluasi data baru tersimpan yang fresh; ingestion EOD terjadwal dan budget memerlukan kebijakan operator. Reset password memerlukan konfigurasi SMTP host/from dan jalur SMTP; allowlist HTTPS tidak menyediakan koneksi TCP SMTP. Jangan menyatakan email terkirim bila pengirim belum tersedia.

Validasi:

- Backend: `.venv/bin/python -m pytest tests/ -q`. `TEST_DATABASE_URL` harus disposable.
- Frontend: `npm run lint` dan `npm run build`.
- OpenAPI: `.venv/bin/python -m scripts.export_openapi`, lalu review `docs/openapi.yaml`.
- Browser: pasang `requirements-browser.txt` ke venv bila perlu. Chromium sistem di mesin ini `/usr/bin/chromium`; periksa lagi setelah restore. Jalankan backend `tests.browser_app:app`, worker `tests.browser_worker` terpisah, dan Next produksi dengan proxy ke backend fixture. Kedua proses fixture memerlukan `BROWSER_SMOKE=1`, `TESTING=1`, dan database khusus dengan DSN mengandung `browser-r1`. Jalankan `tests/browser_smoke.py` dengan `BROWSER_BASE_URL`/`BROWSER_OUTPUT_DIR`. Fixture membuktikan perilaku aplikasi, bukan akses provider nyata. Hentikan proses fixture setelah selesai dan pertahankan API/worker/frontend normal.

Laporan implementasi mencatat bukti validasi dan gerbang rilis: akses provider nyata, email nyata, pilot lima pengguna, load/retensi staging dan lisensi. Simpan log/state di path ignored atau `/workspace/.cloud-setup`. Jangan commit `.env`/database. Penyimpanan konfigurasi bukan publish atau bukti pemulihan task baru.

Pembaruan PRD 1.3: CLI read-only `.venv/bin/python -m app.worker.market_ops status` melaporkan konfigurasi boolean, antrean/umur sesi, heartbeat dan progres worker terpisah, serta riwayat ingestion. Heartbeat setiap 15 detik kedaluwarsa pada 60 detik; itu tidak membuktikan koneksi provider atau data terbaru. Ingestion opt-in tersedia lewat `app.worker.market_ops ingest`, default nonaktif dan universe wajib eksplisit maksimal 20 ticker. Jangan mengaktifkan scheduler/kalender sebelum budget, provider, jaringan dan jadwal diterima. Jalankan `tests/browser_post_audit.py` dan `python -m tests.browser_audit_followup` terhadap fixture browser untuk regresi audit lama dan BUG-005–007, payload alert, navigasi serta UX terkait. Suite follow-up juga memerlukan environment database browser-r1 yang sama karena menyiapkan data uji terkontrol; tidak boleh memakai database development/produksi.

Head migrasi terbaru `r4_operations` menambah tabel heartbeat/ingestion di atas `r3_read_paths`. Backup database berisi data sebelum upgrade; jalankan API/worker setelah migrasi. Rehearsal PostgreSQL lokal berisi akun/watchlist/rencana diverifikasi terpisah dari staging; lihat JSON dan runbook pada docs. Jangan memakai angka benchmark lokal empat worker sebagai bukti kapasitas staging yang belum diuji. Proposal konfigurasi cloud tersimpan di repository tetap belum diterapkan karena draft sebelumnya stale; jangan berulang kali menyimpan draft lama sebagai solusi.

Pembaruan PRD 1.4: jalankan juga `.venv/bin/python -m tests.browser_stabilization_v3` pada fixture yang sama untuk respons run lama, draft catatan, timestamp lintas zona dan UX V3. Timestamp run dinormalisasi UTC pada serialisasi; tidak ada migrasi data baru. Lihat `docs/implementasi_prd_1_4_20261020.md`.
