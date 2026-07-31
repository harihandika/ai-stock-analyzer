# Panduan Lengkap Penggunaan AI Stock Analyzer

Aplikasi **AI Stock Analyzer** adalah platform cerdas untuk menganalisis saham menggunakan kombinasi indikator teknikal klasik, pola pergerakan harga modern (Smart Money Concepts / SMC, Wyckoff Theory), analisis statistik historis (Backtesting), dan kecerdasan buatan (AI) berbasis model Claude 3.5 Sonnet.

---

## 1. Ringkasan Fitur Utama

### 🔐 A. Keamanan & Manajemen Akun
- **Otentikasi Token Ganda (JWT Access & Refresh Token)**: Keamanan tingkat lanjut dengan otentikasi JWT yang aman.
- **Server-Side Revocation & Token Rotation**: Fitur logout yang menghapus token di sisi server dan perputaran token sekali pakai (One-Time Use) untuk mencegah peretasan token.
- **Pengaturan Akun & Kuota (`/settings`)**: Halaman khusus untuk melihat profil pengguna, status langganan (*Free* vs *Premium*), dan grafik penggunaan kuota harian.

### 📊 B. Eksplorasi Saham & Charting Interaktif
- **Pencarian Real-Time**: Pencarian emiten saham (IHSG / US Stock) secara cepat dengan dukungan *debounce search*.
- **Grafik OHLCV Dynamic**: Visualisasi grafik harga saham historis (Open, High, Low, Close, Volume) dengan opsi timeframe interaktif (1W, 1M, 3M, 6M, 1Y).

### ⚙️ C. Engine Analisis Teknikal & Pola Otomatis
- **Indikator Dasar**: RSI (14), EMA (20, 50, 200), MACD, VWAP, ATR, dan OBV.
- **Volume Price Analysis (VPA)**: Mendeteksi sinyal anomali volume (*Stopping Volume*, *No Demand*, *Climactic Volume*).
- **Smart Money Concepts (SMC Engine)**:
  - *Order Blocks (Bullish & Bearish)*: Area jejak institusi/market maker.
  - *Liquidity Sweeps*: Mendeteksi pergerakan jebakan *false breakout* pada harga tertinggi/terendah.
  - *Fair Value Gap (FVG)*, *Break of Structure (BOS)*, dan *Change of Character (CHOCH)*.
- **Pola Klasik (Pattern Engine)**:
  - *Cup & Handle*: Pola kelanjutan tren naik dengan konsolidasi mangkuk.
  - *Bull Flag*: Pola tiang bendera lonjakan harga dan fase *retest*.
  - *Double Bottom* & Wyckoff Accumulation Phase (Phase A - E).

### 🤖 D. Kecerdasan Buatan (Claude AI Engine)
- **AI Recommendation**: Sinyal rekomendasi otomatis (`BULLISH`, `BEARISH`, atau `NEUTRAL`).
- **AI Summary & Insight**: Penjelasan komprehensif dalam bahasa profesional mengenai kombinasi fundamental, VPA, SMC, dan Wyckoff phase.
- **Confidence Score & Risk Level**: Skor tingkat keyakinan analisis (0-100%) beserta perkiraan risiko.

### 🧪 E. Backtest Strategi Trading (`/stock/[ticker]/backtest`)
- **Simulasi Parameter Interaktif**: Pengujian strategi historis dengan kustomisasi jumlah tahun histori, Target Profit (%), dan Stop Loss (%).
- **Stats Grid & Metric Summary**: Menampilkan statistik akurasi strategi mencakup *Win Rate (%)*, *Total Trades*, *Average Profit (%)*, dan *Max Drawdown (%)*.
- **Tabel Trade History**: Rincian tanggal eksekusi *Buy/Sell*, harga eksekusi, persentase profit, status transaksi (*WIN/LOSS*), dan alasan eksekusi (*reason*).

---

## 2. Struktur Menu & Navigasi

Aplikasi memiliki tata letak (*Layout*) modern berbasis *Glassmorphism* dan *Dark Theme* dengan navigasi berikut:

