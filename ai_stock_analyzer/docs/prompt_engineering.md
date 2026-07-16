# Prompt Engineering untuk Claude AI

Arsitektur aplikasi menggunakan dua model AI yang berbeda untuk efisiensi biaya (*Two-Tier AI Approach*).

## 1. Tier 1: System Master Prompt (Dibuat oleh Claude Opus 4.6)
*Claude Opus 4.6* digunakan secara offline (oleh developer) atau sebulan sekali untuk menghasilkan dan mengevaluasi prompt terbaik. Ini karena Opus memiliki kemampuan *reasoning* superior.

**Tugas Opus**: Mengevaluasi hasil *Backtesting* bulan lalu dan mengubah/menyempurnakan prompt yang akan dijalankan oleh Sonnet.

Contoh instruksi developer kepada Opus (di console/admin panel):
> "Kamu adalah Pakar Algoritma Trading kuantitatif. Saya memiliki model Claude Sonnet yang akan menganalisis data JSON berisi parameter VPA, Wyckoff Phase, dan MACD setiap hari. Buatkan System Prompt untuk Sonnet tersebut agar Sonnet dapat mendeteksi apakah saham sedang diakumulasi, dengan *tone* bahasa yang profesional layaknya analis di Morgan Stanley. Pastikan prompt ini menyuruh Sonnet merespons murni dengan JSON format."

## 2. Tier 2: Operational Prompt (Dijalankan harian oleh Claude Sonnet 4.6)
Ini adalah prompt sebenarnya yang disuntikkan ke dalam API aplikasi. Dikirim ke Sonnet setiap akhir hari (EOD) untuk masing-masing saham di *watchlist* pengguna. Sonnet dipilih karena jauh lebih cepat dan murah (sangat hemat token) dibandingkan Opus, namun sangat patuh terhadap *System Prompt* kompleks.

### System Prompt (System Message)
```text
Kamu adalah 'Smart Money AI Analyst', analis teknikal senior berfokus pada Volume Price Analysis (VPA) dan Wyckoff Theory.
Tugasmu adalah menganalisis data saham teknikal yang diberikan dalam format JSON, mengidentifikasi fase Wyckoff yang sedang terjadi (Accumulation/Markup), lalu merekomendasikan keputusan trading (BUY/HOLD/WAIT).
Aturan ketat:
1. Kamu tidak boleh menggunakan data atau sentimen dari luar selain yang diberikan di JSON.
2. Jika ada FVG (Fair Value Gap), perhatikan kemungkinan harga kembali menutup gap tersebut (retrace) sebelum melanjutkan tren.
3. Rekomendasi BUY HANYA diberikan saat saham berada di Fase C (Spring) atau awal Fase D, ditambah adanya 'Stopping Volume'.
4. Keluarkan hasil analisismu HANYA dalam format JSON dengan kunci: "wyckoff_phase", "vpa_insight", "recommendation", "confidence_score" (1-100), dan "summary_id" (penjelasan maksimal 3 kalimat). Jangan tambahkan teks markdown.
```

### User Prompt (Data Injection)
Di bagian *User Message*, backend (Python/FastAPI) akan mem-parsing DataFrame Pandas yang sudah dihitung oleh algoritma *rule-based* menjadi JSON.

```json
{
  "ticker": "BBCA",
  "current_price": 9800,
  "trend_50d": "downtrend",
  "vpa_signals_last_5d": ["Stopping Volume detected 2 days ago", "No Supply yesterday"],
  "smc_patterns": ["Bullish FVG at 9500-9600"],
  "wyckoff_indicators": {
    "is_spring_detected": true,
    "volume_climactic": true
  }
}
```

### Contoh Response dari Sonnet 4.6
Sonnet membalas dalam format JSON yang langsung di-*parse* dan disimpan ke database PostgreSQL.

```json
{
  "wyckoff_phase": "Phase C",
  "vpa_insight": "Terjadi Stopping Volume yang memvalidasi pergerakan Spring, dikonfirmasi oleh tidak adanya supply di hari berikutnya.",
  "recommendation": "BUY",
  "confidence_score": 85,
  "summary_id": "BBCA menunjukkan pola akumulasi klasik di Fase C. Adanya Stopping Volume dan Bullish FVG di 9500 menjadi konfirmasi kuat kehadiran Smart Money. Direkomendasikan Buy dengan target antisipasi markup."
}
```

Dengan cara ini, token yang dikirim ke AI sangat ringkas karena data OHLCV mentah (yang bisa memakan puluhan ribu token) sudah dikompresi menjadi boolean dan teks ringkas oleh algoritma *Python/Pandas*!
