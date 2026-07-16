# Security Checklist (Pre-Deployment)

Sebelum aplikasi AI Stock Analyzer masuk ke tahap production, pastikan Anda telah melakukan *cross-check* pada poin-poin keamanan berikut. Mengingat aplikasi ini terkoneksi dengan API berbayar (Anthropic) dan menyimpan data user (termasuk hash password), keamanan menjadi sangat krusial.

## 1. Secrets Management
- [ ] **Tidak ada API Key di GitHub**: Pastikan `.env` telah masuk ke `.gitignore` dan Anda tidak pernah secara tidak sengaja meng-commit `ANTHROPIC_API_KEY`.
- [ ] **Secret Key FastAPI**: Ubah `SECRET_KEY` default di environment variable Render menjadi string acak baru (minimal 32 karakter). Anda bisa men-generate-nya dengan perintah: `openssl rand -hex 32`.
- [ ] **Rotasi API Key (Opsional)**: Jika Anda merasa token Anthropic Anda pernah bocor saat proses *development*, segera *revoke* (hapus) key tersebut dari dashboard Anthropic dan generate yang baru.

## 2. Database Security (Supabase)
- [ ] **Password Kuat**: Pastikan password role `postgres` di Supabase Anda sangat kuat dan tidak menggunakan kata yang umum.
- [ ] **Batasi Akses Jaringan (Jika Memungkinkan)**: Jika Anda menggunakan VPS/Cloud Provider yang mendukung *IP Whitelisting*, daftarkan hanya IP dari server backend Anda agar database tidak terbuka lebar ke seluruh internet.
- [ ] **Enkripsi Hash User**: Pastikan modul otentikasi FastAPI (`passlib` & `bcrypt`) berjalan sempurna untuk menghash password user sebelum disimpan di tabel `users`.

## 3. Rate Limiting & Perlindungan Token AI
- [ ] **Batasi Endpoint AI**: Endpoint `POST /api/v1/analysis/{ticker}` saat ini akan memicu pemanggilan Anthropic secara *real-time*. Jika API ini diekspos ke publik tanpa batas, tagihan Anthropic Anda bisa membengkak.
    - **Tindakan Lanjutan (Backlog)**: Tambahkan implementasi *Rate Limiting* (contoh: menggunakan `slowapi` atau middleware) agar satu *user* hanya bisa me-request batas tertentu per menit.
    - **Role Check**: Pastikan endpoint tersebut dikunci menggunakan `Depends(get_current_active_user)`. Jika perlu, ubah agar hanya role "Admin" atau "Premium User" yang bisa men-trigger-nya.

## 4. Middleware & Header
- [ ] **CORS Policy**: Saat ini CORS di `main.py` mengizinkan semua origin (`allow_origins=["*"]`). Sebelum live, ubah daftar ini hanya untuk domain frontend/aplikasi client Anda (contoh: `["https://saham-frontend.vercel.app"]`).
- [ ] **HTTPS Enforced**: Pastikan server web Anda (Render) menggunakan koneksi HTTPS dan me-reject traffick HTTP biasa. Render biasanya menangani hal ini secara *default*.

## 5. Pemeliharaan Dependency
- [ ] Lakukan perintah `pip audit` secara berkala untuk mengecek kerentanan (*vulnerability*) pada library Python pihak ketiga (seperti `pandas`, `fastapi`, dsb) yang Anda gunakan. 
- [ ] Bot seperti *Dependabot* di GitHub disarankan untuk diaktifkan agar mendapat *pull request* otomatis saat ada *patch* keamanan.
