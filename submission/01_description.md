# Pustaka Aman - Deskripsi Proyek

**Challenge:** A - The Workplace Brain
**Skenario:** Orientasi karyawan baru: penggantian biaya, hak cuti, kewenangan persetujuan.
**Blurb:** Asisten pengetahuan kantor yang tahu batas aksesnya.

## 1. Ikhtisar

Pustaka Aman adalah asisten yang menjawab pertanyaan karyawan dari dokumen, chat, dan tugas perusahaan,
dengan sumber bernomor, dan tidak pernah memperlihatkan data yang bukan haknya. Pengguna utamanya:
karyawan baru, staf operasional, dan tim HR. Nilai yang diberikan: HR berhenti menjadi "leher botol"
pertanyaan berulang, dan perusahaan bisa memakai AI di atas data internal tanpa risiko kebocoran.

## 2. Real-world insight

[Isi dengan pengalamanmu sendiri: melatih tim Finance, Accounting, dan Tax serta Procurement memakai AI,
dan membangun HRIS. Tulis 3-5 kalimat: siapa yang kesulitan, apa yang terjadi saat AI dipakai tanpa
batas akses, dan apa yang kamu lihat langsung. Jangan mengarang angka.]

Pengamatan kunci: aturan "data apa yang boleh dimasukkan ke AI" hanya bekerja kalau orang patuh.
Keamanan harus ada di sistem, bukan di ingatan pengguna.

## 3. Desain solusi

**Prinsip:** AI adalah satu-satunya komponen yang bisa salah atau tertipu, maka ia diapit aturan pasti
di kedua sisi.

- **Sebelum AI:** gerbang akses menjalankan query tetap ke tabel izin (parameter hanya ID sesi),
  lalu pencarian teks penuh hanya di potongan yang diizinkan. Data tanpa label masuk karantina.
- **Identitas:** sesi login dibuat manusia di terminal dengan PIN, ditandatangani dengan kunci di luar
  workspace. Agen tidak punya parameter identitas. Klaim identitas di chat diabaikan dan dicatat.
- **Saat data masuk:** pembaca file gagal-tertutup (teks tersembunyi, metadata, makro, zip bomb),
  baris berisi perintah untuk AI dihapus sebelum diindeks, NIK dan nomor HP disamarkan.
- **Sesudah AI:** validator memeriksa setiap sumber yang dikutip ada dalam izin, setiap angka ada di
  sumber, tidak ada nama data rahasia, tidak ada tautan atau gambar asing. Gagal = kalimat baku.
- **Catatan:** log berantai hash; perintah "tunjukkan log" menampilkan tabel dan status integritas.
- **Penolakan simetris:** jawaban untuk hal yang tidak boleh diketahui identik dengan jawaban untuk hal
  yang tidak ada.

**Peran prompt:** SKILL.md mengatur urutan langkah (cari -> jawab -> validasi), format lencana peran dan
sitasi bernomor, aturan prioritas sumber saat konflik, serta penanganan error yang tidak boleh menyamar
sebagai "tidak ditemukan". Expert "Pustaka Aman" di WorkBuddy memastikan skill selalu dipakai.

## 4. Nilai bisnis

[Isi dengan angka yang kamu ukur sendiri, misalnya: waktu HR menjawab pertanyaan berulang per minggu
sebelum vs sesudah; jumlah percobaan akses tidak sah yang terdeteksi di log selama uji; hasil uji
X/20.] Kesalahan yang dicegah: kebocoran gaji dan proyek rahasia, angka karangan, instruksi tersisip.

## 5. Batasan dan rencana lanjutan

Lihat accountability sheet. Produksi: gerbang menjadi API di server (misalnya HRIS), login SSO,
ingest bertahap, pencarian semantik.
