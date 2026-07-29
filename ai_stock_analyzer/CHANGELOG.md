# Changelog

Semua perubahan penting pada AI Stock Analyzer akan dicatat dalam file ini.
Format merujuk pada [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased] — Sprint 10
### Added
- Halaman Settings/Profile di frontend (`/settings`).
- Layar navigasi untuk Pengguna (Settings, Logout).
- Halaman Backtest Strategy dengan form parameter interaktif (`/stock/[ticker]/backtest`).
- Tampilan detail hasil backtest (Win Rate, Total Trades, Trade History table).

## [1.3.0] — Sprint 9
### Added
- Order Block detection (Bullish & Bearish) via SMC Engine.
- Liquidity Sweep (High & Low) false-breakout detection.
- Pola klasik Cup & Handle untuk konfirmasi uptrend.
- Pola klasik Bull Flag untuk mendeteksi lonjakan pole dan konsolidasi.
- Integrasi parameter baru (SMC & Pattern) ke Prompt Builder AI (Claude Sonnet).

### Changed
- Modifikasi endpoint sinkronisasi (`do_sync_stock`) untuk menyimpan SMC dan Pattern di kolom `smc_patterns` (JSONB).

## [1.2.0] — Sprint 8
### Added
- Endpoint POST `/auth/logout` untuk revoke Refresh Token secara aman.
- Model `RefreshToken` (ORM) dan fitur one-time use rotation (deteksi pencurian token).
- Infrastruktur Cache berbasis Redis (dengan graceful fallback ke InMemory jika server Redis offline).
- `CorrelationIdMiddleware` untuk tracking lifecycle request HTTP (observability).
- Tracking field `analyzed_by` pada histori Analisis AI.

### Fixed
- Timezone offset-naive vs offset-aware pada JWT expiration date di SQLite/PostgreSQL.

## [1.1.0] — Sprint 6-7
### Added
- Rate limiting dengan SlowAPI.
- Paginasi pada endpoint list (Stocks & Watchlists).
- Tier-based access control (Free vs Premium Quota).
- Standardisasi JSON structured logging.
- Frontend Web Application (Next.js App Router, Tailwind CSS, Lucide Icons).
- Watchlist dashboard dan detail saham interaktif.

## [1.0.0] — Sprint 1-5
### Added
- Foundation: FastAPI Backend, SQLAlchemy ORM, JWT Authentication.
- Integrasi `yfinance` untuk fetching data pasar.
- Engine Indikator Teknikal (RSI, EMA 20/50/200, MACD, ATR, VWAP, OBV).
- Engine Volume Price Analysis (VPA) dan Wyckoff Phase (Akumulasi/Distribusi).
- Integrasi Anthropic Claude Sonnet API untuk rekomendasi trading (AI-Powered).
- Background Worker dengan Celery.
- Docker & Docker Compose setup.
