"""Log seragam: ada waktu, nama peran, dan bisa ditulis ke file buat laporan."""

import sys
import time
from datetime import datetime

_lock = None


def setup(nama_peran: str, file_log: str = ""):
    global _lock
    import threading

    _lock = threading.Lock()
    setup.nama = nama_peran
    if file_log:
        from pathlib import Path

        Path(file_log).parent.mkdir(parents=True, exist_ok=True)
        setup.fh = open(file_log, "a", encoding="utf-8")
    else:
        setup.fh = None


def log(teks: str):
    nama = getattr(setup, "nama", "?")
    stempel = datetime.now().strftime("%H:%M:%S")
    baris = f"[{stempel}][{nama}] {teks}"
    if _lock is not None:
        with _lock:
            print(baris, flush=True)
            fh = getattr(setup, "fh", None)
            if fh:
                fh.write(baris + "\n")
                fh.flush()
    else:
        print(baris, flush=True)


def banner(judul: str):
    log("=" * 62)
    log(judul)
    log("=" * 62)


def deadline(detik: float, fungsi, *a):
    """Jalankan fungsi sampai mengembalikan nilai benar, atau None kalau habis waktu."""
    batas = time.time() + detik
    while time.time() < batas:
        hasil = fungsi(*a)
        if hasil:
            return hasil
        time.sleep(0.05)
    return None
