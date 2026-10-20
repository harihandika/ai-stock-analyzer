# Implementasi PRD 1.3 — audit 8d9645d

Tanggal: 20 Oktober 2026, Asia/Jakarta (WIB). Baseline aplikasi `8d9645d`; bukti audit dipublikasikan pada `9c36fcf`. Acuan: [PRD 1.3](prd_kesiapan_pilot_8d9645d.md), [ringkasan audit](review_audit_8d9645d_2026-10-20.md) dan [runbook](operasional_pilot.md).

## Perbaikan produk

| Paket | Perubahan | Batas penerimaan |
|---|---|---|
| AF-01 / BUG-005 | Riwayat diekstrak ke `AnalysisHistory`. Compare memakai versi konteks, ticker dan urutan ID; request lama dibatalkan/diabaikan pada ganti ticker/pilihan/tab/unmount. Respons dengan identitas berbeda ditolak. Panel menampilkan ticker, ID, tanggal data, waktu hasil, provider/model dan revisi kedua sisi. | Pembuktian melalui API/Chromium dengan respons ditahan, error terlambat, urutan terbalik, null dan identitas salah; tidak mengubah rumus selisih skor. |
| AF-02 / BUG-006 | Payload sinyal hanya membawa field yang sesuai; `direction: null` tidak dikirim. Harga/perubahan tetap memakai arah/ambang. Validasi field diterjemahkan dan draft bertahan saat gagal. Label kontrol riset memiliki ID serta nama aksesibel yang eksplisit. | Kontrak backend lama tetap diterima; default arah tidak dilonggarkan menjadi null. Membuat rule belum membuktikan trigger dari provider nyata. |
| AF-03 / BUG-007 | Filter terapan, sort, arah dan halaman berada di parameter URL `sc_`. Back/Forward/refresh/preset mempertahankan kriteria; state hasil ditandai konteks request/akun. Posisi dan fokus kandidat disimpan per entri history. Page tidak tersedia disesuaikan dengan penjelasan. | Query diterapkan ulang pada data tersimpan, sehingga harga/hasil dapat berubah. Parameter tidak dikenal tidak diteruskan ke API; false tidak dianggap true. |
| UX-01 | Perubahan unread dipublikasikan dengan ID akun; header menolak respons polling yang lebih lama. Pembacaan notifikasi independen dari kegagalan daftar alert/job; hasil load lama tidak menimpa state baru. | Diuji pada mark-read dengan kegagalan pembacaan job terkontrol; polling tetap digunakan untuk perubahan eksternal. |
| UX-02 | Label backtest dan error alert memakai bahasa Indonesia; bantuan menjelaskan tingkat kemenangan, rata-rata hasil, drawdown, bps/fee/slippage. Angka, kode API dan ekspor tetap mengikuti kontrak backend. | Tidak mengubah strategi, hasil finansial atau menafsirkan confidence sebagai peluang profit. |
| UX-03 | Dashboard menyediakan langkah pertama cari saham → periksa data → watchlist, dapat ditutup/dibuka ulang, preferensi per akun. Tombol pencarian memfokuskan kontrol yang sebenarnya. | Interaksi terkontrol diuji; manfaat bagi lima peserta manusia belum diukur. |
| UX-04 | Bantuan indikator menampilkan sesi/sumber, fase/pola yang tersedia dan tautan memilih candle sesi indikator. Null tidak menjadi pola contoh; pemilihan ulang dapat kembali ke sesi yang sama. | Tanggal ditelusuri terhadap API fixture. Kualitas Wyckoff/SMC pada pasar nyata belum diterima. |
| KP-05, bagian UI | Fragment token pada tautan reset langsung membuka form password baru; sukses membersihkan fragment. | Token valid dari fixture membuktikan reset/revocation; pengiriman SMTP nyata tetap belum diuji. |

## Kesiapan operasional yang disiapkan

Migrasi **`r4_operations`** menambahkan tabel heartbeat dan run ingestion di atas `r3_read_paths`. Tidak menambah kolom pada akun/harga/rencana atau menulis ulang data finansial.

- Worker menulis heartbeat setiap 15 detik melalui task/session terpisah dari panggilan AI. Setelah 60 detik tanpa heartbeat, status unavailable. Progres siklus dan error dicatat terpisah dengan kode tersanitasi. Worker graceful stop dicatat; proses yang mati paksa diketahui melalui umur heartbeat. Riwayat lebih dari tujuh hari dibersihkan saat startup worker.
- `market_ops status` membaca heartbeat/progres, antrean tertua, job overdue, sesi data dan 20 run ingestion terbaru. Credential configured tidak dianggap provider connected. UI alert membedakan pause, notifikasi akun nonaktif, menunggu data/analisis/sesi sebelumnya/worker/baseline dan siap dievaluasi.
- Ingestion default tetap nonaktif. Wrapper CLI menyimpan run running lalu hasil completed/incomplete/blocked/failed, expected/actual session, waktu dan attempt. Kegagalan tidak menyimpan URL provider/exception private. Retensi run 30 hari, lock tetap satu host; scheduler tidak dipasang atau diaktifkan.
- Snapshot SQLite online mencakup WAL, memverifikasi quick_check/revision dan hanya menulis target baru berizin 0600. Restore menolak overwrite database yang ada. PostgreSQL memakai pg_dump/pg_restore pada database rehearsal baru.
- Panduan startup, tabel stack README, OpenAPI dan workflow browser diperbarui. [Lembar penerimaan pilot](pilot_acceptance_template.md) tersedia tanpa data peserta palsu. Proposal startup cloud di repository diperbarui sebagai bahan rekonsiliasi; draft cloud lama yang stale tidak disimpan ulang atau diklaim aktif.

