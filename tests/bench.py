#!/usr/bin/env python3
"""
bench.py - Mengukur kecepatan gerbang akses pada beberapa ukuran data.

  python bench.py              (ukuran kecil dan sedang)
  python bench.py --besar      (tambah ukuran besar)

Yang diukur:
  ingest        membangun indeks dari nol
  cari          satu pencarian (median dan p95)
  validasi      satu validasi jawaban (median dan p95)
  cli           satu panggilan lewat terminal, seperti yang dilakukan WorkBuddy
                (termasuk waktu menyalakan Python)
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent" / "gerbang-akses" / "scripts"))
os.environ.setdefault("PUSTAKA_AMAN_RAHASIA", str(Path(__file__).resolve().parents[1] / "state" / ".rahasia_uji"))
import argparse
import json
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import contoh_data
import gerbang

KATA = ("cuti tunjangan bensin lembur gudang makassar kapal stok vendor laporan "
        "proyek klaim reimbursement jadwal shift karyawan divisi operasional").split()


def buat_data_besar(ws, n_dok, n_chat):
    contoh_data.buat(ws)
    dok = ws / "data" / "dokumen"
    izin = ws / "data" / "izin.csv"
    baris_izin = []
    rnd = random.Random(1)
    for i in range(n_dok):
        paragraf = ["# Dokumen " + str(i), "Berlaku sejak: 2026-01-01"]
        paragraf += [" ".join(rnd.choices(KATA, k=40)) for _ in range(5)]
        (dok / f"dok_{i}.md").write_text("\n\n".join(paragraf), encoding="utf-8")
        level = rnd.choice(["internal", "internal", "terbatas", "rahasia"])
        baris_izin.append(f"dok_{i},dokumen,{level},Operasional,,U003,\n")
    with izin.open("a", encoding="utf-8") as f:
        f.writelines(baris_izin)
    chat = json.loads((ws / "data" / "chat.json").read_text(encoding="utf-8"))
    for i in range(n_chat):
        chat.append({"id": f"X{i}", "grup": "grup_umum", "pengirim": "Staf", "tanggal": "2026-10-01",
                     "teks": " ".join(rnd.choices(KATA, k=15))})
    (ws / "data" / "chat.json").write_text(json.dumps(chat), encoding="utf-8")


def ukur(fungsi, ulang):
    waktu = []
    for _ in range(ulang):
        t = time.perf_counter()
        fungsi()
        waktu.append((time.perf_counter() - t) * 1000)
    waktu.sort()
    return statistics.median(waktu), waktu[int(len(waktu) * 0.95) - 1]


def satu_ukuran(n_dok, n_chat):
    ws = Path(tempfile.mkdtemp()) / "ws"
    buat_data_besar(ws, n_dok, n_chat)

    t = time.perf_counter()
    info = gerbang.ingest(ws)
    t_ingest = time.perf_counter() - t

    pertanyaan = ["berapa tunjangan bensin", "jadwal kapal makassar", "klaim reimbursement lembur",
                  "stok gudang vendor", "proyek divisi operasional"]
    i = iter(range(10**6))
    cari_med, cari_p95 = ukur(lambda: gerbang.cari(ws, "U001", pertanyaan[next(i) % 5]), 50)
    val_med, val_p95 = ukur(lambda: gerbang.validasi(
        ws, "U001", "Tunjangan bensin saat ini Rp750.000.", ["CHAT:grup_hr_pengumuman#M001"]), 50)

    skrip = Path(__file__).with_name("gerbang.py")
    cli_med, _ = ukur(lambda: subprocess.run(
        [sys.executable, str(skrip), "cari", "--ws", str(ws), "--user", "U001", "--q", "tunjangan bensin"],
        capture_output=True, check=True), 10)

    # Izin berubah (akses dicabut) -> hanya tabel izin dimuat ulang
    izin = ws / "data" / "izin.csv"
    izin.write_text(izin.read_text(encoding="utf-8").replace(",U003,", ",,"), encoding="utf-8")
    t = time.perf_counter()
    gerbang.cari(ws, "U001", "tunjangan bensin")
    t_izin = (time.perf_counter() - t) * 1000

    # Satu dokumen berubah -> pertanyaan berikutnya memicu ingest ulang penuh
    (ws / "data" / "dokumen" / "dok_0.md").write_text("# Dokumen 0\n\nisi baru", encoding="utf-8")
    t = time.perf_counter()
    gerbang.cari(ws, "U001", "tunjangan bensin")
    t_berubah = (time.perf_counter() - t) * 1000

    shutil.rmtree(ws.parent)
    return {"dokumen": n_dok, "chat": n_chat, "potongan": info["potongan_diindeks"],
            "ingest_s": t_ingest, "cari": (cari_med, cari_p95), "validasi": (val_med, val_p95),
            "cli_ms": cli_med, "izin_berubah_ms": t_izin, "setelah_berubah_ms": t_berubah}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--besar", action="store_true")
    ukuran = [(50, 500), (500, 5000)] + ([(3000, 30000)] if ap.parse_args().besar else [])
    print(f"{'potongan':>9} | {'ingest':>8} | {'cari med/p95':>15} | {'validasi med/p95':>17} | "
          f"{'1x CLI':>8} | {'izin berubah':>12} | {'dokumen berubah':>15}")
    for n_dok, n_chat in ukuran:
        r = satu_ukuran(n_dok, n_chat)
        print(f"{r['potongan']:>9} | {r['ingest_s']:>6.2f} s | "
              f"{r['cari'][0]:>6.1f}/{r['cari'][1]:>5.1f} ms | "
              f"{r['validasi'][0]:>7.1f}/{r['validasi'][1]:>5.1f} ms | "
              f"{r['cli_ms']:>5.0f} ms | {r['izin_berubah_ms']:>9.0f} ms | {r['setelah_berubah_ms']:>12.0f} ms")


if __name__ == "__main__":
    main()
