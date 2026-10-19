# Kajian alternatif integrasi AI dan data pasar

Tanggal kajian: 19 Oktober 2026. Acuan kebutuhan: [PRD perbaikan](prd_perbaikan_aplikasi.md) dan [implementasi R1](implementasi_r1.md).

Status: riset dokumentasi dan rancangan langkah berikutnya. Provider aplikasi belum diganti. Perubahan R1 dan dokumen ini masih lokal, belum di-commit atau di-push.

## Rekomendasi awal

Uji **Google Gemini untuk AI** dan bandingkan **EODHD dengan Sectors API v2 untuk data IDX**. Untuk kebutuhan harga historis dan backtest saat ini, prioritaskan spike teknis EODHD; dokumentasinya mencakup bursa Jakarta, raw OHLC, adjusted close, serta panduan penyesuaian harga. Sectors menarik bila pengembangan juga membutuhkan fundamental dan broker/foreign flow Indonesia. Gemini menyediakan JSON schema dan client async yang cocok dengan kontrak analisis berbasis Pydantic. Ini prioritas pengujian, bukan keputusan bahwa provider sudah layak produksi.

**Groq** menjadi alternatif AI terkelola; **Ollama lokal** menjadi pilihan jika ingin menjalankan model sendiri. **Twelve Data** menjadi kandidat data pasar tambahan, dengan cakupan IDX dan paket akses yang masih perlu dikonfirmasi. EODHD dan Sectors sama-sama mendokumentasikan IDX, tetapi kualitas data dan hak penggunaan untuk aplikasi tetap harus dibuktikan.

Belum ada alternatif gratis dengan OHLCV IDX lengkap, penyesuaian harga, dan hak penggunaan aplikasi yang terbukti dalam kajian ini. Akun/API key gratis tidak otomatis menyediakan data IDX atau hak menampilkan data kepada pengguna lain.

## Alternatif Anthropic

