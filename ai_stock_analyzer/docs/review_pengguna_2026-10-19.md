# Sumber feedback pengguna — 19 Oktober 2026

Sumber: feedback dari sesi “Edit ai-stock-analyzer” yang ditempelkan pengguna dalam percakapan ini. Teks review di bawah diarsipkan sebagai dasar [revisi PRD](prd_perbaikan_aplikasi.md). Review memeriksa commit `42d887a`; implementasi R1 pada `541c281` terjadi sesudah baseline tersebut.

Catatan bukti: berkas `results.json`, `backtest.json`, dan screenshot disebut dalam review, tetapi berkas aslinya tidak disertakan di percakapan ini. Revisi PRD memakai isi review dan inspeksi source saat ini; tidak mengklaim telah membuka artefak atau mengulang pengujian browser review tersebut.

---

# Review pengalaman pengguna AI Stock Analyzer

Tanggal: 19 Oktober 2026 (WIB). Commit: 42d887a, cocok dengan origin/main setelah git fetch.

## Ruang lingkup dan batas pengujian

Frontend Next.js dan backend FastAPI dijalankan lokal. Browser Chromium melalui Playwright dipakai untuk login dengan akun seed, membuka dashboard, detail BBCA.JK, ticker INVALIDXYZ, settings, watchlist, serta detail pada viewport 390 × 844. Database SQLite pengujian terpisah berada di /tmp; tidak memakai database produksi. Tidak mengubah source aplikasi.

Environment tidak memiliki API key Claude yang siap dipakai dan akses jaringan ke penyedia pasar tidak tersedia dalam daftar tujuan yang diizinkan. Karena itu keberhasilan analisis Claude dan data pasar terbaru belum diverifikasi. Backtest crash direproduksi memakai respons terkontrol yang mengikuti format aktual Backtester.get_results_dict(), bukan hasil transaksi pasar sungguhan. Registrasi, pembayaran, dan pemulihan password belum diuji menyeluruh.

## Yang sudah membantu pengguna

Navigasi Dashboard → detail → watchlist/backtest mudah ditemukan. Login akun seed berhasil. Dashboard dan watchlist dapat ditampilkan. Detail menyediakan chart candlestick, pilihan rentang, indikator dan ringkasan AI dalam satu tempat. Layout mobile menumpuk konten sehingga tetap dapat dibaca. Dasar produk cocok untuk riset saham Indonesia dan AS.

## Prioritas perbaikan

| Prioritas | Temuan dan bukti | Dampak dan perbaikan |
| --- | --- | --- |
| P0 | Detail INVALIDXYZ menampilkan chart acak, BULLISH 88%, RSI 65.40, MACD +2.15 dan Phase C. Label [MOCK DATA] hanya ada di ringkasan. Dashboard dan watchlist memakai harga/perubahan hardcoded tanpa label. | Data tidak tersedia terlihat seperti data investasi. Tampilkan status data kosong/error; pisahkan demo secara eksplisit dengan banner yang mencakup seluruh halaman. Jangan mengganti chart valid saat analisis AI gagal. |
| P0 | Tombol Analisis Ulang AI pada src/app/stock/[ticker]/page.tsx memanggil POST /stocks/{ticker}/sync. Handler itu hanya menyimpan harga dan indikator; analisis AI ada di POST /analysis/{ticker}. | Pesan sukses menjanjikan analisis yang tidak dijalankan. Hubungkan urutan sync → analisis → refresh, tampilkan tahap dan kegagalan masing-masing. |
| P0 | Frontend mengirim target_profit_pct:10 dan stop_loss_pct:5; BacktestRequest menerima target_profit dan stop_loss dalam pecahan, default 0.05 dan 0.03. Backend menghasilkan recent_trades; frontend membaca trades.length. | Parameter dapat diabaikan dan halaman crash. Respons mengikuti schema backend berhasil mereproduksi Cannot read properties of undefined (reading 'length'). Satukan kontrak request/response dan satuan. Backend sudah mengembalikan persen, frontend masih mengalikan 100. |
| P0 | Target AI di frontend selalu current_price × 1.05; riskLevel selalu MEDIUM; confidence kosong diganti 70. | Angka terlihat seperti hasil model. Ambil nilai terverifikasi dari API atau tampilkan belum tersedia. |
| P1 | Dashboard menampilkan AAPL Rp 224 dan MSFT Rp 412, sedangkan detail memakai dolar. | Gunakan metadata currency/exchange yang konsisten dan pembulatan harga yang sesuai. |
| P1 | Tombol 1H dan 1D sama-sama menampilkan lima hari dari candle harian. Rentang 1Y mengambil maksimal 100 bar. | Label tidak sesuai data. Pisahkan interval candle dengan rentang tanggal dan fetch histori yang cukup. |
| P1 | Settings menunjukkan Usage Today tanpa angka, hanya / Unlimited. UserResponse tidak menyertakan analysis_quota_used. | Pengguna tidak tahu pemakaian. Sertakan kuota terpakai, tersisa, reset berikutnya dan zona waktunya. |
| P1 | src/api/auth.ts mengunci base URL ke localhost:8000, sedangkan services/api.ts mendukung NEXT_PUBLIC_API_URL. | Login/registrasi berisiko gagal saat deployment. Pakai konfigurasi API bersama. Temuan berdasarkan source, bukan deployment eksternal. |
| P1 | Logout sidebar memanggil endpoint tanpa refresh_token, sedangkan endpoint meminta body. Logout settings mengirim body. | Pencabutan refresh token sidebar berpotensi gagal. Samakan implementasi dan verifikasi token lama ditolak. Temuan berdasarkan source. |
| P2 | Label komponen Input tidak terkait input lewat htmlFor; toggle password tidak punya nama aksesibel dan dilewati Tab. Tombol ikon header juga tanpa nama. | Perbaiki akses keyboard dan screen reader. Locator browser berbasis label tidak menemukan field login; pengujian memakai ID untuk melanjutkan. |
| P2 | Screenshot mobile menunjukkan tombol 1D–1Y kecil dan rapat, nama perusahaan generik pada detail, serta spasi antarikon/teks minim. | Perbesar area sentuh dan rapikan jarak; tampilkan metadata perusahaan secara independen dari keberhasilan analisis/chart. |
| P2 | Notifikasi sinkronisasi hari ini dan badge selalu statis. | Hubungkan dengan kejadian nyata atau hilangkan pesan sukses sampai data tersedia. |

