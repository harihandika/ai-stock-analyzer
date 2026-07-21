# AI Stock Analyzer

Platform analisis saham berbasis AI yang menggunakan **Volume Price Analysis (VPA)**, **Wyckoff Theory**, dan **Smart Money Concepts (SMC)** untuk mengidentifikasi peluang investasi dengan probabilitas tinggi.

## 🏗️ Tech Stack

| Layer | Teknologi |
|---|---|
| **Backend API** | Python 3.11, FastAPI |
| **Database** | PostgreSQL (Supabase untuk production) |
| **ORM & Migration** | SQLAlchemy 2.0 (Async), Alembic |
| **Authentication** | JWT (python-jose), bcrypt (passlib) |
| **AI Engine** | Claude Sonnet 4.6 (Anthropic SDK) |
| **Analysis** | pandas, pandas-ta, scipy, yfinance |
| **Background Worker** | Celery + Redis |
| **Local Dev** | Docker Compose |

---

## 🚀 Cara Menjalankan (Development)

### 1. Prerequisites
- Python 3.11+
- Docker Desktop (untuk PostgreSQL + Redis lokal)
- Akun Anthropic (untuk API Key)

### 2. Clone & Setup Environment

**PENTING**: Aplikasi ini membutuhkan **Python 3.12**. Jika laptop Anda memiliki versi yang lebih baru (misal 3.14), gunakan `uv` untuk memastikan virtual environment Anda terkunci di versi 3.12.

```bash
# Clone repositori
git clone <repo-url>
cd ai_stock_analyzer

# Buat virtual environment dengan Python 3.12
uv venv --python 3.12 .venv

# Aktivasi Venv
# (Wajib dilakukan SETIAP KALI Anda membuka jendela terminal baru)
# Windows (PowerShell/CMD):
.venv\Scripts\activate

# Linux/Mac Asli:
source .venv/bin/activate

# Git Bash di Windows:
source .venv/Scripts/activate

# Verifikasi versi Python (Pastikan muncul 3.12.x)
python --version

# Install dependencies (menggunakan uv agar lebih cepat)
uv pip install --python .venv -r requirements.txt
```

### 3. Konfigurasi Environment

```bash
# Salin template .env
cp .env.example .env

# Edit .env dengan editor Anda
# Isi: DATABASE_URL, SECRET_KEY, ANTHROPIC_API_KEY
```

### 4. Jalankan Database Lokal

```bash
# Jalankan PostgreSQL + Redis via Docker
docker-compose up -d

# Verifikasi container berjalan
docker-compose ps
```

### 5. Migrasi Database

```bash
# Generate migrasi pertama (initial schema)
alembic revision --autogenerate -m "initial_schema"

# Jalankan migrasi
alembic upgrade head
```

### 6. Jalankan Server

```bash
uvicorn app.main:app --reload --port 8000
```

Buka di browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## 🧪 Menjalankan Tests

```bash
# Install test dependencies (sudah termasuk di requirements.txt)
pip install pytest pytest-asyncio httpx aiosqlite

# Jalankan semua tests
pytest tests/ -v

# Jalankan test spesifik
pytest tests/api/test_auth.py -v
```

---

## 📁 Struktur Proyek

```
ai_stock_analyzer/
├── app/
│   ├── api/                  # FastAPI Routers (HTTP Interface)
│   │   ├── dependencies.py   # JWT Auth & DB Session dependency
│   │   └── routers/
│   │       ├── auth.py       # /auth/register, /auth/token, /auth/me
│   │       ├── stocks.py     # /stocks, /stocks/{ticker}/chart, watchlist
│   │       └── analysis.py   # /analysis (Sprint 4)
│   ├── core/                 # Konfigurasi & keamanan
│   │   ├── config.py         # Pydantic Settings
│   │   └── security.py       # JWT + bcrypt
│   ├── domain/               # Domain Layer
│   │   ├── models/models.py  # SQLAlchemy ORM Models
│   │   └── schemas/          # Pydantic Schemas
│   ├── infrastructure/
│   │   └── database.py       # Async SQLAlchemy engine
│   ├── services/             # Business Logic (Sprint 2-4)
│   │   ├── indicator_engine.py
│   │   ├── wyckoff_engine.py
│   │   ├── smc_engine.py
│   │   └── ai_service.py
│   ├── worker/               # Celery Background Tasks (Sprint 4)
│   │   ├── celery_app.py
│   │   └── tasks.py
│   └── main.py               # FastAPI entrypoint
├── alembic/                  # Database migrations
├── docs/                     # Dokumentasi PRD & Arsitektur
├── tests/                    # Pytest test suite
├── docker-compose.yml        # Local dev: PostgreSQL + Redis
├── .env.example              # Template environment variables
└── requirements.txt
```

---

## 🗺️ Sprint Roadmap

| Sprint | Status | Objective |
|---|---|---|
| **Sprint 1** | ✅ **DONE** | Foundation: FastAPI, Auth, ORM, Alembic |
| **Sprint 2** | 🔜 Next | Data Ingestion: yfinance, Indicator Engine |
| **Sprint 3** | ⏳ Planned | VPA/Wyckoff/SMC Engine (non-AI) |
| **Sprint 4** | ⏳ Planned | AI Integration: Claude Sonnet + Celery |
| **Sprint 5** | ⏳ Planned | Deployment: Docker, Supabase, Render |

---

## 🔐 Keamanan

- Password di-hash menggunakan **bcrypt** (tidak pernah disimpan plaintext)
- JWT token menggunakan algoritma **HS256** dengan expiry 24 jam
- Endpoint sensitif dilindungi dengan dependency `get_current_active_user`
- File `.env` tidak boleh di-commit ke Git
