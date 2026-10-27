"""Ambil paket python3 + seluruh dependensinya dari mirror Alpine ke vm/repo/.

VM Bob tidak bisa menjangkau internet (NAT kampus memotong), tapi bisa menjangkau
laptop di subnet yang sama (192.168.59.1). Script ini dijalankan di laptop, hasilnya
dijadikan repo lokal yang di-serve oleh kemas-dan-serve.py di port 8000.

Pakai:  python scripts/vm/mirror-apk.py
"""
from __future__ import annotations

import os
import re
import tarfile
import urllib.request

VERSI = "v3.20"
ARsitektur = "x86_64"
CABANG = ["main", "community"]
ASAL = f"https://dl-cdn.alpinelinux.org/alpine/{VERSI}"
AKAR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TUJUAN = os.path.join(AKAR, "vm", "repo")


def unduh(url: str, tujuan: str) -> None:
    if os.path.exists(tujuan) and os.path.getsize(tujuan) > 0:
        return
    os.makedirs(os.path.dirname(tujuan), exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as r, open(tujuan + ".part", "wb") as f:
        while True:
            potongan = r.read(1 << 16)
            if not potongan:
                break
            f.write(potongan)
    os.replace(tujuan + ".part", tujuan)
    print(f"   {os.path.basename(tujuan)}  {os.path.getsize(tujuan) // 1024} KB")


def baca_indeks(cabang: str):
    """Kembalikan (paket: {nama, versi, deps, provides}) dan jalur berkasnya."""
    berkas = os.path.join(TUJUAN, cabang, ARsitektur, "APKINDEX.tar.gz")
    unduh(f"{ASAL}/{cabang}/{ARsitektur}/APKINDEX.tar.gz", berkas)
    paket = {}
    with tarfile.open(berkas, "r:gz") as tf:
        for anggota in tf.getmembers():
            if not anggota.name.endswith("APKINDEX"):
                continue
            teks = tf.extractfile(anggota).read().decode("utf-8", "replace")
            for blok in teks.split("\n\n"):
                field = {}
                for baris in blok.splitlines():
                    if len(baris) > 2:
                        field[baris[0]] = baris[2:]
                if "P" in field:
                    paket[field["P"]] = {
                        "nama": field["P"],
                        "versi": field.get("V", ""),
                        "deps": field.get("D", "").split(),
                        # CATATAN: di APKINDEX 'C:' = checksum paket, provides ada di 'p:'.
                        "provides": field.get("p", "").split(),
                        "cabang": cabang,
                    }
            break
    return paket


def cocok(dep: str, daftar_provides: dict, semua_paket: dict):
    """Terjemahkan satu string dependensi (mis. 'so:libssl.so.3', 'musl>=1.2') ke nama paket."""
    kandidat = dep
    for op in ("~=", ">=", "="):
        if op in dep:
            kandidat = dep.split(op)[0]
            break
    if "@" in kandidat:
        kandidat = kandidat.split("@")[0]
    if kandidat in semua_paket:
        return kandidat
    return daftar_provides.get(kandidat)


def tutup(nama_awal: str, semua_paket: dict) -> list[str]:
    daftar_provides = {}
    for p, info in semua_paket.items():
        for prov in info["provides"]:
            for op in ("~=", ">=", "="):
                if op in prov:
                    prov = prov.split(op)[0]
                    break
            daftar_provides.setdefault(prov, p)
    terambil, antrean = set(), [nama_awal]
    while antrean:
        n = antrean.pop()
        if n in terambil or n not in semua_paket:
            continue
        terambil.add(n)
        for dep in semua_paket[n]["deps"]:
            t = cocok(dep, daftar_provides, semua_paket)
            if t and t not in terambil:
                antrean.append(t)
    return sorted(terambil)


def utama() -> None:
    semua = {}
    for cabang in CABANG:
        print(f"== indeks {cabang} ==")
        semua.update(baca_indeks(cabang))
    print(f"   {len(semua)} paket terdaftar di indeks")

    perlu = tutup("python3", semua)
    print(f"== python3 butuh {len(perlu)} paket ==")
    total = 0
    for n in perlu:
        info = semua[n]
        berkas = f"{info['nama']}-{info['versi']}.apk"
        tujuan = os.path.join(TUJUAN, info["cabang"], ARsitektur, berkas)
        print(f"-> {n}")
        unduh(f"{ASAL}/{info['cabang']}/{ARsitektur}/{berkas}", tujuan)
        total += os.path.getsize(tujuan)
    print(f"== selesai: {total / 1e6:.1f} MB ada di vm/repo/ ==")


if __name__ == "__main__":
    utama()
