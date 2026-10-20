# PRD 1.3 — Perbaikan audit dan kesiapan pilot AI Stock Analyzer

Acuan perbaikan terbaru: [PRD 1.4 setelah audit V3 pada dc67ff9](prd_stabilisasi_audit_v3_dc67ff9.md). BUG-005–007 di bawah sudah diverifikasi diperbaiki oleh V3; gerbang layanan nyata dan pilot yang belum diterima tetap berlaku.

Tanggal: 20 Oktober 2026, Asia/Jakarta (WIB). Status: **acuan implementasi; capaian dan gerbang tersisa dicatat pada [laporan pelaksanaan](implementasi_prd_1_3_20261020.md)**. Baseline audit aplikasi: `8d9645d` pada `work`; `main` masih `d17f260` ketika penyusunan dimulai. Bukti audit diterbitkan pada commit `9c36fcf` di branch `audit/user-testing-8d9645d-20261020`. Acceptance di bawah adalah target; bukan pernyataan seluruh layanan/pilot telah diterima.

Dokumen ini melanjutkan [PRD 1.2](prd_perbaikan_pasca_audit_d17f260.md). [Ringkasan audit terbaru dan bukti sumber](review_audit_8d9645d_2026-10-20.md) serta [catatan baseline](status_baseline_8d9645d_2026-10-20.md) membedakan hasil auditor, pencocokan source dan batas penerimaan. Akses lintas sesi tidak diperlukan lagi: laporan GitHub, matriks final dan evidence utama sudah diperiksa.

Hasil audit: **115 lulus, 3 gagal, 5 terblokir dan 4 belum diuji, total 127 observasi**. Empat bug lama dinyatakan fixed and verified. Tiga temuan tambahan adalah BUG-005 P1, BUG-006 P2 dan BUG-007 P2; belum ada bukti ketiganya diperkenalkan oleh commit kandidat. Urutan pertama rencana ini adalah menutup ketiga temuan tersebut.

## 1. Masalah, pengguna dan hasil

Investor dapat melihat panel perbandingan BBCA ketika riwayat aktif sudah AAPL, gagal menyimpan alert sinyal, dan kehilangan filter setiap kembali dari detail saham. Ini menghambat kepercayaan konteks analisis dan riset beberapa kandidat. Mobile/kalkulator sudah membaik dan perlu dipertahankan. Bukti provider nyata, pengiriman email, operasi terjadwal dan penggunaan pada perangkat nyata tetap belum lengkap. Perbedaan `main` dan kandidat juga dapat membuat penilaian berikutnya memakai versi lama.

Tujuan paket ini:

1. Menampilkan perbandingan hanya untuk ticker dan dua record yang sedang dipilih, termasuk saat jaringan lambat.
2. Membuat alert BUY/HOLD/WAIT dari UI dan mempertahankan konteks screener saat Back/Forward/refresh.
3. Menetapkan satu kandidat untuk CI/staging, kemudian membuktikan provider IDX/AS, ingestion/alert dan pemulihan akun nyata.
4. Memperjelas notifikasi/bahasa/onboarding serta mengukur penyelesaian tugas pada perangkat dan peserta manusia.

Tidak menambahkan screener, watchlist, riwayat atau kalkulator dari awal karena fitur tersebut sudah ada. Intraday, broker order, pembayaran, provider ketiga dan janji profitabilitas berada di luar paket. Default provider tetap pilihan konfigurasi eksplisit.

## 2. Prioritas dan status awal

**P1/P2 bug** mengikuti severity audit; P1 konteks perbandingan harus selesai sebelum pilot investor berikutnya. **P3 UX** adalah peningkatan yang dapat dijadwalkan sesudah stabilisasi. Prioritas KP menunjuk kesiapan fitur/rilis; konfigurasi yang belum tersedia tidak dihitung sebagai bug baru. Tidak ada klaim ketiadaan P0 di luar cakupan audit.

