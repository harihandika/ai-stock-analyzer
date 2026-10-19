# Implementasi Perbaikan R1

Tanggal laporan: 18 Oktober 2026, Asia/Jakarta. Perubahan tersedia pada checkout untuk ditinjau; belum dipublikasikan atau dideploy ke produksi.

Acuan: [PRD perbaikan](prd_perbaikan_aplikasi.md). Rilis inti telah diimplementasikan dan diuji secara lokal. Gerbang integrasi provider nyata masih terbuka, sehingga laporan ini tidak menyatakan aplikasi siap rilis publik.

Kajian lanjutan 19 Oktober 2026: [alternatif integrasi AI dan data pasar](alternatif_integrasi.md), termasuk Gemini, Groq, Ollama, Sectors v2, EODHD, dan Twelve Data. Pemilihan dan migrasi provider belum dilakukan.

## Perubahan yang tersedia

| Area | Perilaku setelah perubahan |
|---|---|
| Harga dan grafik | Tidak ada fallback angka/grafik buatan pada mode normal. Harga terakhir tersimpan, tanggal pasar, sumber, mata uang, revisi, dan waktu fetch ditampilkan. Kegagalan bagian AI tidak mengganti chart yang berhasil. |
| Keterkinian | Tanpa kalender bursa yang tervalidasi, status tetap unknown dan dijelaskan di UI. Data harian sesi yang sedang berjalan tidak dipublikasikan sebagai penutupan lengkap. Harga disesuaikan split/dividen dilabeli. |
| Sinkronisasi | Endpoint mutasi wajib login, memiliki rate limit per pengguna, memvalidasi OHLCV, dan mempertahankan data sebelumnya ketika provider atau penyimpanan gagal. |
| AI | Tombol menjalankan sync → AI → baca ulang hasil tersimpan. Kunci kosong, timeout, JSON/kontrak invalid menghasilkan error, bukan HOLD otomatis. Ringkasan aktual, faktor pendukung/penyangkal, keterbatasan, model, prompt, dan revisi input disimpan. |
| Rekomendasi | BUY/HOLD/WAIT digunakan konsisten; confidence dinormalisasi sekali. Dashboard mencari BUY valid pada seluruh instrumen aktif, bukan hanya enam kartu market pertama. Target dan risiko buatan dihapus. |
| Cache hasil | Database menjadi sumber hasil tersimpan berdasarkan ticker, revisi data, model, dan versi prompt. Cache GET chart/latest yang tidak diinvalidasi dihapus. Pembaruan dapat langsung dibaca. |
| Kuota/idempotensi | Reservasi atomik disimpan di database. Hasil baru berhasil memakai satu kuota; cache hit dan kegagalan tidak memakai kuota. Klik ganda ditolak/digunakan ulang, reservasi kedaluwarsa dipulihkan. Reset memakai Asia/Jakarta. |
| Sesi | Satu client/base URL, login JSON, refresh bersama untuk request 401, identitas refresh token unik, konsumsi token atomik, dan logout terhubung ke semua pintu keluar. Access token terikat pada sesi yang dapat dicabut. |
| Backtest | Input persen dan legacy desimal divalidasi eksplisit. Respons bertipe mengembalikan parameter efektif, semua transaksi, equity curve, satuan persen, dan asumsi. Tampilan tidak mengalikan persen lagi. |
| Metodologi | Pivot baru dipakai setelah konfirmasi. Keputusan close dieksekusi pada open berikutnya, termasuk gap. Drawdown berasal dari equity peak-to-trough; posisi akhir ditutup dan dicatat. |
| Penggunaan | Chart harian 1M/3M/6M/1Y, pencarian nama dengan Enter menuju ticker, total dashboard dari metadata, dialog tambah watchlist, catatan privat yang dapat diedit, sort/refresh, dan panel notifikasi tanpa klaim sinkronisasi palsu. |
| Build/kontrak | Tipe lineWidth diperbaiki. Schema respons AI, quote, metadata, serta backtest tersedia pada OpenAPI runtime; YAML dihasilkan ulang dari aplikasi. |

