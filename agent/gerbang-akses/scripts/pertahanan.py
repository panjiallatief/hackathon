#!/usr/bin/env python3
"""
pertahanan.py - Pertahanan terhadap prompt injection.

Prinsip: detektor ini TIDAK diandalkan sebagai pengaman utama (bisa diakali).
Pengaman utamanya ada di arsitektur (gerbang akses + validator). Detektor ini:
  1. membersihkan karakter tak terlihat yang dipakai untuk menyelundupkan perintah,
  2. memberi skor kecurigaan per baris,
  3. MENGHAPUS baris berbahaya sebelum teks dikirim ke AI,
     sehingga AI tidak pernah membaca payload-nya sama sekali.

Hanya memakai pustaka standar Python.
"""
import base64
import re
import unicodedata

PENGGANTI = "[Bagian ini dihapus sistem karena berisi perintah yang ditujukan kepada AI.]"

# Karakter tak terlihat: zero-width, kontrol arah teks (bidi), dan "tag characters"
# (U+E0000-U+E007F) yang bisa menyembunyikan teks ASCII utuh.
_TAK_TERLIHAT = re.compile(
    "[\u200b-\u200f\u2028-\u202e\u2060-\u2064\u2066-\u2069\ufeff\U000e0000-\U000e007f]"
)
_TAG = re.compile("[\U000e0000-\U000e007f]")

# --- Pola berbobot. Skor >= 2 dianggap mencurigakan, >= 3 berbahaya.
_POLA_KUAT = [  # bobot 3: hampir pasti serangan
    r"\b(abaikan|lupakan|acuhkan|langgar)\s+(semua\s+|seluruh\s+)?(instruksi|aturan|perintah|batasan)",
    r"\b(ignore|disregard|forget|override)\s+(all\s+|any\s+|the\s+)?(previous\s+|prior\s+|above\s+)?(instructions|rules|guidelines)",
    r"\byou\s+are\s+now\b",
    r"\bkamu\s+sekarang\s+(adalah|berperan|menjadi)\b",
    r"\b(system\s+prompt|prompt\s+sistem|developer\s+mode|mode\s+pengembang)\b",
    r"<\|im_start\|>|\[/?INST\]|###\s*(system|instruction)",
    # Pura-pura / ganti peran (roleplay)
    r"\b(berpura[- ]?pura|pura[- ]?pura)\s+(menjadi|jadi|sebagai)\b",
    r"\banggap(lah)?\s+(dirimu|diri\s+kamu|diri\s+anda)\b",
    r"\banggap(lah)?\s+(kamu|anda)\s+(sebagai|adalah|seorang)\b",
    r"\b(bayangkan|seolah[- ]?olah|seakan[- ]?akan)\s+(kamu|anda|dirimu)\s+(adalah|sebagai|menjadi|seorang)\b",
    r"\bmulai\s+(sekarang|saat\s+ini|detik\s+ini),?\s+(kamu|anda|dirimu)\s+(adalah|berperan|bertindak|menjadi)\b",
    r"\b(kamu|anda)\s+(berperan|bertindak)\s+sebagai\b",
    r"\bpretend\s+(to\s+be|you\s+are)\b|\broleplay\s+as\b|\byou\s+(must\s+|will\s+|should\s+)?(now\s+)?(act|behave)\s+as\b",
]
_POLA_SEDANG = [  # bobot 2: perintah yang ditujukan ke AI, eksfiltrasi, atau perintah sistem
    r"(?m)^\s*[\[\(]?\s*(ai|asisten|assistant|system|sistem|bot|model|llm|claude|gpt|workbuddy)\s*[\]\)]?\s*[:,\-]\s*"
    r"(tolong\s+|please\s+)?(kirim|teruskan|forward|send|email|tampilkan|show|reveal|bocorkan|hapus|delete|"
    r"jalankan|run|execute|abaikan|ignore|buka|open|ubah|change|unduh|download|unggah|upload)",
    r"\b(catatan|pesan|instruksi)\s+(untuk|kepada|bagi)\s+(ai|asisten|sistem|model|bot)\b",
    r"\b(note|message|instruction)s?\s+(to|for)\s+(the\s+)?(ai|assistant|model|system|bot)\b",
    r"!\[[^\]]*\]\(\s*https?://",  # gambar markdown ke server luar: jalur pencurian data
    r"\b(bagikan|tampilkan|bocorkan|sebarkan|kirimkan|share|reveal|leak|dump)\s+(semua|seluruh|all|every)\s+"
    r"(dokumen|data|file|gaji|slip|rahasia|documents|files|salaries|records)\b",
    r"\brm\s+-rf\b|\bcurl\s+https?://|\bwget\s+|\bos\.system\b|\bsubprocess\b|\bpowershell\b|\binvoke-expression\b",
]
_POLA_KUAT = [re.compile(p, re.I) for p in _POLA_KUAT]
_POLA_SEDANG = [re.compile(p, re.I) for p in _POLA_SEDANG]
_BASE64 = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")


