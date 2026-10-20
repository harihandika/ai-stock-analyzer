# AI Stock Analyzer

Perbaikan R1 tersedia pada checkout: [laporan implementasi dan cara menjalankan](docs/implementasi_r1.md), [PRD perbaikan](docs/prd_perbaikan_aplikasi.md). Gunakan Alembic untuk schema baru/upgrade; jangan mengandalkan create_tables.py untuk memigrasikan database lama.

Platform riset saham yang menggabungkan data teknikal, **Volume Price Analysis (VPA)**, **Wyckoff Theory**, **Smart Money Concepts (SMC)**, analisis AI, watchlist dan rencana transaksi.

---

## 🏗️ Tech Stack

| Layer | Teknologi |
|---|---|
| **Backend API** | Python 3.12, FastAPI |
| **Frontend UI** | Next.js 16.2.10 (App Router), React 19, Tailwind CSS 4, Lucide Icons |
| **Database** | PostgreSQL / SQLite (Development) |
| **ORM & Migration** | SQLAlchemy 2.0 (Async), Alembic |
| **Authentication** | JWT (python-jose), bcrypt (passlib), One-Time Refresh Token Rotation |
| **Cache & Observability** | Redis (dengan InMemory Fallback), Correlation ID Middleware |
| **AI Engine** | Anthropic atau Gemini, dipilih melalui konfigurasi server |
| **Analysis Engine** | pandas, pandas-ta, scipy, yfinance |
| **Background Worker** | Worker produk dengan antrean database; Celery lama terpisah |

---

## ✨ Fitur Utama

1. **SMC & Pattern Recognition Engine**:
   - **Order Blocks (Bullish & Bearish)**: Menemukan area jejak institusi/market maker.
   - **Liquidity Sweeps**: Mendeteksi jebakan *false breakout* pada area High/Low.
   - **Pola Klasik**: Mendeteksi pola *Cup & Handle* dan *Bull Flag*.
2. **Backtesting Strategi Trading**:
   - Pengujian histori interaktif berbasis Target Profit (%), Stop Loss (%), dan tahun histori.
   - Perhitungan otomatis *Win Rate*, *Average Profit*, *Max Drawdown*, dan *Trade History Table*.
3. **Manajemen Akun & Kuota Harian**:
   - Fitur logout aman di sisi server (*token revocation*).
   - Pengaturan profil & grafik pemakaian kuota harian (*Free: 3x/hari*, *Premium: Unlimited*).
4. **Interactive Dashboard & Stock Detail**:
   - Pencarian real-time dengan *debounce search*.
   - Chart OHLCV interaktif dengan pilihan timeframe (1W hingga 1Y).
   - Integrasi Watchlist pribadi dengan catatan (*notes*).

---

## 🚀 Cara Menjalankan (Development)

### 1. Prerequisites
- Python 3.12
- Node.js 24 (sesuai CI)
- Docker Desktop (opsional untuk PostgreSQL + Redis)
- API key provider AI yang dipilih untuk analisis nyata; kredensial/paket pasar sesuai sumber dan hak penggunaan. Pengujian fixture tidak memerlukannya.

### 2. Backend Setup (`ai_stock_analyzer`)

```bash
cd ai_stock_analyzer

# Buat virtual environment
uv venv --python 3.12 .venv

# Aktivasi Venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Siapkan .env dari .env.example bila belum ada; isi konfigurasi database
# dan secret melalui environment privat. Pertahankan file yang sudah ada.
# Terapkan migrasi sebelum API/worker dijalankan.
.venv/bin/alembic upgrade head

# Jalankan server FastAPI
uvicorn app.main:app --reload --port 8000
```

- **Swagger UI Documentation**: http://localhost:8000/docs
- **OpenAPI Schema Specification**: `docs/openapi.yaml`

### 3. Frontend Setup (`ai_stock_analyzer_frontend`)

```bash
cd ai_stock_analyzer_frontend

# Install dependencies
npm install

# Jalankan development server
npm run dev
```

Buka aplikasi di browser: **http://localhost:3000**

---

## 🧪 Menjalankan Unit & Integration Tests

```bash
cd ai_stock_analyzer
.venv/bin/python -m pytest tests/ -q
```

---

## 📖 Dokumentasi Lengkap & Changelog

- **[CHANGELOG.md](CHANGELOG.md)**: Catatan rilis lengkap dari Sprint 1 hingga Sprint 10.
- **[OpenAPI Spec](docs/openapi.yaml)**: Kontrak API yang diekspor dari runtime.
## Implementasi tindak lanjut PRD

Rencana lanjutan: [PRD 1.3 perbaikan audit dan kesiapan pilot](docs/prd_kesiapan_pilot_8d9645d.md), berdasarkan kandidat `8d9645d` dan [audit yang dipublikasikan pada 9c36fcf](docs/review_audit_8d9645d_2026-10-20.md). Prioritas awal: konteks perbandingan, alert sinyal dan pemulihan filter screener. [Catatan baseline](docs/status_baseline_8d9645d_2026-10-20.md) membedakan pekerjaan selesai, penerimaan yang masih terbuka dan status branch.

Operasional kandidat berikutnya: [runbook pilot](docs/operasional_pilot.md). Migrasi `r4_operations` menambahkan heartbeat worker dan riwayat ingestion; jalankan Alembic sebelum memperbarui API/worker. CLI status membedakan heartbeat/progres dari kredensial atau koneksi provider.

Pelaksanaan PRD 1.3, bukti tes/migrasi/restore dan gerbang eksternal yang masih terbuka dicatat pada [laporan 20 Oktober](docs/implementasi_prd_1_3_20261020.md). Gunakan [lembar penerimaan pilot](docs/pilot_acceptance_template.md) untuk pengukuran perangkat/responden dan layanan nyata.

Rencana setelah audit commit `d17f260`: [PRD 1.2 pasca-audit](docs/prd_perbaikan_pasca_audit_d17f260.md). Perbaikan kalkulator/header/CSS/chart, formulir bertahap, informasi data serta alat operasional dicatat dalam [laporan implementasi pasca-audit](docs/implementasi_pasca_audit_20261019.md), termasuk gerbang provider/email/pilot yang belum selesai.

Riset/pemantauan, job persisten, pilihan Gemini/EODHD, rencana transaksi, akun dan backtest berbiaya dijelaskan pada [laporan implementasi PRD](docs/implementasi_prd_20261019.md). Selain API dan frontend, jalankan worker produk terpisah dengan environment/database yang sama:

```bash
.venv/bin/alembic upgrade head
.venv/bin/python -m app.worker.product_worker
```

Worker memakai antrean pada database aplikasi; jangan memakai broker SQLite lama sebagai antrean produk. Penggunaan provider/email nyata tetap membutuhkan konfigurasi dan verifikasi sebagaimana laporan.
