# PRD 1.2 — Perbaikan pasca-audit AI Stock Analyzer

Tanggal: 19 Oktober 2026, Asia/Jakarta (WIB). Status: **rencana implementasi**, belum merupakan perbaikan source atau keputusan rilis. Baseline: `d17f260`, sudah berada di `main`.

Pembaruan pelaksanaan: [laporan implementasi pasca-audit](implementasi_pasca_audit_20261019.md) mencatat perbaikan PA-01–06, CLI ingestion/status, pengujian dan gerbang nyata/manual yang masih terbuka. Acceptance dan estimasi di bawah tetap menjadi acuan rencana, bukan klaim semua gerbang selesai.

Acuan: [ringkasan audit terbaru sesi Edit ai-stock-analyzer](review_audit_d17f260_2026-10-19.md), [PRD 1.1](prd_perbaikan_aplikasi.md), dan [laporan implementasi](implementasi_prd_20261019.md). PRD ini berisi pekerjaan sesudah baseline, sedangkan kontrak dan prinsip integritas data PRD 1.1 tetap berlaku.

## 1. Masalah dan hasil yang dituju

Alur riset, penyimpanan dan perhitungan backend sudah bekerja pada pengujian terkontrol. Hambatan berikutnya adalah hasil kalkulator yang tidak mengikuti perubahan input, kontrol mobile yang terpotong, spacing yang tidak diterapkan, serta angka chart yang bergantung hover. Pengguna berisiko membaca ukuran posisi lama atau gagal menjangkau informasi penting di ponsel.

Audit melaporkan 133 kasus lulus, 13 gagal, tujuh terblokir dan 12 belum diuji. Empat bug unik menjelaskan 13 kegagalan; header 320px berulang pada sepuluh halaman. Tidak ditemukan P0 pada skenario audit yang dijalankan. Pernyataan tersebut tidak membuktikan ketiadaan P0 di seluruh produk atau kesiapan produksi.

Hasil yang dituju:

1. Angka risiko/lot selalu terkait input yang terlihat dan sama dengan hasil tersimpan untuk snapshot input tersebut.
2. Semua kontrol utama dapat dijangkau pada lebar 320px dan nilai chart dapat dibaca lewat sentuhan maupun keyboard.
3. Formulir cukup sederhana untuk mencoba perhitungan, dengan asumsi biaya, currency dan lot tetap terlihat.
4. Pengguna memahami perbedaan tanggal data pasar, waktu pengambilan dan status keterkinian.
5. Rilis yang memakai data nyata memiliki bukti provider, kalender/ingestion, email dan operasional yang sesuai cakupannya.

## 2. Ruang lingkup dan prioritas

**P1 produk:** BUG-001 wajib diselesaikan sebelum pilot investor berikutnya. **P2 produk:** BUG-002/003/004, hierarki informasi data dan penyederhanaan formulir. **P0 gerbang rilis:** pembuktian integrasi/operasional sebelum mengaktifkan fitur publik yang bergantung layanan tersebut. Ketergantungan konfigurasi tidak dihitung sebagai bug aplikasi.

Tetap dipertahankan: job persisten, kuota atomik, ownership akun, watchlist, screener, riwayat/ekspor, backtest berbiaya dan rumus finansial yang sudah diverifikasi. Penambahan screener, alert atau riwayat dari awal bukan ruang lingkup paket ini. Intraday, broker order, pembayaran, model baru tambahan dan target profitabilitas strategi juga berada di luar paket.

## 3. Persyaratan produk dan penerimaan

### PA-01 — Hasil kalkulator mengikuti input (P1, BUG-001)

