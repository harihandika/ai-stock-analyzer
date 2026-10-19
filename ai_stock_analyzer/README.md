# AI Stock Analyzer

Perbaikan R1 tersedia pada checkout: [laporan implementasi dan cara menjalankan](docs/implementasi_r1.md), [PRD perbaikan](docs/prd_perbaikan_aplikasi.md). Gunakan Alembic untuk schema baru/upgrade; jangan mengandalkan create_tables.py untuk memigrasikan database lama.

Platform analisis saham berbasis AI yang menggunakan **Volume Price Analysis (VPA)**, **Wyckoff Theory**, dan **Smart Money Concepts (SMC)** untuk mengidentifikasi peluang investasi dengan probabilitas tinggi.

---

## 🏗️ Tech Stack

| Layer | Teknologi |
|---|---|
| **Backend API** | Python 3.12, FastAPI |
| **Frontend UI** | Next.js 14 (App Router), React, Tailwind CSS, Lucide Icons |
| **Database** | PostgreSQL / SQLite (Development) |
| **ORM & Migration** | SQLAlchemy 2.0 (Async), Alembic |
| **Authentication** | JWT (python-jose), bcrypt (passlib), One-Time Refresh Token Rotation |
| **Cache & Observability** | Redis (dengan InMemory Fallback), Correlation ID Middleware |
| **AI Engine** | Claude 3.5 Sonnet (Anthropic SDK) |
| **Analysis Engine** | pandas, pandas-ta, scipy, yfinance |
| **Background Worker** | Celery + Redis |

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
- Node.js 18+ (untuk Frontend Next.js)
- Docker Desktop (opsional untuk PostgreSQL + Redis)
- Akun Anthropic (untuk API Key Claude)

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

Rencana setelah audit commit `d17f260`: [PRD 1.2 pasca-audit](docs/prd_perbaikan_pasca_audit_d17f260.md). Perbaikan kalkulator/header/CSS/chart, formulir bertahap, informasi data serta alat operasional dicatat dalam [laporan implementasi pasca-audit](docs/implementasi_pasca_audit_20261019.md), termasuk gerbang provider/email/pilot yang belum selesai.

Riset/pemantauan, job persisten, pilihan Gemini/EODHD, rencana transaksi, akun dan backtest berbiaya dijelaskan pada [laporan implementasi PRD](docs/implementasi_prd_20261019.md). Selain API dan frontend, jalankan worker produk terpisah dengan environment/database yang sama:

```bash
.venv/bin/alembic upgrade head
.venv/bin/python -m app.worker.product_worker
```

Worker memakai antrean pada database aplikasi; jangan memakai broker SQLite lama sebagai antrean produk. Penggunaan provider/email nyata tetap membutuhkan konfigurasi dan verifikasi sebagaimana laporan.