Sebagian pekerjaan B07/B08/B09b sudah ikut tersedia karena diperlukan untuk menyambungkan alur dengan benar. Ini tidak berarti seluruh R2 selesai.

## Kebijakan backtest yang berlaku

- Strategi teknikal harian, bukan rekam jejak keputusan AI.
- Ekuitas awal ternormalisasi 100, alokasi 100%, compounding, satu posisi, tanpa ukuran lot/likuiditas.
- Target/stop diperiksa pada close; order keluar pada open berikutnya. Exit dapat berbeda dari threshold karena gap.
- Timeout setelah 30 sesi evaluasi, keluar pada open berikutnya. Akhir periode ditutup pada close terakhir.
- Biaya dan slippage diasumsikan nol dan ditampilkan; return belum disebut return bersih.
- Data provider memakai penyesuaian split/dividen. Seluruh transaksi tersedia, bukan hanya sepuluh sampel.

## Verifikasi dan batas bukti

Hasil verifikasi lokal:

| Pemeriksaan | Hasil |
|---|---|
| Seluruh suite backend SQLite | 79 lulus, tidak ada gagal/skip |
| Seluruh suite backend PostgreSQL 16 | 79 lulus, tidak ada gagal/skip |
| Build dan lint frontend | Lulus |
| Ruff pada seluruh file Python yang diubah/ditambahkan | Lulus |
| Migrasi SQLite baru dan legacy | Lulus; fixture akun/watchlist tetap ada |
| Migrasi PostgreSQL baru dan legacy berisi data | Lulus; akun, kuota, dan catatan tetap ada |
| Smoke browser Chromium desktop/360px | 11 pemeriksaan lulus |

Suite masih mengeluarkan peringatan deprecation dependensi dan coroutine pada test adapter worker lama. Kelulusan test adapter tersebut tidak membuktikan worker/job persisten sudah berfungsi.

Workflow [CI](../../.github/workflows/ci.yml) ditambahkan untuk regresi SQLite/PostgreSQL, kesesuaian OpenAPI, build/lint frontend, dan smoke browser. Workflow belum dieksekusi di GitHub pada sesi ini.

Browser menggunakan Chromium sistem dan server fixture terisolasi. Provider pasar/AI pada pengujian tersebut dikontrol; hasilnya membuktikan integrasi UI/API/database dan penanganan kegagalan, bukan konektivitas Yahoo/Anthropic nyata.

Skenario browser: registrasi, login, pencarian nama+Enter, sync/AI/hasil tersimpan, chart, backtest parameter efektif dan hasil, tambah watchlist, penyimpanan catatan, refresh 401 bersamaan, logout/revokasi, kegagalan sebagian API, timeout AI, ticker kosong, navigasi 360px, serta sesi expired tanpa refresh token.

Pemeriksaan nyata terakhir:

- Histori Yahoo Finance BBCA.JK menghasilkan nol bar; redirect ke guce.yahoo.com ditolak proxy dengan 403.
- ANTHROPIC_API_KEY belum tersedia; analisis nyata tidak dieksekusi. Aplikasi sekarang mengembalikan error konfigurasi yang jelas.
- Perlu pengujian provider nyata setelah akses/kunci tersedia; jangan mengganti dengan fixture dan menandainya lulus.

## Menjalankan dan memigrasikan

Gunakan checkout yang ada; cloud task sudah terisolasi dan tidak memerlukan worktree tambahan.

Backend, dari ai_stock_analyzer:

~~~bash
uv venv --python 3.12 --allow-existing .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
~~~

Gunakan .env lokal/injeksi environment yang sudah tersedia. Masukkan kunci provider melalui pengaturan rahasia; jangan menaruh nilai pada Git, log, atau chat. Kunci AI kosong berarti layanan AI belum dikonfigurasi, bukan mode demo.

