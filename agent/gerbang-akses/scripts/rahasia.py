#!/usr/bin/env python3
"""
rahasia.py - Hal-hal yang harus berada DI LUAR workspace agen:
kunci tanda tangan sesi dan PIN pengguna.

Lokasi default: ~/.pustaka-aman/  (ubah lewat variabel lingkungan PUSTAKA_AMAN_RAHASIA)
"""
import hashlib
import hmac
import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


class RahasiaError(Exception):
    pass


def folder_rahasia():
    return Path(os.environ.get("PUSTAKA_AMAN_RAHASIA", Path.home() / ".pustaka-aman"))


def kunci():
    f = folder_rahasia() / "kunci"
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(secrets.token_hex(32), encoding="utf-8")
        os.chmod(f, 0o600)
    return f.read_text(encoding="utf-8").strip().encode()


def tanda_tangan(pesan):
    return hmac.new(kunci(), pesan.encode(), hashlib.sha256).hexdigest()


def terminal_manusia():
    """True hanya di jendela terminal sungguhan (bukan pipe, bukan NUL di Windows)."""
    if not sys.stdin.isatty():
        return False
    if os.name == "nt":
        try:
            import ctypes
            import msvcrt
            mode = ctypes.c_uint32()
            return bool(ctypes.windll.kernel32.GetConsoleMode(
                msvcrt.get_osfhandle(sys.stdin.fileno()), ctypes.byref(mode)))
        except Exception:
            return False
    return True


# ------------------------------------------------------------------ PIN per pengguna

def _hash_pin(pin, garam):
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), garam, 200_000).hex()


def _muat_pin():
    f = folder_rahasia() / "pin.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def atur_pin(user_id, pin):
    if not (pin.isdigit() and 6 <= len(pin) <= 12):
        raise RahasiaError("PIN harus 6-12 digit angka.")
    data = _muat_pin()
    garam = secrets.token_bytes(16)
    data[user_id] = {"garam": garam.hex(), "hash": _hash_pin(pin, garam)}
    f = folder_rahasia() / "pin.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.chmod(f, 0o600)


def cek_pin(user_id, pin, batas_gagal=3, kunci_menit=15):
    f_gagal = folder_rahasia() / "pin_gagal.json"
    gagal = json.loads(f_gagal.read_text(encoding="utf-8")) if f_gagal.exists() else {}
    g = gagal.get(user_id, {"jumlah": 0, "sampai": ""})
    if g["sampai"] and datetime.fromisoformat(g["sampai"]) > datetime.now(timezone.utc):
        raise RahasiaError("Login dikunci sementara karena PIN salah berulang kali.")
    data = _muat_pin().get(user_id)
    if not data or not hmac.compare_digest(_hash_pin(pin, bytes.fromhex(data["garam"])), data["hash"]):
        g["jumlah"] += 1
        if g["jumlah"] >= batas_gagal:
            g = {"jumlah": 0, "sampai": (datetime.now(timezone.utc) + timedelta(minutes=kunci_menit)).isoformat()}
        gagal[user_id] = g
        f_gagal.write_text(json.dumps(gagal), encoding="utf-8")
        raise RahasiaError("ID atau PIN salah.")
    gagal.pop(user_id, None)
    f_gagal.write_text(json.dumps(gagal), encoding="utf-8")


# ------------------------------------------------------------------ sesi bertanda tangan

def buat_sesi(user_id, menit=30):
    sekarang = datetime.now(timezone.utc)
    sesi = {"user_id": user_id, "mulai": sekarang.isoformat(timespec="seconds"),
            "berakhir": (sekarang + timedelta(minutes=menit)).isoformat(timespec="seconds")}
    sesi["tanda_tangan"] = tanda_tangan(f"{sesi['user_id']}|{sesi['mulai']}|{sesi['berakhir']}")
    return sesi


def periksa_sesi(sesi):
    """Kembalikan user_id bila sesi sah dan belum kedaluwarsa, selain itu (None, alasan)."""
    try:
        pesan = f"{sesi['user_id']}|{sesi['mulai']}|{sesi['berakhir']}"
        if not hmac.compare_digest(sesi.get("tanda_tangan", ""), tanda_tangan(pesan)):
            return None, "tanda tangan sesi tidak sah"
        if datetime.fromisoformat(sesi["berakhir"]) < datetime.now(timezone.utc):
            return None, "sesi kedaluwarsa"
        return sesi["user_id"], ""
    except (KeyError, TypeError, ValueError):
        return None, "format sesi rusak"
