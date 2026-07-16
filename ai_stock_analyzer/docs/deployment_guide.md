# Deployment Guide: AI Stock Analyzer

Panduan ini akan membantu Anda meng-hosting AI Stock Analyzer agar bisa diakses dari internet dan berjalan 24/7.
Kita akan menggunakan arsitektur gratis (free tier) yang terdiri dari:
1. **Supabase** (Database PostgreSQL)
2. **Upstash** (Redis Cloud)
3. **Render** (Hosting Backend & Background Worker)

## 1. Setup Database di Supabase
Supabase menyediakan PostgreSQL gratis berkapasitas 500MB yang sangat cukup untuk tahap awal.
1. Buka [Supabase.com](https://supabase.com/) dan buat project baru.
2. Masukkan nama project dan buat password database yang kuat.
3. Setelah project selesai dibuat, buka menu **Settings > Database**.
4. Cari bagian **Connection String** dan pilih opsi **URI**.
5. Copy Connection String tersebut. Formatnya akan seperti ini:
   `postgresql://postgres.xxxxxx:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres`
6. Buka terminal di komputer Anda, masuk ke folder project, lalu jalankan migrasi Alembic untuk membuat struktur tabel di Supabase:
   ```bash
   # Ganti URL di bawah dengan koneksi Supabase Anda
   set SYNC_DATABASE_URL=postgresql://postgres.xxxxxx:PASSWORD_ANDA@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
   
   alembic upgrade head
   ```

## 2. Setup Redis di Upstash
Upstash menyediakan Redis serverless gratis yang sempurna untuk Celery broker.
1. Buka [Upstash.com](https://upstash.com/) dan login.
2. Buat database Redis baru (pilih region Singapore agar dekat dengan Supabase).
3. Scroll ke bawah dan cari bagian **Redis Connect**.
4. Copy `REDIS_URL`. Formatnya akan seperti: `rediss://default:xxxxx@yyyy.upstash.io:32456`.

## 3. Deploy Backend ke Render
Render akan menjalankan FastAPI (Web Service) dan Celery (Background Worker).
1. Buka [Render.com](https://render.com/) dan hubungkan dengan akun GitHub Anda.
2. Buat layanan baru: **New > Web Service**.
3. Hubungkan repositori GitHub AI Stock Analyzer Anda.
4. Isi konfigurasi berikut:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
5. Tambahkan **Environment Variables** berikut:
   - `DATABASE_URL`: `postgresql+asyncpg://...` (Ubah awalan URL Supabase dari `postgresql://` menjadi `postgresql+asyncpg://`)
   - `SYNC_DATABASE_URL`: `postgresql://...` (URL Supabase original)
   - `SECRET_KEY`: Buat string acak yang panjang
   - `ANTHROPIC_API_KEY`: API Key Claude Anda
   - `REDIS_URL`: URL Upstash Anda
6. Klik **Create Web Service**.

## 4. Deploy Celery Worker & Beat ke Render
Agar sinkronisasi harian berjalan otomatis, Anda butuh Background Worker.
1. Di Dashboard Render, klik **New > Background Worker**.
2. Hubungkan kembali repositori yang sama.
3. Isi konfigurasi:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `celery -A app.worker.celery_app worker --loglevel=info`
4. Masukkan Environment Variables yang sama dengan Web Service.
5. Ulangi langkah 1-4 untuk membuat satu worker lagi, tapi ubah **Start Command**-nya menjadi:
   `celery -A app.worker.celery_app beat --loglevel=info`

## 5. Monitoring (UptimeRobot)
Render versi gratis akan "tertidur" jika tidak ada aktivitas selama 15 menit. Agar aplikasi selalu hidup:
1. Buka [UptimeRobot.com](https://uptimerobot.com/).
2. Buat Monitor baru bertipe **HTTP(s)**.
3. Masukkan URL Web Service Render Anda ditambah `/api/v1/health` (contoh: `https://ai-stock-xxx.onrender.com/api/v1/health`).
4. Set interval ping setiap 10 menit.

Aplikasi Anda sekarang sudah berjalan di cloud dan akan menganalisis saham secara otomatis setiap pukul 17:30 WIB!