## Validasi yang dijalankan

Backend akhir: **119 test lulus pada SQLite dan 119 pada PostgreSQL 16**. Run memakai database terpisah; tidak menjalankan fixture drop/create terhadap database development atau produksi. Tes snapshot terarah juga diulang setelah perbaikan penutupan koneksi. Masih ada warning dependency/deprecation dan AsyncMock worker Celery lama; ini bukan bukti Celery lama siap produksi.

Validasi frontend: lint dan build produksi lulus. Tiga suite Chromium lulus: **25 pemeriksaan follow-up baru, 19 smoke dan 72 regresi pasca-audit (116 total)**. Tidak ditemukan error JavaScript pada suite follow-up. Ruff dan kesesuaian OpenAPI juga diperiksa. Ini hasil lokal, bukan hasil CI remote. Log berada di `/workspace/.cloud-setup/ai-stock-analyzer/` dan `/tmp/stock-kp-*`; lokasi lokal tersebut tidak diasumsikan ikut tersedia pada deployment atau sesi lain.

Hasil baru dipisahkan dari matriks audit **115/3/5/4** dan hasil implementasi sebelumnya. Pemeriksaan browser menggunakan build produksi, Chromium dan provider/data/token reset fixture; tidak dinyatakan sebagai audit manusia, SMTP/provider nyata atau sertifikasi perangkat fisik. Fixture notifikasi yang kurang field tautan, selector route announcer, sequencing Back/refresh, dan asumsi pagination dua ticker diperbaiki dalam harness sebelum penerimaan akhir. Tidak dihitung sebagai empat bug aplikasi tambahan.

### Migrasi dan restore berisi data

[JSON hasil rehearsal](rehearsal_prd_1_3_20261020.json) mencatat PostgreSQL 16 lokal disposable: dua akun, dua saham, 120 harga, 120 indikator, satu watchlist, satu rencana dan satu job. Upgrade `r3_read_paths` → `r4_operations` mempertahankan seluruh jumlah. Backup custom di-restore ke database baru; login pemilik, catatan watchlist, versi/perhitungan dua lot dan penolakan data untuk akun lain diverifikasi melalui API.

Restore berikut verifikasi pada sampel tersebut memerlukan sekitar **2,6 detik**. Ini bukan RTO staging/produksi; waktu/resource/dataset jauh berbeda dari penerimaan staging PRD. Percobaan awal helper mengalami warning disposal lintas event loop; helper diperbaiki dan rehearsal akhir dijalankan pada database baru dengan koneksi ditutup dalam loop yang sama.

Database development sudah dibackup sebelum upgrade pada `development-before-r4-20261020.db` di direktori private cloud setup, lalu di-upgrade ke R4. API/worker development dijalankan kembali; status read-only memperlihatkan heartbeat/progres aktif, nol job dan nol saham. Database tersebut tidak diisi data pasar atau akun peserta. Backup/rehearsal private tidak ikut Git.

## Gerbang yang tetap terbuka

| Paket | Bukti lokal yang tersedia | Yang belum dapat dinyatakan selesai |
|---|---|---|
| KP-01 | Kontrak/OpenAPI, lint/build dan pipeline dikonfigurasi untuk suite baru. | Hasil CI remote pada SHA final harus diperiksa melalui run URL, tidak diadopsi dari hasil lokal. |
| KP-02 / G01/G02/T04 | Adapter dan fixture lama tersedia; kredensial AI/EODHD tidak ada, domain provider tidak tersedia pada konfigurasi runtime. | Provider IDX+AS/AI nyata, model/token/biaya, lisensi/budget, adjustment dan pola pasar nyata. |
| KP-03 / G03 | CLI/run history, status evaluasi dan kebijakan opt-in tersedia. Kalender belum terverifikasi dan ingestion nonaktif. | Jadwal/scheduler/publikasi per bursa, ingestion sesi baru serta event dari transisi pasar nyata. |
| KP-04 | Heartbeat independen, expiry 60 detik, progres/error serta status operator/UI diuji terkontrol; worker development aktif. | Supervisor/reboot dan rehearsal penghentian proses pada staging sesungguhnya serta penerimaan alarm/operator. |
| KP-05 / G04 | Reset valid/token/revocation diuji dengan data terkontrol; host/from SMTP belum dikonfigurasi. | Email diterima inbox milik tim melalui SMTP/TLS/egress nyata. |
| KP-06 / G05/T01/T02 | Chromium dan matriks lebar tersedia. Firefox/WebKit binary tidak tersedia pada runtime; tidak memakai perangkat fisik. | Android/iPhone, Safari/Firefox/WebKit, screen reader manual dan variasi zoom/keyboard fisik. |
| KP-07 / T03 | Migrasi, backup/restore berisi data lokal serta alat benchmark yang sudah ada. | Staging dengan resource produksi, load/soak, RPO/RTO serta rollback deployment. Benchmark lama tidak dijalankan ulang sebagai bukti staging. |
| KP-08 / T01/T03 | Protokol/lembar pilot siap diisi. | Lima peserta manusia, waktu/pemahaman nyata, observasi tujuh hari dan keputusan perluasan. |

Tiga ide fitur baru auditor tetap backlog discovery. Paket ini tidak membeli layanan, mengirim email, mengaktifkan ingestion berbayar atau melakukan deployment publik. Tidak menaikkan skor audit atau menyatakan gerbang rilis publik tertutup berdasarkan fixture.