Sebelum upgrade database yang sudah berisi data, buat dan verifikasi backup. Database tanpa alembic_version yang sebelumnya dibuat dengan create_tables.py harus diperiksa terhadap schema legacy sebelum diadopsi; jangan menjalankan stamp secara membabi buta. Pada instance ini, schema dibandingkan dengan migrasi legacy, backup lokal dibuat, lalu database pengembangan dimigrasikan ke r1_integrity. Akun/watchlist yang ada dipertahankan.

Perubahan migrasi legacy hanya menggunakan batch alter yang setara untuk mendukung SQLite dan mempertahankan tipe UUID saat refleksi. PostgreSQL baru dan upgrade schema lama berisi data juga diperiksa.

Access token lama tanpa sid akan diminta refresh atau login kembali. Jangan menggabungkan versi backend/frontend yang mempunyai kontrak berbeda. Untuk rollback produksi, gunakan versi aplikasi yang kompatibel dan backup yang diuji; downgrade schema menghapus metadata baru dan bukan pengganti backup.

Frontend, dari ai_stock_analyzer_frontend:

~~~bash
npm ci
npm run dev
~~~

Secara default browser mengakses /api/v1 pada origin yang sama; Next meneruskan ke backend melalui API_PROXY_TARGET, default http://127.0.0.1:8000. Atur API_PROXY_TARGET sebelum build/dev untuk deployment yang berbeda. NEXT_PUBLIC_API_URL tersedia untuk API lintas origin yang memang dikonfigurasi bersama CORS.

## Mengulang pemeriksaan

Dari direktori backend:

~~~bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m scripts.export_openapi
~~~

Pengujian menggunakan database khusus dan menghapus/membuat ulang tabel fixture. TEST_DATABASE_URL hanya boleh menunjuk database test yang dapat dibuang; jangan arahkan ke database pengguna/produksi.

Untuk PostgreSQL test terisolasi, set TEST_DATABASE_URL ke DSN asyncpg database test, lalu jalankan perintah pytest yang sama. Tidak ada kebutuhan token provider untuk suite terkontrol.

Dari direktori frontend:

~~~bash
npm run lint
npm run build
~~~

Smoke browser opsional:

1. Install requirements-browser.txt ke .venv; sediakan Chromium yang kompatibel dan arahkan BROWSER_EXECUTABLE bila lokasinya berbeda.
2. Siapkan database khusus dengan nama/path mengandung browser-r1, set DATABASE_URL/SYNC_DATABASE_URL ke sana, lalu alembic upgrade head.
3. Jalankan server tests.browser_app:app dengan BROWSER_SMOKE=1 dan TESTING=1. Server menolak memakai database yang tidak ditandai khusus tersebut.
4. Jalankan frontend produksi pada port 3001 dengan proxy ke server fixture, lalu .venv/bin/python tests/browser_smoke.py dari backend. BROWSER_BASE_URL dan BROWSER_OUTPUT_DIR dapat diatur.
5. Hentikan server fixture setelah selesai. Jangan meninggalkannya sebagai layanan pengembangan; gunakan app.main:app dengan database sebenarnya.

## Sisa pekerjaan PRD

- B10/R2: antrean job persisten, status lintas reload, retry worker, dan pemulihan restart. AnalysisRequest saat ini hanya reservasi/idempotensi, bukan job queue.
- B07/B11/R2: daftar saham berhalaman yang lengkap, penyempurnaan bahasa/glosarium, audit aksesibilitas lebih luas, dan pilot lima pengguna.
- B13–B15/R3: alert berbasis kejadian, pemulihan akun/email/preferensi, biaya/slippage/lot serta riwayat/ekspor simulasi.
- Operasional: smoke provider nyata, kalender bursa terverifikasi, pengukuran performa/beban, biaya AI, dan pilot tujuh hari sebelum perluasan rilis.

Tidak ada deployment, publikasi environment, merge, atau pengiriman pesan eksternal sebagai bagian dari implementasi lokal ini.