| ID | Pekerjaan | Prioritas | Status awal | Hubungan PRD lama |
|---|---|---|---|---|
| AF-01 | Konteks compare dan identitas dua record | P1 | BUG-005 / N05 terkonfirmasi audit | Melengkapi riwayat yang sudah ada |
| AF-02 | Payload dan validasi alert per jenis | P2 | BUG-006 / N04; kontrol API X04 lulus | Melengkapi alert yang sudah ada |
| AF-03 | Konteks screener melalui navigasi | P2 | BUG-007 / J10 terkonfirmasi audit | Melengkapi screener yang sudah ada |
| UX-01–04 | Badge, bahasa, orientasi dan bantuan indikator | P3 | Rekomendasi auditor; bukan empat bug tambahan | PA-05/06; fitur yang sudah ada |
| KP-01 | Kandidat rilis, regresi audit dan CI | P1 | Audit sudah dipetakan; branch masih berbeda | PA-10 |
| KP-02 | Provider AI/pasar nyata dan keputusan paket | P1 | Adapter tersedia; bukti nyata belum lengkap | PA-07 |
| KP-03 | Jadwal EOD, kalender dan alert | P1 | CLI tersedia; aktivasi operasional pending | PA-08 |
| KP-04 | Pemantauan worker dan pemulihan operasi | P1 | Status konfigurasi/antrean ada; heartbeat belum tersedia | PA-08/10 |
| KP-05 | Reset password lewat inbox nyata | P1; penyederhanaan UI P2 | Backend/UI ada; pengiriman nyata pending | PA-09 |
| KP-06 | Mobile, browser dan aksesibilitas | P2 | Regresi Chromium ada; matriks nyata belum lengkap | PA-02–06/10 |
| KP-07 | Kapasitas staging, migrasi dan restore | P1 untuk rilis publik | Benchmark lokal ada; penerimaan staging pending | PA-10 |
| KP-08 | Pilot pengguna dan evaluasi tugas | P2 untuk pilot; wajib sebelum perluasan | Responden dan pengukuran belum tersedia | PA-05/06/10 |

## 3. Perbaikan tiga bug sebelum perluasan pilot

### AF-01 — Compare selalu terkait konteks aktif (P1, BUG-005/N05)

- Ikat request pada snapshot ticker aktif, urutan dua ID analisis dan versi konteks. Invalidate saat ticker aktif/pilihan berubah, tab/navigasi meninggalkan konteks atau komponen unmount. Pembatalan request disertai pemeriksaan versi sebelum success/error/loading mengubah state; abort saja tidak cukup untuk respons yang sudah tiba.
- Bersihkan panel aktif ketika konteks berubah. Respons lama yang valid dari API tidak boleh mengisi panel konteks baru atau menghapus error/loading request yang lebih baru. Bedakan draft input Kode saham dari ticker yang benar-benar dimuat; tampilkan ticker aktif secara eksplisit selama pemuatan.
- Validasi kedua record pada respons sesuai ticker dan pasangan ID yang diminta; jika berbeda, tampilkan kegagalan yang jelas dan pertahankan data lain yang sah. Penolakan pasangan ticker berbeda pada backend tetap dipertahankan.
- Pada panel, tampilkan ticker, ID/identitas hasil, tanggal data, waktu hasil WIB dan provider/model **untuk kedua sisi**. Nyatakan urutan perbandingan, revisi input bila tersedia dan data yang belum diketahui. Selisih skor tetap poin persentase, bukan return atau peluang profit.

**Selesai ketika:** reproduksi N05 dengan respons BBCA ditahan dua detik lalu memuat AAPL tidak pernah memperlihatkan panel BBCA pada AAPL. Uji respons A/B datang terbalik, pilihan ID berubah, error lama datang belakangan, Back/Forward, tab ditinggalkan dan unmount. Normal 78→88 tetap +10 poin persentase dan urutan terbalik −10; nilai null tetap belum tersedia. Identitas kedua sisi dapat dibaca pada 320px dan desktop.

### AF-02 — Alert sinyal dapat disimpan dari UI (P2, BUG-006/N04)

- Bentuk payload sesuai jenis: sinyal mengirim ticker/kind/signal; harga/perubahan mengirim ticker/kind/direction/threshold. Field yang tidak relevan tidak diambil dari kontrol yang tidak dirender dan tidak dikirim sebagai null yang melanggar schema.
- Pertahankan kontrak API lama yang valid, termasuk default direction. Perbaikan UI tidak mensyaratkan pelonggaran semua field backend. Jika kontrak berubah, dokumentasikan kompatibilitas dan OpenAPI sebelum mengubah klien.
- Setelah sukses, tampilkan rule yang tersimpan dan statusnya. Tombol menampilkan progres serta mencegah pengiriman berulang selama request berjalan; kegagalan mempertahankan input agar dapat diperbaiki.
- Petakan error validasi ke field/pesan Indonesia yang relevan; pengguna mode sinyal tidak diminta mengisi above/below. Jangan menelan error API atau menampilkan sukses tanpa rule tersimpan.

