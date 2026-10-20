# BUG REPORT — 8d9645d

Tanggal 20 Oktober 2026, WIB. Tiga temuan tambahan terkonfirmasi melalui aplikasi berjalan. Temuan ini belum boleh dianggap diperkenalkan oleh commit8d9645d; audit tidak mereproduksi ketiga kasus ini pada versi sebelumnya. Empat bug sebelumnya sudah ditutup dengan bukti retest pada USER_TESTING_REPORT.md. Tidak ada perbaikan source yang dilakukan auditor.

| ID | Severity | Masalah |
|---|---|---|
| BUG-005 | P1 | Respons perbandingan BBCA muncul ketika riwayat aktif sudah AAPL |
| BUG-006 | P2 | Alert Sinyal AI baru gagal disimpan dari form |
| BUG-007 | P2 | Filter screener hilang setelah membuka saham dan kembali |

## BUG-005 — Respons perbandingan BBCA muncul ketika riwayat aktif sudah AAPL

**Severity:**P1 · **Status:**Reproduced

**Halaman:**/research?tab=history

**Environment:**Chromium 154, Next production, SQLite audit. Dua histori BBCA dan satu histori AAPL berasal fixture. Respons compare ditahan 2 detik untuk mensimulasikan jaringan lambat.

**Langkah reproduksi:**

1. Buka riwayat BBCA.JK yang memiliki dua record.
2. Pilih kedua record dan klik Bandingkan dua hasil.
3. Saat respons compare belum datang, ubah Kode saham menjadi AAPL dan klik Muat riwayat.
4. Biarkan riwayat AAPL selesai dimuat, lalu tunggu respons compare BBCA.

**Expected:** Respons untuk konteks BBCA dibatalkan atau diabaikan. Halaman AAPL tidak menampilkan perbandingan BBCA.

**Actual:** Input aktif AAPL dan daftar satu hasil AAPL tampil bersama panel compare BBCA:BUY→BUY, perubahan skor -10 poin persentase, serta teks fixture khusus BBCA.JK. Panel tidak mencantumkan ticker sehingga konteks salah mudah terlewat.

**Dampak pengguna:** Pengguna dapat membaca perbandingan analisis saham sebelumnya sebagai konteks saham yang sedang diteliti. Ini cacat integritas konteks finansial, bukan kesalahan rumus selisih.

**Bukti:** [N05](evidence/negative.json), [screenshot](evidence/history-stale-comparison.png), negative-trace.zip. Pembanding normal 78→88 lulus X02.

