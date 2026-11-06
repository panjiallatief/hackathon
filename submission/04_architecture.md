# Diagram Arsitektur - Pustaka Aman

File gambar: `04_architecture.svg` (buka di browser, screenshot atau ekspor ke PNG untuk formulir).

```
                 MANUSIA (terminal)                     AGEN (WorkBuddy, Expert "Pustaka Aman")
            ┌──────────────────────┐                 ┌──────────────────────────────┐
            │ sesi.py login + PIN  │                 │ Pertanyaan karyawan          │
            │ -> state/sesi.json   │                 └──────────────┬───────────────┘
            │    (ditandatangani)  │                                │ gerbang.py cari --q
            └──────────┬───────────┘                                ▼
                       │              ╔═════════════ ATURAN PASTI (skrip) ═════════════╗
                       └─────────────►║ 1 Verifikasi tanda tangan sesi -> user_id       ║
                                      ║ 2 Query tetap ke tabel izin (parameter: user_id)║
   data/ ──ingest──► state/gerbang.db ║ 3 Pencarian FTS hanya di potongan diizinkan     ║
   (karantina bila   (sudah disamarkan║ 4 Lencana peran + potongan bernomor             ║
    tanpa label,      & dibersihkan)  ╚════════════════════════╤═══════════════════════╝
    teks tersembunyi)                                          │ JSON: sesi, hasil[1..n]
                       - - - - - - - - - BATAS KEPERCAYAAN - - -┼- - - - - - - - - - - - -
                                                               ▼
                                      ┌──────────────────────────────────────────────┐
                                      │ AI menyusun jawaban: hanya dari hasil,        │
                                      │ sitasi [n], kalimat baku bila kosong          │
                                      └──────────────────────┬───────────────────────┘
                                                             │ gerbang.py validasi
                                      ╔══════════════════════▼═══════════════════════╗
                                      ║ 5 Validator: sumber dalam izin, angka ada di  ║
                                      ║   sumber, tanpa nama rahasia/PII/URL asing    ║
                                      ║   gagal -> kalimat baku                       ║
                                      ║ 6 Log berantai hash (state/log_gerbang.jsonl) ║
                                      ╚═══════════════════════════════════════════════╝

Trade-off: data masih di folder proyek saat demo (agar juri bisa menjalankan); di produksi gerbang
menjadi API server (HRIS) dengan SSO, sehingga data tidak pernah ada di laptop pengguna.
Trade-off: pencarian kata kunci (cepat, deterministik, tanpa dependensi) vs semantik (lebih pintar, lebih lambat).
```
