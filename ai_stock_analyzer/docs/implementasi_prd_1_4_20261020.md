# Implementasi PRD 1.4 — stabilisasi audit V3

Tanggal: 20 Oktober 2026, Asia/Jakarta (WIB). Baseline aplikasi `dc67ff9`. Acuan: [PRD 1.4](prd_stabilisasi_audit_v3_dc67ff9.md) dan [ringkasan sumber V3](review_audit_v3_dc67ff9_2026-10-20.md). Status: **perbaikan kode dan verifikasi lokal selesai; penerimaan eksternal belum selesai**. Gerbang staging, perangkat fisik, peserta dan layanan nyata belum diterima.

## Perubahan

| Paket | Implementasi |
|---|---|
| ST-01 / BUG-008 | Workspace backtest diikat akun/ticker. Pilihan run tersimpan eksplisit; generasi request dan AbortController melindungi hasil/error/finally dari respons lama. Identitas run/ticker diperiksa. Error pilihan dapat dicoba ulang. POST yang sudah tersimpan tidak dibatalkan secara fiktif saat UI beralih. Refresh riwayat gagal terpisah dari hasil tersimpan. Ekspor terikat snapshot run dan dibatalkan saat konteks berganti. |
| ST-02 / BUG-009 | Draft catatan dipisahkan dari nilai tersimpan per ticker/akun. Refresh mempertahankan draft termasuk string kosong; save mengakui hanya teks yang dikirim, tanpa menimpa ketikan lebih baru atau draft saham lain. Error mempertahankan teks dan retry. Link, pencarian, logout dan penghapusan menyediakan keputusan untuk draft; beforeunload dan Navigation API melengkapi proteksi navigasi yang didukung browser. Draft tidak masuk URL/localStorage/log dan tidak diklaim pulih setelah proses browser mati paksa. |
| ST-03 / BUG-010 | Metadata run dinormalisasi UTC pada batas API untuk list/detail/create/CSV. `created_at` memakai schema AwareDatetime, OpenAPI diperbarui. SQLite memakai kontrak writer `CURRENT_TIMESTAMP` UTC; PostgreSQL aware dinormalisasi tanpa pergeseran ganda. Tidak menulis ulang row, tanggal sesi, transaksi, atau menambah migrasi. Formatter UI menolak waktu naive/invalid dan memakai WIB eksplisit. |
| UXV3-01 | Hasil menampilkan ticker, full UUID, waktu WIB, source/revisi, lot, rentang histori dan parameter efektif; membedakan hasil tersimpan dari form simulasi berikutnya. Metadata kosong tidak ditebak. |
| UXV3-02 | Hasil kalkulator diposisikan pada langkah pemeriksaan risiko/lot/biaya, tombol lanjut memfokuskan uraian, ringkasan field belum lengkap tersedia dan langkah simpan eksplisit. Rumus/versi/snapshot penyimpanan dipertahankan. |
| UXV3-03 | Menu Beranda/Daftar pantauan/Pengaturan/Keluar/Notifikasi dan daftar istilah pola terpusat. Nama teknis dapat tetap dijelaskan; kode API, ticker dan kolom ekspor tidak diterjemahkan sembarangan. |
| UXV3-04 | Filter bursa/sort daftar pantauan berada di URL dengan validasi. Back/refresh memulihkan kriteria; entri history menyimpan fokus/scroll kandidat tanpa isi catatan, dibatasi akun dan dikonsumsi setelah pemulihan agar refresh berikutnya tidak mencuri fokus. Harga tetap dikelompokkan per currency. |
| UXV3-05 | Status alert menjelaskan langkah pengguna atau kebutuhan operator, dengan tautan data saham, preferensi notifikasi atau status pekerjaan. Tidak mengubah freshness, memicu ingestion berbayar atau menjanjikan realtime. |
| QA-01 | Suite browser V3 ditambahkan. Workflow memberi annotation berisi nama suite gagal, tanpa mengumumkan nilai credential/isi catatan. Annotation error juga mencatat kelas exception dan lokasi source tes tanpa pesan berisi input/credential. Akar failure CI lama tidak ditebak dari hasil lokal. |

## Verifikasi

