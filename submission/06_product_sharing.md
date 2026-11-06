# Product Sharing - Di mana WorkBuddy memberi nilai, dan apa yang kami pelajari

## Nilai tambah WorkBuddy
- **Skill = SOP + skrip.** Logika pengaman (gerbang, validator, log) hidup sebagai skrip Python di dalam skill,
  sehingga bisa diuji otomatis di luar AI.
- **Expert** memastikan skill selalu dipakai tanpa harus dipanggil manual. Dibuat dengan `expert-manager`.
- **Workspace per proyek** membuat seluruh agen (skill, data, state, bukti, submission) menjadi satu folder
  yang bisa dibuka siapa pun.
- Menjalankan perintah dari chat: AI memanggil `gerbang.py`, membaca JSON-nya, dan menyusun jawaban.

## Yang WorkBuddy belum sediakan, dan kami bangun sendiri
- Gerbang izin sebelum pencarian, identitas dari sesi (bukan chat), validator keluaran, log berantai hash,
  karantina data tanpa label, pembaca file gagal-tertutup.

## Pembelajaran
1. **Skill hanya petunjuk.** Tanpa Expert/skill aktif, AI membaca file sendiri dan membocorkan data.
   Keamanan harus di arsitektur, bukan di instruksi.
2. **Path relatif gagal setelah skill dipasang global** (skrip berjalan dari folder skill). Solusi: skrip
   mencari folder proyek sendiri, dan status `error` tidak boleh menyamar sebagai "tidak ditemukan".
3. **Pemeriksaan terminal berbeda antar OS**; kami menambahkan PIN sebagai pengaman utama persetujuan dan login.
4. **Kecepatan**: satu jawaban butuh 2-3 putaran AI (12-25 detik). Jalur cepat untuk penolakan memangkas satu putaran.
5. [Tambahkan temuanmu sendiri saat menguji di WorkBuddy: model mana yang paling cepat, berapa kredit per uji, dll.]
