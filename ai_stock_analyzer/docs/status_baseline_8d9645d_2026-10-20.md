# Status baseline untuk rencana pilot

Tanggal: 20 Oktober 2026, Asia/Jakarta (WIB). Dokumen ini adalah pencocokan Git, source dan paket audit yang diberikan pengguna, **bukan pelaksanaan audit ulang**.

Status tabel berikut bersifat historis pada saat penyusunan PRD. Perubahan setelah baseline dicatat dalam [laporan implementasi PRD 1.3](implementasi_prd_1_3_20261020.md).

## Sumber dan batas akses

Permintaan pengguna adalah membaca feedback terakhir di sesi **Edit ai-stock-analyzer**. Akses langsung lintas sesi tidak tersedia. Pengguna kemudian memberikan branch `audit/user-testing-8d9645d-20261020` dan commit publikasi `9c36fcf`; paket tersebut berhasil diambil dan dibaca. **Kebutuhan bukti audit sudah terpenuhi**, tanpa perlu meminta salinan feedback lagi.

Sumber yang tersedia:

- [Ringkasan audit terbaru 8d9645d](review_audit_8d9645d_2026-10-20.md) beserta tautan laporan, JSON final dan screenshot pada commit publikasi. Seluruh 144 hash manifest cocok; hash/CRC ZIP diperiksa. Temuan N05/N04/J10 menjadi AF-01–03 dalam PRD.
- [Ringkasan audit d17f260](review_audit_d17f260_2026-10-19.md), dibaca dari sesi sumber pada pekerjaan sebelumnya. Targetnya `d17f260`, bukan `8d9645d`.
- [Laporan implementasi PRD 1.2](implementasi_pasca_audit_20261019.md) dan [JSON benchmark](benchmark_pasca_audit_20261019.json), tersimpan di repository.
- Source lokal pada `8d9645df458c92efa01a5ec279ff98c4f2dee785` dan hasil `git ls-remote origin refs/heads/main refs/heads/work` saat penyusunan.

## Baseline GitHub

| Referensi | Commit | Implikasi |
|---|---|---|
| `main` | `d17f260c9255042ef86735b98f2c3b6b29e1dcdb` | Belum memuat perbaikan pasca-audit berikutnya. |
| `work` / checkout lokal | `8d9645df458c92efa01a5ec279ff98c4f2dee785` | Kandidat yang sudah di-push; memuat perbaikan PRD 1.2. |
| `audit/user-testing-8d9645d-20261020` | `9c36fcf7b9d4665c9d082f0736aee817d38e54c2` | Publikasi artefak audit untuk aplikasi `8d9645d`; bukan commit perbaikan aplikasi. |

Perbedaan branch bukan bukti versi yang sedang digunakan deployment. Commit deployment perlu diverifikasi tersendiri. Penyusunan PRD ini tidak melakukan merge, push atau deployment.

## Pemetaan pekerjaan terdahulu

