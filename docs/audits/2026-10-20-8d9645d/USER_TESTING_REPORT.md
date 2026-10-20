# USER TESTING REPORT — AI Stock Analyzer

## A. Executive Summary

Tanggal: **20 Oktober 2026, WIB**. Commit diuji: **`8d9645df458c92efa01a5ec279ff98c4f2dee785`**, sama dengan HEAD `origin/work` pada awal dan akhir audit. Ini audit penggunaan aplikasi; source tidak diperbaiki, tidak ada commit/push/PR, ingestion berbayar atau email nyata.

**Kesimpulan:** empat bug audit sebelumnya sudah diperbaiki dan diverifikasi lewat browser produksi. Pengalaman mobile dan kalkulator meningkat. Tiga masalah lain dapat direproduksi: respons perbandingan lama muncul pada ticker baru (P1), alert sinyal gagal dibuat dari UI (P2), dan filter screener hilang saat Back (P2). Detail ada di [BUG_REPORT.md](BUG_REPORT.md).

| Hasil akhir | Jumlah skenario/observasi |
|---|---:|
| Lulus | 115 |
| Gagal | 3 |
| Terblokir | 5 |
| Belum diuji | 4 |
| Total | 127 |

Jumlah tersebut bukan persentase coverage source, jumlah pengguna manusia, atau jumlah bug. Tiga kegagalan akhir berasal dari tiga bug unik. Retest tidak dihitung sebagai skenario tambahan bila ID-nya sama. Catatan kegagalan harness dan koreksinya tetap disimpan.

### Environment dan batas bukti

- Frontend Next.js 16.2.10, **production build dengan webpack dan next start**. Build serta pemeriksaan TypeScript pada build berhasil; lihat [build.log](evidence/build.log).
- FastAPI dan worker produk dijalankan sebagai proses terpisah. Dependency yang sudah ada dipakai ulang, tanpa reinstall. Redis tidak tersedia dan cache fallback ke memory; antrean produk memakai database.
- Database audit baru yang disposable: SQLite `qa-browser-r1-20261020.db`, migrasi sampai `r3_read_paths`. Tidak mereset atau memakai database pengguna/produksi.
- Browser Chromium 154, desktop dan emulasi touch 320/360/390/430/768/1440 px, termasuk landscape 844×390. Tidak mengklaim hasil perangkat fisik atau Safari/Firefox.
- Karena checkout aktif masih versi 42d887a, audit memakai arsip target di luar checkout. Pemeriksaan 194 file tracked menunjukkan source snapshot identik dan checkout asli bersih; lihat [environment.json](evidence/environment.json).
- Provider pada browser memakai fixture penjaga `BROWSER_SMOKE=1` dan database khusus. Data 130 candle tahun 2025 serta skor 88% adalah fixture. Label provenance pada UI/record tidak menjadi bukti panggilan provider sungguhan.
- Satu record histori fixture tambahan dipakai untuk perbandingan 78→88. Simulasi alert memakai instrumen `ALERTQA.JK`, crossing 100→110, dan status fresh yang disimulasikan hanya untuk instrumen audit. Ini tidak memverifikasi ingestion atau kalender pasar nyata.
- Suite 114 test dan benchmark dalam laporan implementasi adalah bukti historis penulis repo, bukan hasil audit ini. Fokus audit adalah interaksi pengguna; hanya sampel oracle keuangan tambahan dijalankan.

## B. Real User Journey Results

### Pengguna baru dan investor pemula

Registrasi menampilkan kesalahan password pendek, lalu login berhasil. Dashboard menjelaskan bahwa aplikasi memantau harga penutupan harian dan analisis teknikal. Pencarian BBCA dapat ditemukan di header dan mengarah ke BBCA.JK. Pengguna dapat mencari AAPL dengan cara sama. Panduan/glosarium tersedia melalui navigasi; ini membantu, tetapi istilah bps, EMA, SMC dan provenance masih membutuhkan pembelajaran.