### 📱 Sidebar Utama (Sebelah Kiri)
1. **Dashboard (`/dashboard`)**: Ringkasan pasar, analisis terbaru, dan tren saham terkini.
2. **Watchlist (`/watchlist`)**: Daftar pantauan emiten pribadi beserta catatan khusus (*notes*).
3. **Settings (`/settings`)**: Pengaturan akun, rincian *tier*, pemakaian kuota harian, dan tombol *Log Out*.

### 🔍 Top Header (Bagian Atas)
- **Search Bar**: Pencarian cepat ticker atau nama perusahaan (misal: `BBCA`, `TLKM`, `AAPL`).
- **Notifikasi (Bell Icon)**: Informasi dan notifikasi pembaruan analisis.
- **Profil Dropdown (Settings Icon)**: Akses cepat ke Halaman Profil dan *Sign Out*.

---

## 3. Fitur Berdasarkan Peran Pengguna (Per User Role)

| Fitur | Guest (Tanpa Login) | Free User | Premium User | Admin |
|---|:---:|:---:|:---:|:---:|
| Registrasi & Login | ✅ | ✅ | ✅ | ✅ |
| Cari Saham & Liat Chart | ✅ | ✅ | ✅ | ✅ |
| Tambah & Kelola Watchlist | ❌ | ✅ | ✅ | ✅ |
| Lihat Analisis AI Terakhir | ❌ | ✅ | ✅ | ✅ |
| Request AI Analysis Real-Time | ❌ | Max 3x / hari | ♾️ Unlimited | ♾️ Unlimited |
| Jalankan Simulasi Backtest | ❌ | ✅ Standard | ✅ Fast & Deep | ✅ Unlimited |
| Forced Sync Data Bursa | ❌ | ❌ | ❌ | ✅ Manual Trigger |

---

## 4. Panduan Langkah Demi Langkah Penggunaan

### 📍 Langkah 1: Pendaftaran & Masuk Ke Sistem
1. Akses halaman `/login` atau `/register`.
2. Masukkan **Nama Lengkap**, **Email**, dan **Password** pada form registrasi.
3. Setelah login berhasil, Anda akan dialihkan ke **Dashboard**.

### 📍 Langkah 2: Mencari dan Membaca Detail Saham
1. Ketik nama emiten atau kode ticker (misal: `BBCA` atau `NVDA`) di kolom **Search Bar** di bagian atas header.
2. Klik emiten yang sesuai dari daftar pencarian.
3. Halaman **Stock Detail** akan menampilkan:
   - Grafik Pergerakan Harga (Candlestick Chart) dengan pengubah timeframe (1W hingga 1Y).
   - Laporan Analisis AI (Target Price, Rekomendasi, Confidence Score, AI Summary).
   - Indikator Advanced (RSI, MACD, Volume VPA, dan Wyckoff Phase).

### 📍 Langkah 3: Menambahkan Saham ke Watchlist
1. Pada halaman Detail Saham, klik tombol **"Tambah Watchlist"**.
2. Saham akan secara otomatis disimpan di menu **Watchlist**.
3. Buka menu **Watchlist** dari sidebar kiri untuk memantau pergerakan seluruh emiten favorit Anda dalam satu tampilan.

### 📍 Langkah 4: Melakukan Backtesting Strategi
1. Pada halaman Detail Saham, klik tombol **"Backtest"** di sebelah header saham.
2. Anda akan diarahkan ke halaman `/stock/[ticker]/backtest`.
3. Atur parameter simulasi sesuai gaya trading Anda:
   - **Period (Years)**: Geser slider (1 - 5 Tahun).
   - **Target Profit (%)**: Masukkan target takeprofit (contoh: 10%).
   - **Stop Loss (%)**: Masukkan batas toleransi risiko (contoh: 5%).
4. Klik tombol **"Run Backtest"**.
5. Pelajari hasil *Win Rate*, *Max Drawdown*, dan daftar transaksi pada *Trade History*.

### 📍 Langkah 5: Memeriksa Kuota AI & Pengaturan Akun
1. Buka menu **Settings** pada sidebar atau melalui dropdown profil di kanan atas.
2. Lihat status kuota harian Anda pada bagian **AI Analysis Quota**.
3. Jika kuota *Free User* Anda habis (3/3), kuota akan otomatis di-reset pada hari berikutnya.
4. Klik **Log Out** untuk keluar dari sesi secara aman.
