# PRD dan Rencana Perbaikan AI Stock Analyzer

Tindak lanjut saat ini: [PRD 1.4 setelah audit V3 pada dc67ff9](prd_stabilisasi_audit_v3_dc67ff9.md), berdasarkan feedback terbaru sesi **Edit ai-stock-analyzer** yang sudah dibaca. Prioritas: BUG-008–010, UX lanjutan, CI dan gerbang staging/pilot. [PRD 1.3](prd_kesiapan_pilot_8d9645d.md) serta dokumen sebelumnya tetap menjadi jejak historis.

Versi: 1.1 — tindak lanjut feedback sesi “Edit ai-stock-analyzer”

Tanggal revisi: 19 Oktober 2026, Asia/Jakarta (WIB). Versi awal: 18 Oktober 2026.

Status: rancangan tindak lanjut berdasarkan [review pengguna](review_pengguna_2026-10-19.md). Baseline review adalah `42d887a`; implementasi R1 sudah di-push ke `origin/work` pada commit `541c281`. Validasi provider nyata, staging, dan gerbang rilis publik masih terbuka. Revisi PRD ini bukan implementasi fitur lanjutan atau bukti deployment.

Pembaruan pelaksanaan: [laporan implementasi PRD 19 Oktober](implementasi_prd_20261019.md) mencatat fitur yang sudah tersedia sesudah baseline R1, pengujian, konfigurasi worker/provider, serta gerbang yang masih terbuka. Status historis pada bagian 2 dan backlog baseline tetap menjadi jejak perencanaan; gunakan laporan tersebut untuk capaian terbaru.

Keputusan urutan: tuntaskan validasi inti dan kualitas penggunaan → watchlist serta alert EOD → screener, riwayat analisis, dan perencanaan transaksi. Syarat teknis dan rilis ditulis di bawah; pekerjaan R1 yang sudah tersedia tidak diestimasi ulang sebagai fitur baru.

Pemilik produk: pemilik aplikasi. Penanggung jawab teknis dan QA ditentukan saat pelaksanaan.

## 1. Masalah dan hasil yang dituju

Pengguna membutuhkan jawaban yang dapat ditelusuri: saham apa yang perlu diperhatikan, berdasarkan data kapan, mengapa sinyal muncul, dan apa risikonya. Pada baseline review, beberapa kondisi gagal menghasilkan harga contoh atau rekomendasi yang tampak nyata; alur AI dan kontrak backtest juga tidak konsisten. Perbaikan R1 menangani cacat inti tersebut. Fokus berikutnya adalah membuktikan integrasi nyata dan melengkapi pekerjaan harian pengguna.

Tujuan perbaikan adalah membuat pengguna dapat mempercayai informasi, menyelesaikan alur utama, dan memahami keterbatasan analisis sebelum menambahkan fitur baru.

Dokumen ini melengkapi [PRD awal](prd.md) dan menjadi acuan untuk ruang lingkup perbaikan di bawah. Label selesai pada [rencana sprint lama](agile_sprint_plan.md) merupakan catatan historis, bukan bukti bahwa kriteria dalam dokumen ini sudah terpenuhi.

### Sasaran pengguna

- Investor ritel dan swing trader yang memantau saham Indonesia; saham AS tetap didukung dengan bursa dan mata uang yang benar.
- Pengguna pemula yang membutuhkan penjelasan istilah, sumber data, dan risiko.
- Pengguna aktif yang ingin memantau watchlist, perubahan sinyal, dan riwayat strategi.

### Hasil pengguna yang harus tercapai

1. Mengetahui apakah harga dan analisis merupakan data nyata, data lama, demo, atau belum tersedia.
2. Mencari saham, menjalankan analisis, dan membaca hasil beserta waktu serta dasar analisisnya.
3. Menjalankan backtest dengan parameter yang benar-benar digunakan dan hasil yang bisa dijelaskan.
4. Menyimpan saham untuk dipantau tanpa harus mengingat kode lengkap.
5. Memahami sisa kuota, status sesi, dan tindakan yang tersedia ketika terjadi kegagalan.
6. Pada fase lanjutan, menerima alert EOD, menyaring saham pada cakupan data yang jelas, membandingkan riwayat analisis, dan menyimpan rencana transaksi dengan asumsi risiko yang terbuka.

## 2. Dasar temuan dan batas bukti

Sumber utama revisi adalah [review 19 Oktober](review_pengguna_2026-10-19.md) yang diberikan pengguna, lalu dicocokkan dengan source `541c281` dan [laporan R1](implementasi_r1.md). Review menggunakan SQLite terisolasi dan browser desktop/390 × 844 pada `42d887a`; reproduksi crash backtest memakai respons terkontrol sesuai kontrak mesin saat itu. Screenshot dan JSON review tidak dilampirkan, sehingga tidak dinyatakan sudah ditinjau pada revisi ini.

Baseline lama memiliki 47 test backend lulus. Laporan R1 mencatat 79 lulus pada masing-masing SQLite/PostgreSQL, 11 pemeriksaan browser dengan provider fixture pada desktop/360px, serta build/lint lulus. Angka tersebut adalah hasil implementasi sebelumnya, bukan pengujian baru saat menulis PRD; tidak membuktikan akses provider, deployment eksternal, atau audit penuh 390 × 844.

### 2.1 Temuan pada baseline 42d887a

Tabel berikut merupakan kondisi historis, bukan pernyataan bahwa semua cacat masih ada pada branch `work`.

| Area | Kondisi yang ditemukan | Dampak |
|---|---|---|
| Data detail saham | Kegagalan API memicu grafik acak dan BULLISH 88%; penanda mock hanya berada di ringkasan | Harga dan sinyal contoh dapat disalahartikan sebagai hasil nyata |
| Dashboard/watchlist | Tersedia fallback harga/perubahan statis; saham AS juga diberi Rp; fallback dua candle pada watchlist memakai urutan terbalik | Nilai, mata uang, atau arah perubahan dapat salah |
| Analisis manual | Tombol analisis ulang hanya memanggil sinkronisasi; endpoint pemanggil AI terpisah | Pesan sukses tidak membuktikan AI dijalankan |
| Hasil AI | Ringkasan disimpan sebagai teks tetap; kegagalan provider dapat menjadi payload HOLD; cache tidak memuat revisi model/prompt/data | Hasil gagal atau kedaluwarsa dapat terlihat sah |
| Rekomendasi | Backend memakai BUY/HOLD/WAIT; dashboard menyaring BULLISH/STRONG BUY | Rekomendasi BUY yang valid tidak muncul |
| Backtest | Nama input berbeda, output recent_trades/trades berbeda, dan persentase dikalikan ulang | Parameter diabaikan dan hasil dapat salah atau gagal ditampilkan |
| Metodologi backtest | Drawdown adalah transaksi terburuk; sebagian deteksi swing menggunakan jendela yang melihat bar berikutnya | Risiko dan performa historis dapat dinilai keliru |
| Chart | Pilihan intraday memakai candle harian; jumlah bar belum mengikuti rentang | Pengguna membaca tingkat detail atau cakupan waktu yang salah |
| Akun/kuota | UI membutuhkan analysis_quota_used, tetapi profil API belum mengembalikannya; terdapat beberapa implementasi auth/logout | Kuota dan perilaku sesi tidak konsisten |
| Distribusi aplikasi | Build frontend terhenti pada tipe lineWidth 1.5 | Rilis produksi belum dapat dibangun |

Koreksi temuan terdahulu: halaman login utama memakai src/api/auth.ts dan mengirim JSON yang sesuai backend. Helper login berbentuk form pada src/services/auth.ts tidak membuktikan halaman login utama gagal. Alur login harus diuji melalui browser, bukan ditandai rusak berdasarkan helper tersebut.

### 2.2 Status setiap temuan setelah R1

**Diimplementasikan** berarti perbaikan tersedia pada kode dan memiliki bukti lokal yang dirujuk; tidak berarti sudah dirilis. **Sebagian** berarti masih ada kebutuhan atau audit yang belum selesai. **Belum diverifikasi** berarti memerlukan pengujian nyata/staging. Prioritas pada kolom kedua mengikuti review asli; prioritas backlog berikutnya mengikuti dampak pekerjaan yang tersisa.