| Penyedia | Bukti dari dokumentasi resmi yang dibaca | Kecocokan dan batasan |
|---|---|---|
| Google Gemini | SDK `google-genai` menyediakan `client.aio`, JSON schema, dan schema dari model Pydantic. [Sumber G1](#sumber) | Prioritas uji. Dapat mempertahankan kontrak BUY/HOLD/WAIT dan validasi hasil sekarang. Model, harga, kuota, kebijakan data, serta kualitas bahasa Indonesia harus diverifikasi pada akun yang dipakai. |
| Groq | SDK async tersedia; `response_format` mendukung `json_schema`, khusus model yang mendukungnya. [G2](#sumber) | Alternatif terkelola. Pin model yang lolos uji schema; dukungan JSON mode saja tidak sama dengan pemenuhan seluruh schema. Kecepatan dan biaya belum diukur di aplikasi ini. |
| Ollama lokal | Client async dan contoh resmi output terstruktur memakai `format=...model_json_schema()`. [G3](#sumber) | Mengurangi ketergantungan API eksternal bila model berjalan lokal. Tetap membutuhkan kapasitas server, operasional, dan evaluasi kualitas/latensi. Tidak ada biaya API per token untuk inferensi lokal, tetapi komputasi tetap berbiaya. Mode cloud Ollama memiliki ketentuan berbeda. |

Tidak ada model yang sudah dibenchmark pada data aplikasi. Dukungan schema membantu validasi format; itu tidak membuktikan kebenaran analisis atau kemampuan memprediksi return.

Untuk perbandingan biaya AI, ukur token input/output aktual dan hitung `input_tokens / 1.000.000 × tarif_input + output_tokens / 1.000.000 × tarif_output`, termasuk token tambahan yang ditagihkan model terpilih. Bandingkan biaya per **hasil valid**, tingkat kegagalan, dan latensi, bukan tarif token saja. Harga/kuota Gemini dan Groq belum diverifikasi dari halaman tarif terkini dalam sesi ini.

## Alternatif Yahoo Finance

| Penyedia | Bukti dari dokumentasi resmi yang dibaca | Penilaian |
|---|---|---|
| Sectors API v2 | IDX eksplisit; `/v2/daily/{symbol}/` memiliki close, open, high, low, volume; menerima `BBCA` atau `BBCA.JK`. Maksimal 90 hari kalender per request, 1 kredit. [D1](#sumber) | Prioritas uji untuk fokus Indonesia. OHLC selain close dapat `null`; kelengkapan histori wajib dibuktikan. Kebijakan split/dividen, kedalaman historis, waktu pembaruan, sumber hulu, dan hak penayangan belum dipastikan. |
| EODHD | Dokumentasi resmi mencantumkan `JK` / Jakarta / IDR / XIDX. SDK mendukung histori EOD, splits, dividends, daftar exchange, ticker, dan kalender bursa. Raw OHLC dan `adjusted_close` dijelaskan terpisah. [D2/D4](#sumber) | Prioritas spike harga/backtest. Ada panduan penyesuaian OHLC; jangan menganggap semua OHLC langsung sudah disesuaikan. Data ticker IDX nyata belum diuji. Paket murah berlabel personal use; kebutuhan display dan akses kalender bursa harus diperiksa terpisah. |
| Twelve Data | SDK resmi menyediakan OHLC time series, EOD, exchange/MIC/country, serta output Pandas. [D3](#sumber) | Kandidat untuk perluasan pasar. Cakupan IDX, hak akses paket, histori, penyesuaian harga, dan volume harus diverifikasi sebelum dipilih sebagai sumber IDX. |

**Biaya Sectors yang tercantum pada dokumentasi resmi:** Insider US$59/bulan, termasuk 5.000 kredit API/bulan. Paket Free dan Standard tidak mencakup API. Angka ini berasal dari dokumentasi yang dibaca, bukan penawaran tagihan; periksa [halaman harga](https://sectors.app/pricing) sebelum berlangganan.

**Biaya EODHD yang tercantum pada dokumentasi resmi:** EOD Historical Data — All World mulai US$19,99/bulan untuk **personal use**, mencakup EOD serta splits/dividends. Jangan memakai harga ini sebagai estimasi lisensi aplikasi publik: dokumentasi membedakan internal use dan display use, dengan harga B2B tersendiri. Paket dasar tersebut juga tidak mencakup exchange trading hours. Periksa [harga](https://eodhd.com/pricing) dan hak penggunaan sebelum memilih paket. [D4](#sumber)

Contoh kebutuhan: backfill satu tahun kalender membutuhkan sekitar 5 request per ticker karena batas 90 hari. Untuk 100 ticker, sekitar 500 kredit awal; pembaruan 100 ticker × 22 hari bursa sekitar 2.200 kredit/bulan. Ini estimasi endpoint daily saja, belum termasuk metadata, request ulang, endpoint lain, atau perubahan harga. Endpoint bulk `/v2/close/` dapat mengurangi request harga penutupan, tetapi tidak menggantikan OHLCV untuk candlestick dan backtest.

**Gunakan Sectors v2.** Dokumentasi menyatakan v1 dihentikan pada 11 Mei 2026 dan endpoint v1 mengembalikan 410. Jangan menyalin tutorial lama dengan `/v1/daily/...`.

## Syarat penerimaan sebelum migrasi

1. **Data IDX:** ambil BBCA, BBRI, TLKM, ASII, dan satu saham yang jarang diperdagangkan untuk rentang setidaknya satu tahun; pastikan kedalaman tersedia dan semua potongan 90 hari tersambung tanpa duplikasi. Bedakan hari libur, suspensi/tidak ada transaksi, dan data hilang.
2. **Integritas OHLCV:** harga finite dan positif, volume nonnegatif dalam lembar saham, relasi high/low benar, mata uang IDR, tanggal sesi Asia/Jakarta, serta hanya sesi lengkap. Bar dengan OHLC kosong tidak boleh diganti menjadi candle buatan dari close.
3. **Corporate action:** bandingkan periode yang melewati split dan dividen terhadap sumber pembanding yang sah. Dokumentasikan apakah harga raw, split-adjusted, atau split-and-dividend-adjusted serta perlakuan volume. Jika basis berbeda dari data lama, lakukan backfill ulang seri terkait, bukan mencampurnya.
4. **Kegagalan pasar:** timeout, 401/403, 429, ticker tidak ditemukan, dan data kosong mempertahankan data tersimpan. Pastikan request rentang panjang tidak terpotong diam-diam menjadi hanya 90 hari.
5. **AI:** gunakan kumpulan minimal 30 input dengan tren naik, turun, sideways, indikator bertentangan, dan data kurang. Semua hasil yang diterima wajib lolos schema; error/refusal/truncation tidak boleh disimpan sebagai HOLD. Nilai kesesuaian alasan dengan angka input, bahasa Indonesia, biaya per hasil valid, dan latensi p50/p95.
6. **Kontrak aplikasi:** cache terpisah menurut provider/model/prompt/data revision; confidence tetap dinormalisasi satu kali, cache hit tidak menghabiskan kuota, dan kegagalan tidak menghasilkan rekomendasi sintetis.
7. **Pemakaian aplikasi:** pastikan paket/kontrak mengizinkan penyimpanan historis, penayangan kepada pengguna aplikasi, pemakaian komersial bila relevan, dan pengiriman input ke penyedia AI. Minta konfirmasi sumber hulu bila tujuannya juga menghilangkan ketergantungan pada Yahoo di balik layanan.

## Rencana perubahan setelah kandidat lolos uji

1. Tambahkan interface `AIProvider` dan `MarketDataProvider`, dipilih melalui konfigurasi server. Implementasikan satu kandidat per kategori lebih dahulu agar evaluasi hasilnya jelas.
2. Ganti pemanggilan `call_claude_sonnet` pada service dengan interface tersebut. Pertahankan validasi Pydantic, timeout, batas token, dan pemetaan error yang sudah tersedia. Simpan identitas provider, model aktual, pemakaian token, dan versi prompt; jangan memakai alias model yang berubah diam-diam untuk identitas cache.
3. Adapter pasar memetakan ticker provider ke ticker internal, menyatukan potongan histori, dan mengembalikan OHLCV beserta sumber, mata uang, exchange, timezone sesi, waktu fetch, dan basis penyesuaian harga.
4. Ubah metadata dan pembentukan revisi data: saat ini metadata menganggap data bersumber selalu split-and-dividend-adjusted. Asumsi itu tidak berlaku otomatis untuk provider baru. Identitas/revisi harus mencakup semantik provider dan adjustment agar cache serta data lama tidak tercampur.
5. Jalankan kontrak provider dengan fixture untuk kasus gagal dan smoke nyata dengan kredensial yang disimpan melalui pengaturan environment. Uji ulang alur sync → chart → AI → backtest. Simpan hasil benchmark dan keputusan pemilihan di dokumen ini.
6. Perbarui dokumentasi setup dan domain jaringan provider terpilih. Pergantian provider tidak otomatis menyelesaikan konfigurasi kunci atau akses jaringan cloud.

## Batas verifikasi sesi ini

- Git remote dapat dibaca. Remote HEAD dan checkout masih menunjuk commit `42d887a`; perubahan R1 belum di-commit atau di-push.
- Situs dokumentasi utama `ai.google.dev`, `console.groq.com`, `eodhd.com`, `docs.sectors.app`, dan `twelvedata.com` gagal diakses melalui proxy cloud saat diperiksa. Dokumentasi/SDK resmi di GitHub serta metadata paket PyPI dapat dibaca. Tidak ada bypass jaringan atau perubahan kebijakan runtime.
- Kajian Sectors memakai repository dokumentasi resmi commit `a820bd0` (15 Oktober 2026), termasuk `schema.json`, panduan IDX, panduan v2, dan tabel harga.
- Referensi tambahan dari repository resmi EODHD mencantumkan bursa Jakarta, basis penyesuaian data, paket EOD global, dan pembedaan lisensi personal/display. Penyebutan kode `JK` adalah bukti dokumentasi; belum merupakan hasil smoke API dari environment ini.
- Belum ada request berautentikasi ke API kandidat, pengukuran kualitas/latensi/biaya, pembelian paket, atau migrasi provider. Cakupan yang terdokumentasi dibedakan dari dukungan yang sudah terbukti pada aplikasi.

## Sumber

- **G1:** [Google Gen AI Python SDK: JSON schema/Pydantic dan async](https://github.com/googleapis/python-genai#json-response-schema).
- **G2:** [Groq Python SDK](https://github.com/groq/groq-python) dan [kontrak `response_format`](https://github.com/groq/groq-python/blob/main/src/groq/types/chat/completion_create_params.py).
- **G3:** [Ollama Python SDK](https://github.com/ollama/ollama-python) dan [contoh structured outputs resmi](https://github.com/ollama/ollama-python/blob/main/examples/structured-outputs.py).
- **D1:** [Sectors: IDX API](https://github.com/supertypeai/sectors_api_docs/blob/main/idx-api.mdx), [OpenAPI/schema](https://github.com/supertypeai/sectors_api_docs/blob/main/schema.json), [v2 dan penghentian v1](https://github.com/supertypeai/sectors_api_docs/blob/main/get-started/v2/overview.mdx), [harga API](https://github.com/supertypeai/sectors_api_docs/blob/main/snippets/api-pricing.mdx).
- **D2:** [EODHD Python SDK resmi](https://github.com/EodHistoricalData/EODHD-APIs-Python-Financial-Library), [kode client](https://github.com/EodHistoricalData/EODHD-APIs-Python-Financial-Library/blob/main/eodhd/apiclient.py), [OpenAPI resmi](https://github.com/EodHistoricalData/EODHD-openapi).
- **D3:** [Twelve Data Python SDK resmi](https://github.com/twelvedata/twelvedata-python) dan [metadata paket resminya](https://pypi.org/project/twelvedata/).
- **D4:** EODHD: [daftar exchange](https://github.com/EodHistoricalData/eodhd-claude-skills/blob/main/skills/eodhd-api/references/general/exchanges.md), [panduan adjustment](https://github.com/EodHistoricalData/eodhd-claude-skills/blob/main/skills/eodhd-api/references/general/data-adjustment-guide.md), [paket EOD global](https://github.com/EodHistoricalData/eodhd-claude-skills/blob/main/skills/eodhd-api/references/subscriptions/eod-historical-data-all-world.md), [lisensi personal/B2B/display](https://github.com/EodHistoricalData/eodhd-claude-skills/blob/main/skills/eodhd-api/references/general/pricing-and-plans.md).
