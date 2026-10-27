"""Muat konfigurasi per perangkat. Key & alamat TIDAK ada di dalam kode sumber."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def default_path(role: str) -> Path:
    return PROJECT_ROOT / "config" / "hosts" / f"{role.lower()}.env"


def load(path=None, role=None) -> dict:
    """Baca file `KUNCI=nilai`; kalau ada --config pakai itu, kalau tidak pakai config/hosts/<role>.env."""
    if path is None:
        path = default_path(role)
    path = Path(path)
    if not path.exists():
        contoh = str(path).replace(path.name, path.name + ".example")
        raise SystemExit(
            f"[CONFIG] file tidak ada: {path}\n"
            f"          salin dari contoh lalu isi:  cp {contoh} {path}"
        )
    cfg = {}
    for baris in path.read_text(encoding="utf-8").splitlines():
        baris = baris.strip()
        if not baris or baris.startswith("#") or "=" not in baris:
            continue
        k, v = baris.split("=", 1)
        v = v.split("#", 1)[0].strip().strip("'\"")
        cfg[k.strip().upper()] = v
    for k, v in os.environ.items():
        if k.startswith("KSI_"):
            cfg[k[4:]] = v
    return cfg


def need(cfg: dict, key: str, hints: str = "") -> str:
    nilai = cfg.get(key, "").strip()
    if not nilai:
        raise SystemExit(f"[CONFIG] {key} belum diisi di config.{(' ' + hints) if hints else ''}")
    return nilai
