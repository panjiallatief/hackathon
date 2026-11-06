#!/usr/bin/env python3
"""
pembaca_file.py - Membaca file unggahan dengan aman sebelum masuk indeks.

Memisahkan:
  teks_terlihat   : yang benar-benar dilihat manusia saat membuka file -> boleh diindeks
  teks_tambahan   : teks tersembunyi, komentar, metadata, alt text -> TIDAK diindeks,
                    tetapi tetap diperiksa untuk mencari perintah tersembunyi

Kebijakan "gagal tertutup": kalau file tidak bisa diperiksa dengan benar,
file DITOLAK (masuk karantina), bukan dibaca setengah-setengah.

Format: .md .txt (pustaka standar), .docx (pustaka standar),
        .pdf (butuh PyMuPDF untuk deteksi teks tersembunyi; tanpa itu PDF ditolak).
"""
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

EKSTENSI_DIIZINKAN = {".md", ".txt", ".docx", ".pdf"}
BATAS_UKURAN_FILE = 20 * 1024 * 1024        # 20 MB
BATAS_UKURAN_DIEKSTRAK = 100 * 1024 * 1024  # anti "zip bomb"
BATAS_RASIO_KOMPRESI = 100

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
NAMA_SAH = re.compile(r"^[A-Za-z0-9_\-]{1,80}$")


def _hasil(status="ok", alasan="", terlihat="", tambahan=None, temuan=None):
    return {"status": status, "alasan_tolak": alasan, "teks_terlihat": terlihat,
            "teks_tambahan": tambahan or [], "temuan": temuan or []}


def baca_file(path, batas_ekstrak=BATAS_UKURAN_DIEKSTRAK):
    path = Path(path)
    ext = path.suffix.lower()
    if not NAMA_SAH.match(path.stem):
        return _hasil("tolak", "nama file tidak sah (hanya huruf, angka, _ dan -)")
    if ext not in EKSTENSI_DIIZINKAN:
        return _hasil("tolak", f"jenis file tidak diizinkan: {ext or '(tanpa ekstensi)'}")
    if path.stat().st_size > BATAS_UKURAN_FILE:
        return _hasil("tolak", "ukuran file melebihi batas")
    try:
        if ext in (".md", ".txt"):
            return _hasil(terlihat=path.read_text(encoding="utf-8"))
        if ext == ".docx":
            return _baca_docx(path, batas_ekstrak)
        return _baca_pdf(path)
    except Exception as e:  # file rusak atau sengaja dibuat aneh -> tolak
        return _hasil("tolak", f"file tidak dapat diperiksa: {type(e).__name__}")


# ------------------------------------------------------------------ DOCX

def _cek_zip(zf, batas_ekstrak):
    total = 0
    for info in zf.infolist():
        nama = info.filename
        if nama.startswith("/") or ".." in nama.split("/"):
            return "isi arsip mencoba keluar folder (path traversal)"
        if nama.lower().endswith("vbaproject.bin"):
            return "berisi makro (VBA)"
        total += info.file_size
        if info.compress_size and info.file_size / info.compress_size > BATAS_RASIO_KOMPRESI:
            return "rasio kompresi tidak wajar (indikasi zip bomb)"
    if total > batas_ekstrak:
        return "ukuran setelah diekstrak melebihi batas (indikasi zip bomb)"
    return ""


def _run_tersembunyi(run):
    rpr = run.find(f"{W}rPr")
    if rpr is None:
        return ""
    if rpr.find(f"{W}vanish") is not None or rpr.find(f"{W}specVanish") is not None:
        return "teks disembunyikan (hidden)"
    warna = rpr.find(f"{W}color")
    if warna is not None and warna.get(f"{W}val", "").upper() in ("FFFFFF", "FEFEFE"):
        return "teks putih"
    ukuran = rpr.find(f"{W}sz")
    if ukuran is not None and ukuran.get(f"{W}val", "99").isdigit() and int(ukuran.get(f"{W}val")) <= 4:
        return "huruf sangat kecil"
    return ""


