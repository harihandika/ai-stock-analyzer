# PRD dan Rencana Perbaikan AI Stock Analyzer

Versi: 1.0

Tanggal: 18 Oktober 2026, Asia/Jakarta

Status: R1 telah diimplementasikan secara lokal; validasi provider nyata dan gerbang rilis publik belum selesai. Lihat [laporan implementasi](implementasi_r1.md) untuk bukti serta sisa R2/R3.

Pemilik produk: pemilik aplikasi. Penanggung jawab teknis dan QA ditentukan saat pelaksanaan.

## 1. Masalah dan hasil yang dituju

Pengguna membutuhkan jawaban yang dapat ditelusuri: saham apa yang perlu diperhatikan, berdasarkan data kapan, mengapa sinyal muncul, dan apa risikonya. Saat ini beberapa kondisi gagal justru menghasilkan harga contoh atau rekomendasi yang tampak nyata. Alur analisis AI dan backtest juga belum konsisten antara frontend dan backend.

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

## 2. Dasar temuan dan batas bukti

Temuan berasal dari inspeksi kode, pemeriksaan API, dan validasi lingkungan sebelumnya. Suite backend yang didokumentasikan menghasilkan 47 test lulus, tetapi belum membuktikan alur browser, integrasi provider nyata, maupun kebenaran metodologi backtest.

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

Pengunduhan browser pengujian dan akses Yahoo Finance sebelumnya diblokir kebijakan jaringan. Analisis Anthropic nyata belum divalidasi tanpa kredensial. Keterbatasan lingkungan tersebut harus dipisahkan dari cacat aplikasi dan diuji ulang setelah akses tersedia.

## 3. Prioritas dan ruang lingkup

| Prioritas | Makna | Cakupan |
|---|---|---|
| P0 | Penghambat rilis inti: informasi salah, fungsi utama rusak, atau artefak rilis gagal | Integritas data, hasil AI, kontrak dan metodologi minimum backtest, build serta regresi |
| P1 | Wajib untuk rilis pengalaman penggunaan berikutnya | Chart harian, dashboard/pencarian, watchlist, sesi/kuota, pekerjaan AI asinkron, penjelasan |
| P2 | Pengembangan setelah stabilitas inti terukur | Alert, personalisasi, pemulihan akun dan realisme backtest tambahan |

Termasuk: perbaikan frontend Next.js dan backend FastAPI yang sudah ada, kontrak API, penyimpanan metadata, migrasi terkait, pengujian, serta observabilitas yang dibutuhkan.

Di luar rilis inti: eksekusi transaksi broker, prediksi keuntungan terjamin, aplikasi mobile native, analisis berita/sentimen, fundamental lengkap, pembayaran premium, dan portofolio transaksi nyata. Intraday tidak ditampilkan sebagai fitur aktif sebelum sumber dan implementasinya tersedia.

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
- Cache AI, jika digunakan, membedakan ticker, revisi data, model, versi prompt, dan mode. Perubahan input tidak menggunakan hasil lama secara diam-diam.

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

**FR-11 · P2 · Alert yang nyata:** mulai dengan in-app alert harga menembus batas dan perubahan BUY/HOLD/WAIT pada data baru. Trigger memakai transisi kondisi, kunci deduplikasi, dan waktu data; tidak mengirim ulang pada setiap polling. Pengguna dapat mematikan alert; data stale/demo tidak memicunya. Alert intraday atau email memerlukan sumber/layanan tambahan.

**FR-12 · P2 · Pemulihan akun dan personalisasi:** edit nama, preferensi notifikasi, ubah password, dan lupa password. Pemulihan akun memerlukan provider email, token sekali pakai dengan expiry, pesan yang tidak membocorkan keberadaan akun, serta pencabutan sesi sesuai kebijakan. Konsistensi bahasa dan glosarium dasar masuk B11/P1.

**FR-13 · P2 · Simulasi lebih realistis:** fee/slippage configurable dengan satuan basis poin, modal/ukuran lot, pembanding buy-and-hold, ekspor seluruh transaksi, dan penyimpanan run. Validasi eksekusi intraday membutuhkan data serta aturan tersendiri; tidak disimpulkan dari candle harian.

## 7. Kontrak API dan penyimpanan yang diusulkan

Semua perubahan di bagian ini merupakan target implementasi, bukan endpoint yang sudah tersedia.

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

Pembaruan kontrak wajib disertai schema Pydantic, tipe frontend, OpenAPI runtime dan dokumentasi statis yang konsisten. Adapter kompatibilitas mempunyai test, pemakai yang teridentifikasi, dan jadwal penghapusan setelah seluruh konsumen bermigrasi. Jangan menafsirkan input ambigu atau mengubah angka lama secara massal tanpa pemeriksaan.

