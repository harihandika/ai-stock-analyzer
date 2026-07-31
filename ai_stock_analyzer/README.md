# AI Stock Analyzer

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
pytest tests/ --ignore=tests/worker -v
```

---

## 📖 Dokumentasi Lengkap & Changelog

- **[CHANGELOG.md](CHANGELOG.md)**: Catatan rilis lengkap dari Sprint 1 hingga Sprint 10.
- **[OpenAPI Spec](docs/openapi.yaml)**: Dokumentasi API lengkap 15 endpoint.