def _teks_bagian(xml, lokasi):
    """Pisahkan teks terlihat dan tersembunyi dari satu bagian dokumen Word."""
    root = ET.fromstring(xml)
    terlihat, tambahan = [], []
    for par in root.iter(f"{W}p"):
        bagian_terlihat = []
        for run in par.iter(f"{W}r"):
            teks = "".join(t.text or "" for t in run.iter(f"{W}t"))
            if not teks:
                continue
            sebab = _run_tersembunyi(run)
            if sebab:
                tambahan.append((f"{lokasi} ({sebab})", teks))
            else:
                bagian_terlihat.append(teks)
        if bagian_terlihat:
            terlihat.append("".join(bagian_terlihat))
    for doc_pr in root.iter(f"{WP}docPr"):  # teks alternatif gambar
        for atribut in ("descr", "title"):
            if doc_pr.get(atribut):
                tambahan.append((f"{lokasi} (alt text gambar)", doc_pr.get(atribut)))
    return terlihat, tambahan


def _baca_docx(path, batas_ekstrak):
    with zipfile.ZipFile(path) as zf:
        masalah = _cek_zip(zf, batas_ekstrak)
        if masalah:
            return _hasil("tolak", masalah)
        nama_isi = set(zf.namelist())
        terlihat, tambahan = [], []

        bagian_utama = ["word/document.xml"] + sorted(
            n for n in nama_isi if re.match(r"word/(header|footer|footnotes|endnotes)\d*\.xml$", n))
        for nama in bagian_utama:
            if nama in nama_isi:
                t, x = _teks_bagian(zf.read(nama), nama.split("/")[-1])
                if nama == "word/document.xml":
                    terlihat.extend(t)
                else:
                    tambahan.extend((nama.split("/")[-1], s) for s in t)
                tambahan.extend(x)

        if "word/comments.xml" in nama_isi:
            t, x = _teks_bagian(zf.read("word/comments.xml"), "komentar")
            tambahan.extend(("komentar", s) for s in t)
            tambahan.extend(x)

        for meta in ("docProps/core.xml", "docProps/app.xml", "docProps/custom.xml"):
            if meta in nama_isi:
                for el in ET.fromstring(zf.read(meta)).iter():
                    if el.text and el.text.strip():
                        tambahan.append((f"metadata {el.tag.split('}')[-1]}", el.text.strip()))
    return _hasil(terlihat="\n\n".join(terlihat), tambahan=tambahan)


# ------------------------------------------------------------------ PDF

def _muat_pymupdf():
    try:
        import pymupdf
        return pymupdf
    except ImportError:
        try:
            import fitz
            return fitz
        except ImportError:
            return None


def _baca_pdf(path):
    pymupdf = _muat_pymupdf()
    if pymupdf is None:
        # Gagal tertutup: tanpa alat pemeriksa teks tersembunyi, PDF tidak diterima.
        return _hasil("tolak", "PDF butuh PyMuPDF untuk diperiksa (pip install pymupdf)")
    terlihat, tambahan = [], []
    with pymupdf.open(path) as doc:
        if doc.is_encrypted:
            return _hasil("tolak", "PDF terkunci kata sandi")
        if doc.embfile_count() > 0:
            return _hasil("tolak", "PDF berisi file lampiran tersembunyi")
        for kunci, nilai in (doc.metadata or {}).items():
            if nilai and kunci not in ("format", "encryption"):
                tambahan.append((f"metadata {kunci}", str(nilai)))
        for nomor, page in enumerate(doc, 1):
            baris = []
            for span in page.get_texttrace():
                teks = "".join(chr(c[0]) for c in span.get("chars", []))
                if not teks.strip():
                    continue
                warna = span.get("color") or (0, 0, 0)
                putih = len(warna) >= 3 and all(v >= 0.95 for v in warna[:3])
                if span.get("type") == 3:
                    tambahan.append((f"halaman {nomor} (teks tak terlihat)", teks))
                elif span.get("opacity", 1) < 0.1:
                    tambahan.append((f"halaman {nomor} (teks transparan)", teks))
                elif putih:
                    tambahan.append((f"halaman {nomor} (teks putih)", teks))
                elif span.get("size", 12) < 2:
                    tambahan.append((f"halaman {nomor} (huruf sangat kecil)", teks))
                else:
                    baris.append(teks)
            if baris:
                terlihat.append(" ".join(baris))
            for annot in page.annots() or []:
                isi = (annot.info or {}).get("content", "")
                if isi:
                    tambahan.append((f"halaman {nomor} (anotasi)", isi))
    return _hasil(terlihat="\n\n".join(terlihat), tambahan=tambahan)