**Selesai ketika:** BUY/HOLD/WAIT masing-masing berhasil 201 melalui form, tampil dalam daftar dan bertahan setelah reload. Harga/perubahan above/below tetap bekerja; beralih jenis berulang kali tidak mengirim nilai tersembunyi lama. Input tidak valid ditolak tanpa menghapus draft. Kontrol X04 dan retest N04 dijadikan regresi kontrak/UI, independen dari provider nyata.

### AF-03 — Riset screener berlanjut setelah kembali (P2, BUG-007/J10)

- Jadikan URL sumber state **filter yang sudah diterapkan**, sort, arah dan page. Gunakan nama parameter yang tidak berbenturan dengan tab/ticker/halaman histori, misalnya namespace `sc_`, lalu petakan field yang diizinkan ke API screener.
- Inisialisasi form dari URL; Terapkan filter, pagination, reset dan muat preset memperbarui state/URL secara konsisten. Back/Forward dan refresh memuat kriteria yang sama. Filter yang belum disimpan sebagai preset juga dipertahankan.
- Validasi parameter sesuai kontrak: boolean false tidak menjadi true karena string nonempty, page bilangan positif, RSI 0–100/min≤max, sort/pola dari daftar yang didukung. Parameter tidak dikenal tidak diteruskan ke API; input invalid menghasilkan pesan yang dapat diperbaiki.
- Simpan/pulihkan anchor kartu dan posisi scroll sesuai entri navigasi setelah hasil siap. Kembali dari detail menyorot/memfokuskan kandidat sebelumnya bila masih tersedia. Jika data berubah atau page tidak tersedia, jelaskan penyesuaian tanpa membuat hasil lama seolah terkini.
- Pertahankan cakupan/metadata hasil, preset dan ownership akun. URL menyimpan kriteria publik, tidak menyimpan data akun atau catatan privat. Hasil boleh diambil ulang; query yang sama tidak menjanjikan harga yang tidak berubah.

**Selesai ketika:** IDX, volume 1000, RSI 20–60 tetap terisi setelah buka BBCA → Back, dengan query hasil sesuai filter. Uji page kedua pada dataset cukup, sort naik/turun, Forward, refresh, muat/reset preset, filter tanpa preset, tab/ticker lain, URL invalid dan data/page berubah. Posisi kandidat kembali pada enam lebar, tanpa memulihkan hasil akun sebelumnya setelah logout.

## 4. Peningkatan UX sesudah stabilisasi

| ID | Perubahan | Penerimaan | Estimasi |
|---|---|---|---:|
| UX-01 | Sinkronkan badge dan daftar sesudah mark-read (B03). Gunakan state/count bersama atau invalidasi segera; polling tetap untuk perubahan eksternal. | Sesudah respons sukses, badge dan status event sesuai unread API tanpa menunggu polling 30 detik; target ≤1 detik pada uji terkontrol. Request gagal tidak mengurangi count secara permanen; ganti akun membersihkan state. | 0,25–0,5 hari |
| UX-02 | Bahasa Indonesia konsisten pada backtest dan error form; bantuan ringkas untuk tingkat kemenangan, rata-rata hasil, drawdown, bps/fee/slippage. | Label/pesan dapat dipahami, satuan dan angka tetap sama dengan API; 1 bps dijelaskan 0,01%. Hasil historis tidak disajikan sebagai janji profit. Error alert terkait AF-02 wajib selesai bersama bug, bukan menunggu paket ini. | 0,5–1 hari |
| UX-03 | Orientasi pertama yang singkat: cari saham → baca sumber/tanggal atau sinkronkan → simpan watchlist; dapat ditutup. | Tautan menuju alur yang ada; dismissal tersimpan per akun dan dapat dibuka ulang. Kegunaan dinilai pada KP-08, bukan diasumsikan dari klik otomatis. | 0,5–1 hari |
| UX-04 | Bantuan RSI/MACD/Wyckoff/SMC yang menautkan pola tersedia ke tanggal/candle/sumber dan batas interpretasinya. | Pola kosong/kurang data tetap belum tersedia. Contoh terkontrol membuktikan hubungan tanggal; validitas pasar nyata mengikuti T04/KP-02. Tidak menambahkan label/sinyal contoh sebagai pengganti. | 0,5–1 hari |