Sesudah login belum ada jalur utama yang menuntun pemula menjalankan tugas pertama. Auditor menggunakan pencarian dan panduan untuk melanjutkan. Ini penilaian kualitatif satu auditor yang menyimulasikan persona, bukan pengukuran pemahaman lima responden.

| Fitur | Aktivitas Pengguna | Hasil | Catatan UX |
|---|---|---|---|
| Akun | Register, password pendek, login, logout dan login ulang | Lulus J01/J18 | Validasi terlihat; token lama ditolak setelah logout. |
| Panduan/dashboard | Memahami fungsi, membuka glosarium | Lulus J02 | EOD dan skor model dijelaskan; ajakan tugas pertama dapat lebih jelas. |
| Analisis IDX | Cari BBCA, detail, harga/tanggal, chart, periode, AI, watchlist | Lulus J03–J06 fixture | Tanggal penutupan dan fetch dipisahkan; angka candle dapat dibaca tanpa hover. |
| Analisis AS | Cari AAPL, analisis dan watchlist | Lulus J06 fixture | USD/NASDAQ berbeda dengan IDR/IDX; tidak ada konversi mata uang buatan. |
| Indikator | Baca OHLCV, EMA, RSI, MACD dan nilai kosong | Lulus J05/M*-workflow | EMA 200 yang belum cukup histori tampil Belum tersedia. Wyckoff/SMC nyata belum divalidasi. |
| Watchlist | Tambah/hapus, notes, sorting, filter, reload | Lulus J08/N06 | Catatan bertahan. Selector awal J07 diperbaiki; lihat catatan retest. |
| Monitoring | Harga 105, baseline 100, crossing 110, jeda/aktif/delete | Lulus B01–B04 fixture | Baseline tidak memicu historis, crossing satu event tanpa duplikasi. |
| Alert sinyal | Pilih Sinyal AI baru/BUY lalu simpan | Gagal N04/R-signal | HTTP 422, pesan English meminta arah yang tidak tersedia pada form sinyal. |
| Screener | Kombinasi IDX, volume 1000, RSI 20–60; simpan/muat filter | Lulus J09/J11 | Filter tersimpan berguna dan input RSI salah ditolak. |
| Kembali dari screener | Buka BBCA dari hasil, lalu tombol Back browser | Gagal J10 | Bursa, volume dan RSI kembali kosong; pengguna harus memakai preset atau mengisi ulang. |
| Backtest | Modal, TP/SL, fee/slippage, dua run | Lulus J13 fixture | Parameter efektif sesuai. Histori utama sinus menghasilkan nol trade, jadi bukan bukti strategi menguntungkan. |
| Backtest nonnol | Baca dua transaksi ledger pada empat lebar | Lulus F01/F02 terkontrol | Winrate 50%, equity dan fee cocok oracle; renderer mendapat respons terkontrol, bukan provider nyata. |
| Trade planning | Hitung 20 lot→ubah modal→2 lot, simpan/edit/batal/reload | Lulus J14/J15,N01–N03 | Hasil lama hilang; payload lama yang terlambat tidak menjadi hasil aktif. |
| Riwayat | Baca, bandingkan 78→88, CSV/PDF | Lulus J16/X02 normal | Selisih 10poin persentase jelas. Pergantian ticker saat compare berjalan gagal N05. |
| Recovery | Ticker invalid, AI gagal,503 parsial, retry, sesi kedaluwarsa | Lulus J17/N07/N09/X03 | Tidak membuat chart/skor palsu; data yang tersedia bertahan. |

### Apakah lebih membantu daripada proses manual?

**Ya, untuk mengumpulkan chart, catatan, filter, perhitungan lot dan rencana di satu tempat.** Kalkulator mengurangi kebutuhan menyalin angka ke spreadsheet, dan preset membantu riset berulang. Namun manfaat keputusan investasi belum dapat diterima untuk penggunaan publik: konteks perbandingan dapat salah, alert sinyal tidak dapat dibuat, dan sumber pasar/model nyata belum diverifikasi. Tidak ada kesimpulan profitabilitas masa depan atau kualitas strategi dari fixture ini.