| ID review | Prioritas asli | Temuan | Status pada 541c281 dan tindak lanjut |
|---|---|---|---|
| U01 | P0 | Chart/sinyal palsu dan harga hardcoded | Diimplementasikan: fallback normal dihapus, data kosong/gagal dibedakan, chart valid dipertahankan. Ulangi skenario `INVALIDXYZ` pada staging melalui B12; demo eksplisit belum menjadi fitur. |
| U02 | P0 | Tombol AI hanya menyinkronkan harga | Diimplementasikan: sync → AI → baca hasil tersimpan, pesan tahap/gagal. Eksekusi provider nyata belum diverifikasi; B16. |
| U03 | P0 | TP/SL diabaikan, trades crash, persen dikalikan ulang | Diimplementasikan: schema request/response, validasi satuan, parameter efektif, seluruh trades, tanpa perkalian ulang. Regresi kontrak tetap wajib pada B12. |
| U04 | P0 | Target +5%, risiko MEDIUM, confidence 70 buatan | Diimplementasikan: nilai pengganti dihapus; hasil aktual tervalidasi. Rencana transaksi baru hanya melalui FR-14/B19. |
| U05 | P1 | Saham AS diberi Rp | Diimplementasikan: format memakai currency instrumen. Verifikasi satu IDX dan satu AS lintas halaman dengan data nyata melalui B16/B12. |
| U06 | P1 | Interval/rentang chart tidak sesuai data | Sebagian: hanya candle harian 1M/3M/6M/1Y, rentang aktual ditampilkan dan batas 100 bar dihapus. Pembuktian cakupan histori/warm-up indikator dan sentuhan mobile tersisa pada B07/B11. |
| U07 | P1 | Kuota di settings kosong | Diimplementasikan: terpakai/tersisa/reservasi/reset WIB dari API. Penyempurnaan bahasa Free/Premium dan onboarding pada B09b/B20. |
| U08 | P1 | Login mengunci localhost | Diimplementasikan: client/base URL bersama dan proxy same-origin. Deployment lintas origin/host belum diverifikasi; B12. |
| U09 | P1 | Logout sidebar tidak mencabut refresh token | Diimplementasikan: logout bersama, sesi access/refresh dapat dicabut; fixture browser/API memeriksa penolakan token lama. Pertahankan regresi dua pintu logout pada B12. |
| U10 | P2 | Label, toggle password, tombol ikon tidak aksesibel | Sebagian: htmlFor/id, nama/pressed toggle, nama tombol header, dan browser berbasis label sudah tersedia. Audit keyboard, fokus, pesan error, dan screen reader menyeluruh tersisa pada B11. |
| U11 | P2 | Target sentuh rapat dan metadata perusahaan generik | Sebagian: rentang memakai tombol baru dan nama tidak bergantung hasil AI. Ukuran target, jarak, 390 × 844, serta nama saat quote gagal masih perlu dituntaskan pada B07/B11. |
| U12 | P2 | Notifikasi/badge statis | Diimplementasikan: klaim sukses/badge buatan dihapus; panel kosong dijelaskan. Alert dari kejadian nyata adalah pekerjaan B13, bukan notifikasi yang sudah tersedia. |

### 2.3 Status usulan fitur

| Usulan review | Sudah tersedia | Sisa pekerjaan dan acuan |
|---|---|---|
| Transparansi data | Sumber, tanggal penutupan, waktu fetch, currency, revisi, waktu analisis | Kalender/status pasar dan label delay berdasarkan kemampuan provider; FR-01/B16. `unknown` tetap dipakai bila belum dapat ditentukan. |
| Watchlist harian | Dialog pencarian, notes editable, sort kode/perubahan, refresh | Sort harga, filter bursa, status sudah ditambahkan; FR-09/B08. |
| Alert harga/sinyal | Belum ada engine alert | Alert EOD harga/persen/sinyal, preferensi, deduplikasi, tautan; FR-11/B13. |
| Rencana transaksi | Belum ada | Entry, stop, target, reward/risk, horizon, pembatalan, modal/lot; FR-14/B19. |
| Screener | Pencarian dan BUY picks seluruh instrumen aktif | Filter terstruktur seluruh cakupan tersinkron, simpan filter; FR-15/B17. Picks bukan screener lengkap atau cakupan seluruh IDX. |
| Riwayat analisis | Record AI menyimpan waktu/model/prompt/revisi | Daftar berhalaman, perbandingan, CSV dan PDF bertahap; FR-16/B18. |
| Backtest dapat dinilai | Kontrak, semua transaksi, equity curve, drawdown kausal | Fee/slippage, lot/modal, benchmark, simpan run/ekspor; FR-13/B15. |
| Akun/onboarding | Register/login dan kuota lokal sudah diuji pada R1 | Reset/ubah password, edit profil, glosarium .JK/indikator, penjelasan paket; FR-12/B14/B20. Pembayaran belum diuji atau direncanakan untuk fase inti. |

Akses provider pasar/AI nyata masih belum terverifikasi. [Kajian alternatif](alternatif_integrasi.md) memprioritaskan pengujian Gemini serta perbandingan EODHD/Sectors. Adapter opsional Gemini/EODHD kemudian diimplementasikan sesuai [laporan pelaksanaan](implementasi_prd_20261019.md); default provider tidak otomatis diganti dan penerimaan nyata masih terbuka. Gangguan izin jaringan atau kredensial dipisahkan dari cacat aplikasi. Pengujian browser lokal tidak membuktikan workflow CI remote dan staging berhasil.

## 3. Prioritas dan ruang lingkup

| Prioritas | Makna | Cakupan |
|---|---|---|
| P0 | Penghambat rilis inti: informasi salah, fungsi utama rusak, atau artefak rilis gagal | Integritas data, hasil AI, kontrak dan metodologi minimum backtest, build serta regresi |
| P1 | Wajib pada paket pengalaman penggunaan yang dipilih | Chart/pencarian/watchlist, sesi/kuota, job, aksesibilitas, alert EOD, screener dan riwayat secara bertahap |
| P2 | Pengembangan setelah stabilitas inti terukur | Email alert/PDF, personalisasi, pemulihan akun, rencana transaksi dan realisme backtest tambahan |

Termasuk: perbaikan frontend Next.js dan backend FastAPI yang sudah ada, kontrak API, metadata, migrasi, pengujian, observabilitas, dan fitur lanjutan yang dipilih menurut tahap di bagian 9. Aksesibilitas alur utama menjadi syarat P1 rilis berikutnya meskipun review awal menempatkannya pada P2.

Di luar rilis inti: eksekusi transaksi broker, prediksi keuntungan terjamin, aplikasi mobile native, analisis berita/sentimen, fundamental lengkap, pembayaran premium, dan portofolio transaksi nyata. Rencana transaksi merupakan catatan/simulasi, bukan order broker. Intraday tidak ditampilkan sebagai fitur aktif sebelum sumber dan implementasinya tersedia. PDF menyusul setelah CSV; email alert menyusul setelah in-app alert dan layanan pengirim tersedia.

## 4. Prinsip perilaku produk

- Data yang tidak ada ditampilkan sebagai tidak tersedia, bukan angka nol atau angka buatan.
- Data nyata terakhir boleh ditampilkan saat gagal refresh, dengan tanggal dan status yang jelas.
- Mode demo harus dipilih secara eksplisit dan diberi label pada seluruh harga, grafik, analisis, dan hasil backtest. Demo tidak mengurangi kuota atau bercampur dengan hasil nyata.
- Harga harian diberi label penutupan/EOD; istilah real-time hanya digunakan jika sumber memang mendukungnya.
- Pada R1, pilihan 1H/intraday yang masih memakai data harian dihapus atau dinonaktifkan; penyempurnaan rentang chart mengikuti R2.
- Confidence adalah skor model, bukan probabilitas keuntungan yang sudah terkalibrasi.
- Target, stop loss, risiko, dan fundamental hanya muncul jika memiliki dasar serta metode yang tersedia. Jika belum, tampilkan belum tersedia.
- Pesan berhasil hanya muncul setelah operasi yang disebut benar-benar selesai dan hasilnya tersimpan.

## 5. Alur utama yang dituju

### 5.1 Masuk dan menemukan saham

Pengguna mendaftar atau masuk, melihat dashboard dengan status data, lalu mencari kode atau nama perusahaan. Enter dan klik hasil memilih instrumen yang sama. Ticker ambigu menampilkan pilihan bursa; ticker tidak dikenal menampilkan keadaan tidak ditemukan tanpa grafik demo otomatis.

### 5.2 Menjalankan analisis

Detail menampilkan data terakhir dan waktu analisis. Pengguna menekan Analisis Ulang AI, melihat tahapan mengambil data, menghitung indikator, menjalankan AI, lalu menyimpan hasil. Hasil baru baru ditandai berhasil setelah dapat dibaca kembali. Bila gagal, hasil terakhir tetap tersedia dengan pesan gagal pembaruan dan opsi coba lagi.

### 5.3 Menjalankan backtest

Pengguna memilih periode, target profit, dan stop loss; aplikasi mengirim parameter yang tervalidasi. Hasil menampilkan parameter efektif, rentang data aktual, asumsi simulasi, statistik, serta transaksi. Tidak ada transaksi merupakan hasil valid. Provider gagal atau histori tidak cukup merupakan kegagalan yang dijelaskan, bukan statistik nol yang menyerupai keberhasilan.

### 5.4 Memantau harian

Pengguna menambah saham dari pencarian, menyimpan catatan, dan mengurutkan watchlist. Harga dan perubahan mempunyai sumber, mata uang, serta waktu. Pada tahap lanjutan pengguna dapat membuat alert dengan kondisi yang terukur.

