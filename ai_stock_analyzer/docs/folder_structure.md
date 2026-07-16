# Folder Structure (FastAPI Clean Architecture)

Sesuai dengan arsitektur yang direncanakan di `architecture_and_c4.md`, kita akan membagi proyek menjadi beberapa layer. Ini adalah struktur direktori standar (Python) untuk AI Stock Analyzer:

```text
ai_stock_analyzer/
├── app/
│   ├── api/                  # Interface Adapters: HTTP Controllers/Routers
│   │   ├── dependencies.py   # FastAPI Dependencies (Auth, DB session)
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── stocks.py
│   │   │   └── analysis.py
│   ├── core/                 # Shared configs, security, constants
│   │   ├── config.py         # Pydantic BaseSettings (ENV vars)
│   │   └── security.py       # JWT hashing & verification
│   ├── domain/               # Enterprise Logic Layer: Entities & Models
│   │   ├── models/           # SQLAlchemy ORM Models
│   │   └── schemas/          # Pydantic Schemas (Request/Response validation)
│   ├── infrastructure/       # External concerns (DB, AI SDK, External APIs)
│   │   ├── database.py       # Postgres Session config
│   │   ├── anthropic_client.py # Claude SDK wrapper
│   │   └── market_data.py    # Yahoo Finance / Alpaca client
│   ├── services/             # Application Logic / Use Case Layer
│   │   ├── indicator_engine.py # Pandas-TA wrapper
│   │   ├── smc_engine.py     # Smart Money Concept calculation
│   │   ├── wyckoff_engine.py # Wyckoff phase logic
│   │   └── ai_service.py     # Orchestrating data to Claude
│   ├── worker/               # Background task queue (Celery)
│   │   ├── tasks.py          # Daily EOD runner (Fetch data -> Calc -> AI)
│   │   └── celery_app.py
│   └── main.py               # FastAPI application entrypoint
├── docs/                     # Semua file dokumentasi PRD & Arsitektur
├── tests/                    # Pytest unit & integration tests
│   ├── api/
│   ├── services/
│   └── conftest.py
├── .env.example              # Template environment variables
├── alembic.ini               # Konfigurasi migrasi database
├── docker-compose.yml        # Docker compose untuk Local Dev (Postgres, Redis)
├── Dockerfile                # Dockerfile untuk Production deployment
└── requirements.txt          # Python dependencies
```

## Penjelasan Layer:
1. **`app/api/`**: Tempat router FastAPI berada. Hanya menangani *request/response* HTTP. Logika dilempar ke `services/`.
2. **`app/domain/`**: Tempat definisi tabel PostgreSQL (ORM) dan validasi struktur JSON (Pydantic).
3. **`app/services/`**: Otak aplikasi. Di sinilah logika *Volume Price Analysis* (VPA) dan persiapan prompt AI dilakukan.
4. **`app/infrastructure/`**: Tempat aplikasi berinteraksi dengan dunia luar, seperti menembak API Claude (`anthropic_client.py`) atau mengambil data saham (`market_data.py`).
