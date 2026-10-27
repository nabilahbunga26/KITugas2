"""Kemas proyek jadi vm/proyek.zip lalu sajikan lewat HTTP supaya VM Bob bisa mengunduh.

Jalankan di PowerShell/CMD biasa (TANPA admin), biarkan terbuka selama VM Bob mengunggah:
    python scripts/vm/kemas-dan-serve.py
"""

import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

AKAR = Path(__file__).resolve().parents[2]
TUJUAN = AKAR / "vm" / "proyek.zip"
ADA = ["src", "config", "tests", "README.md"]
SKIP_FOLDER = {"__pycache__", ".pytest_cache"}


def buat_zip():
    with zipfile.ZipFile(TUJUAN, "w", zipfile.ZIP_DEFLATED) as z:
        for nama in ADA:
            p = AKAR / nama
            if p.is_file():
                z.write(p, nama)
            for f in sorted(p.rglob("*")):
                if not f.is_file() or any(s in SKIP_FOLDER for s in f.parts):
                    continue
                z.write(f, f.relative_to(AKAR).as_posix())
    return TUJUAN.stat().st_size // 1024


def serve(port=8000):
    kb = buat_zip()
    print(f"[SERVER] vm/proyek.zip siap ({kb} KB).")
    print(f"[SERVER] VM Bob ambil lewat: http://192.168.59.1:{port}/proyek.zip")
    print("[SERVER] Ctrl+C untuk berhenti. Jangan di-close sebelum VM selesai wget.")
    import os
    os.chdir(AKAR / "vm")
    ThreadingHTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler).serve_forever()


if __name__ == "__main__":
    serve()
