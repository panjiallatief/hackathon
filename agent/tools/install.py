#!/usr/bin/env python3
"""
install.py - Memasang skill dari agent/ ke tempat yang dibaca WorkBuddy.

WorkBuddy membaca skill proyek dari <workspace>/.workbuddy-ai/skills/<nama>/.
agent/ adalah satu-satunya sumber kebenaran; salinan di .workbuddy-ai/ jangan diedit.

  python agent/tools/install.py            pasang / perbarui
  python agent/tools/install.py --check    cek apakah salinan masih sama dengan sumber
  python agent/tools/install.py --hapus    cabut
"""
import argparse
import hashlib
import shutil
from pathlib import Path

AKAR = Path(__file__).resolve().parents[2]
SUMBER = AKAR / "agent"
TUJUAN = AKAR / ".workbuddy-ai" / "skills"
SKILL = ["gerbang-akses"]


def _sidik(folder):
    h = hashlib.sha256()
    for f in sorted(folder.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            h.update(str(f.relative_to(folder)).encode())
            h.update(f.read_bytes())
    return h.hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--hapus", action="store_true")
    a = ap.parse_args()
    for nama in SKILL:
        src, dst = SUMBER / nama, TUJUAN / nama
        if a.hapus:
            shutil.rmtree(dst, ignore_errors=True)
            print(f"{nama}: dicabut")
        elif a.check:
            if not dst.exists():
                print(f"{nama}: BELUM TERPASANG")
            else:
                print(f"{nama}: {'ok' if _sidik(src) == _sidik(dst) else 'BASI, jalankan install.py lagi'}")
        else:
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
            print(f"{nama}: terpasang di {dst}")


if __name__ == "__main__":
    main()
