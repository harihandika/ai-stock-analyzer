# Software Architecture & C4 Model

## 1. Architectural Pattern: Clean Architecture
Aplikasi ini akan dibangun menggunakan **Clean Architecture** (juga dikenal sebagai Hexagonal Architecture/Ports and Adapters) menggunakan framework **FastAPI (Python)**. 

Tujuan utamanya adalah mengisolasi logika bisnis analisis saham (VPA, Wyckoff, Smart Money Concepts) dari elemen eksternal seperti database dan penyedia layanan AI.

### Struktur Layer:
- **Domain Layer**: Berisi entitas inti bisnis (`Stock`, `PriceData`, `User`, `AnalysisResult`).
- **Use Case Layer**: Berisi logika aplikasi (`FetchDailyPrices`, `CalculateIndicators`, `DetectWyckoffPhase`, `GenerateAIRecommendation`).
- **Interface Adapters Layer**: FastAPI Controllers (Router), Repositories Interfaces.
- **Infrastructure Layer**: Implementasi SQLAlchemy untuk PostgreSQL, Celery/Redis untuk background queue, HTTP Client untuk external market data, dan Anthropic SDK untuk Claude AI.

## 2. AI Integration Strategy (Cost Optimization)
Sesuai arahan workflow referensi, kita menggunakan **Two-Tier AI Approach**:
1. **Strategic (Opus 4.6)**: Digunakan di luar aplikasi (atau via admin panel) untuk menyusun *System Prompt* terbaik, mendesain kriteria teknikal, dan mengevaluasi performa prompt.
2. **Operational (Sonnet 4.6)**: *Background worker* (Celery) akan berjalan setiap tutup pasar (End of Day). Worker ini akan mengumpulkan data harga, volume, hasil VPA (diolah oleh algoritma Python biasa non-AI), dan pola SMC. Data ini kemudian diinjeksikan ke *System Prompt* dan dikirim ke **Sonnet 4.6** untuk menghasilkan narasi analisis yang dibaca pengguna. Ini menghemat penggunaan token Opus yang mahal.

## 3. C4 Model Diagrams

### Level 1: System Context Diagram
Diagram ini menunjukkan interaksi sistem aplikasi dengan aktor eksternal.

```mermaid
C4Context
    title System Context diagram for AI Stock Analyzer

    Person(investor, "Long-term Investor/Trader", "Membaca analisis saham harian dan mencari pola akumulasi Smart Money.")
    
    System(stockAnalyzer, "AI Stock Analyzer", "Menyediakan data harga historis, perhitungan VPA/SMC, dan rekomendasi AI harian.")
    
    System_Ext(marketData, "Market Data Provider", "Penyedia data OHLCV harian (misal: Yahoo Finance, Alpaca, atau IDX).")
    System_Ext(aiService, "Anthropic API", "Layanan Claude AI (Sonnet 4.6) untuk memproses rekomendasi harian.")

    Rel(investor, stockAnalyzer, "Melihat analisis saham, menyetel watchlist", "HTTPS")
    Rel(stockAnalyzer, marketData, "Mengambil harga & volume harian", "REST/HTTPS")
    Rel(stockAnalyzer, aiService, "Mengirim data teknikal, menerima narasi AI", "REST/HTTPS")
```

### Level 2: Container Diagram
Menunjukkan arsitektur internal dari sistem.

```mermaid
C4Container
    title Container diagram for AI Stock Analyzer

    Person(investor, "Investor", "Membaca analisis")
    
    System_Boundary(c1, "AI Stock Analyzer") {
        Container(webApp, "Web Application", "React/Next.js", "Menampilkan dashboard dan visualisasi chart saham.")
        Container(apiApp, "API Application", "Python, FastAPI", "Menyediakan endpoint REST, menangani otentikasi dan logika utama.")
        Container(workerApp, "Background Worker", "Python, Celery", "Melakukan agregasi data harian, perhitungan VPA, dan eksekusi AI di latar belakang.")
        ContainerDb(db, "Relational Database", "PostgreSQL", "Menyimpan data pengguna, riwayat saham, hasil indikator, dan analisis AI.")
        ContainerDb(cache, "Cache & Queue", "Redis", "Menyimpan data sementara dan antrean tugas untuk worker.")
    }

    System_Ext(marketData, "Market Data Provider")
    System_Ext(aiService, "Anthropic API")

    Rel(investor, webApp, "Visits", "HTTPS")
    Rel(webApp, apiApp, "Makes API calls to", "JSON/HTTPS")
    Rel(apiApp, db, "Reads from and writes to", "SQLAlchemy")
    Rel(apiApp, cache, "Publishes tasks / Reads cache", "Redis Protocol")
    Rel(workerApp, cache, "Consumes tasks", "Redis Protocol")
    Rel(workerApp, db, "Saves analysis results", "SQLAlchemy")
    
    Rel(workerApp, marketData, "Fetches OHLCV data", "HTTPS")
    Rel(workerApp, aiService, "Requests analysis from Claude Sonnet", "HTTPS")
```

### Level 3: Component Diagram (API Application)
Memperlihatkan komponen internal di dalam backend FastAPI sesuai Clean Architecture.

```mermaid
C4Component
    title Component diagram for API Application

    Container_Boundary(api, "API Application (FastAPI)") {
        Component(controllers, "Routers / Controllers", "FastAPI Router", "Menerima request HTTP, validasi payload.")
        Component(useCases, "Use Cases / Services", "Python Class", "Orkestrasi logika bisnis (Clean Arch).")
        Component(vpaEngine, "VPA & SMC Engine", "Pandas/Pandas-TA", "Menghitung indikator dan deteksi pola Smart Money.")
        Component(repo, "Repositories", "SQLAlchemy", "Abstraksi akses database.")
        Component(aiGateway, "AI Gateway", "Anthropic SDK", "Abstraksi komunikasi ke layanan AI.")
    }
    
    ContainerDb(db, "PostgreSQL", "Relational Database")
    System_Ext(aiService, "Anthropic API")

    Rel(controllers, useCases, "Delegates business logic to")
    Rel(useCases, repo, "Reads/Writes data via")
    Rel(useCases, vpaEngine, "Calculates signals using")
    Rel(useCases, aiGateway, "Gets AI insights via")
    
    Rel(repo, db, "Executes SQL queries on", "SQL/TCP")
    Rel(aiGateway, aiService, "Makes API requests to", "JSON/HTTPS")
```