Catatan lama yang sumbernya tidak dapat dibuktikan diberi provenance unknown dan dikeluarkan dari rekomendasi aktif sampai dihitung ulang. Jangan melabeli seluruh histori sebagai nyata atau menghapus data pengguna untuk mempermudah migrasi.

## 8. Kebutuhan nonfungsional dan pengukuran

Target berikut adalah usulan penerimaan, belum merupakan hasil pengukuran produksi.

| Aspek | Target dan cara verifikasi |
|---|---|
| Performa API tersimpan | p95 ≤1 detik untuk daftar/quote/chart dari database/cache, fixture 100 ticker dengan histori lima tahun dan 20 pengguna serentak di staging; panggilan provider diukur terpisah |
| Job asinkron | Respons penerimaan p95 ≤1 detik saat worker tersedia; proses memiliki batas total 120 detik sebelum failed/retryable, tidak loading tanpa batas |
| Aksesibilitas | Alur utama dapat dipakai dengan keyboard; label input, fokus dialog, tombol ikon, dan pesan error dapat dibaca teknologi bantu; warna bukan satu-satunya penanda |
| Responsivitas | Uji viewport 360px dan 1440px; tidak ada overflow halaman horizontal selain tabel/chart yang memang dapat digeser |
| Keamanan | Auth/otorisasi pada resource privat, rate limit, rotasi token atomik, HTTPS pada deployment, tidak ada token/password/API key pada log atau analitik |
| Ketahanan data | Provider gagal tidak menimpa data terakhir; proses ulang tidak menduplikasi analisis, kuota, transaksi, atau alert |
| Observabilitas | request_id/job_id, tahap gagal, latensi provider, cache hit, revisi input, dan token usage dicatat tanpa isi rahasia |

Ukur sebelum rilis dan selama pilot tujuh hari: proporsi analisis baru berhasil/diterima, kegagalan per provider, umur data per bursa, waktu penyelesaian, biaya per eksekusi, dan penyelesaian alur cari → detail → watchlist. Laporkan jumlah sampel; kegagalan provider tidak dihilangkan dari metrik keseluruhan.

Kriteria mutu: nol hasil sintetis tanpa label pada pengujian, nol selisih parameter/persentase pada fixture kontrak, nol P0 terbuka saat rilis. Target win-rate perdagangan tertentu bukan kriteria keberhasilan produk ini.

## 9. Backlog dan urutan implementasi

Estimasi adalah rentang awal, bukan komitmen tanggal. Asumsi: satu engineer backend, satu frontend, QA paruh waktu, reviewer produk tersedia, dan akses staging/provider siap. Satu engineer mengerjakan berurutan sehingga estimasi perlu disusun ulang.

| ID | Pekerjaan | Prioritas | Pemilik peran | Dependensi | Bukti selesai |
|---|---|---|---|---|---|
| B01 | Hilangkan error build chart; rekam regresi awal dan sinkronkan kontrak | P0 | Frontend + backend | Tidak ada | Build produksi lulus; fixture kontrak disepakati |
| B02 | Metadata, status data, currency, urutan perubahan, hapus fallback normal | P0 | Backend + frontend | B01 | FR-01 lulus pada failure injection |
| B03 | Normalisasi hasil/rekomendasi AI dan penanganan gagal/cache | P0 | Backend + frontend | B01–B02 | FR-02/03; hasil baru terbaca setelah update |
| B04 | Hubungkan sync → AI, batas eksekusi, kuota atomik dan idempotensi minimum | P0 | Backend + frontend | B03 + B09a | Sukses/gagal parsial dan klik ganda benar |
| B05 | Benarkan input/output/persen backtest serta validasi legacy | P0 | Backend + frontend | B01 | FR-05 lulus end-to-end |
| B06 | Audit kausalitas sinyal, timing eksekusi dan equity drawdown | P0 | Backend + QA | B05 | FR-06 lulus pada fixture deterministik |
| B07 | Chart harian, pencarian, dashboard total/rekomendasi | P1 | Frontend + backend | B02–B03 | FR-07/08 lulus |
| B08 | Watchlist dialog, notes, sort/refresh dan otorisasi | P1 | Frontend + backend | B02 + B07 | FR-09 lulus dua akun |
| B09a | Kuota atomik dan API, satukan auth/base URL, rotasi/refresh/logout | P0 | Backend + frontend | B01 | Aturan kuota serta alur sesi browser lulus pada R1 |
| B09b | Tampilan kuota, waktu reset dan penyempurnaan profil | P1 | Frontend + backend | B09a | UI FR-10 sesuai API pada R2 |
| B10 | Job asinkron persisten, worker, retry dan status UI | P1 | Backend + frontend | B04 + B09a | FR-04, restart worker dan job ownership lulus |
| B11 | Bahasa, penjelasan analisis, glosarium dan aksesibilitas | P1 | Frontend + produk | B03 + B07 | Uji pengguna dan keyboard selesai |
| B12 | CI, migrasi, uji browser dan staging untuk setiap rilis | P0/P1 | QA + engineer | Mengikuti paket rilis | Seluruh release gate paket terpenuhi |
| B13 | Alert in-app berbasis kejadian/deduplikasi | P2 | Backend + frontend | B02 + B08 + B10 | FR-11 lulus |
| B14 | Pemulihan akun dan preferensi | P2 | Backend + frontend | B09a/B09b; provider email | FR-12 lulus |
| B15 | Fee/slippage, benchmark, riwayat dan ekspor backtest | P2 | Backend + frontend | B06 | FR-13 lulus terhadap fixture biaya |

