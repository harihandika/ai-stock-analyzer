# Product Requirements Document (PRD) - AI Stock Analyzer

## 1. Vision & Mission
- **Vision**: Menjadi platform analisis saham terdepan yang memanfaatkan kecerdasan buatan untuk mengidentifikasi pergerakan institusi keuangan (*Smart Money*) berdasarkan *Volume Price Analysis* (VPA) dan *Wyckoff Theory*, memberdayakan investor jangka panjang untuk mengambil keputusan dengan probabilitas tinggi.
- **Mission**: Menyediakan analisis harian otomatis yang hemat biaya komputasi (token efisien) namun memiliki akurasi tingkat institusi, memberikan sinyal fase akumulasi/distribusi secara presisi kepada *swing trader* dan investor jangka panjang.

## 2. Target Market & User Persona
**User Persona**: "The Smart Investor / Swing Trader"
- **Profil**: Investor saham jangka panjang atau *swing trader* yang fokus pada pergerakan harga dan volume (VPA).
- **Karakteristik**: Tidak melakukan *day trading* (scalping). Lebih mementingkan posisi masuk (entry) yang aman di fase akumulasi (Wyckoff Phase C/D) untuk ditahan berminggu-minggu atau berbulan-bulan.
- **Pain Points**: Kesulitan menyaring (*screening*) ratusan emiten saham setiap hari untuk menemukan anomali volume harga dan membaca fase Wyckoff secara manual. Biaya langganan platform AI institusi sangat mahal.
- **Goals**: Mendapatkan rekomendasi dan penjelasan terperinci berbasis AI tentang saham-saham mana yang sedang diakumulasi oleh "Smart Money".

## 3. Product Strategy & AI Token Optimization
Mengacu pada dokumen workflow, aplikasi akan menggunakan pendekatan *Two-Tier AI Model* untuk menghemat biaya operasional:
1. **Strategic Engine (Claude Opus 4.6)**: Digunakan *hanya sesekali* untuk merumuskan Prompt Master, merancang arsitektur awal, dan melakukan audit sistem berkala.
2. **Operational Engine (Claude Sonnet 4.6)**: Digunakan untuk *tugas harian/rutin* seperti mengeksekusi analisis VPA, membaca pola *Smart Money Concept* (SMC), dan memberikan rekomendasi harian kepada pengguna berdasarkan Prompt Master yang dibuat oleh Opus.

## 4. Functional Requirements
1. **Data Ingestion Module**:
   - Sistem harus dapat menarik data harga (OHLC) dan Volume saham secara harian (End of Day).
2. **Indicator & Pattern Engine**:
   - Menghitung indikator dasar (EMA, SMA, RSI, MACD, ATR, VWAP, OBV).
   - Mendeteksi *Classic Patterns* (Double Bottom, Cup & Handle, Bull Flag).
3. **Advanced VPA & Wyckoff Engine (Non-AI)**:
   - Mendeteksi *Smart Money Concept* (BOS, CHoCH, Order Block, Fair Value Gap/FVG, Liquidity Sweep).
   - Mendeteksi Fase Wyckoff (Phase A - E) secara algoritmik berdasarkan Volume Price Analysis.
4. **AI Recommendation Engine**:
   - Mengirimkan data Wyckoff, VPA, dan Indikator ke model *Claude Sonnet 4.6*.
   - Menyajikan ringkasan bahasa natural tentang arah saham dan rekomendasi (Buy/Hold/Wait).
5. **Portfolio & Watchlist**:
   - Pengguna dapat menyimpan saham favorit ke dalam watchlist dan mendapatkan alert jika ada pergerakan volume signifikan.

## 5. Non-Functional Requirements (NFR)
1. **Tech Stack**: Backend Python (FastAPI) karena kompatibilitas tertinggi dengan library data science (`pandas`, `pandas-ta`) dan integrasi AI (Anthropic SDK). Database menggunakan PostgreSQL.
2. **Performance**: API response time untuk data riwayat saham < 200ms. Analisis AI dapat memakan waktu hingga 5-10 detik (dijalankan asinkronus).
3. **Scalability**: Arsitektur harus mendukung penambahan jumlah emiten saham dan *concurrent users* melalui horizontal scaling.
4. **Security**: Menerapkan JWT (JSON Web Token) untuk otentikasi API, dan enkripsi pada data pribadi pengguna.

## 6. Key Performance Indicators (KPI)
- **AI Token Cost per User**: Biaya operasional AI (Sonnet) di bawah batas $X per bulan per pengguna aktif.
- **Accuracy of VPA/Wyckoff Detection**: Persentase *win-rate* dari sinyal yang direkomendasikan AI (target > 65% untuk swing trading).
- **User Retention Rate**: Persentase pengguna yang kembali melihat analisis saham di bulan berikutnya.

## 7. Future Features (Roadmap Phase II)
- Integrasi analisis sentimen dari berita keuangan dan sosial media.
- Fitur *Backtesting* otomatis untuk melihat performa rekomendasi AI di masa lalu.
- Aplikasi Mobile (Flutter/React Native).