### 5.5 Riset lanjutan dan rencana transaksi

Pengguna membuka screener, memilih cakupan/filter, lalu menuju detail saham. Ia membandingkan analisis bertanggal, menyimpan rencana entry/stop/target dengan modal dan risiko, serta memasang alert EOD bila data memenuhi kebijakan keterkinian. Rencana menampilkan sumber setiap angka dan tetap dapat dibaca saat AI gagal; tidak membuat atau mengirim order broker.

## 6. Persyaratan dan kriteria penerimaan

### E1 — Integritas harga dan status data

**FR-01 · P0 · Data pasar yang dapat ditelusuri**

Sebagai pengguna, saya ingin membedakan data nyata, lama, demo, kosong, dan gagal.

- Seluruh fallback harga, persentase, confidence, target, dan grafik buatan dihapus dari mode normal.
- Respons harga/chart menyertakan source, currency, exchange, fetched_at, market_as_of, interval, data_revision, dan data_state. Waktu data pasar berbeda dari waktu request.
- data_state menggunakan fresh/stale/unavailable/demo/unknown; status refresh dipisahkan agar data terakhir tetap dapat dibaca ketika pembaruan gagal. Timestamp memakai ISO 8601 berzona UTC pada API dan waktu bursa/pengguna yang dilabeli pada UI.
- Nilai hilang menggunakan null dengan alasan yang dapat ditampilkan; nol yang valid tetap ditampilkan sebagai nol.
- Harga terakhir tetap disimpan ketika pembaruan gagal. Error satu bagian dashboard tidak menghentikan bagian lain.
- Stale ditentukan menurut jadwal rilis data dan kalender bursa instrumen, termasuk hari libur/akhir pekan; jika status belum dapat ditentukan, gunakan unknown.
- Mata uang mengikuti instrumen: IDR dan USD tidak dikonversi atau diberi simbol yang salah.
- Pisahkan waktu sesi pasar, waktu publikasi provider bila tersedia, dan waktu fetch. Status open/closed mengikuti kalender serta zona bursa; label delayed atau besaran delay hanya ditampilkan bila diketahui dari provider. EOD tidak disebut real-time, dan delay yang tidak diketahui tidak ditebak.
- Nama, ticker, bursa, serta currency berasal dari metadata instrumen yang bisa dimuat tanpa keberhasilan chart/AI. Nama yang belum tersedia diberi status belum tersedia, bukan nama perusahaan buatan; kegagalan quote tidak menghapus metadata yang sudah valid.
- Perubahan dua candle dihitung dari candle terbaru terhadap candle sebelumnya. Harga 10.000 menjadi 10.100 menghasilkan +1%, dengan urutan kronologis konsisten.
- Notifikasi sinkronisasi hanya muncul dari kejadian nyata; jika belum ada riwayat, panel menyatakan belum ada notifikasi.

**Penerimaan:** ketika market API dipaksa 403, timeout, kosong, dan 500, tidak muncul data sintetis tanpa label; status gagal terlihat dan data asli terakhir tidak tertimpa.

### E2 — Analisis AI yang benar dan dapat dijelaskan

**FR-02 · P0 · Jalankan proses yang dijanjikan**

- Pada rilis inti, frontend boleh mengorkestrasi endpoint sinkronisasi lalu endpoint AI yang sudah ada secara berurutan. Mengganti label tombol saja tidak menyelesaikan kebutuhan ini.
- Endpoint sinkronisasi yang menulis data dan endpoint AI wajib terautentikasi, diotorisasi sesuai kebijakan tier, serta dibatasi per pengguna. Default R1: pengguna free dan premium boleh menyinkronkan instrumen valid; AI free mengikuti tiga eksekusi baru berhasil per hari.
- AI dijalankan hanya dengan data/indikator yang cukup. Kegagalan sinkronisasi menghentikan proses baru dan menjelaskan tahap yang gagal.
- Timeout, respons model tidak valid, kunci kosong, dan kegagalan provider tidak disimpan sebagai hasil AI nyata berstatus berhasil atau HOLD otomatis.
- Ringkasan aktual disimpan bersama ticker, waktu data, waktu pembuatan, provider/model, versi prompt, revisi data, dan mode real/demo.
- Setelah berhasil, baca ulang hasil tersimpan; chart/latest-analysis yang di-cache diperbarui atau diinvalidasi. Cache hit harus menunjuk hasil valid yang dapat dibaca, bukan sekadar respons provider.
- Cache AI, jika digunakan, membedakan ticker, revisi data, provider/model aktual, versi prompt, dan mode. Perubahan input tidak menggunakan hasil lama secara diam-diam; penambahan identitas provider lintas adapter dituntaskan pada B16.

**Penerimaan:** sinkronisasi berhasil tetapi AI timeout menghasilkan status gagal AI, tanpa toast sukses analisis dan tanpa menimpa hasil valid terakhir. Percobaan berhasil berikutnya menampilkan hasil baru tanpa menunggu TTL cache.

**FR-03 · P0 · Kontrak rekomendasi dan laporan**

- Nilai kanonik adalah BUY, HOLD, WAIT; tidak ada rekomendasi merupakan null, bukan HOLD.
- Confidence pada API/UI memakai skala 0–100; respons model 0–1 dikonversi tepat sekali dan divalidasi sebelum disimpan.
- Dashboard memasukkan BUY yang valid dari seluruh cakupan daftar rekomendasi, bukan hanya enam kartu market pertama.
- Laporan berisi ringkasan, faktor pendukung, faktor penyangkal, horizon, keterbatasan, serta tanggal data. Hasil tidak menjanjikan fundamental jika input hanya teknikal.
- Target +5%, risiko MEDIUM, confidence 70%, dan teks ringkasan tetap tidak dipakai sebagai pengganti hasil yang belum tersedia.

**Penerimaan:** fixture BUY dengan confidence 0,88 dari model menjadi BUY 88% pada database/API/UI. Confidence 0 tetap 0, dan confidence tidak ada ditampilkan belum tersedia.

**FR-04 · P1 · Proses asinkron yang tahan pengulangan**

- Setelah alur inti benar, pindahkan proses lama ke job dengan status queued, syncing, calculating, analyzing, persisting, succeeded, failed.
- Job tersimpan dan hanya dapat dibaca oleh pengguna yang berhak; tidak mengandalkan proses browser tetap terbuka.
- Klik ganda dengan idempotency key yang sama mengembalikan job yang sama. Retry kegagalan tidak menggandakan hasil atau tagihan kuota.
- Broker/worker dikonfigurasi melalui environment; jangan mengandalkan broker SQLite yang dilacak Git sebagai antrean produksi.
- Worker restart, provider rate limit, dan job kedaluwarsa mempunyai batas retry, timeout, serta jalur pemulihan yang diuji.

### E3 — Backtest yang konsisten dan jujur

**FR-05 · P0 · Satu kontrak parameter dan hasil**

- Input kanonik: years 1–5, target_profit_pct >0 hingga 20, stop_loss_pct >0 hingga 10. Satuan adalah persen: 10 berarti 10%, dikonversi menjadi 0,10 sekali di mesin.
- Respons menyertakan period_years, requested_parameters, effective_parameters, data_start, data_end, assumptions, total_trades, win_rate_pct, avg_profit_pct, max_drawdown_pct, dan trades.
- Seluruh nilai berakhiran pct memakai skala persen. Win 3 dari 4 = 75%; harga 100 ke 110 = profit 10%, tanpa perkalian ulang di UI.
- Seluruh transaksi dapat diakses; R1 boleh mengembalikan seluruh transaksi sekaligus. Gunakan pagination bila volumenya memerlukan; jangan membatasi hasil ke sepuluh transaksi terakhir tanpa penjelasan.
- Status transaksi kanonik WIN/LOSS/BREAKEVEN dipisahkan dari exit_reason seperti TAKE_PROFIT, STOP_LOSS, TIMEOUT, END_OF_PERIOD.
- Field tak dikenal ditolak 422. Dukungan input legacy target_profit/stop_loss dalam desimal harus melalui adapter eksplisit; jangan menebak satuan dari nilainya. Payload campuran legacy/kanonik ditolak.

**Penerimaan:** input target 10% dan stop 5% diterima mesin sebagai 0,10 dan 0,05 serta tercantum kembali pada hasil. Empty trades dapat dirender; payload tidak cocok gagal dengan pesan validasi yang jelas.

**FR-06 · P0 · Metodologi minimum sebelum hasil dipercaya**

