#!/usr/bin/env python3
"""
run_cases.py - Menjalankan tests/cases.json terhadap gerbang, lalu MENULIS ULANG
submission/03_test_results.md. Jalankan setiap kali kode atau data berubah,
supaya tabel hasil uji tidak pernah basi.

  python tests/run_cases.py
"""
import json
import os
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

AKAR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AKAR / "agent" / "gerbang-akses" / "scripts"))
os.environ.setdefault("PUSTAKA_AMAN_RAHASIA", str(AKAR / "state" / ".rahasia_uji"))

import contoh_data  # noqa: E402
import gerbang  # noqa: E402
import pasang_serangan  # noqa: E402


def jalankan(kasus, ws, cache):
    r = gerbang.cari(ws, kasus["user"], kasus["tanya"])
    cache[kasus["id"]] = r
    cek = kasus["cek"]
    ids = [h["id"] for h in r.get("hasil", [])]
    teks = " ".join(h["teks"] for h in r.get("hasil", [])).lower()
    masalah = []
    if "status" in cek and r["status"] != cek["status"]:
        masalah.append(f"status {r['status']}, harap {cek['status']}")
    for x in cek.get("ada", []):
        if not any(x in i for i in ids):
            masalah.append(f"'{x}' tidak ditemukan")
    for x in cek.get("tidak_ada", []):
        if any(x in i for i in ids):
            masalah.append(f"'{x}' MUNCUL padahal tidak boleh")
    if cek.get("kosong") and ids:
        masalah.append("hasil tidak kosong")
    if cek.get("peringatan") and not any("peringatan" in h for h in r.get("hasil", [])):
        masalah.append("tidak ada peringatan injeksi")
    if "teks_tidak_memuat" in cek and cek["teks_tidak_memuat"].lower() in teks:
        masalah.append(f"teks memuat '{cek['teks_tidak_memuat']}'")
    if "identik_dengan" in cek:
        lain = cache.get(cek["identik_dengan"])
        if lain is None or [h["id"] for h in lain.get("hasil", [])] != ids:
            masalah.append(f"hasil berbeda dari {cek['identik_dengan']}")
    return ids, masalah


def main():
    ws = Path(tempfile.mkdtemp()) / "ws"
    contoh_data.buat(ws)
    pasang_serangan.pasang(ws)
    data = json.loads((AKAR / "tests" / "cases.json").read_text(encoding="utf-8"))
    baris, cache, lulus = [], {}, 0
    for k in data["kasus"]:
        ids, masalah = jalankan(k, ws, cache)
        ok = not masalah
        lulus += ok
        baris.append((k, ok, masalah, ids))
    shutil.rmtree(ws.parent)

    total = len(baris)
    out = [f"# Hasil Uji - Pustaka Aman (Challenge A)", "",
           f"Dijalankan otomatis oleh `tests/run_cases.py` pada {date.today().isoformat()}. "
           f"**{lulus}/{total} lulus** di lapis kode. Kolom *Percakapan* hanya bisa dibuktikan di chat WorkBuddy; "
           f"bukti screenshot ada di folder `evidence/` dengan nama `TC-xx.png`.", "",
           "> Kasus di file ini adalah kasus buatan tim selama dataset resmi belum diterima. "
           "Ganti dengan 20 kasus resmi panitia begitu tersedia.", "",
           "| ID | Kategori | Pertanyaan (sebagai) | Harapan | Kode | Percakapan | Catatan |",
           "|---|---|---|---|---|---|---|"]
    for k, ok, masalah, ids in baris:
        perc = "perlu demo" if k.get("percakapan") else "-"
        catatan = "; ".join(masalah) if masalah else ""
        out.append(f"| {k['id']} | {k['kategori']} | {k['tanya']} ({k['user']}) | {k['harapan']} | "
                   f"{'LULUS' if ok else 'GAGAL'} | {perc} | {catatan} |")
    gagal = [(k, m) for k, ok, m, _ in baris if not ok]
    out += ["", "## Kegagalan yang dilaporkan terbuka", ""]
    if gagal:
        for k, m in gagal:
            out.append(f"- **{k['id']}** ({k['kategori']}): {k['harapan']}. Hasil: {'; '.join(m)}.")
    else:
        out.append("Tidak ada kegagalan di lapis kode pada run ini.")
    out += ["", "## Kasus yang perlu dibuktikan di percakapan", "",
            "Lihat `tests/chat_cases.md`. Untuk tiap kasus: screenshot jawaban agen, simpan ke `evidence/`."]
    (AKAR / "submission" / "03_test_results.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    for k, ok, masalah, _ in baris:
        print(f"{'LULUS' if ok else 'GAGAL'}  {k['id']}  {k['tanya'][:50]}" + (f"  -> {'; '.join(masalah)}" if masalah else ""))
    print(f"\n{lulus}/{total} lulus · ditulis ke submission/03_test_results.md")


if __name__ == "__main__":
    main()
