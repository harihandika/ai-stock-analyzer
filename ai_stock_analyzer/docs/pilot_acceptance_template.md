# Lembar penerimaan pilot PRD 1.3

Template ini belum berisi hasil peserta atau keputusan rilis. Isi setelah pengamatan nyata; tidak mengganti nilai kosong dengan hasil tes otomatis. Acuan: [PRD](prd_kesiapan_pilot_8d9645d.md) dan [runbook operator](operasional_pilot.md).

## Identitas kandidat dan layanan

| Field | Nilai yang harus diisi |
|---|---|
| SHA aplikasi / API / frontend / worker | Belum dicatat |
| Environment dan resource staging / PostgreSQL / jumlah proses | Belum dicatat |
| URL CI remote dan waktu run WIB | Belum dicatat |
| Provider/paket/model aktual, budget dan hak penggunaan | Belum diterima |
| Bukti IDX+AS / adjustment / kalender / sesi pendek / DST | Belum diterima |
| Ingestion terjadwal / alert transisi nyata / replay | Belum diterima |
| Inbox reset nyata / sekali pakai / sesi lama ditolak | Belum diterima |
| Backup terakhir, restore rehearsal, RPO/RTO aktual | Belum diterima di staging |
| Operator dan jalur eskalasi | Belum ditetapkan |

## Tugas dan ukuran

Tugas A: cari saham → jelaskan tanggal/sumber harga → simpan watchlist. Ukur dari instruksi selesai dibaca sampai saham tersimpan, target ≤90 detik pada setidaknya empat dari lima peserta.

Tugas B: masukkan modal/entry/stop/target/risiko/lot, hitung, lengkapi alasan/horizon/pembatalan lalu simpan rencana valid. Target ≤3 menit pada setidaknya empat peserta. Catat bantuan dan kemampuan menyebut risiko nominal, lot dan asumsi biaya. Simpan tanpa memahami angka tidak memenuhi penerimaan pemahaman.

Jangan memberi jawaban sumber/tanggal sebelum pertanyaan pemahaman. Bedakan waktu fetch dan tanggal pasar, stale/unknown, kuota dan skor model yang belum terkalibrasi. Perangkat fisik dan teknologi bantu dicatat versi aktualnya; emulasi diberi label emulasi.

| Peserta anonim | Persona | Perangkat/OS/browser/teknologi bantu | A: detik/berhasil/bantuan | B: detik/berhasil/bantuan | Pemahaman data/risiko/biaya/kuota | Hambatan |
|---|---|---|---|---|---|---|
| P01 | Belum diisi | Belum diuji | Belum diuji | Belum diuji | Belum diuji | Belum dicatat |
| P02 | Belum diisi | Belum diuji | Belum diuji | Belum diuji | Belum diuji | Belum dicatat |
| P03 | Belum diisi | Belum diuji | Belum diuji | Belum diuji | Belum diuji | Belum dicatat |
| P04 | Belum diisi | Belum diuji | Belum diuji | Belum diuji | Belum diuji | Belum dicatat |
| P05 | Belum diisi | Belum diuji | Belum diuji | Belum diuji | Belum diuji | Belum dicatat |

## Pengamatan tujuh hari

Tetapkan waktu mulai/akhir WIB per peserta, persetujuan pencatatan, kegiatan kembali yang dihitung dan denominator peserta yang sudah mencapai jendela pengamatan. Catat jumlah kembali hari berikutnya/hari ketujuh, tugas pantauan, relevansi alert dan alasan berhenti. Peserta yang belum mencapai hari ketujuh belum dapat disebut tidak kembali. Tidak menetapkan angka retensi fiktif sebagai hasil.

## Keputusan

Untuk setiap AF/UX/KP, catat lulus/gagal/terblokir/belum diuji, SHA, langkah, expected/actual, bukti tersanitasi dan reviewer. Ringkas hambatan yang paling sering muncul dan tiket tindak lanjut. Keputusan lanjut pilot/perbaiki/perluas publik harus menyebut cakupan yang diterima dan gerbang yang masih terbuka. Hindari nama/email/password/token peserta pada artefak yang dibagikan.
