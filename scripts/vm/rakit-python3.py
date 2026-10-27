"""Gabungkan semua paket Alpine di vm/repo jadi satu tarball: vm/alpine-python3.tgz

VM Bob tinggal `wget` lalu `tar -xzf ... -C /`. Tidak pakai apk, tidak butuh internet.

Pakai:  python scripts/vm/mirror-apk.py   # unduh paketnya
        python scripts/vm/rakit-python3.py  # bungkus jadi satu tarball
"""
import os
import tarfile

AKAR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = os.path.join(AKAR, "vm", "repo")
TUJUAN = os.path.join(AKAR, "vm", "alpine-python3.tgz")
# musl = libc yang lagi dipakai hidup-hidup oleh ISO live; menimpanya bisa merusak sistem.
CORET = ("musl-", "busybox-")


def daftar_apk():
    hasil = []
    for cabang in sorted(os.listdir(REPO)):
        arsitektur = os.path.join(REPO, cabang, "x86_64")
        if not os.path.isdir(arsitektur):
            continue
        for f in sorted(os.listdir(arsitektur)):
            if f.endswith(".apk") and not f.startswith(CORET):
                hasil.append(os.path.join(arsitektur, f))
    return hasil


def utama() -> None:
    berkas = daftar_apk()
    if not berkas:
        raise SystemExit("vm/repo kosong -> jalankan dulu: python scripts/vm/mirror-apk.py")
    jumlah = 0
    with tarfile.open(TUJUAN, "w:gz", format=tarfile.GNU_FORMAT) as keluar:
        for apk in berkas:
            with tarfile.open(apk, "r:gz") as in_apk:
                for anggota in in_apk.getmembers():
                    if anggota.name.startswith((".SIGN", ".PKGINFO")):
                        continue
                    # busybox tar di VM bisa bingung dengan header PAX khas apk-tools.
                    anggota.pax_headers = {}
                    if anggota.isfile():
                        keluar.addfile(anggota, in_apk.extractfile(anggota))
                    else:
                        keluar.addfile(anggota)
                    jumlah += 1
            print(f"   + {os.path.basename(apk)}")
    mb = os.path.getsize(TUJUAN) / 1e6
    print(f"== {jumlah} berkas dari {len(berkas)} paket -> {mb:.1f} MB ==")
    print(f"URL VM: http://192.168.59.1:8000/{os.path.basename(TUJUAN)}")


if __name__ == "__main__":
    utama()