- Setiap hasil dikaitkan dengan snapshot/fingerprint input yang dinormalisasi: ticker, currency, entry/stop/target, modal, risiko, lot dan seluruh asumsi biaya/slippage. Field rencana tambahan ikut versi draft agar konteks hasil tidak tertukar saat edit.
- Gunakan keadaan jelas: belum dihitung, input berubah, sedang menghitung, hasil terkini atau gagal. Sesudah input relevan berubah, angka lama disembunyikan dari panel hasil aktif dan tampil pesan **Input berubah — hitung ulang**. Jangan menampilkan 20 lot sebagai hasil input Rp1 juta.
- Respons calculate yang terlambat tidak boleh mengaktifkan hasil untuk input berbeda. Gunakan pembatalan request atau pemeriksaan versi; mencocokkan versi tetap diperlukan bila respons sudah tiba sebelum pembatalan.
- Simpan menghitung ulang di server dari snapshot yang dikirim. Respons simpan memperbarui kartu dan pratinjau yang sesuai snapshot tersebut. Bila pengguna mengubah input saat request berjalan, panel draft baru tetap berstatus perlu hitung ulang. Simpan tidak bergantung hasil UI lama.
- Edit, batal edit, ganti ticker dan mulai rencana baru membersihkan konteks hasil sebelumnya. Konflik versi tetap 409 dengan jalur memuat ulang; rencana pengguna tidak ditimpa diam-diam.

**Penerimaan:** modal Rp10 juta, risiko 1%, entry 1.000, stop 950, target 1.100, lot 100, biaya 0 menghasilkan 2.000 lembar/20 lot dan risiko Rp100.000. Sesudah modal menjadi Rp1 juta, hasil lama langsung tidak aktif; perhitungan/simpanan baru menghasilkan 200 lembar/2 lot, risiko Rp10.000 dan sisa modal Rp800.000. Uji juga entry, stop, target, risiko, fee, slippage, currency/lot tidak valid, serta respons lambat yang datang terbalik. Tidak mengubah rumus finansial hanya untuk memperbaiki state tampilan.

### PA-02 — Header utuh pada 320px (P2, BUG-002)

- Search dapat mengecil atau dibuka melalui kontrol khusus; menu, pencarian, notifikasi dan pengaturan tetap tersedia. Padding/gap header menyesuaikan ruang, tanpa mengecilkan target sentuh utama di bawah 44 × 44 CSS px.
- Uji bounding box tiap kontrol: sisi kiri ≥0, sisi kanan ≤lebar viewport dan seluruh area klik terlihat. `overflow-x: hidden` atau `scrollWidth` yang tidak bertambah tidak membuktikan kontrol utuh.
- Dropdown/search/menu tidak terpotong scroll container, dapat dibuka keyboard, mempunyai fokus terlihat dan jalur tutup yang jelas.

**Penerimaan:** sepuluh halaman yang terkena M-320-* lulus pada 320, 360, 390, 430, 768 dan 1440px. Tombol yang sebelumnya berakhir di x=334 harus sepenuhnya berada di 320px. Periksa modal watchlist, landscape 844 × 390, zoom teks 200%, keyboard dan perubahan orientasi. Jangan sekadar menyembunyikan kontrol yang tidak muat.

### PA-03 — Cascade CSS dan spacing sesuai desain (P2, BUG-003)

- Hapus reset universal padding/margin yang redundan atau pindahkan aturan reset ke layer yang sesuai Tailwind. Pilih berdasarkan pemeriksaan cascade hasil build; hindari `!important` menyeluruh.
- Input `p-3` memakai computed padding 12px pada skala default; tab `px-4/py-2` memakai padding horizontal 16px/vertikal 8px. Kontrol tab utama mempunyai area klik minimal 44px tinggi; link teks biasa di paragraf tidak perlu dijadikan tombol.
- Gunakan jarak konsisten antarlabel, field, section dan aksi; pesan error/fokus tidak menempel tepi atau tertutup. Periksa form rencana, screener, akun, tab riset, kartu hasil, modal dan dialog auth.
- Reset yang diperbaiki dapat mengubah dimensi header dan legend. PA-02/PA-04 harus diretest dengan CSS final.

**Penerimaan:** computed style membuktikan padding, tab yang sebelumnya 26px memenuhi target sentuh, dan tidak ada kontrol terpotong pada matriks layar. Periksa build produksi selain development; screenshot atau class CSS saja bukan bukti utility sudah diterapkan.

### PA-04 — Angka chart tersedia pada sentuhan/keyboard (P2, BUG-004)

