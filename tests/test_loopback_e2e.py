"""Uji end-to-end: 3 proses (KDC, Alice, Bob) di 127.0.0.1, 3 port berbeda.

Membuktikan langkah 1-5 + chat dua arah jalan sebelum dites di 3 perangkat nyata.
Untuk demo tetap wajib 3 IP berbeda (ketentuan no.2 & no.3) -- loopback hanya uji otomatis.
Jalankan: python tests/test_loopback_e2e.py  atau  python -m pytest tests/test_loopback_e2e.py
"""

import re
import subprocess
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parents[1]
DATA = AKAR / "tests" / "data"

ENV = {
    "kdc": "KDC_PORT=4444\nMASTER_KEY_ALICE=KasMasterKeyAAAA\n"
           "MASTER_KEY_BOB=KbsMasterKeyBBBB\nSESSION_KEY_LEN=16\n",
    "alice": "NAME=ALICE\nCHAT_PORT=5555\nKDC_IP=127.0.0.1\nKDC_PORT=4444\n"
             "PEER_NAME=BOB\nMASTER_KEY=KasMasterKeyAAAA\n",
    "bob": "NAME=BOB\nCHAT_PORT=5556\nKDC_IP=127.0.0.1\nKDC_PORT=4444\n"
           "PEER_NAME=ALICE\nMASTER_KEY=KbsMasterKeyBBBB\n",
}


def tulis_env():
    DATA.mkdir(exist_ok=True)
    for peran, isi in ENV.items():
        (DATA / f"auto-{peran}.env").write_text(isi, encoding="utf-8")
    return {peran: str(DATA / f"auto-{peran}.env") for peran in ENV}


def jalankan_end_to_end():
    cfg = tulis_env()
    base = [sys.executable, "-m", "src.main"]
    log_kdc = DATA / "kdc-out.txt"
    with open(log_kdc, "w", encoding="utf-8") as fh_kdc:
        kdc = subprocess.Popen(
            [*base, "--role", "kdc", "--config", cfg["kdc"]],
            cwd=AKAR, stdout=fh_kdc, stderr=subprocess.STDOUT,
        )
        try:
            time.sleep(1.5)
            bob = subprocess.Popen(
                [*base, "--role", "bob", "--auto", "recv", "--config", cfg["bob"]],
                cwd=AKAR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            alice = subprocess.run(
                [*base, "--role", "alice", "--auto", "init", "--config", cfg["alice"]],
                cwd=AKAR, capture_output=True, text=True, timeout=90,
            )
            keluar_bob = bob.communicate(timeout=90)[0]
        finally:
            kdc.terminate()
            kdc.wait(timeout=10)
    return alice.stdout, keluar_bob, log_kdc.read_text(encoding="utf-8")


def test_langkah_1_5_dan_chat_dua_arah():
    keluar_alice, keluar_bob, keluar_kdc = jalankan_end_to_end()
    gabung = "\n".join((keluar_alice, keluar_bob, keluar_kdc))
    for n in range(1, 6):
        assert f"[LANGKAH {n}]" in gabung, f"langkah {n} tidak muncul:\n{gabung[-1500:]}"
    kunci = re.findall(r"dapat session key '([^']+)'", gabung)
    assert kunci and set(kunci) == {kunci[0]}, f"key tidak sama di kedua sisi: {kunci}"
    assert "UJI-DARI-ALICE" in keluar_bob, "Bob tidak menerima pesan Alice"
    assert "TERIMA-OLEH-BOB" in keluar_alice, "Alice tidak menerima balasan Bob"


if __name__ == "__main__":
    a, b, k = jalankan_end_to_end()
    print(a)
    print("-" * 28 + " BOB " + "-" * 28)
    print(b)
    print("-" * 28 + " KDC " + "-" * 28)
    print(k)
    kunci = set(re.findall(r"dapat session key '([^']+)'", a + b + k))
    print(f"\nkey sama di kedua sisi: {kunci}")
    assert len(kunci) == 1 and "TERIMA-OLEH-BOB" in a and "UJI-DARI-ALICE" in b, "UJI GAGAL"
    print("LULUS end-to-end: langkah 1-5 + chat dua arah")