Status monitoring yang lebih mudah dipahami adalah bagian KP-03/04: rule tersimpan/aktif dibedakan dari menunggu data eligible, baseline terbentuk, siap dievaluasi, dijeda dan gagal. Tampilkan sesi terakhir dan kesiapan worker **hanya bila diukur**; jika belum diketahui, gunakan status belum terverifikasi. Status tersebut harus menjelaskan bahwa alert memakai EOD, bukan pemantauan realtime. Penerimaannya mencakup rule aktif tanpa data fresh, worker berhenti dan baseline awal yang tidak memicu event.

## 5. Persyaratan kesiapan pilot dan layanan nyata

### KP-01 — Semua pengujian merujuk kandidat yang sama

- Catat SHA `main`, `work`, versi deployment dan target audit; jangan menyimpulkan deployment mengikuti `main` tanpa bukti. Rekonsiliasi kandidat melalui review/merge sesuai alur repository ketika pelaksanaan memang diotorisasi.
- Gunakan pemetaan audit pada AF-01–03 dan [ringkasan sumber](review_audit_8d9645d_2026-10-20.md). Setiap tiket mencatat commit, langkah reproduksi, hasil yang diharapkan/terjadi, severity dan bukti. Empat bug yang sudah fixed and verified tetap menjadi regresi.
- Jalankan workflow remote pada kandidat: SQLite/PostgreSQL, kontrak OpenAPI, frontend lint/build dan kedua suite browser yang sudah ada. Catat run URL/SHA; hitungan lokal historis tidak menggantikan hasil remote.
- Perbarui panduan utama agar versi Next.js/Node, provider opsional, worker database dan migrasi `r3_read_paths` sesuai source; README masih memuat tabel stack dan prasyarat lama. Pisahkan worker produk yang dipakai dari Celery lama.

**Selesai ketika:** ada manifest kandidat, hasil CI remote, matriks feedback/retest dan runbook yang konsisten. N05/N04/J10 lulus pada kandidat baru dan empat reproduksi BUG-001–004 tetap lulus pada build produksi. Matriks 127 observasi audit lama dipertahankan sebagai histori; hasil retest baru dilaporkan terpisah dengan SHA baru.

### KP-02 — Data dan analisis nyata untuk IDX dan AS

- Prioritas uji mengikuti [kajian yang sudah ada](alternatif_integrasi.md): Gemini untuk AI dan EODHD untuk histori IDX/AS. Ini kandidat evaluasi, bukan keputusan pembelian atau penerimaan kualitas. Tidak membangun adapter baru sebelum mengetahui hasilnya.
- Periksa konfigurasi environment terkini: keberadaan secret, domain/egress dan model yang tersedia tanpa mencetak nilai. [Usulan cloud](cloud-environment-r2-proposal.json) perlu direkonsiliasi dari pengaturan terkini; draft lama yang stale bukan konfigurasi aktif.
- Catat kebutuhan penggunaan, paket/cakupan, hak penyimpanan/display, batas request dan budget dari pemilik aplikasi. Harga kajian lama diverifikasi ulang sebelum keputusan berbiaya.
- Minimal BBCA.JK dan AAPL: metadata, histori nonempty, OHLCV, currency, sesi, kedalaman histori dan adjustment diverifikasi terhadap sumber provider yang sah. Periksa contoh split/dividen dan data kosong; interval tetap EOD. Periode yang tidak tersedia dinyatakan terbatas, bukan dibuatkan candle.
- Tutup T04 dengan sampel pasar nyata untuk Wyckoff/SMC: telusuri kondisi pola ke candle/input dan tanggal, periksa sifat kausal pada sampel, lalu bandingkan alasan AI terhadap fakta yang benar-benar tersedia. Ini penerimaan keterlacakan, bukan pembuktian profitabilitas seluruh strategi.
- Jalankan job AI nyata untuk masing-masing instrumen, simpan dan baca ulang hasilnya. Rekam provider/model aktual, revisi input, waktu, token dan biaya bila tersedia; biaya yang belum dapat direkonsiliasi diberi status belum terukur. Evaluasi alasan terhadap input serta format hasil, bukan return masa depan.
- Timeout/429/respons malformed tetap mempunyai tes terkontrol; chart valid bertahan ketika AI gagal, kuota dan idempotensi mengikuti kontrak yang ada.