### Tahap pelaksanaan

| Tahap | Estimasi | Hasil yang dituju | Gerbang keluar |
|---|---|---|---|
| Persiapan | 2–3 hari kerja | Baseline, kontrak dan fixture; audit migrasi/kausalitas; akses provider/browser | B01 siap; dependensi dan baseline tercatat |
| R1 — Kebenaran fungsi inti | 2–3 minggu setelah persiapan | B02–B06, B09a dan B12 untuk R1; analisis sinkron yang jujur, harga nyata, backtest benar, serta sesi/kuota valid | Seluruh P0 lulus; tidak ada hasil produksi palsu |
| R2 — Penggunaan harian | 2–3 minggu setelah R1 | B07–B08, B09b, B10–B11 dan B12 untuk R2 | Chart/watchlist, job worker, tampilan kuota serta penjelasan lulus end-to-end |
| R3 — Pengembangan lanjutan | Estimasi setelah R2/pilot | B13–B15 dipilih berdasarkan kebutuhan nyata | Acceptance fitur terpilih dan layanan pendukung siap |

Perkiraan R1+R2: sekitar 5–7 minggu kalender dengan asumsi di atas. Audit algoritma, perbaikan migrasi, dan akses eksternal dapat mengubah rentang. Temuan tersebut ditulis sebagai perubahan estimasi, bukan diloloskan dari kriteria.

B02 dan B05 dapat berjalan paralel setelah kontrak B01; audit B06 dimulai sedini mungkin. B07/B08 tidak perlu menunggu seluruh job asinkron selesai, tetapi rilisnya tetap memerlukan bukti integrasi.

## 10. Strategi validasi dan release gate

| Lapisan | Skenario minimum |
|---|---|
| Unit/domain | Persen dan currency, null vs zero, urutan candle, model-output validation, kalender bursa, kuota reset Jakarta, kausalitas, equity drawdown |
| API/kontrak | Backtest parameter efektif dan empty trades, field tak dikenal/legacy, BUY/HOLD/WAIT, profil kuota, notes ownership, error terstruktur |
| Integrasi | Sync/AI/database/cache, rollback kegagalan, request bersamaan, quota reservation, provider timeout/429/invalid JSON, worker restart pada R2 |
| Browser R1 | Register → login JSON → navigasi/cari ticker dengan UI yang tersedia → detail → analisis → tambah/hapus watchlist → backtest → refresh sesi → logout, desktop/mobile dan dua akun |
| Browser R2 | Alur R1 ditambah autocomplete nama/bursa, rentang chart, edit notes/sort, kuota/profil UI, status job persisten, serta pemulihan setelah restart worker |
| Provider nyata | Histori nonempty dan currency/time metadata untuk instrumen IDX dan AS; satu analisis AI tersimpan dapat dibaca ulang; biaya percobaan dicatat |
| Build/deployment | Suite backend terdokumentasi, test baru yang relevan, build/typecheck frontend, lint tanpa pelanggaran baru, serta migrasi PostgreSQL |

Setiap release harus memenuhi:

