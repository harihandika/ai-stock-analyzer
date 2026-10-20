# PRD 1.4 — Stabilisasi pengalaman pengguna setelah audit V3

Tanggal: 20 Oktober 2026, Asia/Jakarta (WIB). Status: **kode dan verifikasi lokal selesai; gerbang eksternal masih terbuka**. Lihat [laporan implementasi](implementasi_prd_1_4_20261020.md). Baseline aplikasi: [`dc67ff9445d91ce8a83270bcb08d4ca72282cd8b`](https://github.com/harihandika/ai-stock-analyzer/commit/dc67ff9445d91ce8a83270bcb08d4ca72282cd8b), branch `work` pada audit V3. Dokumen ini melanjutkan [PRD 1.3](prd_kesiapan_pilot_8d9645d.md) dan [laporan pelaksanaannya](implementasi_prd_1_3_20261020.md).

## 1. Sumber, baseline dan batas bukti

Sesi **Edit ai-stock-analyzer** berhasil dibaca langsung melalui alat pembaca thread. Acuan terbaru adalah jawaban akhir audit V3 pada thread `01a15241-d3d2-77fe-b924-a5b233e3a091`, turn `01a15926-516a-74d2-bd3e-ab5734a8bce5`. [Ringkasan sumber V3](review_audit_v3_dc67ff9_2026-10-20.md) mencatat temuan dan keterbatasannya.

- Hasil auditor: **87 lulus, 3 gagal, 5 terblokir, 4 belum diuji**; 90 pemeriksaan dieksekusi, 99 observasi total. Angka ini tidak digabungkan dengan audit sebelumnya atau tes implementasi.
- BUG-008, BUG-009 dan BUG-010 masing-masing berseverity **P2 menurut auditor**. Tidak ada bukti audit bahwa ketiganya diperkenalkan oleh commit baseline ini.
- BUG-005–007 dinyatakan fixed and verified pada pengujian V3; badge notifikasi, pembatalan hasil kalkulator lama dan workflow touch juga membaik. Pertahankan sebagai cakupan regresi.
- Paket V3 berisi lima laporan dan ZIP sekitar 54 MB di workspace sesi sumber, belum dipublikasikan oleh auditor. Penyusunan PRD membaca ringkasan/percakapan dan mencocokkan source lokal; **tidak mengklaim telah mengunduh atau memverifikasi ulang hash ZIP, seluruh screenshot dan trace V3**.
- Pengujian V3 menggunakan Chromium, build produksi dan fixture pasar/AI pada SQLite terisolasi. Waktu tugas otomatis dan skor pengalaman auditor bukan studi lima pengguna manusia, benchmark staging atau bukti provider nyata.
- Pemeriksaan CI terpisah menemukan [run #6](https://github.com/harihandika/ai-stock-analyzer/actions/runs/39368011622) gagal pada langkah browser; backend SQLite/PostgreSQL, OpenAPI dan lint/build frontend sukses. Reproduksi lokal dengan database baru lulus 19 smoke test, tetapi belum menjelaskan failure remote. Jangan menghubungkan tiga bug V3 dengan failure CI tanpa log.
- Pengguna menyatakan staging, perangkat dan peserta yang ditanyakan **belum ada**. Tidak ada jadwal pilot atau deployment yang dapat dinyatakan sudah berjalan.

## 2. Masalah dan hasil yang dituju

Investor yang membuka beberapa hasil backtest dapat membaca hasil yang tidak lagi sesuai pilihannya. Catatan riset yang sedang ditulis dapat hilang saat menambah saham lain. Waktu pembuatan run dapat bergeser tujuh jam, sehingga urutan dan identitas hasil sulit dipercaya. Hambatan berikutnya adalah form rencana yang panjang, campuran bahasa, konteks watchlist yang hilang saat kembali, serta status alert yang belum menjelaskan tindakan selanjutnya.

Hasil yang dituju:

1. Hasil, indikator loading/error dan ekspor selalu mengikuti run/ticker yang terakhir dipilih pengguna.
2. Menambah atau memuat ulang watchlist tidak menghapus draft catatan yang belum disimpan secara diam-diam.
3. Timestamp API menyatakan instant yang sama pada SQLite/PostgreSQL dan tampil konsisten dengan label WIB di berbagai zona browser.
4. Pengguna memahami hasil aktif, langkah menyimpan rencana dan cara menyelesaikan status alert yang menunggu.
5. CI hijau pada kandidat yang tepat, kemudian tersedia staging untuk penerimaan perangkat dan manusia.

Pengguna sasaran tetap investor pemula, investor aktif yang meneliti beberapa kandidat, serta pengguna ponsel. Tidak mengubah rumus risiko/lot, strategi backtest, kontrak satuan persen/bps, atau mengartikan confidence sebagai probabilitas profit.

## 3. Cakupan dan urutan prioritas

| Urutan | Paket | Jenis | Prioritas pengerjaan |
|---|---|---|---|
| 1 | ST-01 — Lindungi konteks run backtest / BUG-008 | Perbaikan bug P2 | Wajib sebelum penerimaan kandidat |
| 2 | ST-02 — Pertahankan draft catatan / BUG-009 | Perbaikan bug P2 | Wajib sebelum penerimaan kandidat |
| 3 | ST-03 — Kontrak timestamp UTC/WIB / BUG-010 | Perbaikan bug P2 | Wajib sebelum penerimaan kandidat |
| 4 | UXV3-01 — Identitas dan parameter hasil aktif | UX, mendukung ST-01/03 | Dikerjakan bersama backtest |
| 5 | UXV3-02–05 — Rencana, bahasa, konteks watchlist, bantuan alert | UX lanjutan | Setelah tiga bug ditutup |
| Paralel | QA-01 — Diagnosis CI dan bukti run | Kualitas rilis | Menjadi syarat setiap kandidat |
| Setelah akses tersedia | PILOT-01–03 — Staging, perangkat fisik, peserta | Penerimaan eksternal | Gerbang pilot, bukan tes lokal |

Urutan ini menunjukkan ketergantungan pekerjaan, bukan perubahan severity auditor. Persyaratan di bawah adalah acuan penerimaan. Status pelaksanaan dan batas bukti terbaru berada pada laporan implementasi; gerbang CI/staging/pilot tidak otomatis selesai bersama perbaikan source.

## 4. Persyaratan tiga perbaikan wajib

### ST-01 — Pilihan run backtest tidak tertimpa respons lama

Cerita pengguna: setelah memilih run A kemudian B, saya tetap membaca B meskipun respons A selesai belakangan.

Perilaku yang diwajibkan:

- Simpan identitas pilihan aktif secara eksplisit. Status loading, hasil, error dan ekspor memiliki konteks akun, ticker, run dan generasi permintaan yang sama.
- Batalkan fetch yang sudah tidak relevan jika memungkinkan dan abaikan respons sukses/error/finally yang lebih lama. Abort saja tidak cukup sebagai guard.
- Saat pilihan berubah, hilangkan atau tandai hasil lama secara jelas sebagai hasil sebelumnya. Jangan menampilkan hasil A seolah-olah milik B saat B sedang dimuat.
- Terapkan aturan pilihan terakhir juga pada interaksi menjalankan simulasi baru, membuka run tersimpan, pergantian ticker, keluar halaman dan pergantian akun. Pembatalan tampilan tidak berarti pekerjaan server yang sudah diterima pasti dibatalkan.
- Validasi `run_id` dan ticker respons terhadap konteks yang diminta. Respons salah identitas tidak ditampilkan sebagai hasil sah.
- Gagal memperbarui daftar riwayat setelah simulasi berhasil tidak boleh menghilangkan hasil yang sudah tersimpan atau menjanjikan simulasi gagal; tampilkan kegagalan refresh riwayat secara terpisah.

Penerimaan:

1. Tahan respons A, pilih B, selesaikan B, lalu lepaskan A: hasil, label pilihan dan target ekspor tetap B.
2. Ulangi dengan error A terlambat serta A→B→A; spinner/error lama tidak mengubah state pilihan terakhir.
3. B gagal: tampilkan kegagalan B dan tombol coba lagi; tidak otomatis menggantinya dengan hasil A.
4. Respons dengan run/ticker salah ditolak. Request selesai setelah keluar halaman/akun tidak mengisi halaman atau akun baru.
5. Jalankan simulasi lalu buka run lain ketika respons pertama masih tertunda; hanya maksud UI terakhir yang diterbitkan. Run yang sah di server tetap muncul ketika riwayat dimuat ulang.

### ST-02 — Draft catatan watchlist terlindungi

Cerita pengguna: saya bisa menambah AAPL sambil menulis catatan BBCA tanpa kehilangan tulisan yang belum disimpan.

Perilaku yang diwajibkan:

- Pisahkan catatan tersimpan dari draft per ticker dan akun, beserta status belum disimpan/menyimpan/gagal/tersimpan.
- Refresh daftar karena tambah ticker atau muat ulang hanya mengisi catatan baru dan catatan yang tidak sedang diubah. Draft dirty mempertahankan teks persis, termasuk draft kosong untuk menghapus catatan.
- Menyimpan satu ticker tidak membersihkan draft ticker lain. Jika teks berubah saat save masih berlangsung, respons save hanya mengakui snapshot yang dikirim; perubahan sesudahnya tetap dirty.
- Error API mempertahankan draft dan memberi tindakan coba lagi. Tidak ada autosave tersirat, permintaan analisis tambahan atau penulisan catatan tanpa tindakan Simpan.
- Sebelum meninggalkan halaman atau menghapus ticker yang mempunyai draft, berikan pilihan tetap mengedit atau membuang secara eksplisit. Untuk reload/penutupan browser gunakan proteksi yang didukung browser; dialog browser tidak menjamin pemulihan setelah proses ditutup paksa.
- Cakupan paket ini: perlindungan draft selama sesi halaman dan peringatan sebelum keluar. Pemulihan lintas perangkat, penutupan paksa dan penyimpanan draft jangka panjang belum termasuk. Jangan menyimpan isi catatan di URL, log atau penyimpanan browser permanen secara default.
- Pergantian akun menghapus draft dari memori akun sebelumnya. Penghapusan ticker yang dikonfirmasi membuang draft ticker tersebut saja.

Penerimaan:

1. Ubah catatan BBCA tanpa menyimpan → tambah AAPL → draft BBCA tetap sama dan bertanda belum disimpan. Ulangi dua kali dengan teks dan draft kosong.
2. Edit dua ticker → simpan satu → draft ticker lain tidak berubah; hasil simpan pertama dapat diverifikasi setelah reload yang sudah disetujui.
3. Tahan respons save, ubah teks lagi, lepaskan respons: teks terbaru tetap ada dan belum disimpan.
4. Gagal add/load/save tidak menghapus draft; retry tidak membuat catatan tersimpan untuk ticker yang salah.
5. Navigasi/hapus dengan draft menyediakan keputusan eksplisit; ganti akun tidak membocorkan teks lama.

### ST-03 — Waktu run tidak bergantung zona browser

Cerita pengguna: run yang sama menampilkan waktu pembuatan WIB yang sama di browser Jakarta maupun UTC.

Kontrak:

- `created_at` pada list, metadata detail dan respons create yang menyediakan timestamp harus berupa ISO 8601 dengan zona, dinormalisasi ke UTC (`Z` atau `+00:00`). Nilai offset sah dari penyimpanan tidak boleh digeser dua kali.
- SQLite dapat mengembalikan datetime tanpa zona meskipun model memakai `DateTime(timezone=True)`. Normalisasi dilakukan pada batas serialisasi yang teruji, bukan menambah tujuh jam di frontend.
- Untuk row lama tanpa zona, gunakan UTC hanya setelah memastikan asal penulisannya memang UTC. Jika provenance tidak dapat dipastikan, tampilkan waktu tidak terverifikasi dan dokumentasikan pemetaan; jangan menggeser data historis massal berdasarkan tebakan.
- Frontend memakai formatter bersama untuk instant, zona tampilan `Asia/Jakarta` dan label WIB; null/invalid/naive yang belum memiliki kebijakan tidak boleh diam-diam dianggap zona browser.
- Tanggal sesi pasar (`YYYY-MM-DD`) tetap tanggal sesi, bukan instant UTC. Jangan menggeser `data_start`, `data_end` atau tanggal candle lewat perbaikan timestamp.
- Perbarui schema/OpenAPI dan konsistensi metadata secara additive. Audit endpoint waktu lain untuk menemukan pola serupa, tetapi hanya ubah setelah ada tes dan keputusan kompatibilitas.

Penerimaan:

1. Instant `2026-10-20T04:58:39Z` tampil `20 Oktober 2026, 11.58.39 WIB` di browser UTC, Asia/Jakarta dan America/New_York, baik dari SQLite maupun PostgreSQL.
2. Nilai `+07:00` yang ekuivalen menghasilkan instant sama; uji pergantian tanggal UTC, null/invalid dan row legacy tanpa zona.
3. Dua run milik audit tidak berbeda tujuh jam antara zona browser; list, detail, hasil baru dan ekspor yang menyertakan waktu memakai instant konsisten.
4. Urutan riwayat, ownership, UUID, nilai transaksi, tanggal sesi dan perhitungan hasil tidak berubah.

## 5. Persyaratan UX lanjutan

| ID | Perubahan | Acceptance criteria |
|---|---|---|
| UXV3-01 | Header hasil aktif menampilkan ticker, ID run yang dapat dilihat lengkap, waktu WIB, histori yang dipakai, TP/SL, modal, lot, fee/slippage, revisi/sumber bila tersedia. Bedakan parameter hasil tersimpan dari form simulasi berikutnya. | Pilihan A/B dengan parameter berbeda memperbarui seluruh identitas dan target ekspor secara serentak. Metadata kosong berlabel belum tersedia; tidak ditebak dari form yang sekarang. Tidak memicu simulasi ulang saat membuka run. |
| UXV3-02 | Alur rencana menunjukkan langkah Hitung → Periksa risiko/biaya/lot → Lengkapi alasan/horizon/pembatalan → Simpan, disertai ringkasan field yang masih diperlukan. | Hasil perhitungan invalid saat input berubah; versi dan nilai yang disimpan sesuai snapshot sah terakhir. Pindah ke form lanjutan mempertahankan input. Uji edit, batal, gagal validasi dan refresh tanpa merusak hasil 20→2 lot. Keberhasilan pemahaman mengikuti pilot manusia. |
| UXV3-03 | Seragamkan bahasa menu, tombol dan penjelasan pola. Buat daftar istilah Indonesia dengan nama teknis asli seperlunya, misalnya “Daftar pantauan (watchlist)”. | Satu tindakan memiliki nama yang konsisten di menu, heading, bantuan dan error. BUY/HOLD/WAIT, ticker, nama provider, kode API dan kolom ekspor tidak diubah sembarangan. Tidak menambahkan klaim profit dari nama pola. |
| UXV3-04 | Filter bursa dan urutan watchlist tersimpan di URL yang divalidasi. Back/Forward/refresh mengembalikan pilihan; kandidat fokus/scroll dipulihkan setelah data siap jika masih ada. | Uji IDX/AS, sort harga/perubahan, nilai URL tidak sah, kandidat dihapus dan dua akun. Konten draft catatan tidak masuk URL; perlindungan ST-02 tetap berlaku. Harga lintas mata uang tidak disortir sebagai angka yang langsung sebanding. |
| UXV3-05 | Setiap status alert menunggu memiliki penjelasan singkat dan langkah berikutnya yang sesuai, misalnya buka saham untuk memeriksa data atau jalankan analisis bila eligible. | Menunggu data/kalender, analisis, sesi sebelumnya, worker, baseline, dijeda dan preferensi nonaktif diuji terpisah. Aksi operator dibedakan dari aksi pengguna. UI tidak menandai fresh/siap dari klik, tidak mengaktifkan ingestion/provider berbayar, dan tetap menjelaskan EOD. |

## 6. CI dan gerbang penerimaan eksternal

### QA-01 — CI pada kandidat yang dapat dilacak

1. Dapatkan log run gagal melalui akses resmi GitHub API atau log yang diekspor pemilik repo. `api.github.com` saat ini ditolak proxy. Draft penambahan domain gagal `stale_base`; rekonsiliasi melalui konfigurasi environment terbaru, tanpa mengulang draft yang sama atau meminta token di chat.
2. Tentukan suite/assertion yang gagal, klasifikasikan masalah harness/setup/aplikasi dan buat reproduksi yang sesuai. Jangan menebak akar masalah dari exit code 1 atau mengurangi assertion agar hijau.
3. Perbaiki penyebab yang terkonfirmasi; pastikan kegagalan menyisakan diagnosis yang cukup dan bukti yang tersanitasi. Akses artefak dibatasi dan tidak membawa token, password, catatan akun atau database.
4. Penerimaan: URL run, SHA, waktu WIB, setiap job/step, jumlah tes dan hasil akhir tercatat. SQLite/PostgreSQL, schema, lint/build dan suite browser wajib berhasil pada kandidat final. Run lama yang hijau tidak menggantikan SHA baru.

### PILOT-01 — Siapkan lalu uji staging

Staging belum tersedia. Sebelum publikasi, pemilik layanan menetapkan hosting, resource/budget, domain/TLS, database disposable, operator dan profil akses. Menyiapkan konfigurasi yang dapat ditinjau berbeda dari membuat layanan berbayar atau deployment publik.

- Frontend/API/worker memakai SHA yang sama dan konfigurasi proxy/auth yang terverifikasi. Gunakan database dan secret staging yang terpisah; data akun produksi tidak disalin untuk pilot ini.
- Uji registrasi/login/logout/reset, ownership dua akun, search/detail, watchlist, riwayat/compare, screener, rencana, backtest dan status alert. Tiga kasus ST diuji melalui build produksi di staging.
- Jalankan heartbeat/stop/restart, antrean/deadline, migrasi berisi data, backup/restore dan load sesuai resource staging. Target RPO ≤24 jam/RTO ≤60 menit harus diukur di staging; rehearsal lokal sebelumnya bukan penggantinya.
- Catat provider/model/sumber/tanggal dan status fixture atau nyata per skenario. Gerbang provider IDX/AS, kalender/ingestion, trigger dan inbox SMTP nyata dari PRD 1.3 tetap terbuka sampai ada bukti nyata.
- Penerimaan: manifest deployment, URL layanan dan CI, hasil smoke, resource/dataset serta restore rehearsal tersedia; error dan skenario blocked tidak ditutup sebagai pass.

### PILOT-02 — Perangkat dan aksesibilitas

Uji pada setidaknya satu Android dengan Chrome dan satu iPhone dengan Safari; catat model/OS/browser. Cakup keyboard layar, fokus, scroll, modal, long press chart, tabel transaksi, filter, catatan dirty, rencana dan jaringan lambat. Tambahkan keyboard desktop dan screen reader yang disebutkan versinya. Enam viewport emulasi tetap digunakan untuk regresi layout, tanpa diklaim sebagai perangkat fisik.

### PILOT-03 — Lima peserta dan observasi tujuh hari

Rekrut lima peserta nyata dengan persona pemula/aktif/mobile, jadwal dan persetujuan pencatatan. Jangan menghubungi orang atau mengirim undangan otomatis tanpa instruksi. Gunakan [lembar pilot](pilot_acceptance_template.md):

- Tugas A cari saham → jelaskan tanggal/sumber → simpan watchlist: target ≤90 detik pada ≥4/5 peserta.
- Tugas B hitung/periksa risiko-lot-biaya → lengkapi → simpan rencana: target ≤3 menit pada ≥4/5 peserta dan pemahaman angka yang benar.
- Tambahkan tugas pilih dua run berurutan, sebut run/parameter/waktu aktif, lalu ubah catatan dan tambah ticker. Catat salah baca, kehilangan draft, bantuan dan waktu; target nol kehilangan draft tanpa keputusan pengguna pada tugas yang diamati.
- Ukur kembali hari berikutnya/hari ketujuh hanya pada peserta yang sudah mencapai jendela tersebut. Angka Agent V3 tidak menjadi baseline kecepatan manusia atau hasil retensi.

## 7. Rencana uji dan definisi selesai

| Area | Bukti minimum |
|---|---|
| ST-01 | Respons A/B ditahan dan dibalik, error terlambat, salah identitas, ticker/akun/unmount, run baru bersamaan dengan membuka hasil lama; label dan ekspor ikut diperiksa |
| ST-02 | Dua draft, tambah/muat ulang/gagal API, draft kosong, edit saat save, navigasi/hapus, akun berbeda; teks dan status diverifikasi sebelum/sesudah |
| ST-03 | SQLite dan PostgreSQL, tiga zona browser, offset ekuivalen, pergantian hari, legacy/null/invalid; bandingkan instant API dan teks UI |
| Regresi | BUG-005–007, badge langsung, kalkulator 20→2 lot, identitas compare, Back/Forward screener, reset/logout/ownership, chart/missing data dan touch |
| UX | Label/istilah, parameter aktif vs draft form, rencana bertahap, filter watchlist dan tindakan alert; keyboard serta enam lebar emulasi |
| Operasi | CI kandidat final, deployment manifest, provider/SMTP sesuai status aktual, restore/load, perangkat dan hasil peserta dicatat terpisah |

Definisi selesai **implementasi lokal**: ST-01–03 dan UX yang disepakati diterapkan, tes regresi bermakna lulus, kontrak/OpenAPI konsisten, laporan menyebut SHA serta bukti. Definisi **diterima untuk pilot staging** juga memerlukan QA-01 dan PILOT-01; definisi **pilot selesai** memerlukan PILOT-02/03 dan gerbang layanan nyata yang dipilih. Jangan menyebut seluruh PRD selesai hanya karena source dipush atau tes lokal hijau.

Setiap bug dicatat sebagai open → fixed locally → retested → verified, dengan expected/actual, SHA, database, zona dan bukti. Status blocked/not-tested tetap terlihat. Metrik tiga bug bukan skor keseluruhan produk atau bukti profitabilitas.

## 8. Urutan kerja, estimasi dan dependensi

Estimasi berikut adalah usaha satu engineer, bukan komitmen kalender atau waktu yang sudah dikerjakan:

| Tahap | Paket dan penanggung jawab peran | Estimasi |
|---|---|---:|
| 1 | Engineer frontend/backend: ST-01 + UXV3-01, ST-02, ST-03; QA menyiapkan kasus terkontrol | 3–5 hari kerja |
| 2 | Engineer/desainer: UXV3-02–05; QA regresi dan penyempurnaan istilah | 2–4 hari kerja |
| 3 | Engineer/QA: diagnosis CI dan laporan kandidat; dapat paralel sejak tahap 1 jika log tersedia | 0,5–1,5 hari kerja setelah akses |
| 4 | Operator/engineer: konfigurasi dan pengujian staging, restore/load | 1–3 hari kerja setelah hosting/akses ditetapkan |
| 5 | QA/produk: perangkat, lima peserta dan observasi | 1–2 hari usaha awal, ditambah jendela observasi minimal 7 hari |

Paket kode/UX/CI diperkirakan **5,5–10,5 hari kerja**, di luar tunggu akses dan penyediaan staging/peserta. Hosting, budget, akun uji, provider/SMTP dan perangkat adalah dependensi yang belum dipenuhi, bukan kegagalan tes produk. Jadwal kalender baru ditetapkan setelah dependensi dan owner nyata tersedia.

## 9. Backlog setelah stabilisasi

Perbandingan lintas saham, jurnal evaluasi rencana dan ringkasan perubahan watchlist sejak kunjungan terakhir tetap discovery. Masing-masing memerlukan skenario pengguna, desain data, privasi, metrik manfaat dan estimasi terpisah sebelum menjadi komitmen implementasi. Tidak termasuk integrasi broker, order otomatis, intraday, pembayaran atau penambahan provider tanpa keputusan konfigurasi.