- Pada perangkat tanpa hover, tampilkan ringkasan candle terakhir secara permanen atau panel pilihan candle yang terlihat. Tap/long press mengubah tanggal dan nilai secara bersamaan; visibilitas tidak hanya memakai `group-hover`.
- Ringkasan memuat tanggal, OHLC, volume, EMA/RSI/MACD yang tersedia beserta satuan/currency. Nilai indikator yang kosong tampil belum tersedia; tidak menjadi nol atau angka contoh.
- Sediakan alternatif yang dapat difokuskan keyboard untuk memilih candle, misalnya slider tanggal atau kontrol sebelumnya/berikutnya, dengan nilai tekstual yang dapat dibaca teknologi bantu.
- Panel dapat ditempatkan di bawah chart atau area yang tidak menghalangi candle/drag. Scroll halaman, pan/zoom chart dan kontrol reset ke candle terbaru tetap dapat digunakan.

**Penerimaan:** pada `hasTouch=true`, `isMobile=true`, `hover:none`, tap dan long press 900ms menghasilkan panel yang benar-benar terlihat, bertanggal sesuai candle, dengan angka sama dengan dataset acuan. Periksa nilai/null dan pergantian rentang. Lulus emulasi Chromium belum menggantikan pengujian Android/iPhone fisik dan Safari/WebKit.

### PA-05 — Sumber, tanggal dan keterkinian mudah dibaca (P2)

- Dekat harga tampil sumber, currency/bursa, **tanggal penutupan pasar** dan badge fresh/stale/unknown dengan teks, bukan warna saja.
- Waktu **diambil** ditampilkan terpisah dengan zona WIB; jelaskan bahwa fetch baru tidak mengubah candle lama menjadi harga terkini. Waktu analisis/model/revisi tetap dibedakan dari tanggal harga.
- Rincian kalender, basis adjustment dan penjelasan teknis dapat dibuka agar tampilan utama ringkas. Status unknown menyebut verifikasi kalender/jadwal belum tersedia; jangan mengubahnya menjadi fresh berdasarkan umur fetch.

**Penerimaan:** BBCA.JK dan AAPL konsisten dari dashboard → detail → watchlist. Fixture stale yang diambil hari ini tetap stale; sumber/tanggal tidak hilang saat AI gagal. Pada pilot, ≥4 dari 5 pengguna dapat menyebut sumber, tanggal harga dan arti unknown tanpa bantuan.

### PA-06 — Form rencana bertahap (P2)

- Kelompok dasar kalkulator: ticker/currency, entry, stop, target, modal, batas risiko dan aturan lot. Biaya/slippage dapat berada pada bagian lanjutan yang mudah dibuka, dengan ringkasan asumsi selalu terlihat.
- Area entry, horizon, alasan dan kondisi pembatalan diminta saat menyimpan rencana lengkap. Pengguna dapat mencoba kalkulator sebelum menulis uraian rencana; validasi numerik/instrumen tetap berlaku.
- Endpoint calculate saat ini menerima `PlanInput` lengkap. Bila payload minimal diperlukan, pisahkan kontrak validasi kalkulasi dari penyimpanan; tetap terima payload lengkap klien lama secara eksplisit, pertahankan penolakan field tidak dikenal, dan dokumentasikan OpenAPI. Jangan mengisi alasan/horizon/area dengan teks atau harga buatan.
- Hasil dan tombol simpan menjelaskan lembar/lot, risiko nominal, nilai beli, sisa modal, reward/risk dan biaya yang dipakai. Semua hasil tetap mengikuti PA-01 dan server sebagai sumber perhitungan.

**Penerimaan:** kalkulasi dasar berhasil tanpa uraian rencana; simpan menolak field rencana wajib yang kosong dengan fokus/pesan yang sesuai. Edit versi lama tetap utuh, currency tidak dikonversi otomatis, nol lot dijelaskan, dan minimal 4 dari 5 peserta pilot menyimpan rencana valid ≤3 menit serta menjelaskan risiko dan biaya.

### PA-07 — Integrasi nyata yang dapat diterima (P0 gerbang G1)