**Penyebab yang ditelusuri:** [ai_stock_analyzer_frontend/src/app/research/page.tsx:433](https://github.com/harihandika/ai-stock-analyzer/blob/8d9645df458c92efa01a5ec279ff98c4f2dee785/ai_stock_analyzer_frontend/src/app/research/page.tsx#L433) mengosongkan perbandingan saat ticker dimuat; handler perbandingan di [ai_stock_analyzer_frontend/src/app/research/page.tsx:519](https://github.com/harihandika/ai-stock-analyzer/blob/8d9645df458c92efa01a5ec279ff98c4f2dee785/ai_stock_analyzer_frontend/src/app/research/page.tsx#L519) kemudian memanggil setComparison tanpa pemeriksaan ticker/versi request atau pembatalan.

**Rekomendasi perbaikan:** Ikat request compare ke snapshot activeTicker dan ID yang dipilih, batalkan saat konteks berubah, serta periksa snapshot sebelum setState. Tampilkan ticker, tanggal dan model kedua record pada panel. Tambahkan regresi respons lambat dan navigasi saat request berjalan.

## BUG-006 — Alert Sinyal AI baru gagal disimpan dari form

**Severity:**P2 · **Status:**Reproduced

**Halaman:**/research?tab=monitoring

**Environment:**Chromium 154, build produksi, akun disposable dan BBCA.JK terdaftar. Tidak memerlukan panggilan provider untuk reproduksi.

**Langkah reproduksi:**

1. Buka Alert dan job untuk BBCA.JK.
2. Ubah Jenis alert menjadi Sinyal AI baru.
3. Pilih sinyal BUY.
4. Klik Simpan alert.

**Expected:** Rule sinyal tersimpan dan muncul dalam daftar alert. Form sinyal tidak meminta arah harga yang tidak berlaku.

**Actual:** UI mengirim {kind:"signal", direction:null, threshold:null, signal:"BUY"}. API menolak HTTP 422 dengan literal_error pada direction. UI menampilkan “Input should be 'above' or 'below'”. Tidak ada rule yang disimpan.

**Dampak pengguna:** Fitur monitoring sinyal tidak dapat digunakan dari UI. Pesan error meminta field yang tidak tersedia pada mode tersebut.

**Bukti:** [Retest N04](evidence/signal-retest.json), [screenshot](evidence/signal-alert-error.png). Kontrol X04 membuktikan API menerima 201 bila direction tidak dikirim.

**Penyebab yang ditelusuri:** [ai_stock_analyzer_frontend/src/app/research/page.tsx:646](https://github.com/harihandika/ai-stock-analyzer/blob/8d9645df458c92efa01a5ec279ff98c4f2dee785/ai_stock_analyzer_frontend/src/app/research/page.tsx#L646) selalu memasukkan FormData.get("direction"), sedangkan kontrol arah tidak dirender untuk kind signal. [ai_stock_analyzer/app/domain/schemas/product.py:26](https://github.com/harihandika/ai-stock-analyzer/blob/8d9645df458c92efa01a5ec279ff98c4f2dee785/ai_stock_analyzer/app/domain/schemas/product.py#L26) mengharuskan direction above/below bila dikirim; null tidak valid.

**Rekomendasi perbaikan:** Untuk alert sinyal, hilangkan direction dari payload atau gunakan default kontrak yang disepakati. Pisahkan payload per jenis alert agar field tidak relevan tidak terkirim. Terjemahkan validasi menjadi pesan yang bisa ditindaklanjuti. Uji BUY/HOLD/WAIT dari UI.

## BUG-007 — Filter screener hilang setelah membuka saham dan kembali

**Severity:**P2 · **Status:**Reproduced

**Halaman:**/research (Screener)

**Environment:**Chromium 154 production. Filter tersimpan dan data fixture tersedia. Tidak memerlukan respons lambat.

**Langkah reproduksi:**

1. Isi Bursa IDX, Volume minimal 1000, RSI minimum 20 dan maksimum 60.
2. Klik Terapkan filter; BBCA.JK muncul.
3. Buka BBCA.JK dari hasil.
4. Tekan tombol Back browser untuk kembali ke screener.

**Expected:** Kriteria, halaman dan hasil yang aktif dipulihkan sehingga pengguna dapat menilai kandidat berikutnya tanpa mengulang pencarian.

**Actual:** URL kembali ke /research;Bursa, Volume dan RSI kembali kosong. Daftar kembali ke cakupan tanpa filter. Preset yang sudah disimpan masih dapat dimuat manual, tetapi filter aktif tidak dipertahankan.

**Dampak pengguna:** Riset beberapa kandidat memerlukan pengisian ulang atau pemilihan preset berulang; filter belum disimpan hilang sepenuhnya.

**Bukti:** [J10](evidence/journey.json), [sebelum](evidence/screener-filtered.png), [sesudah Back](evidence/screener-after-back.png), journey-trace.zip.

**Penyebab yang ditelusuri:** [ai_stock_analyzer_frontend/src/app/research/page.tsx:110](https://github.com/harihandika/ai-stock-analyzer/blob/8d9645df458c92efa01a5ec279ff98c4f2dee785/ai_stock_analyzer_frontend/src/app/research/page.tsx#L110) menyimpancriteria/page sebagai state lokal. [ai_stock_analyzer_frontend/src/app/research/page.tsx:149](https://github.com/harihandika/ai-stock-analyzer/blob/8d9645df458c92efa01a5ec279ff98c4f2dee785/ai_stock_analyzer_frontend/src/app/research/page.tsx#L149) memperbarui state tanpa menaruhnya diURL atau penyimpanan yang dipulihkan saat Back.

**Rekomendasi perbaikan:** Serialisasi filter, sort dan page keURL sambil mempertahankan tab/ticker. Inisialisasi form dariURL dan pulihkan posisi hasil. UjiBack/Forward, refresh, preset serta filter belum disimpan.

## Observasi yang tidak dihitung sebagai bug baru

- Setelah Tandai dibaca, unread API 0 tetapi badge header tetap 1 sampai polling berikutnya. Ini ketidaksinkronanUX; event tidak diduplikasi dan database sudah benar(B03).
- Kegagalan selectorJ07/N04 dan pembacaan DOM tidak atomikM390 ditangani dengan retest. Tidak ada bug harga/tanggal yang diklaim dari masalah harness tersebut.
- Provider nyata, SMTP dan perangkat fisik tidak tersedia; batas environment dilaporkanBlocked, bukan bug aplikasi.
- Tidak ada klaim tidak terdapatP0 di seluruh produk. Pada cakupan audit ini, bug paling berat yang direproduksi adalahP1 diBUG-005.