- Sinyal pada waktu T hanya memakai data yang sudah tersedia pada T. Swing yang membutuhkan bar sesudah T baru tersedia setelah masa konfirmasi; audit semua indikator/pola yang dipakai simulasi.
- Baseline strategi memakai keputusan setelah penutupan T dan entry pada open sesi berikutnya. TP/SL dievaluasi pada setiap close sejak sesi entry; keputusan exit dieksekusi pada open sesi berikutnya dengan harga open aktual, termasuk gap. TP/SL bukan jaminan harga eksekusi intraday. Aturan ini ditampilkan.
- Posisi ditutup pada open berikutnya jika sudah melewati 30 sesi sejak entry tanpa exit lain; timeout dihitung dari sesi perdagangan, termasuk sesi entry. Tidak ada re-entry pada sesi exit.
- Gunakan satu posisi per instrumen dengan ekuitas awal ternormalisasi 100 dan alokasi 100%; tandai bahwa ukuran lot/likuiditas belum dimodelkan. Definisikan harga tersesuaikan atau tidak secara konsisten untuk split/dividen.
- Equity curve ditandai ke harga pasar pada setiap sesi. Drawdown = (puncak ekuitas sebelumnya - ekuitas saat ini) / puncak ekuitas; nilai maksimum ditampilkan positif. Ekuitas 100 → 120 → 90 mempunyai max drawdown 25%.
- Posisi terbuka pada akhir periode ditutup pada close terakhir dengan alasan END_OF_PERIOD dan dicatat; tidak dihilangkan dari evaluasi.
- Return gagal-data, histori kurang, atau indikator belum cukup dibedakan dari simulasi valid tanpa transaksi.
- Pada rilis inti, biaya/slippage yang belum dimodelkan harus dinyatakan sebagai asumsi 0, bukan diklaim sebagai return bersih.
- Label hasil menyatakan backtest strategi teknikal. Hasil ini bukan evaluasi historis keputusan AI karena keputusan tersebut belum direkam sebagai sinyal yang dapat diuji.

**Penerimaan:** pengujian kausalitas memotong data pada T dan memastikan sinyal sebelum/di T tidak berubah ketika bar masa depan ditambahkan. Fixture equity, split, gap, tanpa transaksi, dan posisi akhir menghasilkan perhitungan sesuai definisi.

### E4 — Chart, pencarian, dan dashboard

**FR-07 · P1 · Periode dan interval yang sesuai**

- Pisahkan rentang tampilan dari interval candle. Baseline hanya interval harian dengan rentang 1M/3M/6M/1Y; pilihan 1H/intraday dinonaktifkan atau dihilangkan.
- Pengambilan data mengikuti rentang, bukan batas 100 bar tetap. Bila histori kurang, tampilkan rentang aktual tanpa membuat bar tambahan.
- Perhitungan EMA 200 memakai bar pemanasan di luar rentang tampilan bila diperlukan; nilai belum cukup tetap null.
- Chart menyediakan legenda, waktu data, satuan harga, serta keadaan loading/error/empty yang berbeda.
- Pada 360px, 390 × 844, dan 1440px, kontrol rentang serta aksi utama mempunyai target sentuh minimal 44 × 44 CSS px, jarak antarkontrol minimal 8px, fokus terlihat, dan tidak menimbulkan overflow halaman. Tidak menjadikan teks label besar sebagai pengganti area tombol yang bisa disentuh.

**FR-08 · P1 · Menemukan instrumen dan peluang**

- Cari kode atau nama dengan autocomplete; Enter memilih hasil yang dipilih atau membuka daftar hasil, bukan menganggap nama perusahaan sebagai ticker.
- Hasil menampilkan nama, ticker, bursa, dan currency. Respons pencarian lama tidak menimpa query terbaru.
- Dashboard memakai total dari pagination metadata, menyediakan daftar berhalaman, dan memisahkan belum ada rekomendasi dari gagal memuat rekomendasi.
- BUY/HOLD/WAIT dan dasar pemeringkatan konsisten; skor model tidak dipasarkan sebagai probabilitas profit.

**Penerimaan:** ticker tidak dikenal tidak membuka rekomendasi demo; total 25 saham tetap 25 ketika halaman hanya memuat enam.

### E5 — Watchlist dan akun

**FR-09 · P1 · Watchlist untuk pekerjaan harian**

- Ganti window.prompt dengan dialog pencarian dan validasi; pengguna memilih instrumen terdaftar yang sesuai.
- Tambah/hapus, catatan pribadi yang dapat diedit, sort nama/perubahan, dan refresh manual tersedia. Catatan disimpan per pemilik, bukan teks tetap.
- Cegah duplikasi; kegagalan tidak menghapus item. Tampilkan data terakhir beserta status dan waktu.
- Pengguna A tidak dapat membaca/mengubah watchlist atau catatan pengguna B.
- Tambahkan filter bursa dan sort harga/perubahan naik/turun, dengan nilai null di akhir. Sort harga nominal tidak mencampur IDR/USD sebagai perbandingan ekonomis: pengguna memilih satu currency/bursa dahulu, atau tampilan mengelompokkan currency tanpa konversi diam-diam.
- Hasil pencarian dan detail menunjukkan status Sudah ditambahkan untuk item yang ada; tombol tambah tidak menghasilkan duplikasi saat klik ganda. Perubahan notes/filter/sort tetap jelas setelah refresh dan kegagalan sebagian harga.

**Penerimaan lanjutan:** pengguna memfilter IDX, mengurutkan perubahan, mengedit notes, lalu reload tanpa kehilangan catatan. Memilih saham yang sudah ada menunjukkan status tersebut. Harga tanpa data berada di akhir dan saham AS tetap USD.

**FR-10 · P1 · Kuota dan sesi konsisten**

- Satukan client/config auth agar login/register/profil/logout/refresh memakai alamat API yang dikonfigurasi; pertahankan login JSON yang sudah benar.
- Semua tombol logout mengirim refresh token yang diperlukan, mencabut sesi terkait, dan membersihkan state/cookie secara konsisten.
- Refresh token baru mempunyai identitas unik; token lama tidak dapat dipakai ulang, termasuk rotasi dalam detik yang sama dan request bersamaan.
- Refresh hanya dijalankan sekali untuk kumpulan request 401; seluruh request menunggu atau gagal secara terbatas, tanpa antrean menggantung.
- Profil API mengembalikan quota_limit, quota_used, quota_remaining, quota_reset_at, serta tier. Premium menggunakan limit null dengan label tidak terbatas.
- Kuota harian reset pukul 00.00 Asia/Jakarta. Kuota yang ditampilkan sudah memperhitungkan pergantian hari, bukan menunggu analisis baru.
- Kuota direservasi secara atomik untuk eksekusi baru; berhasil nyata dan tersimpan mengonsumsi satu, gagal melepas reservasi, cache hit/demo tidak mengonsumsi. Tidak boleh melampaui batas pada request bersamaan.

**Penerimaan:** free hanya mendapat tiga eksekusi baru berhasil per hari, termasuk saat dua request datang pada sisa satu kuota. UI dan API menunjukkan angka yang sama; refresh dan logout diuji pada desktop/mobile.

Pengendalian kuota, autentikasi endpoint, konfigurasi base URL, serta kebenaran refresh/logout adalah dependensi P0 untuk R1. Penyempurnaan tampilan kuota/profil ada di P1; otorisasi job dituntaskan saat R2 menambahkan job.

### E6 — Fitur setelah stabil

**FR-11 · P1 untuk paket pemantauan · Alert EOD yang nyata**

- Mulai dengan in-app alert milik pengguna: harga close menembus ambang, perubahan persen terhadap close sesi sebelumnya, atau transisi BUY/HOLD/WAIT pada hasil AI nyata yang baru tersimpan.
- Arah naik/turun, ambang, basis perubahan, ticker, status aktif, dan perilaku setelah trigger terlihat sebelum disimpan. Baseline berupa alert berulang saat terjadi transisi baru; kondisi yang terus terpenuhi tidak memicu ulang setiap polling.
- Evaluasi hanya untuk revisi/sesi baru yang lolos kebijakan kelengkapan dan keterkinian. Data stale/demo/unavailable/unknown tidak memicu alert; analisis lama yang tidak cocok dengan revisi harga juga tidak.
- Event menyimpan jenis, nilai pemicu, waktu pasar, waktu evaluasi, sumber/revisi dan tautan saham. Kunci unik berdasarkan alert dan kejadian pasar mencegah duplikasi ketika worker retry/restart.
- Pengguna dapat menjeda/menghapus alert dan menandai notifikasi dibaca; badge berasal dari event belum dibaca. Preferensi bersifat privat. Email dan intraday tetap di luar paket awal.

**Penerimaan:** close 100 → 110 melintasi ambang naik 105 menghasilkan satu event; evaluasi ulang sesi/revisi yang sama tetap satu. Jika harga turun di bawah ambang lalu melintasi kembali pada sesi baru, satu event baru boleh dibuat. Data stale dan hasil HOLD buatan tidak memicu event.

**FR-12 · P2 · Pemulihan akun dan personalisasi**

