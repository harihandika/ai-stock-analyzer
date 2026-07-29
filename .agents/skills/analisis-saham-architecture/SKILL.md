---
name: analisis-saham-architecture
description: Petunjuk arsitektur, standar penulisan kode, dan konfigurasi environment untuk proyek AI Stock Analyzer. Gunakan skill ini setiap kali membuat atau memodifikasi kode backend (FastAPI) dan frontend (Next.js).
---

# Arsitektur Proyek AI Stock Analyzer

## 1. Backend (FastAPI & Python)
- **Python Environment**: Selalu gunakan Virtual Environment dari `uv` (`.venv/Scripts/activate`). Jangan jalankan `pip install` global.
- **Port PostgreSQL Docker**: Database PostgreSQL berjalan di port **`5433`** (karena port 5432 digunakan oleh service lokal Windows). Selalu gunakan port 5433 pada SQLAlchemy / Alembic connection string.
- **Database Migration**: Gunakan Alembic untuk setiap perubahan schema DB (`alembic revision --autogenerate -m "..."` & `alembic upgrade head`).
- **Framework**: FastAPI dengan struktur modul terpisah (`app/api`, `app/core`, `app/models`, `app/schemas`, `app/services`).

## 2. Frontend (Next.js & TypeScript)
- **Framework**: Next.js (App Router / Pages Router) di dalam folder `ai_stock_analyzer_frontend`.
- **TypeScript**: Wajib menggunakan strict typing. Hindari tipe `any`.
- **Styling**: Gunakan Tailwind CSS & Lucide React Icons.

## 3. Workflow Eksekusi
- Backend server dijalankan dari folder `ai_stock_analyzer` dengan `uvicorn app.main:app --reload --port 8000`.
- Frontend server dijalankan dari folder `ai_stock_analyzer_frontend` dengan `npm run dev`.
