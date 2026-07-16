# Gunakan base image Python 3.12 (karena versi ini sudah kita verifikasi bebas dari masalah kompilasi C++)
FROM python:3.12-slim

# Set working directory di dalam container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependency sistem yang mungkin dibutuhkan oleh library (misal build-essential jika diperlukan)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy file requirements terlebih dahulu (untuk memanfaatkan cache layer Docker)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh kode aplikasi
COPY . .

# Expose port yang akan digunakan FastAPI
EXPOSE 8000

# Script entrypoint untuk menjalankan Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