**Selesai ketika:** dua paket bukti IDX/AS tersanitasi dan keputusan provider/budget/lisensi diterima. Bukti fixture saja tidak menutup tiket. Bila provider gagal memenuhi kebutuhan, catat gap dan revisi pilihan sebelum menambah adapter.

### KP-03 — Pembaruan EOD dan alert yang dapat dipercaya

- Gunakan CLI ingestion yang sudah ada. Tentukan universe awal eksplisit BBCA.JK/AAPL, satu scheduler, kalender yang diterima dan jadwal sesuai publikasi masing-masing bursa. Pilot baru diperluas setelah biaya serta durasi run terukur; batas CLI saat ini 20 ticker.
- Konfigurasi `MARKET_CALENDAR_VERIFIED` dan delay hanya setelah memeriksa hari libur IDX/AS, sesi pendek, DST AS dan waktu publikasi. Fetch hari ini atas harga lama tetap stale/unknown. Jika jadwal berbeda per bursa tidak dapat diwakili konfigurasi global yang ada, tambahkan kebijakan per bursa dengan validasi; jangan memakai asumsi global tanpa pemeriksaan.
- Simpan hasil run dan ringkasan per ticker: status, sesi yang diharapkan/diterima, waktu mulai/selesai, attempt dan kode kegagalan. Rincian ini tersedia bagi operator dan memiliki retensi yang ditetapkan; tidak cukup hanya stdout yang hilang setelah proses selesai.
- Retry bounded, run tidak tumpang tindih, dan histori valid tetap tersedia saat provider gagal. Pertahankan satu scheduler per host; desain koordinasi terdistribusi hanya jika deployment memerlukannya.
- Alert dievaluasi setelah data sesuai kalender tersedia. Baseline awal, replay sesi, restart dan dua worker tidak menggandakan event. Stale/unknown tidak memicu; preferensi/ownership/pause tetap berlaku. Kanal pilot adalah notifikasi dalam aplikasi, bukan email/push baru.

**Selesai ketika:** sedikitnya satu ingestion sesi baru nyata per bursa berhasil pada jadwal yang dipilih, operator dapat menemukan run gagal, dan tes transisi terkontrol 100→110 melewati 105 menghasilkan tepat satu event sesudah replay/restart. Bukti alert atas transisi pasar nyata dicatat terpisah; jika belum terjadi pada akun uji selama jendela pilot, statusnya tetap pending.

### KP-04 — Worker berhenti dapat diketahui dan dipulihkan

- Tambahkan heartbeat worker yang tersimpan dan dapat dibaca operator, terpisah dari jumlah job. Catat identitas instance, waktu heartbeat UTC, progres terakhir dan umur antrean tertua tanpa menyimpan secret atau payload pengguna pada metrik.
- Usulan awal interval heartbeat ≤15 detik dan status tidak sehat setelah 60 detik tanpa heartbeat. Heartbeat tidak boleh tertahan seluruh durasi panggilan provider; bedakan worker hidup dari job yang tidak maju/deadline terlewati. Ambang diterima ulang pada staging.
- Sediakan pemeriksaan API/database, worker, scheduler, sesi pasar terakhir dan kegagalan pengiriman secara terpisah. Secret configured tidak boleh ditampilkan sebagai provider connected atau email delivered.
- Jalankan API, frontend dan worker melalui supervisor yang ditetapkan deployment. Dokumentasikan siapa menangani alarm, restart, antrean macet dan rollback. Mulai dari pemeriksaan/kanal operasional yang dipakai pemilik aplikasi.

**Selesai ketika:** penghentian worker terdeteksi ≤60 detik, restart memulihkan layanan, job melewati deadline berakhir sesuai kontrak dan reservasi kuota dilepas tepat satu kali. Jalankan skenario crash/dua worker pada PostgreSQL tanpa menggandakan record analisis atau alert. Kegagalan terdeteksi dapat ditautkan ke job/run tanpa membocorkan data akun lain.