- Pilih satu provider AI dan sumber pasar yang memenuhi pilot. Adapter Gemini/EODHD sudah tersedia; provider tambahan tidak menjadi syarat. Default tidak diganti diam-diam.
- Rekonsiliasi konfigurasi cloud dari draft terkini; draft lama ditolak karena stale. Verifikasi secret tersedia dan domain aktif tanpa mencetak nilai. [Usulan konfigurasi tersimpan sebagai file](cloud-environment-r2-proposal.json) adalah bahan rekonsiliasi, bukan bukti grant runtime.
- Konfirmasi budget, paket/cakupan IDX+AS, hak menyimpan/menampilkan data, raw/adjusted OHLCV dan jadwal publikasi. Tidak membeli paket atau mengasumsikan lisensi personal berlaku untuk publik.
- Pilot minimum BBCA.JK dan AAPL: histori nonempty, OHLCV masuk akal, currency/bursa/tanggal/basis adjustment konsisten, histori cukup untuk rentang yang ditawarkan atau keterbatasan periode dinyatakan. Uji satu hasil AI nyata tersimpan dan terbaca ulang untuk masing-masing instrumen; catat model aktual, input revision, token, latensi dan biaya aktual bila tersedia. Jika biaya belum tersedia, tandai belum terukur.
- Timeout/429/refusal/malformed response tetap diuji terkontrol; kegagalan tidak menghasilkan harga/sinyal pengganti. Evaluasi alasan AI terhadap input, bukan janji profit atau target win-rate.

**Penerimaan:** bukti request nyata yang tersanitasi memenuhi kedua instrumen dan pembacaan ulang; fixture tidak menggantikannya. Kalender/alert baru diaktifkan setelah PA-08. Tanpa kredensial/izin/lisensi yang sesuai, G1 tetap terblokir meskipun adapter lolos tes.

### PA-08 — Ingestion EOD, kalender dan alert operasional (P0 untuk aktivasi alert, G3)

- Tetapkan universe pilot, provider, kalender IDX/AS, delay publikasi, jadwal ingestion dan budget. Worker saat ini mengevaluasi data tersimpan; ia belum menyediakan jadwal pengambilan seluruh pasar.
- Jadwal ingestion mengambil sesi yang sudah selesai, menyimpan sumber/revisi dan membatasi retry. Data gagal/unknown/stale tidak memicu event. Hari libur, sesi pendek, zona waktu dan corporate action diperiksa terhadap sumber yang sah.
- Setelah sesi baru fresh tersimpan, worker mengevaluasi transisi rule; baseline awal tidak memicu historis, replay/restart tidak menggandakan event atau kuota. Preferensi, ownership, pause/resume dan mark-read tetap berlaku.
- Sediakan status worker/antrean, umur sesi terakhir per bursa, kegagalan provider dan ingestion yang dapat ditindaklanjuti tanpa rahasia di log. Uji worker benar-benar dihentikan/dijalankan ulang, dua worker dan job deadline pada lingkungan penerimaan.

**Penerimaan:** lintasan harga terkontrol 100→110 melewati ambang 105 menghasilkan satu event; replay sesi yang sama tetap satu. Demonstrasikan ingestion EOD nyata serta event dari rule akun uji yang sah, bukan modifikasi harga pasar. Jika transisi nyata belum terjadi selama jendela pilot, bukti operasional tersebut tetap pending. Jangan membuat data palsu untuk menandai gerbang selesai.

### PA-09 — Pemulihan akun lewat email nyata (P0 untuk publikasi fitur reset, G5-akun)

- Konfigurasi SMTP host/from, secret, TLS dan jalur egress SMTP yang benar. Allowlist HTTPS cloud tidak dengan sendirinya menyediakan TCP SMTP.
- Uji inbox yang dikuasai tim/pemilik aplikasi: request reset, tautan valid, token sekali pakai/30 menit, expiry/replay, password baru dan penolakan seluruh sesi lama. Pesan permintaan existing/unknown tetap generik; token/password tidak masuk log, analitik atau artefak.
- Uji kegagalan pengiriman, throttling dan klik ganda. Layanan tidak menyatakan email pasti terkirim saat belum dikonfigurasi/gagal; URL publik aplikasi harus sesuai deployment.