- Edit nama/preferensi, ubah password dengan verifikasi password lama, serta lupa password dengan provider email yang dikonfigurasi. Token reset sekali pakai, ber-expiry, dan tidak dicatat pada log; pesan permintaan reset tidak membocorkan keberadaan akun.
- Setelah reset password, cabut sesi lama sesuai kebijakan yang ditampilkan; baseline mencabut seluruh sesi dan meminta login ulang. Uji token kedaluwarsa, replay, dua akun, rate limit, serta kegagalan pengiriman tanpa pesan sukses yang keliru.
- Onboarding ringan berbahasa Indonesia mengenalkan `.JK`, IDX/AS, EOD, sumber/waktu, BUY/HOLD/WAIT, confidence, dan arti indikator. Glosarium dapat dibuka kembali tanpa menghalangi alur utama.
- Halaman Free/Premium menjelaskan hak akses dan kuota yang benar-benar diterapkan server. Jangan menampilkan checkout/upgrade seolah aktif sebelum alur pembayaran, entitlement, dan penanganan gagal tersedia. Monetisasi membutuhkan PRD terpisah bila dipilih.

Konsistensi bahasa/glosarium dan penjelasan tier masuk B11/B20/P1. Reset password/edit profil masuk B14/P2 dan tidak menjadi dependensi perubahan UI yang bisa dikerjakan lebih dahulu.

**FR-13 · P2 · Simulasi lebih realistis**

- Fee beli/jual dan slippage masing-masing dikonfigurasi dalam basis poin; 10 bps = 0,1%. Tampilkan parameter efektif, modal awal, aturan lot, uang kas tidak terpakai, gross/net return, dan total biaya. Validasi seluruh nilai finite/nonnegatif dengan batas API yang terdokumentasi.
- Slippage yang merugikan diterapkan ke harga eksekusi beli/jual; fee dihitung atas nilai transaksi masing-masing. Tidak mengurangkan biaya yang sama dua kali. Drawdown dihitung dari equity curve setelah biaya, dengan mark-to-market dan biaya kas yang konsisten.
- Benchmark buy-and-hold memakai modal, tanggal entry/akhir, currency, adjustment, fee/slippage dan lot yang sama. Tampilkan jumlah bar/transaksi, rentang aktual, serta alasan bila histori tidak cukup untuk periode yang diminta. Jangan menghitung dividen lagi jika basis total-return sudah memasukkannya.
- Simpan run yang selesai beserta parameter, versi strategi, data revision, asumsi, trades dan equity curve. Ekspor CSV mencakup seluruh transaksi/metadata; run milik pengguna tidak dapat dibaca akun lain.
- Pertahankan kausalitas dan aturan eksekusi FR-06. Eksekusi intraday tidak disimpulkan dari candle harian.

**Penerimaan:** fixture beli 100 dan jual 110, satu lembar, fee 10 bps per sisi dan slippage 0 menghasilkan biaya 0,21 serta laba bersih 9,79; profit terhadap harga beli awal adalah 9,79%. Return terhadap modal total yang benar-benar dikeluarkan memakai denominator termasuk fee dan diberi nama berbeda. Fixture lain memeriksa lot, gap, sisa kas, nol transaksi, benchmark, dan equity drawdown setelah biaya.

### E7 — Rencana transaksi

**FR-14 · P2 · Rencana yang dapat dihitung dan ditinjau**

- Pengguna dapat menyimpan rencana long berisi ticker, area entry, harga entry perhitungan yang dipilih dalam area tersebut, stop, target, horizon, alasan, kondisi pembatalan, waktu/data revision, modal dan batas risiko per rencana. Posisi short dan eksekusi broker di luar versi pertama.
- Setiap angka diberi asal: input pengguna atau aturan yang versi/metodenya tersedia. Saran AI boleh mengisi draft hanya jika tervalidasi dan tetap ditinjau pengguna. Target, stop, horizon, atau label risiko tidak diisi angka tetap untuk menutup data kosong.
- Wajib `0 < stop < entry < target`; basis nominal memakai currency instrumen. Rasio reward/risk sebelum biaya = `(target - entry) / (entry - stop)` dan ditampilkan bersama asumsi biaya; bukan peluang menang.
- Kalkulator membatasi jumlah lembar oleh modal tersedia dan nilai risiko yang dipilih, lalu membulatkan ke lot bursa. Baseline IDX 100 lembar/lot; aturan AS mengikuti metadata, tanpa menganggap fractional share selalu didukung. Jika lot/currency tidak diketahui atau modal berbeda currency, minta parameter yang sah; jangan mengonversi diam-diam.
- Biaya/slippage yang dikonfigurasi mengurangi daya beli dan menambah estimasi risiko. Entry/stop tidak menjamin harga eksekusi; gap dan likuiditas dapat meningkatkan kerugian. Rencana lama yang input datanya berubah tetap tersimpan dan ditandai perlu ditinjau.
- Rencana dan catatan hanya dapat dibaca/diubah pemilik. Mengedit rencana menyimpan versi; menyimpan rencana tidak mengeksekusi transaksi atau mengonsumsi kuota AI.

**Penerimaan:** modal Rp10.000.000, batas risiko 1%, entry 1.000, stop 950, target 1.100, lot 100 dan biaya 0 menghasilkan rasio 2:1, maksimal 2.000 lembar/20 lot, nilai beli Rp2.000.000 dan risiko harga Rp100.000. Input tidak valid ditolak; biaya, modal tidak cukup, serta beda currency diuji terpisah.

### E8 — Screener dan riwayat riset

**FR-15 · P1 · Screener pada cakupan data yang jelas**

- Filter bursa, sektor, volume, rentang RSI, fase Wyckoff dan pola SMC memakai schema eksplisit, nilai kanonik dan semantik AND antarfilter. Null tidak otomatis menjadi nol atau cocok; pengguna dapat memilih filter data belum tersedia secara terpisah.
- Pencarian/filter/pagination/sort dilakukan server pada seluruh instrumen aktif dalam cakupan tersinkron, bukan enam kartu dashboard atau satu halaman. Tampilkan jumlah total cakupan, jumlah dengan data valid, hasil cocok, tanggal data dan kriteria sortir. Jangan menyebutnya seluruh IDX bila universe belum lengkap.
- Volume harus mempunyai satuan; batas volume harian memakai lembar saham, dan nilai null tetap dibedakan. Sort berbasis harga mengikuti aturan currency FR-09. Jangan menggabungkan indikator dengan tanggal tidak selaras sebagai satu sinyal terbaru.
- Simpan nama dan konfigurasi filter per pengguna; reload atau membuka tautan hasil tidak mengubah kriterianya. Validasi ulang saved filter ketika versi schema berubah. Preset ditampilkan sebagai contoh kriteria, bukan rekomendasi keuntungan.
- Bagian pertama: bursa/sektor/volume/RSI dan simpan filter. Filter Wyckoff/SMC menyusul setelah pemetaan pola serta revisi indikator tervalidasi; kontrol yang belum didukung tidak ditampilkan sebagai aktif.

**Penerimaan:** dataset terkontrol 25 saham dengan halaman enam item menghasilkan jumlah cocok dan pagination yang sama dengan query seluruh dataset. Saham cocok pada halaman akhir tetap ditemukan, filter tersimpan tetap sama setelah login ulang, dan data null/tanggal tidak cocok dijelaskan. Target performa mengikuti bagian 8.

**FR-16 · P1 · Riwayat analisis dan perbandingan**

- Daftar analisis per ticker berhalaman memuat waktu data, waktu dibuat beserta zona, provider/model aktual, versi prompt, data revision, rekomendasi dan confidence. Cache hit menunjuk record yang sama, bukan membuat histori eksekusi model baru.
- Bandingkan dua hasil tersimpan: perubahan rekomendasi, confidence dalam poin persentase, faktor pendukung/penyangkal dan keterbatasan. Tandai perbedaan revisi data/model/prompt; perbandingan tidak menyiratkan penyebab perubahan atau kalibrasi profit.
- Default hasil pasar umum dapat dibaca pengguna terautentikasi sesuai kebijakan aplikasi; identitas akun pemicu, catatan dan rencana pribadi tidak ikut respons. Bila kelak ada input/prompt privat, hasil tersebut wajib dipisahkan dan diotorisasi sebelum fitur dirilis.
- Data lama tanpa provenance yang dapat dibuktikan ditandai unknown dan tidak masuk rekomendasi aktif. Record lama tidak diberi provider baru secara massal; migrasi aditif mempertahankan data pengguna.
- CSV tahap pertama mengekspor pilihan/rentang yang diminta beserta metadata, tidak hanya halaman terlihat. PDF mengikuti tahap P2 setelah isi CSV/API stabil, dengan sumber, tanggal, asumsi dan penjelasan confidence yang sama. Ekspor tidak memanggil model ulang atau mengurangi kuota; isi sel spreadsheet tidak boleh dieksekusi sebagai formula.

**Penerimaan:** perubahan BUY 80% → WAIT 60% tampil sebagai penurunan 20 poin persentase dengan dua waktu/revisi asli; bukan -20% return. Cache hit tidak menambah jumlah record. CSV seluruh pilihan sesuai jumlah di API, dan akun lain tidak mendapat metadata privat.