Backend: **119 tes SQLite dan 119 tes PostgreSQL 16 lulus** pada database disposable. Tes API ditambah pembuktian instant list/detail/CSV yang sama, metadata create, revisi dan ownership. Tidak menjalankan fixture drop/create pada database development. Terdapat 163 warning dependency/legacy AsyncMock/resource pada masing-masing suite; hasil ini tidak menyatakan worker Celery lama siap produksi.

Frontend lint tanpa error/warning dan build produksi lulus. Empat suite Chromium lulus: **27 stabilisasi V3, 19 smoke, 72 pasca-audit dan 25 follow-up (143 pemeriksaan)**. Tidak ditemukan error JavaScript pada suite V3. Ruff dan konsistensi OpenAPI lulus. [Manifest validasi lokal](validasi_prd_1_4_20261020.json) mencatat cakupannya. Setelah guard loading ditambahkan pada save yang membatalkan refresh, suite V3 dijalankan ulang dan smoke diperiksa kembali; kedua suite lain tetap mencakup komponen yang tidak diubah oleh guard tersebut. Log/evidence lokal berada di `/workspace/.cloud-setup/ai-stock-analyzer/v14/` dan `v14-*.log`. Lokasi tersebut bukan URL staging dan tidak diasumsikan tersedia di sesi lain. Fixture memakai akun/data disposable; database, token dan screenshot privat tidak diunggah ke Git.

Regresi baru menahan respons backtest dan save, memeriksa identitas/ekspor, membandingkan zona UTC/Jakarta/New York, serta menguji draft/navigasi dan URL. Perbaikan implementasi setelah pengujian lokal dicatat sebagai proses verifikasi, bukan bug baseline tambahan: guard history saja tidak cukup untuk Link Next sehingga click harus dihentikan sebelum transisi. Update draft memakai functional React state untuk mempertahankan ketikan ketika pembaruan server memiliki prioritas render berbeda. Assertion draft kosong sempat gagal karena harness mengetik pada halaman yang masih inert sebelum dialog tambah saham ditutup; urutan tes diperbaiki dan skenario respons refresh ditahan ditambahkan, tanpa mengadopsi kegagalan harness itu sebagai bug aplikasi.

Smoke lokal pada worker yang masih menghitung indikator sempat melewati assertion default lima detik, sementara job kemudian sukses. Penantian skor sekarang dibatasi 30 detik, tetap memeriksa hasil 88% dan penyelesaian job. Ini diagnosis timeout harness lokal; belum membuktikan penyebab failure run CI lama. Uji navigasi Back juga menunggu URL detail benar-benar terbuka sebelum kembali, sehingga tidak salah menguji pembatalan transisi yang belum selesai.

## Batas penerimaan dan operasi

- Staging, Android/iPhone dan lima peserta belum tersedia menurut pengguna. Tidak ada deployment publik, undangan peserta atau hasil retensi tujuh hari. [Lembar penerimaan pilot](pilot_acceptance_template.md) diperbarui dengan tugas run/catatan V3.
- Provider IDX/AS, AI, kalender/ingestion/trigger dan SMTP nyata tetap memerlukan konfigurasi serta bukti. Fixture tidak menutup gerbang itu.
- Run CI lama [#6 pada dc67ff9](https://github.com/harihandika/ai-stock-analyzer/actions/runs/39368011622) gagal pada langkah browser; backend/schema/frontend checks sukses. Akses GitHub API sebelumnya ditolak proxy dan draft akses gagal stale_base. Tidak mengulang write terhadap draft yang sama. Status kandidat baru harus diperiksa pada SHA/URL run baru, bukan diwarisi dari run lama.
- Panduan startup dan proposal konfigurasi repository diperbarui untuk suite V3. Proposal **belum diterapkan/disimpan ke cloud draft**; perubahan file tidak mengaktifkan konfigurasi environment.
- Tidak ada migrasi baru; database development tetap pada `r4_operations`. Normalisasi waktu berlaku pada writer server yang diketahui UTC, bukan data import tanpa asal zona yang jelas. Operator harus memetakan import semacam itu sebelum dinyatakan terverifikasi.

Perbaikan kode dan bukti lokal dapat diterima terpisah dari keputusan pilot atau rilis publik. Matriks audit V3 87/3/5/4 tetap catatan historis auditor; hasil implementasi baru tidak mengubah skor atau menghitung ulang audit tersebut.
