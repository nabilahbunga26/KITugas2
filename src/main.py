"""Titik masuk semua peran: python -m src.main --role alice  (lihat menu interaktifnya)."""

import argparse
import sys
import time
from pathlib import Path

AKAR = Path(__file__).resolve().parents[1]
if str(AKAR) not in sys.path:
    sys.path.insert(0, str(AKAR))

from src.ksilib.aes import core  # noqa: E402
from src.ksilib.kdc.node import Node  # noqa: E402
from src.ksilib.kdc.server import KDC  # noqa: E402
from src.ksilib.net import link  # noqa: E402
from src.ksilib.utils import config as cfgio  # noqa: E402
from src.ksilib.utils import log  # noqa: E402

BANTUAN = """
perintah:
  d  jalankan skenario distribusi key (langkah 1-5)
  k  kirim pesan AES ke pasangan
  r  tampilkan pesan yang sudah masuk
  g  ganti key AES (tanpa restart program)
  u  uji encrypt/decrypt lokal
  s  status (IP, port, key, auth)
  q  keluar
"""

MENU_KDC = """
perintah KDC:
  s  daftar klien + master key yang dikenal
  q  keluar
"""


def bangun_argumen():
    p = argparse.ArgumentParser(description="KDC + AES manual (Keamanan Informasi)")
    p.add_argument("--role", required=True, choices=["kdc", "alice", "bob"])
    p.add_argument("--config", default=None, help="default: config/hosts/<role>.env")
    p.add_argument("--kdc", dest="kdc_addr", default=None, help="IP:PORT KDC, menimpa config")
    p.add_argument("--port", type=int, default=None, help="port chat lokal, menimpa config")
    p.add_argument("--peer", default=None, help="nama pasangan (default dari config PEER_NAME)")
    p.add_argument("--advertise-ip", dest="advertise_ip", default=None,
                   help="IP yang didaftarkan ke KDC; pakai alamat yang bisa dijangkau pasangan")
    p.add_argument("--auto", choices=["init", "recv"], default=None,
                   help="jalankan skenario otomatis lalu keluar (buat uji end-to-end)")
    return p.parse_args()


def jalan_kdc(args):
    cfg = cfgio.load(args.config, "kdc")
    log.setup("KDC", cfg.get("LOG_FILE", ""))
    srv = KDC(cfg).jalankan()
    if not sys.stdin or not sys.stdin.isatty():
        # Dijalankan tanpa terminal (uji otomatis / latar belakang): layani terus.
        while True:
            time.sleep(1)
    print(MENU_KDC)
    while True:
        try:
            perintah = input("kdc> ").strip().lower()
        except EOFError:
            # stdin tertutup (jalan di latar belakang): server tidak boleh mati karena ini.
            log.log("stdin tertutup -- KDC tetap melayani. Ctrl+C untuk berhenti.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            break
        if perintah == "s":
            for nama, (ip, port) in srv.daftar.items():
                print(f"  klien {nama}: {ip} chat:{port}")
            print(f"  master key dikenal: {', '.join(srv.master) or '(kosong)'}")
        elif perintah == "q":
            break
        elif perintah:
            print("  perintah: s atau q")
    srv.stop()


def bangun_node(args) -> Node:
    cfg = cfgio.load(args.config, args.role)
    if args.kdc_addr:
        ip, _, port = args.kdc_addr.partition(":")
        cfg["KDC_IP"], cfg["KDC_PORT"] = ip, port or "4444"
    if args.port:
        cfg["CHAT_PORT"] = str(args.port)
    if args.advertise_ip:
        cfg["ADVERTISE_IP"] = args.advertise_ip
    for kunci in ("MASTER_KEY", "CHAT_PORT", "KDC_IP"):
        cfgio.need(cfg, kunci, "di config/hosts/" + args.role + ".env")
    log.setup(args.role.upper(), cfg.get("LOG_FILE", ""))
    node = Node(args.role.upper(), cfg)
    node.dengar.start()
    node.cfg = cfg
    return node


def auto_mode(node: Node, mode: str, pasangan: str):
    if mode == "init":
        node.mulai_sebagai_pengaju(pasangan)
        node.kirim(f"UJI-DARI-{node.nama}")
        pesan = node._tunggu("MSG", 60)
        log.log(f"[AUTO] balasan masuk dari pasangan: {pesan!r}")
    else:
        node.mulai_sebagai_penerima()
        pesan = node._tunggu("MSG", 60)
        log.log(f"[AUTO] pesan masuk: {pesan!r} -> balas")
        node.kirim(f"TERIMA-OLEH-{node.nama}")


def interaktif(node: Node, pasangan: str):
    log.banner(f"{node.nama} siap | {node.status()}")
    print(BANTUAN)
    while True:
        try:
            masuk = input(f"{node.nama.lower()}> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        perintah, _, sisa = masuk.partition(" ")
        perintah = perintah.lower()
        try:
            if perintah == "d":
                if node.nama == "ALICE":
                    node.mulai_sebagai_pengaju(sisa.strip() or pasangan)
                else:
                    node.mulai_sebagai_penerima()
            elif perintah == "k":
                if not sisa.strip():
                    print("  pakai: k <teks ASCII>")
                else:
                    node.kirim(sisa.strip())
            elif perintah == "r":
                if not node.inbox:
                    print("  (belum ada pesan masuk)")
                for ip, teks in node.inbox:
                    print(f"  dari {ip}: {teks}")
            elif perintah == "g":
                baru = sisa.strip() or input("  key ASCII baru (16/24/32 char): ").strip()
                node.ganti_key(baru)
            elif perintah == "u":
                key = input("  key ASCII: ").strip()
                teks = input("  plaintext ASCII: ").strip()
                heks = core.encrypt_hex(key, teks)
                print(f"  ciphertext (heks) : {heks}")
                print(f"  kembali (ASCII)   : {core.decrypt_hex(key, heks)!r}")
            elif perintah == "s":
                print(" ", node.status())
                print("  inbox:", len(node.inbox), "pesan | auth:", node.auth_ok)
            elif perintah in ("q", "quit", "exit"):
                break
            elif perintah:
                print(BANTUAN)
        except (ValueError, OSError, RuntimeError, TimeoutError) as exc:
            print(f"  GAGAL: {exc}")
        time.sleep(0)
    node.dengar.stop()


def main():
    args = bangun_argumen()
    if args.role == "kdc":
        jalan_kdc(args)
        return
    node = bangun_node(args)
    pasangan = args.peer or node.cfg.get("PEER_NAME", "BOB" if node.nama == "ALICE" else "ALICE")
    if args.auto:
        auto_mode(node, args.auto, pasangan)
        node.dengar.stop()
        return
    interaktif(node, pasangan)


if __name__ == "__main__":
    main()