### KP-05 — Pemulihan akun sampai password baru

- Konfigurasikan SMTP/TLS, sender, URL publik dan egress pada lingkungan penerimaan; gunakan inbox milik tim/pemilik aplikasi. Backend reset sudah ada dan tidak perlu dibangun ulang.
- Saat tautan valid dengan token pada fragment dibuka, tampilkan form password baru secara langsung; permintaan tanpa token tetap menampilkan form email. Ini penyederhanaan berdasarkan source, bukan bug audit baru. Sesudah berhasil, bersihkan fragment dan sediakan kembali ke login.
- Existing/unknown email tetap menghasilkan pesan generik. Pengiriman gagal dicatat sebagai kegagalan operator; UI tidak menjanjikan email pasti terkirim. Pertahankan throttling, masa berlaku 30 menit dan token sekali pakai.

**Selesai ketika:** inbox nyata menerima email, reset valid selesai, password lama serta seluruh sesi lama ditolak dan password baru dapat login. Replay, expiry, klik ganda dan kegagalan SMTP ditangani; token/password tidak muncul pada log, screenshot atau analitik. Tanpa SMTP aktif, alur tetap menjelaskan layanan belum tersedia.

### KP-06 — Tugas utama nyaman di perangkat yang didukung

- Pertahankan pengujian geometri sepuluh halaman × 320/360/390/430/768/1440px dan computed padding, fokus, dropdown, state kalkulator serta panel candle. Periksa landscape dan zoom browser 200%; root text 200% terdahulu tidak dianggap pengujian zoom browser lengkap.
- Usulan dukungan pilot: Chrome Android dan Safari iPhone pada perangkat fisik, serta Chromium/Firefox/WebKit desktop. Catat model/OS/versi aktual. Browser/perangkat yang tidak dijalankan ditandai belum diuji, bukan pass.
- Uji keyboard/screen reader pada login, pencarian, watchlist, kalkulator, alert dan reset. Label, fokus, error, perubahan hasil dan ringkasan candle harus dapat dipahami tanpa hover atau warna saja. Tidak mengklaim sertifikasi aksesibilitas penuh.

**Selesai ketika:** tidak ada kontrol utama terpotong, angka OHLC terpilih sesuai data pada touch/keyboard, perubahan input langsung menonaktifkan hasil lama, dan tugas utama tidak memiliki hambatan keyboard/screen reader pada matriks dukungan pilot. Temuan baru memiliki reproduksi/tiket, lalu perbaikan diretest pada CSS/build final.

### KP-07 — Staging dan pemulihan data terbukti

- Gunakan staging berizin dengan resource, database PostgreSQL dan jumlah API/worker yang dicatat. Ulangi workload 100 ticker × histori lima tahun × 20 pengguna; laporkan fase awal dan warm, jumlah sampel, p50/p95/error dan konfigurasi. Gunakan dataset terkontrol untuk beban awal agar biaya provider tidak tercampur.
- Target penerimaan: p95 ≤1 detik untuk daftar/harga/chart/screener tersimpan dan penerimaan job, selama tiga putaran masing-masing 20 request serentak per endpoint. Hasil provider dan penyelesaian worker diukur terpisah dari admission/replay. Tidak menganggap benchmark lokal empat worker sebagai hasil staging.
- Uji migrasi fresh dan upgrade snapshot berisi akun/watchlist/plan/job; lakukan restore backup ke database terpisah. Usulan pilot: backup setidaknya harian, RPO ≤24 jam dan RTO ≤60 menit, dengan nilai aktual diukur dan diterima operator.
- Rehearsal rollback aplikasi/migrasi pada salinan staging. Verifikasi login, ownership, catatan dan versi rencana sesudah restore; baris yang tetap utuh pada upgrade bukan bukti backup dapat dipulihkan.

**Selesai ketika:** target beban dan pemulihan terpenuhi dengan bukti SHA/lingkungan/dataset; tidak ada error aplikasi pada sampel penerimaan dan dampak rate limit dilaporkan tersendiri. Jika target gagal, ukur penyebab dan revisi kapasitas sebelum menetapkan cakupan rilis.

### KP-08 — Lima pengguna dapat menyelesaikan pekerjaan harian