## Fitur yang layak ditambahkan

1. **Transparansi data:** waktu harga dan analisis terakhir, sumber, status pasar, serta penanda delayed/stale. Ini mendukung penilaian semua fitur lain.
2. **Watchlist untuk pekerjaan harian:** pencarian ticker dengan autocomplete sebagai pengganti prompt, catatan yang dapat diedit, urutkan perubahan/harga, filter bursa, dan status sudah ditambahkan. Backend menyimpan notes, UI belum menyediakan pengelolaannya.
3. **Alert harga dan sinyal:** target harga, perubahan persentase, dan sinyal baru dengan preferensi notifikasi serta tautan ke saham terkait.
4. **Rencana transaksi:** area entry, stop loss, target, rasio reward/risk, horizon, kondisi pembatalan, dan kalkulator lot/modal. Sertakan alasan berbasis data yang tersedia.
5. **Screener:** filter sektor, bursa, volume, RSI, fase Wyckoff dan sinyal SMC; dapat menyimpan filter. AI picks saat ini hanya menyaring enam saham yang dimuat dashboard, bukan seluruh pasar.
6. **Riwayat analisis:** timestamp/model, bandingkan perubahan rekomendasi, dan export CSV/PDF. Confidence perlu penjelasan; jangan ditafsirkan sebagai peluang profit tanpa kalibrasi.
7. **Backtest yang dapat dinilai:** biaya transaksi/slippage, pembanding buy-and-hold, equity curve, jumlah sampel, hasil seluruh transaksi, dan drawdown berdasarkan equity curve. Implementasi sekarang memakai kerugian transaksi terburuk sebagai max drawdown.
8. **Akun dan onboarding:** lupa password, ubah password/profil di UI, pengenalan ticker .JK dan istilah indikator, serta penjelasan Free/Premium dan alur upgrade jika monetisasi direncanakan.

## Urutan pengerjaan yang disarankan

Tahap 1: hilangkan data contoh otomatis, benahi analisis AI dan kontrak backtest. Selesai ketika ticker invalid menghasilkan status jelas, analisis menghasilkan record baru, dan backtest mengikuti TP/SL input serta tampil tanpa crash.

Tahap 2: benahi mata uang, timestamp, timeframe, kuota, konfigurasi login dan logout. Verifikasi satu saham IDX dan satu saham AS dari dashboard hingga detail/watchlist.

Tahap 3: tambah pengelolaan watchlist dan alert, lalu screener dan riwayat analisis. Ukur waktu pengguna untuk menemukan saham, menyimpan rencana, dan kembali memantau.

Bukti browser: results.json, backtest.json dan screenshot di folder laporan ini.