| Area / ID lama | Bukti tersedia pada kandidat | Status untuk rencana baru |
|---|---|---|
| BUG-001 / PA-01: hasil risiko lama | [TradePlans](../../ai_stock_analyzer_frontend/src/components/TradePlans.tsx) mengubah versi draft dan menghapus hasil ketika input berubah; respons diperiksa terhadap snapshot. | Fixed and verified pada audit terbaru, termasuk respons lambat. Pertahankan regresi. |
| BUG-002 / PA-02: header 320px | [CSS layout](../../ai_stock_analyzer_frontend/src/components/layout/layout.module.css), [AppLayout](../../ai_stock_analyzer_frontend/src/components/layout/AppLayout.tsx); audit memuat 60 geometri lulus. | Fixed and verified; perangkat fisik dan browser lain masih perlu penerimaan. |
| BUG-003 / PA-03: utility padding kalah | [globals.css](../../ai_stock_analyzer_frontend/src/app/globals.css) tidak lagi mereset seluruh padding/margin; computed style 12px/tab 44px diuji auditor. | Fixed and verified; pertahankan regresi CSS produksi. |
| BUG-004 / PA-04: legend hanya hover | [StockChart](../../ai_stock_analyzer_frontend/src/components/charts/StockChart.tsx) mempunyai panel candle tetap, slider keyboard dan reset; touch 900ms/keyboard lulus. | Fixed and verified; uji Safari/touch fisik belum terbukti. |
| BUG-005: compare berbeda konteks | N05 dan screenshot menunjukkan compare BBCA datang setelah AAPL aktif; source History tidak memeriksa snapshot request. | Terbuka P1; AF-01. |
| BUG-006: alert sinyal 422 | N04/retest mengirim direction null; X04 tanpa direction berhasil 201. | Terbuka P2; AF-02. |
| BUG-007: screener kehilangan konteks | J10 dan screenshot sesudah Back menunjukkan filter kosong; kriteria/page hanya state lokal. | Terbuka P2; AF-03. |
| PA-05/06: metadata/form | [DataStatus](../../ai_stock_analyzer_frontend/src/components/stock/DataStatus.tsx) membedakan tanggal harga/fetch; kalkulasi minimal dan simpan lengkap sudah dipisahkan. | Tersedia; pemahaman dan waktu penyelesaian pengguna belum diukur. |
| PA-07: alternatif provider | [Kajian integrasi](alternatif_integrasi.md), adapter Gemini/EODHD dan tes terkontrol sudah ada. | Penerimaan provider nyata, budget dan hak display masih terbuka menurut laporan terakhir. |
| PA-08: ingestion/alert | [market_ops](../app/worker/market_ops.py) menyediakan status dan ingestion opt-in; default nonaktif, lock hanya satu host. | Jadwal nyata, kalender, heartbeat/monitoring dan bukti alert nyata masih diperlukan. CLI status tidak memeriksa heartbeat. |
| PA-09: pemulihan akun | [Router akun](../app/api/routers/account.py), transport SMTP dan halaman reset tersedia. | Pengiriman inbox nyata belum dibuktikan. Halaman masih meminta pengguna memilih mode reset setelah membuka tautan. |
| PA-10: kesiapan rilis | [Workflow CI](../../.github/workflows/ci.yml), regresi dan alat benchmark sudah ada. | Hasil CI remote kandidat, staging, restore, perangkat/responden dan observasi tujuh hari belum dibuktikan dalam laporan. |

Angka **114 test SQLite, 114 PostgreSQL, 72 pemeriksaan browser pasca-audit dan 19 smoke** adalah hasil yang dicatat implementasi sebelumnya. Angka tersebut tidak dihasilkan ulang pada penyusunan PRD ini, tidak dijumlahkan dengan 165 kasus audit lama atau 127 observasi audit terbaru, dan tidak menjamin integrasi nyata. Benchmark lokal memakai empat API worker pada hasil akhir; ia belum menjadi hasil staging dengan resource produksi.

Tiga bug tambahan dikonfirmasi auditor melalui runtime, lalu bukti dan source-nya dicocokkan dalam pekerjaan ini. Tidak ada reproduksi browser ulang oleh penulis PRD. Usulan heartbeat dan penyederhanaan reset adalah rekomendasi perencanaan; bukan dua bug tambahan yang dikonfirmasi auditor.

## Implikasi untuk rencana

Prioritaskan AF-01 → AF-02/03 dan QA reproduksi sebelum memperluas pilot. UX badge/bahasa/orientasi/indikator ditangani sesudah stabilisasi, sementara gerbang provider/ingestion/SMTP/perangkat/staging/pilot tetap berlaku. [PRD 1.3](prd_kesiapan_pilot_8d9645d.md) kini mencakup audit terbaru, dengan paket koreksi audit 2,25–4 hari teknis. Riwayat hasil audit lama dipertahankan, tidak ditulis ulang sebagai hasil kandidat baru.
