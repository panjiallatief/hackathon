#!/usr/bin/env python3
"""
sesi.py - Login KHUSUS MANUSIA untuk Pustaka Aman.

Dijalankan di jendela terminal biasa (bukan lewat WorkBuddy):
  python agent/tools/sesi.py atur-pin          buat PIN untuk pengguna (sekali)
  python agent/tools/sesi.py login             masuk sebagai pengguna (ID + PIN)
  python agent/tools/sesi.py status            lihat sesi aktif
  python agent/tools/sesi.py logout            keluar

Hasilnya: state/sesi.json yang ditandatangani dengan kunci di ~/.pustaka-aman/.
Agen bisa membaca file itu, tetapi tidak bisa membuat atau mengubahnya,
karena tanda tangannya akan tidak cocok. Setiap percobaan dicatat di log.
"""
import argparse
import csv
import getpass
import json
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AKAR / "agent" / "gerbang-akses" / "scripts"))

import gerbang  # noqa: E402
import rahasia  # noqa: E402


def _wajib_terminal():
    if not rahasia.terminal_manusia():
        print(json.dumps({"status": "error", "pesan": "Hanya bisa dijalankan manusia di terminal interaktif."}))
        sys.exit(1)


def _pengguna(p):
    with (p["sumber"] / "users.csv").open(encoding="utf-8-sig") as f:
        return {r["user_id"]: r for r in csv.DictReader(f)}


def login(ws, menit):
    _wajib_terminal()
    p = gerbang.jalur(ws)
    pengguna = _pengguna(p)
    try:
        uid = input("ID karyawan: ").strip().upper()
        pin = getpass.getpass("PIN (tidak terlihat saat diketik): ")
    except EOFError:
        print("Dibatalkan."); return
    try:
        if uid not in pengguna or pengguna[uid]["status"] != "aktif":
            raise rahasia.RahasiaError("ID atau PIN salah.")
        rahasia.cek_pin(uid, pin)
    except rahasia.RahasiaError as e:
        gerbang.catat_log(p, {"aksi": "login", "user": uid, "hasil": f"ditolak: {e}"})
        print(f"DITOLAK. {e}")
        sys.exit(1)
    sesi = rahasia.buat_sesi(uid, menit)
    p["sesi"].parent.mkdir(parents=True, exist_ok=True)
    p["sesi"].write_text(json.dumps(sesi, indent=2), encoding="utf-8")
    gerbang.catat_log(p, {"aksi": "login", "user": uid, "hasil": "sesi dibuat", "berakhir": sesi["berakhir"]})
    o = pengguna[uid]
    print(f"Sesi aktif: {o['nama']} ({o['peran']}, {o['divisi']}) sampai {sesi['berakhir']} UTC")


def logout(ws):
    p = gerbang.jalur(ws)
    uid, _ = gerbang.sesi_aktif(p)
    if p["sesi"].exists():
        p["sesi"].unlink()
    gerbang.catat_log(p, {"aksi": "logout", "user": uid, "hasil": "sesi dihapus"})
    print("Sesi dihapus.")


def status(ws):
    p = gerbang.jalur(ws)
    uid, alasan = gerbang.sesi_aktif(p)
    if uid is None:
        print(f"Tidak ada sesi aktif ({alasan}).")
        return
    o = _pengguna(p).get(uid, {})
    print(f"Sesi aktif: {o.get('nama', uid)} ({o.get('peran', '?')}, {o.get('divisi', '?')})")


def atur_pin(ws):
    _wajib_terminal()
    p = gerbang.jalur(ws)
    pengguna = _pengguna(p)
    try:
        uid = input("ID karyawan yang diatur PIN-nya (atau 'semua' untuk PIN demo): ").strip()
        if uid.lower() == "semua":
            pin = getpass.getpass("PIN demo untuk SEMUA pengguna contoh (6-12 digit): ")
            for u in pengguna:
                rahasia.atur_pin(u, pin)
            print(f"PIN demo dipasang untuk {len(pengguna)} pengguna. Jangan pakai cara ini untuk data asli.")
            return
        uid = uid.upper()
        if uid not in pengguna:
            print("ID tidak dikenal."); sys.exit(1)
        pin = getpass.getpass("PIN baru (6-12 digit): ")
        if pin != getpass.getpass("Ulangi PIN: "):
            print("PIN tidak sama."); sys.exit(1)
        rahasia.atur_pin(uid, pin)
        print(f"PIN untuk {uid} tersimpan.")
    except (EOFError, rahasia.RahasiaError) as e:
        print(f"Gagal: {e}"); sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("perintah", choices=["login", "logout", "status", "atur-pin"])
    ap.add_argument("--ws", default=str(AKAR))
    ap.add_argument("--menit", type=int, default=30, help="masa berlaku sesi")
    a = ap.parse_args()
    {"login": lambda: login(a.ws, a.menit), "logout": lambda: logout(a.ws),
     "status": lambda: status(a.ws), "atur-pin": lambda: atur_pin(a.ws)}[a.perintah]()


if __name__ == "__main__":
    main()