## C. Bug Findings dan validasi perbaikan lama

| Bug audit sebelumnya | Status akhir | Bukti runtime |
|---|---|---|
| BUG-001:hasil risiko basi | **Fixed and verified** | J14/J15,N01/N02 dan M*-workflow:20 lot→input berubah→hasil tidak aktif→2 lot. Save lambat mempertahankan draft baru. |
| BUG-002:header 320 px terpotong | **Fixed and verified** | Seluruh 60 pasangan halaman/lebar lulus bounding box; kontrol penting tidak disembunyikan. |
| BUG-003:padding utility 0 | **Fixed and verified** | M*-spacing: input p-3 computed 12 px; tab utama tinggi 44 px; build produksi. |
| BUG-004:tooltip hanya hover | **Fixed and verified** | Panel candle terlihat; long press 900 ms, slider keyboard dan reset latest berhasil; date/Close sesuai snapshot dataset. |

Temuan tambahan: **BUG-005 P1**(perbandingan lama untuk ticker lain), **BUG-006 P2**(alert sinyal 422), **BUG-007 P2**(konteks filter hilang saat Back). Reproduksi, expected/actual, screenshot dan akar masalah ditulis lengkap di [BUG_REPORT.md](BUG_REPORT.md).

## D. Mobile Testing Results

| Lebar | Sepuluh halaman | Interaksi penting | Hasil akhir |
|---|---|---|---|
|320 px|10/10 geometri lulus|Hamburger, search, sentuhan candle, slider, kalkulator, modal, save/edit, backtest|Lulus emulasi|
|360 px|10/10 geometri lulus|Navigasi, search, touch/slider, kalkulator, dialog dan Escape|Lulus emulasi|
|390 px|10/10 geometri lulus|Alur yang sama, save/edit, backtest, orientasi 844×390|Lulus setelah retest pembacaan DOM atomik|
|430 px|10/10 geometri lulus|Navigasi, search, touch/slider, kalkulator, dialog|Lulus emulasi|
|768 px|10/10 geometri lulus|Tablet, touch, form, dialog dan keyboard|Lulus emulasi|
|1440 px|10/10 geometri lulus|Desktop, keyboard, slider, form dan dropdown|Lulus desktop|

Halaman yang diperiksa: dashboard, watchlist, detail, backtest, screener, histori, monitoring, rencana, settings, panduan. Geometri mengukur bounding box kontrol, bukan hanya scrollWidth. Panel indikator memiliki nilai tekstual; null tidak diubah menjadi nol. Modal berada di dalam lebar viewport, Escape menutup dan fokus kembali ke pemicu akun. Tabel transaksi yang lebih lebar mendapat scroll horizontal dalam kontainernya.

Bukti contoh: [header/form320 px](evidence/screen-320-plans.png), [candle320 px](evidence/chart-interaction-320.png), [candle390 px](evidence/chart-interaction-390.png), [rencana tersimpan 390 px](evidence/mobile-saved-390.png), [tabel320 px](evidence/backtest-trades-320.png), [landscape](evidence/landscape.png).

Screenshot menangkap posisi scroll saataksi; fullPage tidak selalu menangkap seluruh isi scroll container. Interaksi sentuh merupakan emulasi/CDP. Virtual keyboard fisik, pinch/scroll pada iOS asli dan screen reader manual belum diuji. Jangan menyetarakan hasil ini dengan sertifikasi Android/iPhone.

## E. UX/UI Improvements

Lima masalah paling mengganggu, berdasarkan observasi:

1. **Perbandingan dapat menampilkan data ticker sebelumnya.** Risiko salah konteks lebih penting daripada kosmetik(P1).
2. **Alert sinyal tidak dapat disimpan.** Pesan raw English tentang above/below tidak bisa diperbaiki oleh pengguna melalui form tersebut(P2).
3. **Hasil kerja filter hilang saat Back.** Ini memperlambat membandingkan beberapa kandidat(P2).
4. **Badge notifikasi terlambat mengikuti mark-read.** API mengembalikan unread0, tetapi header masih1 sampai polling berikutnya. Ini observasiUX, bukan bug finansial baru.
5. **Bahasa dan istilah belum konsisten.** Backtest memakai Configuration, Run Backtest, Trade History; pemula harus menghubungkan istilah itu dengan panduan Indonesia.

Spacing, panel candle dan form bertahap adalah peningkatan nyata dan perlu dipertahankan. Perbaikan rinci kondisi-sekarang→alur-usulan ada di [UX_FEATURE_RECOMMENDATIONS.md](UX_FEATURE_RECOMMENDATIONS.md).

## F. New Feature Recommendations

Tiga usulan tambahan, sesudah bug ditangani: perbandingan beberapa saham, jurnal evaluasi rencana dengan input manual, dan ringkasan perubahan watchlist sejak kunjungan terakhir. Ketiganya dipisahkan dari perbaikan bug/UX pada dokumen rekomendasi. Tidak mengusulkan ulang screener, alert, histori, watchlist, ekspor atau kalkulator yang sudah tersedia; tidak mengusulkan eksekusi broker otomatis.

## G. Final Assessment

Skor merupakan penilaian auditor atas cakupan ini, bukan survei manusia atau hasil produksi.

| Dimensi | Skor 0–10 | Dasar dan keterbatasan |
|---|---:|---|
| Ease of Use | 7,5 | Register, pencarian dan kalkulator bertahap mudah dijalankan; kosakata teknis, bahasa campuran dan hilangnya filter masih menghambat. |
| Feature Usability | 7 | Watchlist, preset, rencana, ekspor dan alert harga bekerja; alert sinyal gagal dari UI dan perbandingan memiliki masalah konteks. |
| Financial Data Trustworthiness | 6 | Angka fixture konsisten dan oracle biaya cocok; bug perbandingan beda ticker berisiko menyesatkan. Provider/adjustment nyata belum diterima. |
| Desktop UX | 8 | Spacing dan hierarki tanggal lebih jelas pada build produksi; konteks screener dan perbandingan perlu diperbaiki. |
| Mobile UX | 8 | Enam lebar, header, dialog, sentuhan, slider, hitung/simpan rencana dan backtest dapat digunakan. Perangkat fisik belum diuji. |
| Stability | 7 | Tidak ada pageerrorJS pada suite journey/negative/mobile; recovery503 dan request rencana lambat bekerja. Race pada perbandingan masih terbuka. |
| Overall Product Quality | 7,5 | Peningkatan nyata terhadap d17f260, tetapi tiga bug baru dan gerbang provider/operasional menahan rilis publik. |

**Kesiapan: belum siap untuk rilis publik bagi investor nyata.** Layak melanjutkan pilot internal terkontrol. SelesaikanP1perbandingan, perbaiki alert/konteksriset, lalu terima provider nyata dan operasional sesuai cakupan rilis. Sepuluh prioritas dirinci dalam dokumen rekomendasi.

## Matriks eksekusi dan bukti

Rawcase/log berada di folder evidence. Status akhir berikut menyertakan retest; tidak ada klaim100% coverage.

