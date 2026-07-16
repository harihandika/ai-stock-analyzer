# Database Design & ERD

## 1. Database Selection: PostgreSQL
PostgreSQL dipilih karena:
1. Sangat andal dalam menangani data relasional yang kompleks.
2. Mendukung **Table Partitioning** yang sangat vital untuk menyimpan data time-series (seperti harga saham harian) yang jumlahnya akan terus membengkak seiring waktu.
3. Mendukung fitur JSONB jika kita perlu menyimpan data konfigurasi indikator yang fleksibel.

## 2. Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    USERS {
        uuid id PK
        string email
        string password_hash
        string full_name
        string subscription_tier
        datetime created_at
    }

    STOCKS {
        string ticker PK
        string company_name
        string sector
        string exchange
        boolean is_active
    }

    DAILY_PRICES {
        bigint id PK
        string stock_ticker FK
        date trading_date
        decimal open
        decimal high
        decimal low
        decimal close
        bigint volume
    }

    TECHNICAL_INDICATORS {
        bigint id PK
        string stock_ticker FK
        date trading_date
        decimal rsi_14
        decimal ema_20
        decimal ema_50
        decimal ema_200
        decimal vwap
        string wyckoff_phase
        jsonb smc_patterns
    }

    AI_ANALYSES {
        uuid id PK
        string stock_ticker FK
        date analysis_date
        text ai_summary
        string recommendation "Buy|Hold|Wait"
        int confidence_score
        datetime generated_at
    }

    WATCHLISTS {
        uuid id PK
        uuid user_id FK
        string stock_ticker FK
        datetime added_at
    }

    USERS ||--o{ WATCHLISTS : "has"
    STOCKS ||--o{ WATCHLISTS : "included in"
    STOCKS ||--o{ DAILY_PRICES : "has price history"
    STOCKS ||--o{ TECHNICAL_INDICATORS : "has technical data"
    STOCKS ||--o{ AI_ANALYSES : "has AI insight"
    
    %% Implicit relation constraint for time-series:
    DAILY_PRICES ||--|| TECHNICAL_INDICATORS : "calculated from (1:1 per date)"
```

## 3. Database Optimizations
1. **Partitioning**: Tabel `DAILY_PRICES` dan `TECHNICAL_INDICATORS` akan dipartisi secara bulanan atau tahunan (`PARTITION BY RANGE (trading_date)`) untuk memastikan query pengambilan chart harga berjalan dengan cepat meskipun data mencapai puluhan juta baris.
2. **Indexing**: 
   - Composite index pada `(stock_ticker, trading_date DESC)` di tabel `DAILY_PRICES` dan `TECHNICAL_INDICATORS` karena API akan sering meminta "data 100 hari terakhir untuk saham X".
   - B-Tree index pada kolom pencarian teks (`company_name`, `ticker`).
3. **Caching Layer**: Tabel `AI_ANALYSES` bersifat statis setelah di-generate (EOD). Data ini akan disinkronkan ke Redis agar pemanggilan dari ratusan user tidak membebani database utama.
