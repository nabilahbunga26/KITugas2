"""Gladi PROTOKOL: KDC di WSL Ubuntu + Alice & Bob di Windows, dijalankan sekali klik.

PENTING: ini latihan alur langkah 1-5 + chat + ganti key, BUKAN bukti topologi 3 IP.
Di gladi ini Alice dan Bob sengaja memakai alamat daftar 127.0.0.1 supaya gladi bisa
jalan di satu laptop. Demo yang dinilai tetap butuh Bob di perangkat ketiga
(lihat QUICKSTART bagian "Perangkat ketiga").

Jalankan: python scripts/demo/rehearse.py
"""

import subprocess
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parents[2]
CAPTURE = AKAR / "captures"
PYTHON = sys.executable

# Alamat KDC versi nyata (WSL) supaya gladi tidak bergantung pada isi bob.env.
KDC_ASAL = "172.20.93.6:4444"
# Dalam gladi, kedua node berada di laptop yang sama -> alamat yang diumumkan loopback.
ALAMAT_GLADI = "127.0.0.1"


def ke_wsl(path: Path) -> str:
    teks = str(path).replace("\\", "/")
    return "/mnt/" + teks[0].lower() + teks[2:]


def ip_wsl():
    """IP WSL bisa berubah tiap boot, jadi ditanya langsung ke Ubuntu-nya."""
    try:
        keluar = subprocess.run(
            ["wsl.exe", "-d", "Ubuntu", "-e", "bash", "-lc",
             "ip -4 -o addr show scope global | awk '{print $4}' | cut -d/ -f1"],
            capture_output=True, text=True, timeout=25,
        ).stdout.replace("\r", "").split()
        return next((a for a in keluar if a.startswith("172.")), KDC_ASAL)
    except Exception:
        return KDC_ASAL


def bersih():
    CAPTURE.mkdir(exist_ok=True)
    for f in CAPTURE.glob("*.log"):
        f.unlink()


def mulai_kdc_wsl():
    wsl_dir = ke_wsl(AKAR)
    cmd = (
        f"cd {wsl_dir} && python3 -m src.main --role kdc"
    )
    return subprocess.Popen(
        ["wsl.exe", "-d", "Ubuntu", "-e", "bash", "-lc", cmd],
        cwd=AKAR, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )


def mulai_node(peran: str, kdc_addr: str, port=None):
    cmd = [PYTHON, "-m", "src.main", "--role", peran,
           "--kdc", kdc_addr, "--advertise-ip", ALAMAT_GLADI]
    if port:
        cmd += ["--port", str(port)]
    fh = open(CAPTURE / f"{peran}-console.log", "w", encoding="utf-8")
    return subprocess.Popen(cmd, cwd=AKAR, stdin=subprocess.PIPE, stdout=fh,
                            stderr=subprocess.STDOUT, text=True), fh


def ketik(node, teks, jeda=1.2):
    node.stdin.write(teks + "\n")
    node.stdin.flush()
    time.sleep(jeda)


def baca(nama):
    bagian = []
    for f in (CAPTURE / f"{nama}.log", CAPTURE / f"{nama}-console.log"):
        if f.exists():
            bagian.append(f.read_text(encoding="utf-8", errors="replace").strip())
    return "\n".join(bagian)


def tampilkan(judul, isi, lebar=100):
    print("\n" + "=" * lebar)
    print(judul)
    print("=" * lebar)
    print(isi.strip() or "(kosong)")


def utama():
    bersih()
    kdc_addr = ip_wsl() + ":4444"
    print(f"[GLADI] KDC akan dicari di {kdc_addr} (IP WSL dicek otomatis).")
    print("[GLADI] 1/5 menjalankan KDC di WSL Ubuntu ...")
    kdc = mulai_kdc_wsl()
    time.sleep(6)
    if kdc.poll() is not None:
        print("[GLADI] GAGAL: KDC di WSL langsung mati. Cek python3 di WSL.")
        return 1

    print("[GLADI] 2/5 menjalankan Bob (port 5556) ...")
    bob, fh_bob = mulai_node("bob", kdc_addr, 5556)
    ketik(bob, "d")  # Bob: menunggu tiket (jadi RECEIVER, langkah 3-4-5)

    print("[GLADI] 3/5 menjalankan Alice -> skenario distribusi key 1-5 ...")
    ali, fh_ali = mulai_node("alice", kdc_addr)
    ketik(ali, "d", 3)  # Alice: pengaju langkah 1-2-3, lalu jawab challenge 4-5

    print("[GLADI] 4/5 chat dua arah + ganti key tanpa restart ...")
    ketik(ali, "k halo bob ini alice")
    ketik(bob, "k halo balik alice", 0.6)
    ketik(ali, "g KunciGantiDemo26")   # key ASCII 16 char, ganti tanpa restart (no.5)
    ketik(bob, "g KunciGantiDemo26", 0.6)
    ketik(ali, "k pesan setelah ganti key")
    ketik(bob, "s")
    ketik(ali, "s")

    print("[GLADI] 5/5 merapikan proses ...")
    ketik(ali, "q", 0.4)
    ketik(bob, "q", 0.4)
    for node, fh in ((ali, fh_ali), (bob, fh_bob)):
        try:
            node.wait(timeout=8)
        except subprocess.TimeoutExpired:
            node.kill()
        fh.close()
    kdc.terminate()
    try:
        kdc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        kdc.kill()

    tampilkan("KDC (WSL Ubuntu)", baca("kdc"))
    tampilkan("ALICE (Windows)", baca("alice"))
    tampilkan("BOB (Windows, port 5556)", baca("bob"))
    print("\nLog tersimpan di:", CAPTURE)
    return 0


if __name__ == "__main__":
    raise SystemExit(utama())