### E9 — Integrasi dan keterkinian sebagai syarat rilis

**FR-17 · P0 untuk rilis nyata · Pilih dan buktikan provider**

- Evaluasi Gemini/Groq/Ollama untuk AI serta EODHD/Sectors/Twelve Data untuk pasar mengikuti [kajian alternatif](alternatif_integrasi.md). Pilih satu provider AI dan sumber pasar yang mencakup instrumen pilot; tidak perlu mengintegrasikan semua kandidat. Jika satu sumber tidak mencakup IDX+AS, konfigurasi routing per bursa secara eksplisit dan verifikasi keduanya.
- Provider/model, kunci environment, hak penggunaan data, domain jaringan, error/429/timeout, batas token/biaya, dan observasi kesehatan dapat diperiksa tanpa membuka rahasia. Perubahan konfigurasi draft cloud tidak dianggap sudah aktif sampai runtime dan request nyata terbukti.
- Adapter mempertahankan kontrak OHLCV dan validasi hasil AI. Simpan provider/model aktual pada provenance/cache; bedakan raw, split-adjusted dan split/dividend-adjusted. Pergantian sumber/basis harga memerlukan backfill serta revisi data yang mencegah pencampuran seri lama.
- Verifikasi kalender sesi IDX dan pasar AS, zona waktu, hari libur, sesi pendek bila relevan, serta jadwal publikasi EOD provider. Tanpa kalender/jadwal yang cukup, status tetap unknown dan fitur yang membutuhkan fresh tidak diaktifkan.
- Uji satu instrumen IDX dan satu AS dari dashboard → detail → watchlist → backtest dengan sumber/currency/tanggal yang sama, plus minimal satu analisis AI nyata tersimpan dan terbaca ulang. Rekam provider, model, hasil, waktu, latensi dan biaya; jangan mengganti bukti ini dengan fixture.

**Penerimaan:** histori nonempty tervalidasi untuk kedua bursa, basis adjustment teruji melewati corporate action, hasil AI nyata lolos schema dan sesuai data input, error terstruktur mempertahankan data terakhir, dan keputusan biaya/hak penggunaan tercatat. Bila akses belum tersedia, gerbang tetap terbuka tanpa membuat data pengganti.

## 7. Kontrak API dan penyimpanan yang diusulkan

Kontrak inti R1 sudah tersedia dan harus dipertahankan. Endpoint/entitas baru berikut adalah rancangan, bukan klaim fitur sudah tersedia; finalisasi nama dan schema saat implementasi tanpa mengubah satuan secara diam-diam.

| Area | Keputusan implementasi |
|---|---|
| Metadata pasar | Tambahkan metadata sumber/currency/exchange/interval/waktu pasar/waktu fetch pada quote/chart; versi harga terakhir tetap dapat dibaca ketika refresh gagal |
| Rekomendasi | Gunakan enum BUY/HOLD/WAIT dan null; normalisasi confidence dan simpan versi input/model/prompt |
| Analisis inti | Pertahankan prefix /api/v1 dan route analisis ticker yang ada untuk R1; sukses berarti hasil valid tersimpan. Kegagalan memiliki code, message, stage, retryable, request_id |
| Analisis asinkron | R2 menambahkan POST /api/v1/analysis/jobs dengan ticker/idempotency key dan respons 202; GET /api/v1/analysis/jobs/{job_id} memuat status serta result_id. Migrasi frontend sebelum menonaktifkan pemanggilan sinkron |
| Backtest | Pertahankan POST /api/v1/analysis/{ticker}/backtest; skema kanonik mengikuti FR-05. Tambahkan run_id dan endpoint transaksi berhalaman bila respons tidak membawa seluruh transaksi |
| Kuota | Perluas GET /api/v1/auth/me dengan metadata kuota; jangan membuat perhitungan frontend yang berbeda dari backend |
| Watchlist | Tambah operasi edit notes pada item milik pengguna; dokumentasikan endpoint dan validasi 500 karakter |
| Penyimpanan | Migrasi aditif untuk metadata data/analisis, job/hasil backtest, reservasi kuota/idempotensi, dan alert saat fasenya berjalan |
| Integrasi/keterkinian baru | Tambah identitas provider/basis adjustment pada konfigurasi, provenance dan revisi/cache; metadata instrumen tetap tersedia ketika harga kosong; kalender serta jadwal EOD per bursa |
| Alert baru | CRUD /api/v1/alerts dan daftar/mark-read /api/v1/notifications; entitas AlertRule dan AlertEvent dengan owner dan event key unik; evaluasi dari job tersimpan |
| Screener baru | GET /api/v1/screener untuk filter terstruktur, sort dan pagination; /api/v1/screener/presets untuk filter privat; respons memuat criteria, total, coverage dan waktu data |
| Riwayat baru | GET /api/v1/stocks/{ticker}/analyses dan detail berdasarkan analysis_id; API pembanding menerima dua ID; ekspor berotorisasi dari hasil tersimpan |
| Rencana transaksi baru | /api/v1/trade-plans untuk CRUD/versioning privat; kalkulasi tervalidasi server mengembalikan jumlah lembar/lot, nilai transaksi, risiko dan asumsi |
| Run backtest baru | Entitas BacktestRun dengan owner, parameter/versi/revisi, trades dan equity; run lama tidak dihitung ulang diam-diam saat diekspor |

Pembaruan kontrak wajib disertai schema Pydantic, tipe frontend, OpenAPI runtime dan dokumentasi statis yang konsisten. Adapter kompatibilitas mempunyai test, pemakai yang teridentifikasi, dan jadwal penghapusan setelah seluruh konsumen bermigrasi. Jangan menafsirkan input ambigu atau mengubah angka lama secara massal tanpa pemeriksaan.

Catatan lama yang sumbernya tidak dapat dibuktikan diberi provenance unknown dan dikeluarkan dari rekomendasi aktif sampai dihitung ulang. Jangan melabeli seluruh histori sebagai nyata atau menghapus data pengguna untuk mempermudah migrasi.

## 8. Kebutuhan nonfungsional dan pengukuran

Target berikut adalah usulan penerimaan, belum merupakan hasil pengukuran produksi.

| Aspek | Target dan cara verifikasi |
|---|---|
| Performa API tersimpan | p95 ≤1 detik untuk daftar/quote/chart dari database/cache, fixture 100 ticker dengan histori lima tahun dan 20 pengguna serentak di staging; panggilan provider diukur terpisah |
| Job asinkron | Respons penerimaan p95 ≤1 detik; queued TTL awal 10 menit; maksimal dua attempt dalam deadline eksekusi 120 detik sejak mulai diproses, termasuk backoff. Deadline/timeout provider dibatasi sisa anggaran; tidak retry tanpa batas |
| Aksesibilitas | Alur utama dapat dipakai dengan keyboard; label input, fokus dialog, tombol ikon, dan pesan error dapat dibaca teknologi bantu; warna bukan satu-satunya penanda |
| Responsivitas | Uji 360px, 390 × 844, 1440px, dan zoom teks 200%; tidak ada overflow halaman selain tabel/chart yang dapat digeser; target sentuh utama ≥44 × 44 CSS px dan jarak ≥8px |
| Keamanan | Auth/otorisasi pada resource privat, rate limit, rotasi token atomik, HTTPS pada deployment, tidak ada token/password/API key pada log atau analitik |
| Ketahanan data | Provider gagal tidak menimpa data terakhir; proses ulang tidak menduplikasi analisis, kuota, transaksi, atau alert |
| Observabilitas | request_id/job_id, tahap gagal, latensi provider, cache hit, revisi input, dan token usage dicatat tanpa isi rahasia |

Ukur sebelum rilis dan selama pilot tujuh hari: proporsi analisis baru berhasil/diterima, kegagalan per provider, umur data per bursa, waktu penyelesaian, biaya per eksekusi, dan penyelesaian alur cari → detail → watchlist. Laporkan jumlah sampel; kegagalan provider tidak dihilangkan dari metrik keseluruhan.

Kriteria mutu: nol hasil sintetis tanpa label pada pengujian, nol selisih parameter/persentase pada fixture kontrak, nol P0 terbuka saat rilis. Target win-rate perdagangan tertentu bukan kriteria keberhasilan produk ini.

Target pengalaman pengguna berikut belum diukur; rekam baseline dan hasil pilot dengan jumlah sampel serta median waktu, bukan menyatakan target sebagai capaian:

| Alur | Target pilot dan bukti |
|---|---|
| Cari → detail → watchlist | Minimal 4 dari 5 calon pengguna selesai tanpa bantuan dalam 90 detik dan dapat menyebut sumber/tanggal harga |
| Memahami kuota dan kegagalan | Minimal 4 dari 5 dapat menyebut sisa kuota/reset WIB dan membedakan chart valid dari AI gagal |
| Screener → hasil → detail | Seluruh fixture filter/pagination sesuai dataset acuan; minimal 4 dari 5 pengguna dapat menyimpan/membuka filter tanpa bantuan |
| Membuat rencana | Minimal 4 dari 5 dapat menyimpan rencana valid dalam 3 menit dan menjelaskan risiko nominal serta asumsi lot/biaya |
| Kembali memantau | Pada pilot tujuh hari, laporkan jumlah pengguna yang kembali, alert terkirim/duplikat, serta waktu menuju saham dari notifikasi; kumpulkan baseline sebelum menetapkan target retensi |

## 9. Backlog dan urutan implementasi

Estimasi tindak lanjut menggunakan **hari engineer**, bukan tanggal kalender: satu engineer full-stack, QA/reviewer produk tersedia saat acceptance, source/CI/staging dapat diakses, dan scope per paket sesuai tabel. Waktu menunggu akun, lisensi data, email, kredensial, atau izin jaringan tidak termasuk. Dengan kapasitas berbeda, susun ulang jadwal setelah pekerjaan dipecah; tidak menghitung ulang pekerjaan R1 yang sudah diimplementasikan.

| ID | Pekerjaan | Prioritas | Status dan pekerjaan tersisa | Dependensi / bukti penerimaan |
|---|---|---|---|---|
| B01 | Build/kontrak dasar | P0 | Diimplementasikan R1 | Build/lint lokal lulus; pertahankan pada B12 |
| B02 | Hapus fallback, metadata, currency, urutan perubahan | P0 | Diimplementasikan R1; kalender/provenance lintas provider diteruskan B16 | FR-01; failure injection dan smoke IDX/AS |
| B03 | Hasil AI, rekomendasi, gagal/cache | P0 | Diimplementasikan R1; identitas provider/cache lintas model diteruskan B16 | FR-02/03 dan request nyata |
| B04 | Sync → AI → hasil, reservasi/idempotensi | P0 | Diimplementasikan R1; bukan job queue | B03 + B09a; klik ganda/gagal parsial |
| B05 | Backtest parameter/output/satuan/legacy | P0 | Diimplementasikan R1 | FR-05; regresi TP10/SL5, empty trades, persentase |
| B06 | Kausalitas, timing, equity drawdown | P0 | Diimplementasikan R1 pada fixture; data nyata masih gerbang B16 | FR-06, gap/split/prefix-invariance |
| B07 | Chart/pencarian/daftar saham | P1 | Sebagian: tutup audit histori/warm-up, metadata mandiri, daftar berhalaman lengkap | B02–B03; FR-07/08, U06/U11 |
| B08 | Watchlist harian lengkap | P1 | Sebagian: tambah filter bursa, sort harga, status sudah ditambahkan | B02 + B07; FR-09, notes dan dua akun tetap lulus |
| B09a | Kuota/auth/base URL/refresh/logout | P0 | Diimplementasikan R1 | FR-10; token lama ditolak dan kuota bersamaan |
| B09b | Kuota/profil UI | P1 | Angka/reset tersedia; sisa konsistensi bahasa/tier dan audit keadaan kosong | B09a + B11; tidak mengubah entitlement tanpa keputusan produk |
| B10 | Job persisten/worker/retry/status | P1 | Belum diimplementasikan; AnalysisRequest bukan antrean | B04 + B09a; FR-04, job ownership/restart/timeout |
| B11 | Bahasa/mobile/aksesibilitas/glosarium | P1 | Sebagian: audit lengkap keyboard/screen reader, 390 × 844, target sentuh/spacing, metadata | B07; U10/U11, lima pengguna, label/fokus/error |
| B12 | CI/migrasi/browser/staging | P0/P1 | Bukti lokal R1 tersedia; eksekusi remote dan tiap paket berikutnya masih perlu dibuktikan | Suite sesuai perubahan, CI, migrasi, smoke dan staging |
| B13 | Alert in-app EOD dan preferensi | P1 paket pemantauan | Belum diimplementasikan | B08 + B10 + B16; FR-11, deduplikasi/stale/restart |
| B14 | Reset/ubah password, edit profil/preferensi | P2 | Belum diimplementasikan | B09a; provider email; FR-12, replay/expiry/revoke/dua akun |
| B15 | Fee/slippage/lot, benchmark, run dan CSV backtest | P2 | Belum diimplementasikan; equity/trades sudah baseline | B06 + B16; FR-13, fixture biaya dan run ownership |
| B16 | Evaluasi/pilih/adapter provider, kalender dan smoke nyata | P0 rilis nyata | Kajian tersedia; belum memilih/mengintegrasikan alternatif | FR-17; budget/hak data, kredensial/jaringan, IDX+AS dan AI nyata |
| B17 | Screener dan saved filters | P1 paket riset | Belum diimplementasikan | B07 + B16; FR-15, filter seluruh cakupan/pagination/null |
| B18 | Riwayat/perbandingan analisis dan CSV | P1 paket riset | Penyimpanan dasar ada; UI/API histori/compare/export belum | B03 + B16; FR-16, provenance dan privasi |
| B19 | Rencana transaksi dan kalkulator risiko/modal/lot | P2 | Belum diimplementasikan | B07 + B16; FR-14; metadata lot/biaya serta ownership |
| B20 | Onboarding .JK/indikator dan penjelasan Free/Premium | P1 | Belum tersedia sebagai alur onboarding | B09b + B11; FR-12; tidak mengaktifkan pembayaran |
| B21 | PDF analisis/hasil terpilih | P2 | Belum diimplementasikan; pisah dari CSV | B18; FR-16, isi ekspor dan otorisasi sama dengan sumber |

### Tahap pelaksanaan

| Tahap | Estimasi awal hari engineer | Hasil yang dituju | Gerbang keluar |
|---|---|---|---|
| R1 — Baseline selesai di kode | Tidak dihitung ulang | B01–B06/B09a dan bagian B07/B08/B09b/B11/B12 tersedia pada 541c281 | Bukti lokal dirujuk; bukan pernyataan rilis produksi |
| R1.1 — Validasi rilis inti | 6–10 | B16 + B12: pilih provider, adapter/provenance, kalender/jadwal, staging, regresi tepat U01–U09 | G1: tidak ada P0, data IDX+AS dan AI nyata, kuota/kontrak/session benar |
| R2.1 — Penggunaan harian | 8–12 | Sisa B07/B08/B09b/B11 + B20 dan QA | G2: watchlist lengkap, metadata, keyboard, 360/390/1440px dan pilot 4/5 |
| R2.2 — Pemantauan tahan restart | 8–13 | B10 + B13 dan QA | G3: job/alert tersimpan, ownership, restart/retry, nol event ganda dan tidak memakai stale |
| R2.3 — Riset yang dapat ditelusuri | 8–14 | B17 + B18 dan QA | G4: filter seluruh cakupan, saved filters, perbandingan/provenance, CSV lengkap |
| R3 — Paket lanjutan dipilih setelah pilot | B15 4–7; B19 4–7; B14 3–5; B21 2–4, di luar QA lintas paket | Backtest biaya/benchmark, rencana transaksi, akun, dan PDF dapat dirilis terpisah | G5: acceptance paket terpilih, fixture biaya/lot, privasi dan layanan pendukung |

Urutan ini mengikuti feedback: kebenaran dan pembuktian inti lebih dahulu, kelengkapan watchlist lalu alert, kemudian screener/riwayat. Alert EOD dipilih sebagai P1 paket pemantauan; email/intraday tetap di luar paket. Rencana transaksi dapat disiapkan setelah metadata dan kalkulator disepakati, tetapi tidak menghambat G1–G4.

B07/B08/B11/B20 dapat dikerjakan saat menunggu akses provider; acceptance nyata G1 dan aktivasi alert tetap menunggu B16. B17/B18 tidak wajib menunggu engine alert bila kapasitas tim bertambah. Owner/reviewer produk menetapkan kapasitas, universe pilot, budget serta paket setelah riset provider; tidak memerlukan pengerjaan ulang perbaikan P0 yang sudah terbukti lokal.

## 10. Strategi validasi dan release gate