def normalisasi(teks):
    """Seragamkan bentuk huruf (NFKC) dan buang karakter tak terlihat.
    Mengembalikan (teks_bersih, temuan)."""
    temuan = []
    if _TAG.search(teks):
        tersembunyi = "".join(chr(ord(c) - 0xE0000) for c in _TAG.findall(teks) if 0x20 <= ord(c) - 0xE0000 < 0x7F)
        temuan.append(f"karakter tag tersembunyi (isi: {tersembunyi[:80]!r})")
    if _TAK_TERLIHAT.search(teks):
        temuan.append("karakter tak terlihat")
    teks = _TAK_TERLIHAT.sub("", teks)
    teks = unicodedata.normalize("NFKC", teks)
    return teks, temuan


def _skor_mentah(teks):
    skor, alasan = 0, []
    for p in _POLA_KUAT:
        if p.search(teks):
            skor = max(skor, 3)
            alasan.append(f"pola kuat: {p.pattern[:40]}")
    for p in _POLA_SEDANG:
        if p.search(teks):
            skor = max(skor, 2)
            alasan.append(f"pola sedang: {p.pattern[:40]}")
    return skor, alasan


def skor_injeksi(teks):
    """Skor kecurigaan 0-3 untuk satu potong teks, beserta alasannya."""
    teks, temuan = normalisasi(teks)
    skor, alasan = _skor_mentah(teks)
    # Payload yang disandikan base64: buka sandinya, lalu periksa ulang.
    for kandidat in _BASE64.findall(teks):
        try:
            isi = base64.b64decode(kandidat + "=" * (-len(kandidat) % 4)).decode("utf-8")
        except Exception:
            continue
        s, a = _skor_mentah(isi)
        if s >= 2:
            skor = 3
            alasan.append("perintah tersembunyi dalam base64")
    if temuan:
        alasan.extend(temuan)
        # Penyelundupan karakter tak terlihat sendiri sudah mencurigakan.
        skor = max(skor, 2)
        s, _ = _skor_mentah(teks)
        if s >= 2:
            skor = 3
    return skor, alasan


def bersihkan_untuk_ai(teks):
    """Normalisasi, lalu ganti setiap baris yang mencurigakan dengan PENGGANTI.
    Mengembalikan (teks_aman, skor_tertinggi, daftar_alasan, baris_dihapus)."""
    teks, temuan_awal = normalisasi(teks)
    baris_aman, dihapus, alasan_semua = [], [], list(temuan_awal)
    tertinggi = 2 if temuan_awal else 0
    for baris in teks.splitlines() or [teks]:
        skor, alasan = skor_injeksi(baris)
        tertinggi = max(tertinggi, skor)
        if skor >= 2:
            dihapus.append(baris)
            alasan_semua.extend(alasan)
            if not baris_aman or baris_aman[-1] != PENGGANTI:
                baris_aman.append(PENGGANTI)
        else:
            baris_aman.append(baris)
    return "\n".join(baris_aman), tertinggi, alasan_semua, dihapus


def url_eksternal(teks):
    """Semua URL di teks (untuk validator keluaran)."""
    return re.findall(r"https?://[^\s)\]>\"']+", teks)