**Penerimaan:** email nyata diterima dan alur reset valid selesai, lalu token lama/sesi lama ditolak. Pengujian token invalid atau transport mock tidak cukup. Jika layanan belum tersedia, status fitur reset dijelaskan dan gerbang akun tetap terbuka.

### PA-10 — Bukti pipeline, staging dan pilot (P0 gerbang rilis publik)

- Jalankan pipeline pada commit kandidat rilis: SQLite/PostgreSQL, migrasi fresh dan upgrade snapshot berisi data, kontrak/OpenAPI, lint/typecheck/build produksi dan browser. Suite yang dilewati audit harus memiliki bukti run terkini, bukan mengadopsi hitungan historis.
- Pertahankan empat reproduksi bug sebagai regresi dan matriks bounding box sepuluh halaman × enam lebar. Verifikasi keyboard/fokus/error, zoom 200%, screen reader manual, perangkat Android/iPhone, serta browser yang didukung; yang tidak dijalankan tetap tercatat belum diuji/terblokir.
- Staging disposable dan berizin: 100 ticker, histori lima tahun, 20 pengguna serentak; target p95 ≤1 detik untuk pembacaan tersimpan dan penerimaan job. Panggilan provider, cache warm/cold, tingkat error dan spesifikasi mesin dilaporkan terpisah. Ini target penerimaan, bukan klaim performa sekarang.
- Lengkapi boundary ekspor/filter yang belum diuji audit: CSV 5.000/PDF 200 hasil dan penolakan di atas batas, seluruh pilihan bukan halaman aktif, formula CSV, null/tanggal indikator, kombinasi filter dan ownership. Uji duplikasi request dan worker pada database yang dipakai staging.
- Pilot minimal lima orang, mencakup investor pemula dan trader aktif: alur cari/detail/watchlist ≤90 detik dan rencana valid ≤3 menit pada ≥4 peserta; peserta dapat menjelaskan sumber/tanggal, kuota, risiko dan asumsi biaya. Observasi kembali memantau selama tujuh hari mencatat jumlah peserta kembali, bukan menebak target retensi.
- Siapkan backup/restore yang diuji, supervisor tiga proses, rollback aplikasi yang kompatibel migrasi, pemantauan antrean/latensi/error/biaya, serta keputusan rilis per paket. Data rahasia tidak ikut artefak.

**Penerimaan:** bukti ditautkan ke commit, runtime/database, dataset, jumlah sampel dan lingkungan. Nol P0/P1 terbuka pada cakupan rilis; empat bug audit tertutup dengan bukti retest. P2 yang ditunda harus dikeluarkan dari klaim cakupan dan dicatat dampaknya. Release gate provider/alert/akun tetap berlaku per fitur, tidak ditutup hanya karena CI hijau.

## 4. Backlog, dependensi dan estimasi

Estimasi adalah hari kerja engineer, bukan komitmen tanggal. Asumsi satu engineer dengan akses reviewer/QA; waktu menunggu kredensial, lisensi, jaringan, responden dan pengamatan tujuh hari tidak dimasukkan. Nama owner ditetapkan saat pelaksanaan.

| ID | Paket | Owner peran | Dependensi | Estimasi |
|---|---|---|---|---:|
| PA-01 | Konsistensi hasil kalkulator | Frontend; backend reviewer | Tidak menunggu provider | 0,5–1 hari |
| PA-03 | CSS layer/spacing | Frontend | Tidak menunggu provider | 0,5–1 hari |
| PA-02 | Header/bounding box | Frontend | CSS final PA-03 | 0,5 hari |
| PA-04 | Legend sentuh/keyboard | Frontend + QA mobile | CSS final PA-03 | 1–1,5 hari |
| QA-A | Retest empat bug dan lint/build/browser kandidat | QA + engineer | PA-01–04 | 1 hari |
| PA-05 | Hierarki tanggal/sumber/freshness | Frontend + produk | Metadata yang sudah ada | 0,5–1 hari |
| PA-06 | Form bertahap/kontrak calculate | Frontend + backend | PA-01/03; QA kontrak | 1,5–2 hari |
| PA-07 | Penerimaan provider nyata | Backend + operator + produk | Budget, lisensi, kredensial, domain aktif | 3–5 hari |
| PA-08 | Ingestion/kalender/alert | Backend + operator | PA-07; keputusan universe/jadwal | 2–4 hari |
| PA-09 | SMTP/reset nyata | Backend + operator | Pengirim, inbox uji dan egress | 1–2 hari |
| PA-10 | Pipeline/staging/pilot/rollback | QA + operator + produk | Seluruh paket yang dirilis | 2–3 hari teknis + observasi 7 hari |