1. Acceptance seluruh backlog yang masuk rilis terpenuhi; bukti test mencantumkan run/hasil dan tidak menyamakan skip dengan pass.
2. Regresi backend yang sebelumnya 47 pass tetap lulus; test worker yang relevan wajib dijalankan saat B10, bukan terus dikecualikan.
3. Browser menguji hasil yang dirender dan request aktual. Mock terkontrol dipakai untuk failure/concurrency; smoke provider nyata dicatat terpisah.
4. Database baru dapat dimigrasikan dan snapshot staging lama dapat di-upgrade tanpa kehilangan akun/watchlist. Siapkan backup, pemulihan, dan kompatibilitas versi aplikasi sebelum migrasi.
5. Fitur yang mengandalkan provider/worker/secret belum diverifikasi tidak disebut siap. Jika akses belum tersedia, paket terkait tetap terblokir; fitur independen boleh dikirim terpisah dengan statusnya jelas.
6. Pada pilot R2, lakukan uji produk oleh setidaknya lima calon pengguna: minimal empat menyelesaikan cari → detail → simpan watchlist tanpa bantuan dan dapat menyebutkan tanggal/sumber data. Ini target uji penerimaan R2, bukan syarat fitur R2 harus sudah tersedia pada R1 atau klaim hasil.

## 11. Dependensi, risiko, dan peluncuran

| Dependensi/risiko | Penanganan |
|---|---|
| Akses Yahoo Finance | Verifikasi domain/redirect yang benar melalui operasi read-only; tangani 403/429/timeout tanpa data pengganti palsu |
| Kredensial Anthropic | Masukkan lewat pengaturan environment, bukan chat/Git; mock hanya untuk test/demo. Catat biaya dan model yang benar-benar tersedia |
| Browser CI | Sediakan browser dan akses unduhan yang didukung; HTML HTTP 200 saja tidak menggantikan test interaksi |
| PostgreSQL, Redis dan worker | SQLite tetap untuk dev/test terbatas; staging memverifikasi backend produksi, migrasi, worker serta restart sesuai rilis |
| Kalender dan corporate action | Tetapkan calendar/currency/source per bursa; normalisasi split/dividen konsisten sebelum menyatakan backtest valid |
| Cache/data lama | Invalidasi setelah update, metadata provenance, dan recompute terukur; jangan menghapus histori pengguna secara menyeluruh |
| Risiko penggunaan data masa depan | Audit centered rolling/swing/FVG dan test prefix-invariance; jika belum selesai, hasil backtest belum layak dirilis sebagai terverifikasi |
| Perubahan kontrak API | Adapter eksplisit, test konsumen, dokumentasi dan deploy backend sebelum frontend yang memerlukan field baru |
| Email/alert | In-app terlebih dahulu. Email/reset-password membutuhkan domain pengirim dan provider; jangan menganggapnya sudah tersedia |

Peluncuran: staging → pengguna pilot terbatas → evaluasi kegagalan/biaya → perluasan. Rollback memakai versi aplikasi yang kompatibel dan backup yang diuji. Nonaktifkan fitur bermasalah secara jelas bila perlu; jangan mengembalikan fallback harga atau sinyal buatan.

## 12. Keputusan awal dan hal yang perlu dipastikan

Default perencanaan: analisis teknikal harian, bahasa Indonesia, IDR/USD mengikuti instrumen, BUY/HOLD/WAIT, reset kuota Jakarta, serta rilis perbaikan inti sebelum fitur tambahan.

Pada persiapan, tim mencatat jawaban atas: kapasitas engineer/QA, daftar instrumen pilot, kalender/data provider yang layak, budget AI, dan kebutuhan pemakai API selain frontend ini. Jawaban menyempurnakan jadwal dan kompatibilitas; tidak menghalangi pembuatan fixture dan perbaikan P0 yang sudah jelas.

### Rujukan implementasi saat review

- Data/detail: [halaman saham](../../ai_stock_analyzer_frontend/src/app/stock/[ticker]/page.tsx), [dashboard](../../ai_stock_analyzer_frontend/src/app/dashboard/page.tsx), [watchlist](../../ai_stock_analyzer_frontend/src/app/watchlist/page.tsx).
- AI: [router](../app/api/routers/analysis.py), [service](../app/services/ai_service.py), [client](../app/infrastructure/ai_client.py), [prompt](../app/services/prompt_builder.py).
- Backtest: [halaman](../../ai_stock_analyzer_frontend/src/app/stock/[ticker]/backtest/page.tsx), [mesin](../app/worker/backtester.py), [deteksi pola](../app/services/pattern_engine.py).
- Sesi/kuota: [auth frontend](../../ai_stock_analyzer_frontend/src/api/auth.ts), [client bersama](../../ai_stock_analyzer_frontend/src/services/api.ts), [auth router](../app/api/routers/auth.py), [schema profil](../app/domain/schemas/auth.py).
- Pekerjaan latar: [Celery](../app/worker/celery_app.py), [task](../app/worker/tasks.py).
