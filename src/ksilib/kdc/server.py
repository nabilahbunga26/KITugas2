"""KDC: satu-satunya pihak yang punya master key semua klien dan membangkitkan session key."""

import socket
import time

from ..aes import core
from ..net import link
from ..utils import log
from . import protocol as P


class KDC:
    def __init__(self, cfg: dict):
        self.nama = "KDC"
        self.port = int(cfg.get("KDC_PORT", "4444"))
        self.panjang_key = int(cfg.get("SESSION_KEY_LEN", "16"))
        self.ttl = int(cfg.get("SESSION_KEY_TTL_SECONDS", "0") or 0)
        self.master = {}
        for k, v in cfg.items():
            if k.startswith("MASTER_KEY_") and v:
                self.master[k[len("MASTER_KEY_") :]] = v
        self.daftar = {}  # NAMA -> (ip, chat_port)
        self._sesi = {}  # (A, B) -> (session_key, jam)

    def _master_key_unutk(self, nama: str) -> str:
        if nama not in self.master:
            punya = ", ".join(self.master) or "(kosong)"
            raise ValueError(
                f"KDC tidak punya master key untuk {nama}. "
                f"Tambahkan MASTER_KEY_{nama} di config/hosts/kdc.env. Yang dikenal: {punya}"
            )
        return self.master[nama]

    def _sesi_aktif(self, a: str, b: str):
        """Fitur tambahan: session key dipakai ulang selama TTL belum lewat."""
        if self.ttl <= 0:
            return None
        lama = self._sesi.get((a, b))
        if lama and time.time() - lama[1] < self.ttl:
            return lama[0]
        return None

    def handle(self, baris: str, addr, conn):
        jenis, field = P.parse(baris)

        if jenis == "REG":
            nama, chat_port = field[0], int(field[1])
            if len(field) > 2:
                alamat, sumber = field[2], f"diumumkan sendiri (paket asal {addr[0]})"
            else:
                alamat, sumber = addr[0], "dilihat dari header paket"
            self.daftar[nama] = (alamat, chat_port)
            log.log(f"[REG] {nama} terdaftar di {alamat}:{chat_port} -- sumber alamat: {sumber}")
            return P.build("REGOK", nama)

        if jenis == "REQ1":
            a, b = field[0], field[1]
            log.log(f"[LANGKAH 1] TERIMA permintaan sesi: {a} -> {b} (asal paket {addr[0]}:{addr[1]})")
            if b not in self.daftar:
                return P.build("ERR", f"{b} belum mendaftar ke KDC")
            k_ab = self._sesi_aktif(a, b) or P.bangkitkan_session_key(self.panjang_key)
            ip_b, port_b = self.daftar[b]
            ip_a, port_a = self.daftar.get(a, (addr[0], 0))

            tiket_plain = P.inner({"K": k_ab, "NAME": a, "A": f"{ip_a}:{port_a}"})
            tiket_hex = core.encrypt_hex(self._master_key_unutk(b), tiket_plain)
            balasan_plain = P.inner({"K": k_ab, "B": f"{ip_b}:{port_b}", "TICKET": tiket_hex})
            balasan_hex = core.encrypt_hex(self._master_key_unutk(a), balasan_plain)
            self._sesi[(a, b)] = (k_ab, time.time())

            log.log(f"[KDC] session key baru: {k_ab!r} (ASCII {len(k_ab)} char) -- hanya tampil di layar KDC")
            log.log(f"[KDC] plaintext tiket -> {tiket_plain}")
            log.log(f"[KDC] ciphertext tiket (heks) -> {tiket_hex}")
            log.log(f"[LANGKAH 2] KIRIM ke {a} {ip_a}: REP2|{balasan_hex} (heks, dienkripsi master key {a})")
            return P.build("REP2", balasan_hex)

        if jenis in ("PING", "STATUS"):
            return P.build("PONG", self.nama, len(self.daftar))
        return P.build("ERR", f"pesan tidak dikenal: {jenis}")

    def jalankan(self) -> link.Listener:
        ip_lokal = []
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 53))
            ip_lokal.append(s.getsockname()[0])
        except OSError:
            pass
        finally:
            s.close()
        log.banner(f"KDC mendengar di port {self.port} | IP perangkat ini: {', '.join(ip_lokal) or 'tidak terdeteksi'}")
        log.log(f"master key dikenal untuk: {', '.join(self.master) or '(KOSONG - isi config!)'}")
        if not self.master:
            log.log("PERINGATAN: tidak ada MASTER_KEY_* yang terbaca, permintaan sesi pasti gagal.")
        srv = link.Listener(self.port, self.handle, "KDC")
        srv.start()
        return srv