| ID | Skenario | Hasil akhir | Bukti |
|---|---|---|---|
| J01 | Pengguna baru: register, validasi password dan login | Passed | [journey](evidence/journey.json) |
| J02 | Memahami dashboard dan panduan pertama kali | Passed | [journey](evidence/journey.json) |
| J03 | Cari BBCA lalu buka detail dengan keyboard | Passed | [journey](evidence/journey.json) |
| J04 | Analisis BBCA melalui worker, baca alasan dan sumber | Passed | [journey](evidence/journey.json) |
| J05 | Ubah periode chart dan baca OHLC/indikator | Passed | [journey](evidence/journey.json) |
| J06 | Tambah watchlist dan ulangi analisis AAPL | Passed | [journey](evidence/journey.json) |
| J07 | Watchlist catatan, urutan harga, filter dan reload | Passed | [journey](evidence/journey.json); retest N06 |
| J08 | Tambah/hapus watchlist lewat modal dan escape | Passed | [journey](evidence/journey.json) |
| J09 | Screener kombinasi filter dan preset tersimpan | Passed | [journey](evidence/journey.json) |
| J10 | Buka hasil screener lalu browser Back mempertahankan konteks | Failed | [journey](evidence/journey.json) |
| J11 | Muat ulang preset dan tangani filter tidak valid | Passed | [journey](evidence/journey.json) |
| J12 | Buat alert harga, jeda/aktifkan, pahami status | Passed | [journey](evidence/journey.json) |
| J13 | Backtest modal/fee/slippage dan dua parameter | Passed | [journey](evidence/journey.json) |
| J14 | Trade plan dasar20 lot lalu ubah modal menjadi 2 lot | Passed | [journey](evidence/journey.json) |
| J15 | Simpan rencana: validasi uraian, refresh, edit dan batal | Passed | [journey](evidence/journey.json) |
| J16 | Histori dan eksporCSV/PDF tersimpan | Passed | [journey](evidence/journey.json) |
| J17 | Ticker invalid dan providerAI gagal tanpa sinyal buatan | Passed | [journey](evidence/journey.json) |
| J18 | Settings, kuota, logout dan login ulang | Passed | [journey](evidence/journey.json) |
| M320-dashboard | dashboard: kontrol dan isi 320 px | Passed | [mobile](evidence/mobile.json) |
| M320-watchlist | watchlist: kontrol dan isi 320 px | Passed | [mobile](evidence/mobile.json) |
| M320-detail | detail: kontrol dan isi 320 px | Passed | [mobile](evidence/mobile.json) |
| M320-backtest | backtest: kontrol dan isi 320 px | Passed | [mobile](evidence/mobile.json) |
| M320-screener | screener: kontrol dan isi 320 px | Passed | [mobile](evidence/mobile.json) |
| M320-history | history: kontrol dan isi 320 px | Passed | [mobile](evidence/mobile.json) |
| M320-monitoring | monitoring: kontrol dan isi 320 px | Passed | [mobile](evidence/mobile.json) |
| M320-plans | plans: kontrol dan isi 320 px | Passed | [mobile](evidence/mobile.json) |
| M320-settings | settings: kontrol dan isi 320 px | Passed | [mobile](evidence/mobile.json) |
| M320-guide | guide: kontrol dan isi 320 px | Passed | [mobile](evidence/mobile.json) |
| M320-workflow | Navigasi, pencarian, candle, watchlist dan kalkulator 320 px | Passed | [mobile](evidence/mobile.json) |
| M320-spacing | Padding dan target sentuh tab 320 px | Passed | [mobile](evidence/mobile.json) |
| M320-dialog | Modal watchlist dan dropdown akun 320 px | Passed | [mobile](evidence/mobile.json) |
| M360-dashboard | dashboard: kontrol dan isi 360 px | Passed | [mobile](evidence/mobile.json) |
| M360-watchlist | watchlist: kontrol dan isi 360 px | Passed | [mobile](evidence/mobile.json) |
| M360-detail | detail: kontrol dan isi 360 px | Passed | [mobile](evidence/mobile.json) |
| M360-backtest | backtest: kontrol dan isi 360 px | Passed | [mobile](evidence/mobile.json) |
| M360-screener | screener: kontrol dan isi 360 px | Passed | [mobile](evidence/mobile.json) |
| M360-history | history: kontrol dan isi 360 px | Passed | [mobile](evidence/mobile.json) |
| M360-monitoring | monitoring: kontrol dan isi 360 px | Passed | [mobile](evidence/mobile.json) |
| M360-plans | plans: kontrol dan isi 360 px | Passed | [mobile](evidence/mobile.json) |
| M360-settings | settings: kontrol dan isi 360 px | Passed | [mobile](evidence/mobile.json) |
| M360-guide | guide: kontrol dan isi 360 px | Passed | [mobile](evidence/mobile.json) |
| M360-workflow | Navigasi, pencarian, candle, watchlist dan kalkulator 360 px | Passed | [mobile](evidence/mobile.json) |
| M360-spacing | Padding dan target sentuh tab 360 px | Passed | [mobile](evidence/mobile.json) |
| M360-dialog | Modal watchlist dan dropdown akun 360 px | Passed | [mobile](evidence/mobile.json) |
| M390-dashboard | dashboard: kontrol dan isi 390 px | Passed | [mobile](evidence/mobile.json) |
| M390-watchlist | watchlist: kontrol dan isi 390 px | Passed | [mobile](evidence/mobile.json) |
| M390-detail | detail: kontrol dan isi 390 px | Passed | [mobile](evidence/mobile.json) |
| M390-backtest | backtest: kontrol dan isi 390 px | Passed | [mobile](evidence/mobile.json) |
| M390-screener | screener: kontrol dan isi 390 px | Passed | [mobile](evidence/mobile.json) |
| M390-history | history: kontrol dan isi 390 px | Passed | [mobile](evidence/mobile.json) |
| M390-monitoring | monitoring: kontrol dan isi 390 px | Passed | [mobile](evidence/mobile.json) |
| M390-plans | plans: kontrol dan isi 390 px | Passed | [mobile](evidence/mobile.json) |
| M390-settings | settings: kontrol dan isi 390 px | Passed | [mobile](evidence/mobile.json) |
| M390-guide | guide: kontrol dan isi 390 px | Passed | [mobile](evidence/mobile.json) |
| M390-workflow | Navigasi, pencarian, candle, watchlist dan kalkulator 390 px | Passed | [mobile](evidence/mobile.json); retest evidence/mobile-retest.json |
| M390-spacing | Padding dan target sentuh tab 390 px | Passed | [mobile](evidence/mobile.json); retest evidence/mobile-retest.json |
| M390-dialog | Modal watchlist dan dropdown akun 390 px | Passed | [mobile](evidence/mobile.json); retest evidence/mobile-retest.json |
| M-landscape | Perubahan orientasi390→844→390 dan chart | Passed | [mobile](evidence/mobile.json); retest evidence/mobile-retest.json |
| M430-dashboard | dashboard: kontrol dan isi 430 px | Passed | [mobile](evidence/mobile.json) |
| M430-watchlist | watchlist: kontrol dan isi 430 px | Passed | [mobile](evidence/mobile.json) |
| M430-detail | detail: kontrol dan isi 430 px | Passed | [mobile](evidence/mobile.json) |
| M430-backtest | backtest: kontrol dan isi 430 px | Passed | [mobile](evidence/mobile.json) |
| M430-screener | screener: kontrol dan isi 430 px | Passed | [mobile](evidence/mobile.json) |
| M430-history | history: kontrol dan isi 430 px | Passed | [mobile](evidence/mobile.json) |
| M430-monitoring | monitoring: kontrol dan isi 430 px | Passed | [mobile](evidence/mobile.json) |
| M430-plans | plans: kontrol dan isi 430 px | Passed | [mobile](evidence/mobile.json) |
| M430-settings | settings: kontrol dan isi 430 px | Passed | [mobile](evidence/mobile.json) |
| M430-guide | guide: kontrol dan isi 430 px | Passed | [mobile](evidence/mobile.json) |
| M430-workflow | Navigasi, pencarian, candle, watchlist dan kalkulator 430 px | Passed | [mobile](evidence/mobile.json) |
| M430-spacing | Padding dan target sentuh tab 430 px | Passed | [mobile](evidence/mobile.json) |
| M430-dialog | Modal watchlist dan dropdown akun 430 px | Passed | [mobile](evidence/mobile.json) |
| M768-dashboard | dashboard: kontrol dan isi 768 px | Passed | [mobile](evidence/mobile.json) |
| M768-watchlist | watchlist: kontrol dan isi 768 px | Passed | [mobile](evidence/mobile.json) |
| M768-detail | detail: kontrol dan isi 768 px | Passed | [mobile](evidence/mobile.json) |
| M768-backtest | backtest: kontrol dan isi 768 px | Passed | [mobile](evidence/mobile.json) |
| M768-screener | screener: kontrol dan isi 768 px | Passed | [mobile](evidence/mobile.json) |
| M768-history | history: kontrol dan isi 768 px | Passed | [mobile](evidence/mobile.json) |
| M768-monitoring | monitoring: kontrol dan isi 768 px | Passed | [mobile](evidence/mobile.json) |
| M768-plans | plans: kontrol dan isi 768 px | Passed | [mobile](evidence/mobile.json) |
| M768-settings | settings: kontrol dan isi 768 px | Passed | [mobile](evidence/mobile.json) |
| M768-guide | guide: kontrol dan isi 768 px | Passed | [mobile](evidence/mobile.json) |
| M768-workflow | Navigasi, pencarian, candle, watchlist dan kalkulator 768 px | Passed | [mobile](evidence/mobile.json) |
| M768-spacing | Padding dan target sentuh tab 768 px | Passed | [mobile](evidence/mobile.json) |
| M768-dialog | Modal watchlist dan dropdown akun 768 px | Passed | [mobile](evidence/mobile.json) |
| M1440-dashboard | dashboard: kontrol dan isi 1440 px | Passed | [mobile](evidence/mobile.json) |
| M1440-watchlist | watchlist: kontrol dan isi 1440 px | Passed | [mobile](evidence/mobile.json) |
| M1440-detail | detail: kontrol dan isi 1440 px | Passed | [mobile](evidence/mobile.json) |
| M1440-backtest | backtest: kontrol dan isi 1440 px | Passed | [mobile](evidence/mobile.json) |
| M1440-screener | screener: kontrol dan isi 1440 px | Passed | [mobile](evidence/mobile.json) |
| M1440-history | history: kontrol dan isi 1440 px | Passed | [mobile](evidence/mobile.json) |
| M1440-monitoring | monitoring: kontrol dan isi 1440 px | Passed | [mobile](evidence/mobile.json) |
| M1440-plans | plans: kontrol dan isi 1440 px | Passed | [mobile](evidence/mobile.json) |
| M1440-settings | settings: kontrol dan isi 1440 px | Passed | [mobile](evidence/mobile.json) |
| M1440-guide | guide: kontrol dan isi 1440 px | Passed | [mobile](evidence/mobile.json) |
| M1440-workflow | Navigasi, pencarian, candle, watchlist dan kalkulator 1440 px | Passed | [mobile](evidence/mobile.json) |
| M1440-spacing | Padding dan target sentuh tab 1440 px | Passed | [mobile](evidence/mobile.json) |
| M1440-dialog | Modal watchlist dan dropdown akun 1440 px | Passed | [mobile](evidence/mobile.json) |
| N01 | Hitung lambat tidak mengaktifkan hasil modal lama | Passed | [negative](evidence/negative.json) |
| N02 | Simpan lambat tidak menimpa draft terbaru | Passed | [negative](evidence/negative.json) |
| N03 | Kalkulator inputinvalid dan errorAPI tidak memakai hasil lama | Passed | [negative](evidence/negative.json) |
| N04 | Alert sinyalBUY dapat dibuat dari UI | Failed | [negative](evidence/negative.json); retest evidence/signal-retest.json |
| N05 | Response perbandingan lama tidak muncul setelah ticker diganti | Failed | [negative](evidence/negative.json) |
| N06 | Watchlist: catatan/filter/sorting dengan selector label aktual | Passed | [negative](evidence/negative.json) |
| N07 | Kegagalanparsial AI mempertahankan chart, retry pulih | Passed | [negative](evidence/negative.json) |
| N08 | Badge data lama bertahan walau waktu fetch baru | Passed | [negative](evidence/negative.json) |
| N09 | Sesi expired tanpa refresh kembali ke login | Passed | [negative](evidence/negative.json) |
| B01 | Buat alertharga dan baselinefixture100tanpatrigger | Passed | [notifications](evidence/notifications.json) |
| B02 | Perubahanfixture100→110memicu satu notifikasi dan dedup | Passed | [notifications](evidence/notifications.json) |
| B03 | Markread mengubah status event dan countAPI | Passed | [notifications](evidence/notifications.json) |
| B04 | Pause/resume/delete alert tersimpan | Passed | [notifications](evidence/notifications.json) |
| X01 | Harga/currency/tanggal konsisten dashboard-detail-watchlist | Passed | [extra](evidence/extra.json) |
| X02 | Perbandingan normal 78→88 menyebut poin persentase | Passed | [extra](evidence/extra.json) |
| X03 | Kegagalan watchlist lambat dan pemulihan | Passed | [extra](evidence/extra.json) |
| X04 | AlertsignalAPI valid bila direction tidak dikirim | Passed | [extra](evidence/extra.json) |
| X-mobile-320 | Simpan/edit rencana dan jalankan backtest pada 320 px | Passed | [extra](evidence/extra.json) |
| X-mobile-390 | Simpan/edit rencana dan jalankan backtest pada 390 px | Passed | [extra](evidence/extra.json) |
| F01 | Oracle independen dua transaksi dengan biaya/slippage pada engine target | Passed | [financial-sample](evidence/financial-sample.json) |
| F02 | Renderdua trade ledger dan persen di320/390/768/1440 px | Passed | [filled-backtest](evidence/filled-backtest.json) |
| G01 | Integrasi AI Anthropic/Gemini nyata | Blocked | [limitations](evidence/market-status.json) |
| G02 | Integrasi pasar Yahoo/EODHD nyata IDX+AS | Blocked | [limitations](evidence/market-status.json) |
| G03 | Ingestion/trigger alert pasar nyata | Blocked | [limitations](evidence/market-status.json) |
| G04 | Email reset nyata | Blocked | [limitations](evidence/market-status.json) |
| G05 | Android/iPhone fisik | Blocked | [limitations](evidence/market-status.json) |
| T01 | Pilot manusia investor pemula/trader dan screen reader lengkap | Not Tested | [limitations](evidence/market-status.json) |
| T02 | Firefox/WebKit, virtual keyboard fisik dan variasi zoom penuh | Not Tested | [limitations](evidence/market-status.json) |
| T03 | Staging, soak tujuh hari, load dan PostgreSQL pada audit ini | Not Tested | [limitations](evidence/market-status.json) |
| T04 | Validitas pola Wyckoff/SMC pada dataset pasar nyata | Not Tested | [limitations](evidence/market-status.json) |

### Koreksi harness dan batas tambahan

- J07 awal berhenti karena selectlabel exact. N06 menyelesaikan sorting/filter/notes/reload melalui selector yang benar; hasilnya lulus.
- N04 awal memakai label Sinyal yang ambigu. Retest menggunakan select yang benar dan menemukan kegagalan aplikasi nyata:direction null/422.
- M390-workflowawal membaca tanggal dan nilai pada dua waktu saat crosshair masihbergerak. Retest mengambil satu snapshot DOM yang sama; tidak ada ketidaksesuaian tanggal/harga. M390-spacing awal tidak mencapai form karena kegagalan sebelumnya; retest lulus.
- Market/provider, ingestion nyata, SMTP dan perangkat fisik tetapBlocked. Semua riwayatAI dan harga pada audit ini berasal fixture, bukan bukti kualitas/akurasi data pasar nyata.
