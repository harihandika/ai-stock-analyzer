# AI Stock Analyzer - Handover Document
Dokumen ini merangkum status terakhir dari proyek `AI Stock Analyzer` untuk mempermudah AI Assistant di sesi chat yang baru.

## 1. Status Proyek Saat Ini
- **Backend (FastAPI)**: Berjalan normal. 
  - Environment sudah menggunakan Python 3.12 (dikunci menggunakan `uv venv`). 
  - Migrasi database (`alembic upgrade head`) sudah selesai dan struktur tabel sudah terbuat.
- **Database (Docker)**: PostgreSQL dan Redis berjalan normal via Docker. 
  - **Catatan Penting**: Port PostgreSQL telah diubah menjadi `5433` (karena port `5432` bentrok dengan PostgreSQL bawaan Windows). File `.env` dan `docker-compose.yml` sudah diperbarui untuk menggunakan port 5433.
- **Frontend (Next.js)**: Proyek frontend sudah disiapkan di folder `ai_stock_analyzer_frontend` dan server development bisa berjalan normal.

## 2. Cara Menjalankan Aplikasi
- **Menjalankan Database**: 
  - Masuk ke folder: `cd ai_stock_analyzer`
  - Jalankan perintah: `docker-compose up -d`
- **Menjalankan Backend (FastAPI)**: 
  - Masuk folder: `cd ai_stock_analyzer`
  - Aktifkan venv (Git Bash di Windows): `source .venv/Scripts/activate`
  - Jalankan server: `uvicorn app.main:app --reload --port 8000`
- **Menjalankan Frontend (Next.js)**: 
  - Masuk folder: `cd ai_stock_analyzer_frontend`
  - Jalankan server: `npm run dev`

## 3. Instruksi untuk AI Assistant Baru
Silakan baca dokumen ini sebagai konteks awal. Anda bisa langsung bertanya kepada user mengenai tugas atau fokus selanjutnya yang ingin dikerjakan berdasarkan progres di atas.