| Lapisan | Skenario minimum |
|---|---|
| Unit/domain | Persen dan currency, null vs zero, urutan candle, model-output validation, kalender bursa, kuota reset Jakarta, kausalitas, equity drawdown |
| API/kontrak | Backtest parameter efektif dan empty trades, field tak dikenal/legacy, BUY/HOLD/WAIT, profil kuota, notes ownership, error terstruktur |
| Integrasi | Sync/AI/database/cache, rollback kegagalan, request bersamaan, quota reservation, provider timeout/429/invalid JSON, worker restart pada R2 |
| Browser R1 | Register → login JSON → navigasi/cari ticker dengan UI yang tersedia → detail → analisis → tambah/hapus watchlist → backtest → refresh sesi → logout, desktop/mobile dan dua akun |
| Browser R2 | Alur R1 ditambah filter/sort watchlist dan status sudah ditambahkan, target sentuh/fokus/390 × 844, kuota/onboarding; paket job/alert serta screener/history diuji saat masing-masing siap |
| Provider nyata | Histori nonempty dan currency/time metadata untuk instrumen IDX dan AS; satu analisis AI tersimpan dapat dibaca ulang; biaya percobaan dicatat |
| Build/deployment | Suite backend terdokumentasi, test baru yang relevan, build/typecheck frontend, lint tanpa pelanggaran baru, serta migrasi PostgreSQL |
| Job/alert | Klik ganda, kepemilikan dua akun, worker/broker restart, queued TTL/deadline, 429/backoff, satu event per transisi, preferensi/mark-read, tidak memicu pada stale/unknown |
| Screener/riwayat | Filter dataset penuh dan pagination, null/tanggal tidak cocok, saved filters privat, perbandingan dua versi, cache hit tidak menggandakan histori, CSV seluruh pilihan aman |
| Rencana/backtest biaya | Long entry/stop/target, currency/lot, modal/risiko/biaya/slippage, benchmark dengan asumsi sama, run privat, CSV lengkap dan hasil perhitungan acuan |
| Akun/onboarding | Reset/ubah password, token sekali pakai/expired/replay, pencabutan sesi, email gagal, tier sesuai API; penjelasan confidence dan .JK diuji pada pengguna |

Setiap release harus memenuhi:

1. Acceptance seluruh backlog yang masuk rilis terpenuhi; bukti test mencantumkan run/hasil dan tidak menyamakan skip dengan pass.
2. Regresi baseline R1 yang didokumentasikan 79 pass pada masing-masing SQLite/PostgreSQL tetap lulus dengan bukti run terbaru; test worker yang relevan wajib dijalankan saat B10, bukan terus dikecualikan. Penambahan fitur membutuhkan kasus domain yang bermakna, bukan mengejar jumlah test.
3. Browser menguji hasil yang dirender dan request aktual. Mock terkontrol dipakai untuk failure/concurrency; smoke provider nyata dicatat terpisah.
4. Database baru dapat dimigrasikan dan snapshot staging lama dapat di-upgrade tanpa kehilangan akun/watchlist. Siapkan backup, pemulihan, dan kompatibilitas versi aplikasi sebelum migrasi.
5. Fitur yang mengandalkan provider/worker/secret belum diverifikasi tidak disebut siap. Jika akses belum tersedia, paket terkait tetap terblokir; fitur independen boleh dikirim terpisah dengan statusnya jelas.
6. Pada pilot R2, lakukan uji produk oleh setidaknya lima calon pengguna: minimal empat memenuhi target alur pada bagian 8. Ini target uji penerimaan, bukan klaim hasil. Ukur rencana transaksi ketika paket B19 masuk pilot, bukan sebelum fiturnya tersedia.
7. Ulangi kasus persis review: `INVALIDXYZ` tidak menampilkan chart/sinyal buatan; BBCA.JK dan saham AS mempertahankan currency lintas halaman; TP10/SL5 sampai ke mesin; logout sidebar/settings mencabut sesi; label login dapat ditemukan dan kontrol password dapat dicapai dengan Tab. Catat commit, runtime, viewport, request/hasil, screenshot dan console error tanpa rahasia.
8. Gerbang G1–G5 pada bagian 9 berlaku per paket: kegagalan G1 menahan rilis analisis nyata; G2 menahan klaim UX R2.1 selesai; G3 menahan aktivasi alert; G4 menahan screener/history; G5 menahan hanya paket lanjutan terkait. Data terakhir dan fitur yang sudah tervalidasi tetap dapat dipakai dengan status yang jujur.

## 11. Dependensi, risiko, dan peluncuran

| Dependensi/risiko | Penanganan |
|---|---|
| Pilihan sumber pasar | Yahoo tetap implementasi saat ini; evaluasi EODHD/Sectors serta cakupan AS melalui B16 sebelum mengganti. Verifikasi OHLC lengkap, basis adjustment, kalender/jadwal, budget, serta hak simpan/display; paket personal tidak diasumsikan cukup untuk aplikasi publik |
| Provider AI | Anthropic tetap implementasi saat ini; Gemini/Groq/Ollama masih kandidat. Pilih berdasar schema, evaluasi alasan terhadap input, bahasa Indonesia, latensi, token/biaya dan kemampuan server bila lokal; jangan menyebut kandidat sudah terintegrasi |
| Kredensial dan izin jaringan | Masukkan lewat pengaturan environment, bukan chat/Git; uji domain/request aktual. Draft belum sama dengan runtime aktif; kegagalan konfigurasi ditampilkan tanpa data pengganti |
| Browser CI | Sediakan browser dan akses unduhan yang didukung; HTML HTTP 200 saja tidak menggantikan test interaksi |
| PostgreSQL, Redis dan worker | SQLite tetap untuk dev/test terbatas; staging memverifikasi backend produksi, migrasi, worker serta restart sesuai rilis |
| Kalender dan corporate action | Tetapkan calendar/currency/source per bursa; normalisasi split/dividen konsisten sebelum menyatakan backtest valid |
| Cache/data lama | Invalidasi setelah update, metadata provenance, dan recompute terukur; jangan menghapus histori pengguna secara menyeluruh |
| Risiko penggunaan data masa depan | Audit centered rolling/swing/FVG dan test prefix-invariance; jika belum selesai, hasil backtest belum layak dirilis sebagai terverifikasi |
| Perubahan kontrak API | Adapter eksplisit, test konsumen, dokumentasi dan deploy backend sebelum frontend yang memerlukan field baru |
| Email/alert | In-app terlebih dahulu. Email/reset-password membutuhkan domain pengirim dan provider; jangan menganggapnya sudah tersedia |
| Cakupan/pola screener | Metadata sektor dan indikator harus ada serta selaras tanggal. Tampilkan cakupan tersinkron dan versi pola; jangan mengklaim semua saham IDX atau dukungan pola yang belum diimplementasikan |
| Risiko perencanaan transaksi | Aturan lot dan biaya dapat berbeda per bursa/broker; parameter harus terlihat. Perhitungan risiko berbasis stop adalah estimasi, bukan jaminan kerugian maksimum |
| Metadata/ekspor privat | Pisahkan hasil pasar umum dari owner/session/notes/trade plan; otorisasi ekspor dan pencegahan formula CSV diuji. PDF memerlukan waktu implementasi/operasi terpisah |

Peluncuran: staging → pengguna pilot terbatas → evaluasi kegagalan/biaya → perluasan. Rollback memakai versi aplikasi yang kompatibel dan backup yang diuji. Nonaktifkan fitur bermasalah secara jelas bila perlu; jangan mengembalikan fallback harga atau sinyal buatan.

## 12. Keputusan awal dan hal yang perlu dipastikan

Default perencanaan: analisis teknikal harian, bahasa Indonesia, IDR/USD mengikuti instrumen, BUY/HOLD/WAIT, reset kuota Jakarta, serta rilis perbaikan inti sebelum fitur tambahan.

Sebelum B16 dijalankan, catat budget AI/pasar, kebutuhan personal atau display ke pengguna lain, instrumen pilot IDX+AS, serta credential/network yang benar-benar tersedia. Kapasitas engineer/QA dan pemakai API selain frontend menyempurnakan estimasi serta kompatibilitas. Penyusunan fixture, audit mobile/keyboard dan perbaikan UI independen tetap dapat berjalan sambil menunggu akses; provider dan tanggal peluncuran tidak diputuskan secara tersirat oleh PRD.

Revisi 1.1 memasukkan seluruh 12 temuan dan 8 usulan pada review, memperbarui status R1, serta menambah FR-14–FR-17/B16–B21. Tidak ada perubahan source aplikasi, migrasi database, pengujian provider nyata, atau deployment dalam penyusunan revisi dokumen ini.

### Rujukan implementasi saat review

- Data/detail: [halaman saham](../../ai_stock_analyzer_frontend/src/app/stock/[ticker]/page.tsx), [dashboard](../../ai_stock_analyzer_frontend/src/app/dashboard/page.tsx), [watchlist](../../ai_stock_analyzer_frontend/src/app/watchlist/page.tsx).
- AI: [router](../app/api/routers/analysis.py), [service](../app/services/ai_service.py), [client](../app/infrastructure/ai_client.py), [prompt](../app/services/prompt_builder.py).
- Backtest: [halaman](../../ai_stock_analyzer_frontend/src/app/stock/[ticker]/backtest/page.tsx), [mesin](../app/worker/backtester.py), [deteksi pola](../app/services/pattern_engine.py).
- Sesi/kuota: [auth frontend](../../ai_stock_analyzer_frontend/src/api/auth.ts), [client bersama](../../ai_stock_analyzer_frontend/src/services/api.ts), [auth router](../app/api/routers/auth.py), [schema profil](../app/domain/schemas/auth.py).
- Pekerjaan latar: [Celery](../app/worker/celery_app.py), [task](../app/worker/tasks.py).