Urutan pelaksanaan:

1. **Paket A — koreksi yang langsung dapat dikerjakan, 3,5–5 hari:** PA-01 → PA-03 → PA-02/04 → QA-A. Keluar ketika empat bug ditutup; pilot finansial menunggu PA-01. Pekerjaan ini tidak bergantung API key.
2. **Paket B — pengalaman harian, 2–3 hari:** PA-05/06 dan regresi terkait. Keluar ketika formulir/data dapat dipahami dan kalkulator konsisten, siap diuji pengguna.
3. **Paket C — penerimaan operasional, 8–14 hari teknis:** PA-07/08/09/10 setelah dependensi siap. Persiapan CI/SMTP/pilot dapat berjalan saat menunggu provider. Gerbang fitur yang bergantung provider tidak dilewati.

Total indikatif berurutan **13,5–22 hari kerja teknis**, ditambah waktu tunggu dan observasi tujuh hari yang dapat beririsan. Estimasi diperbarui setelah discovery konfigurasi dan retest awal; tidak menetapkan tanggal rilis sebelum dependensi tersedia.

## 5. Matriks penerimaan ringkas

| Area | Bukti minimum | Syarat keluar |
|---|---|---|
| Risiko/lot | Input berubah, request terlambat, save/edit/cancel, pembanding API | Tidak ada hasil aktif yang berasal dari snapshot lama |
| CSS/header | Computed style + bounding box + screenshot produksi pada enam lebar | Empat kasus bug terkait tampilan tertutup, kontrol utama utuh |
| Chart | Touch dan keyboard; angka dibanding dataset/null; perangkat fisik | Angka terbaca tanpa hover, tanggal/nilai sesuai pilihan |
| Provider | IDX+AS dan dua hasil AI nyata tersimpan, lisensi/budget | G1 terpenuhi untuk universe pilot |
| Alert | Ingestion sesi baru + replay/restart/dedup + preferensi | G3 terpenuhi; stale/unknown tidak memicu |
| Akun | Inbox nyata, reset valid/expiry/replay dan sesi lama | G5-akun terpenuhi |
| Staging/pilot | Pipeline commit kandidat, load, backup/restore, lima peserta/tujuh hari | Target terukur dan keputusan rilis tercatat |

Setiap tiket mencatat ID audit/PRD, acceptance yang diuji, commit, hasil lulus/gagal/terblokir/belum diuji, artefak tersanitasi dan reviewer. Hitungan test implementasi sebelumnya dan audit eksternal dilaporkan terpisah. Kegagalan konfigurasi tidak diubah menjadi pass atau bug source tanpa bukti.

## 6. Keputusan dan batas penyusunan dokumen

Default: prioritaskan empat bug, pertahankan kontrak/rules finansial, lalu perjelas data dan sederhanakan form. Tetap gunakan fixture untuk QA yang independen dari jaringan, serta bukti nyata terpisah untuk penerimaan provider/email. Fitur baru besar tidak mendahului stabilisasi ini.

Sebelum paket C: pastikan pemilik budget/lisensi, provider pilot, pengaturan environment terkini, pengirim email, universe/jadwal ingestion, lingkungan staging dan lima responden. Jika belum tersedia, paket A/B tetap dapat selesai; status rilis paket C tetap terblokir sesuai dependensinya.

Penyusunan PRD ini membaca transkrip audit dan mencocokkan source `d17f260`; tidak menjalankan audit ulang, mengubah source aplikasi, membeli layanan, mengirim email, menerapkan konfigurasi cloud atau melakukan deployment. Bukti ZIP/screenshot audit berada pada sesi sumber sebagaimana [catatan sumber](review_audit_d17f260_2026-10-19.md).