- Rekrut lima peserta yang mencakup investor pemula dan trader aktif. Gunakan akun uji terpisah, instruksi tugas yang sama dan catat bantuan yang diberikan. Hasil lima peserta bersifat indikatif, bukan statistik seluruh pasar.
- Tugas A: cari saham → baca detail → simpan watchlist, target ≤90 detik pada ≥4 dari 5 peserta.
- Tugas B: hitung dan simpan rencana valid, target ≤3 menit pada ≥4 peserta. Peserta dapat menyebut modal, risiko nominal, lot dan asumsi biaya tanpa bantuan.
- Pemahaman: ≥4 peserta dapat menyebut sumber/tanggal harga, membedakan fetch dengan tanggal pasar, memahami unknown/stale dan menemukan kuota. Confidence tidak ditafsirkan sebagai peluang profit yang telah terkalibrasi.
- Observasi tujuh hari: catat peserta yang kembali pada hari berikutnya/hari ketujuh, keberhasilan tugas pantauan, alert relevan, kebingungan dan alasan berhenti. Tetapkan persetujuan pencatatan dan kumpulkan data minimum; jangan mengarang target retensi sebelum baseline tersedia.

**Selesai ketika:** ada catatan tugas, waktu, bantuan, temuan dan keputusan lanjut/perbaiki. Kegagalan target menghasilkan backlog berdasarkan hambatan yang diamati. Tidak mengisi hasil pilot dengan skor audit atau tes otomatis.

## 6. Urutan pengerjaan, dependensi dan estimasi

Estimasi adalah hari kerja engineer/QA, belum termasuk menunggu akses, lisensi, perangkat dan responden. Owner di bawah adalah peran, bukan orang yang sudah ditugaskan. Jangan menetapkan tanggal rilis sebelum dependensi siap.

| Paket | Owner peran | Dependensi | Estimasi teknis |
|---|---|---|---:|
| AF-01 | Frontend + QA | Tidak menunggu provider | 0,5–1 hari |
| AF-02 | Frontend + backend reviewer | Kontrak alert yang sudah tersedia | 0,25–0,5 hari |
| AF-03 | Frontend + QA | URL/router dan dataset pagination | 1–1,5 hari |
| QA-AF | QA + engineer | AF-01–03, build final | 0,5–1 hari |
| UX-01–04 | Frontend + produk | AF stabil; KP-08 untuk pemahaman manusia | 1,75–3,5 hari |
| KP-01 | Engineer + reviewer | Akses GitHub/CI; kandidat sesudah AF | 0,5–1 hari |
| KP-02 | Backend + operator + pemilik produk | Budget/hak penggunaan, secret, network | 2–4 hari |
| KP-03 | Backend + operator | KP-02; kalender/jadwal diterima | 1,5–3 hari |
| KP-04 | Backend + operator | Deployment/supervisor ditetapkan | 1,5–2,5 hari |
| KP-05 | Full stack + operator | SMTP/sender/egress/inbox | 1–1,5 hari |
| KP-06 | QA + frontend | Build kandidat dan perangkat/browser | 1–2 hari |
| KP-07 | Operator + QA | KP-01/04; staging disposable | 1,5–2,5 hari |
| KP-08 | Produk + QA | KP-02/03/05/06 untuk cakupan pilot penuh | 1–2 hari + observasi 7 hari |

**Paket koreksi audit AF-01–03 + QA-AF: 2,25–4 hari**, dapat dimulai tanpa key provider. **Paket UX: 1,75–3,5 hari**. **Kesiapan pilot KP-01–08: 10–18,5 hari**. QA-AF berfokus pada reproduksi/race/navigasi tiga bug; KP-01 mencakup CI remote, kandidat, panduan dan penerimaan regresi keseluruhan agar pekerjaan tidak dihitung dua kali.

Total seluruh cakupan indikatif **14–26 hari kerja teknis**, ditambah waktu tunggu dan observasi tujuh hari. Paket UX dapat ditunda sesuai dampak pilot. Estimasi belum mencakup tiga ide fitur baru, temuan tambahan di luar audit ini atau adapter pengganti jika evaluasi provider gagal.

Urutan yang disarankan:

1. **Tahap A:** AF-01 → AF-02/03 → QA-AF dan KP-01. Keluar ketika N05/N04/J10 lulus serta BUG-001–004 tetap tertutup. Prioritas paling awal adalah konteks compare dan identitas record.
2. **Tahap B:** UX-01–04 sesuai kapasitas, KP-04/06 dan persiapan staging. Pekerjaan independen dari provider dapat dimulai sambil menyiapkan akses; jangan mengalihkan prioritas dari tiga bug.
3. **Tahap C:** setelah akses tersedia, terima KP-02, operasikan KP-03 dan selesaikan KP-05. Jalankan KP-07 pada kandidat final, lalu KP-08/observasi tujuh hari. Perubahan kandidat memerlukan regresi yang terdampak.

## 7. Gerbang dan keputusan rilis

| Gerbang | Bukti wajib | Jika belum terpenuhi |
|---|---|---|
| Koreksi audit | AF-01–03/QA-AF lulus; empat regresi lama tetap lulus | BUG-005 menghalangi pilot investor; alert sinyal dan kesinambungan screener belum diterima. |
| Kandidat | SHA konsisten, audit 9c36fcf dipetakan, CI remote dan regresi pada kandidat baru lulus | Penerimaan final belum dapat ditutup. |
| Riset nyata | KP-02 diterima untuk IDX/AS dan model terpilih | Analisis dengan provider nyata belum diklaim siap pilot. |
| Alert otomatis | KP-03/04 diterima; jadwal/kalender/run/event dapat diverifikasi | Ingestion tetap nonaktif dan kesiapan alert otomatis tetap pending. |
| Pemulihan akun | KP-05 berhasil melalui inbox nyata | Pemulihan email tetap berstatus belum tersedia/diterima. |
| Perluasan publik | KP-06/07/08 diterima, nol P0/P1 pada cakupan rilis | Pilot terbatas pada cakupan yang sudah diterima; belum menjadi rilis publik. |

Setiap acceptance mencatat **lulus / gagal / terblokir / belum diuji**, SHA, environment, waktu, dataset, langkah, expected/actual dan artefak tersanitasi. Pemilik produk/operator menetapkan keputusan rilis berdasarkan cakupan yang benar-benar terbukti. Tes terkontrol dan layanan nyata dilaporkan terpisah.

## 8. Ide fitur setelah stabilisasi — belum menjadi komitmen implementasi

| Ide dari auditor | Nilai dan batas | Dependensi / syarat discovery |
|---|---|---|
| Perbandingan 2–3 saham | Membantu memilih kandidat sejajar; berbeda dari compare dua histori satu ticker. Currency tetap terpisah tanpa konversi buatan. | AF-01/03 stabil; tentukan metrik/tanggal yang sebanding dan validasi kebutuhan pada pilot. |
| Jurnal evaluasi rencana manual | Catat keputusan, pembatalan dan pelajaran; bedakan input pengguna dari data pasar/hasil broker. | Definisikan status, hak edit dan hubungan versi rencana; tidak mengirim order. |
| Perubahan watchlist sejak kunjungan terakhir | Ringkas perubahan tanggal/harga/rekomendasi dengan sumber yang tersedia. | Ingestion sah, snapshot kunjungan dan aturan perubahan; tidak disebut realtime. |

Ketiganya memerlukan discovery dan estimasi tersendiri setelah bug, layanan nyata dan hasil pilot ditinjau. Belum termasuk total hari kerja di atas.

## 9. Hal yang perlu tersedia saat pelaksanaan

- Paket audit dan commit target sudah tersedia serta dipetakan. Saat eksekusi, catat SHA perbaikan dan artefak retest agar penutupan bug dapat diperiksa.
- Pemilik keputusan provider/budget/lisensi dan secret/network yang aktif; jangan membeli layanan atau menganggap file proposal sudah diterapkan.
- Lingkungan staging, operator/supervisor, sender/inbox uji, perangkat dan lima responden.

Penyusunan dokumen ini memeriksa source, GitHub refs, laporan audit terbaru, JSON final, tiga screenshot dan checksum paket. Tidak menjalankan ulang aplikasi/test suite, mengubah source produk, melakukan merge/push, mengirim email atau mengaktifkan layanan eksternal. Seluruh angka runtime audit diatribusikan ke laporan sumber, bukan hasil run baru penulis PRD.
