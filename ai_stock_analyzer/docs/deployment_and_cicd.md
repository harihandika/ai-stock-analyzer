# Deployment & CI/CD Strategy (Free-Tier)

Untuk meminimalkan biaya karena aplikasi ini untuk pemakaian pribadi, kita menggunakan *stack* deployment gratis yang andal.

## 1. Hosting Infrastructure
- **Database (PostgreSQL)**: **Supabase** (Free Tier menyediakan 500MB DB space, cukup untuk menyimpan riwayat harga ratusan saham selama beberapa tahun, apalagi dengan tabel berpartisi).
- **Backend & Worker (FastAPI/Celery)**: **Render.com** atau **Koyeb** (menyediakan instance gratis Docker Container. *Render* akan *sleep* jika tidak ada trafik, cocok untuk script harian. *Koyeb* lebih cepat wake-up).
- **Cache/Queue (Redis)**: **Upstash** (Menyediakan serverless Redis gratis hingga 10k request per hari, sangat cocok untuk antrean *Celery worker*).

## 2. Dockerization
Aplikasi harus di-bundle ke dalam container Docker agar mudah di-deploy di cloud.

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .

# Install dependencies (termasuk pandas, fastapi, sqlalchemy)
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY ./app /app/app
COPY ./alembic.ini /app/
COPY ./main.py /app/

# Expose port (biasanya Render menggunakan environment PORT)
EXPOSE 8000

# Command to run API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
*(Catatan: Untuk Celery worker, perintah CMD di Render diubah menjadi `celery -A app.worker.celery_app worker --loglevel=info`)*

## 3. CI/CD (Continuous Integration / Continuous Deployment)
Kita akan menggunakan **GitHub Actions** untuk memastikan kode yang masuk bersih dan otomatis ter-deploy.

**File: `.github/workflows/deploy.yml`**
```yaml
name: Deploy API to Render

on:
  push:
    branches:
      - main

jobs:
  test-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies & Run Tests
        run: |
          pip install -r requirements.txt pytest
          pytest tests/

      # Jika test sukses, trigger deploy webhook ke Render
      - name: Trigger Render Deployment
        if: success()
        run: curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK }}
```

## 4. Monitoring (UptimeRobot)
Karena menggunakan layanan gratis (Render) yang bisa *sleep*, kita gunakan **UptimeRobot** (gratis) untuk me-ping endpoint `/health` dari FastAPI setiap 15 menit agar backend tetap "terjaga" (*awake*) sesaat sebelum pasar tutup (EOD) untuk bersiap memproses data AI.
