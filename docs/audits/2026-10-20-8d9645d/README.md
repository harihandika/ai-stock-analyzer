# Audit pengguna AI Stock Analyzer — 20 Oktober 2026

Target pengujian: [`8d9645df458c92efa01a5ec279ff98c4f2dee785`](https://github.com/harihandika/ai-stock-analyzer/commit/8d9645df458c92efa01a5ec279ff98c4f2dee785).
Branch penyimpanan: `audit/user-testing-8d9645d-20261020`.

## Membaca di GitHub

- [Laporan pengujian pengguna](USER_TESTING_REPORT.md): hasil, cakupan, dan batas pengujian.
- [Laporan bug](BUG_REPORT.md): tiga bug beserta langkah reproduksi dan bukti.
- [Rekomendasi UX dan fitur](UX_FEATURE_RECOMMENDATIONS.md): prioritas perbaikan.
- [Folder evidence](evidence): screenshot PNG, hasil JSON, log, ekspor fixture, dan tiga trace Playwright.

Bukti tiga bug utama:

- [Perbandingan BBCA tampil pada konteks AAPL](evidence/history-stale-comparison.png).
- [Pembuatan alert sinyal gagal](evidence/signal-alert-error.png).
- [Filter screener sesudah kembali](evidence/screener-after-back.png), dibandingkan dengan [filter sebelum membuka saham](evidence/screener-filtered.png).

## Mengunduh paket lengkap

Buka [ZIP audit](AI_STOCK_ANALYZER_USER_AUDIT_8d9645d.zip), lalu klik **Download raw file** pada halaman GitHub. Ekstrak ZIP, kemudian buka `index.html` dengan browser. HTML memuat ketiga laporan dan screenshot pilihan tanpa koneksi internet. Screenshot lengkap ada di folder `evidence`.

ZIP ini adalah salinan byte-identik paket audit asli, tanpa tambahan README atau checksum publikasi. GitHub tidak menjalankan halaman HTML dari tampilan file; unduh dan buka secara lokal.

SHA-256 ZIP:

```
77f6d14f33e8b789179d65d33af1b3fc408a85a9169093c961b111ce2321fb52
```

Untuk meninjau trace, gunakan Playwright Trace Viewer secara lokal, misalnya `npx playwright show-trace evidence/negative-trace.zip` bila Playwright tersedia. Screenshot dan JSON dapat dibaca tanpa Playwright. Hasil terverifikasi yang sudah menormalkan retest tercatat di `evidence/execution-matrix.json`; log mentah juga memuat kegagalan harness yang dijelaskan dalam laporan.

## Konteks untuk sesi AI berikutnya

Baca tiga laporan dan bukti yang dirujuk. Hasil akhir: 115 lulus, 3 gagal, 5 terblokir, 4 belum diuji; total 127 observasi. Empat bug audit sebelumnya sudah diverifikasi diperbaiki. Tiga temuan tambahan: respons perbandingan terlambat melintasi ticker (P1), payload alert sinyal ditolak 422 (P2), dan filter screener hilang saat Back (P2). Jangan menganggap ketiganya diperkenalkan oleh commit target: audit tidak menguji kasus yang sama pada versi sebelumnya.

Data pasar dan respons AI berasal dari fixture terkontrol. Integrasi provider asli, SMTP nyata, dan perangkat fisik belum diverifikasi. Ini bukan bukti kesiapan produksi menyeluruh.

## Isi dan sanitasi publikasi

Publikasi ini hanya menambahkan folder audit. Kode aplikasi tidak diubah dan branch `work` tidak diperbarui. Pernyataan dalam laporan asli bahwa auditor tidak melakukan commit/push merujuk pada pelaksanaan audit; commit publikasi artefak dilakukan kemudian atas permintaan pengguna.

Tidak disertakan database, file `.env`, konfigurasi credential, atau script eksekusi audit. Trace autentikasi sudah disamarkan sebelum paket asli dibuat. Pemeriksaan tambahan terhadap 276 resource teks, termasuk isi ZIP trace, tidak menemukan pola JWT, private key, token provider yang diperiksa, URL dengan credential, atau password fixture yang diketahui. Field autentikasi terstruktur yang diperiksa sudah disamarkan. Pemeriksaan otomatis ini melengkapi pemeriksaan cakupan berkas; bukan jaminan deteksi semua bentuk rahasia.

Akun, data finansial, dan ekspor yang tampak pada bukti merupakan fixture audit di database disposable, bukan data pengguna produksi. Screenshot dipertahankan untuk menjaga bukti visual. `SHA256SUMS` mencatat hash seluruh berkas publikasi selain dirinya sendiri.
