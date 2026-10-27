"""Node = peran Alice atau Bob. Kelas yang sama, jadi keduanya bisa sender sekaligus receiver."""

import threading
import time

from ..aes import core
from ..net import link
from ..utils import log
from . import protocol as P


class Node:
    def __init__(self, nama: str, cfg: dict):
        self.nama = nama
        self.master_key = cfg["MASTER_KEY"]
        self.chat_port = int(cfg["CHAT_PORT"])
        self.kdc_ip = cfg["KDC_IP"]
        self.kdc_port = int(cfg.get("KDC_PORT", "4444"))
        # Alamat yang kita umumkan ke KDC. Kosong = pakai alamat sumber koneksi (yang dilihat KDC).
        # Wajib diisi kalau pasangan menjangkau kita lewat adapter lain, mis. Windows punya
        # 172.20.80.1 ke WSL tapi VM tetangga harus lewat 192.168.88.1.
        self.advertise_ip = cfg.get("ADVERTISE_IP", "").strip()
        self.session_key = None
        self.peer = None  # (nama, ip, port)
        self.auth_ok = False
        self.inbox = []
        self._nonce = None
        self._lock = threading.Lock()
        self._ev = {k: threading.Event() for k in ("TICKET", "CHAL", "RESP", "MSG", "KCONF")}
        self._trig = {}
        self.dengar = link.Listener(self.chat_port, self.handle, nama)

    # ---------- util ----------
    def _set(self, kode, nilai):
        with self._lock:
            self._trig[kode] = nilai
        self._ev[kode].set()

    def _tunggu(self, kode, detik):
        if not self._ev[kode].wait(detik):
            raise TimeoutError(f"menunggu {kode} lebih dari {detik}s (pihak lain jalan?)")
        self._ev[kode].clear()
        with self._lock:
            return self._trig.pop(kode)

    def _peer_addr(self):
        if not self.peer:
            raise RuntimeError("belum punya alamat pasangan -- jalankan distribusi key dulu")
        return self.peer[1], self.peer[2]

    def tanya_kdc(self, baris):
        return link.one_shot(self.kdc_ip, self.kdc_port, baris)

    # ---------- handler pesan masuk (sisi receiver) ----------
    def handle(self, baris: str, addr, conn):
        jenis, field = P.parse(baris)

        if jenis == "TICKET3":
            plain = core.decrypt_hex(self.master_key, field[0])
            isi = P.outer(plain)
            self.session_key = isi["K"]
            ip_a, port_a = isi["A"].rsplit(":", 1)
            self.peer = (isi["NAME"], ip_a, int(port_a))
            log.log(f"[LANGKAH 3] TERIMA tiket dari {addr[0]} (heks {len(field[0])//2} byte)")
            log.log(f"[LANGKAH 3] decrypt dengan master key {self.nama} -> {plain}")
            log.log(f"[LANGKAH 3] dapat session key {self.session_key!r} + alamat pasangan {self.peer}")
            self._set("TICKET", True)
            return "OK-TICKET"

        if jenis == "CHAL4":
            plain = core.decrypt_hex(self.session_key, field[1])
            isi = P.outer(plain)
            log.log(f"[LANGKAH 4] TERIMA challenge dari {addr[0]}: {plain}")
            self._set("CHAL", isi["NONCE"])
            return "OK-CHAL"

        if jenis == "RESP5":
            plain = core.decrypt_hex(self.session_key, field[0])
            isi = P.outer(plain)
            benar = int(self._nonce) + 1 if self._nonce else None
            ok = isi.get("REPLY") and int(isi["REPLY"]) == benar
            self.auth_ok = bool(ok)
            log.log(f"[LANGKAH 5] TERIMA respons dari {addr[0]}: {plain} -> challenge cocok: {ok}")
            log.log("[SIAP] kedua sisi memegang session key yang sama. Masuk mode chat AES." if ok
                    else "[BAHAYA] respons tidak cocok -- key beda / pesan dirusak")
            self._set("RESP", ok)
            return "OK-AUTH" if ok else "BAD-AUTH"

        if jenis == "MSG":
            try:
                teks = core.decrypt_hex(self.session_key, field[0])
            except ValueError as exc:
                log.log(f"[CHAT] gagal dekripsi dari {addr[0]}: {exc} (key tidak sama?)")
                return "ERR-KEY"
            log.log(f"[CHAT] {self.peer[0] if self.peer else addr[0]} -> {self.nama}: {teks!r} "
                    f"(heks {len(field[0])//2} byte)")
            self.inbox.append((addr[0], teks))
            self._set("MSG", teks)
            return "OK-MSG"

        if jenis == "KCONF":
            sama = P.sidik(self.session_key or "") == field[0]
            if sama:
                self.auth_ok = True
            log.log(f"[KEY] pasangan melaporkan sidik {field[0]} -> key SAMA: {sama}")
            return P.build("KCONF", "OK" if sama else "BEDA")

        if jenis == "BYE":
            return "BYE"
        return P.build("ERR", f"pesan tidak dikenal: {jenis}")

    # ---------- alur ----------
    def registrasi(self):
        pesan = P.build("REG", self.nama, self.chat_port)
        if self.advertise_ip:
            pesan += P.SEP + self.advertise_ip
        jawab = self.tanya_kdc(pesan)
        log.log(f"[REG] {jawab} -> KDC {self.kdc_ip}:{self.kdc_port}, alamat terdaftar "
                f"{self.advertise_ip or '(dari header paket)'}")
        if jawab.startswith("ERR"):
            raise RuntimeError(jawab)

    def mulai_sebagai_pengaju(self, nama_pasangan: str, tunggu: float = 300):
        """Alice: langkah 1-2-3 lalu jawab challenge (4) dan kirim respons (5)."""
        self.registrasi()
        jawab = self.tanya_kdc(P.build("REQ1", self.nama, nama_pasangan))
        jenis, field = P.parse(jawab)
        if jenis != "REP2":
            raise RuntimeError(f"KDC menolak: {jawab}")
        log.log(f"[LANGKAH 2] TERIMA dari KDC {self.kdc_ip}: REP2|{field[0]} (heks)")
        plain = core.decrypt_hex(self.master_key, field[0])
        isi = P.outer(plain)
        self.session_key = isi["K"]
        ip, port = isi["B"].split(":")
        self.peer = (nama_pasangan, ip, int(port))
        log.log(f"[LANGKAH 2] decrypt master key {self.nama} -> {plain}")
        log.log(f"[LANGKAH 2] dapat session key {self.session_key!r}, tiket {len(isi['TICKET'])//2} byte heks, "
                f"alamat {nama_pasangan} = {ip}:{port}")

        balasan = link.one_shot(ip, int(port), P.build("TICKET3", isi["TICKET"]))
        log.log(f"[LANGKAH 3] KIRIM tiket ke {nama_pasangan} {ip}:{port} -> {balasan}")
        if not balasan.startswith("OK"):
            raise RuntimeError(f"pasangan menolak tiket: {balasan}")

        log.log(f"[LANGKAH 4] menunggu challenge dari {nama_pasangan} -- di jendelanya harus sudah ketik 'd' "
                f"(kalau belum, dia tidak akan pernah bertanya)")
        n = self._tunggu("CHAL", tunggu)
        self._nonce = n
        balas = P.inner({"NONCE": n, "REPLY": str(int(n) + 1)})
        heks = core.encrypt_hex(self.session_key, balas)
        link.one_shot(*self._peer_addr(), P.build("RESP5", heks))
        log.log(f"[LANGKAH 5] KIRIM ke {nama_pasangan}: encrypt ASCII {balas!r} -> heks {heks}")
        self.auth_ok = True
        log.log("[SIAP] sesi aktif, key AES dua arah sudah sama. Ketik 'k' untuk kirim pesan.")

    def mulai_sebagai_penerima(self, tunggu: float = 300):
        """Bob: tunggu tiket (3), kirim challenge (4), tunggu respons (5)."""
        self.registrasi()
        log.log(f"[TUNGGU] menunggu tiket dari pasangan di port {self.chat_port} ...")
        self._tunggu("TICKET", tunggu)
        n = P.nonce()
        self._nonce = n
        plain = P.inner({"NONCE": n})
        heks = core.encrypt_hex(self.session_key, plain)
        link.one_shot(*self._peer_addr(), P.build("CHAL4", n, heks))
        log.log(f"[LANGKAH 4] KIRIM challenge ke {self.peer[0]}: encrypt ASCII {plain!r} -> heks {heks}")
        ok = self._tunggu("RESP", tunggu)
        if not ok:
            raise RuntimeError("challenge langkah 4 tidak dijawab dengan benar oleh pasangan")

    # ---------- chat ----------
    def kirim(self, teks: str):
        if not self.session_key:
            raise RuntimeError("belum punya session key")
        heks = core.encrypt_hex(self.session_key, teks)
        log.log(f"[CHAT] ASCII {teks!r} -> heks {heks}")
        balasan = link.one_shot(*self._peer_addr(), P.build("MSG", heks))
        if balasan != "OK-MSG":
            log.log(f"[CHAT] pasangan membalas: {balasan}")
        return heks

    def ganti_key(self, key_baru: str):
        core.expand_key(core.to_ascii(key_baru))  # validasi panjang & ASCII
        self.session_key = key_baru
        self.auth_ok = False
        log.log(f"[KEY] key chat {self.nama} diganti -> {key_baru!r} (ASCII {len(key_baru)} char)")
        try:
            jawab = link.one_shot(*self._peer_addr(), P.build("KCONF", P.sidik(key_baru)))
            if jawab == "KCONF|OK":
                self.auth_ok = True
            log.log(f"[KEY] pasangan bilang: {jawab} (kalau BEDA, suruh pasangan ganti key yang sama)")
        except OSError as exc:
            log.log(f"[KEY] pasangan belum bisa dihubungi: {exc}")

    def status(self) -> str:
        k = self.session_key
        alamat_lokal = self.advertise_ip or link.ip_yang_dipakai_untuk(self.kdc_ip)
        return (
            f"peran={self.nama} chat_port={self.chat_port} ip_terdaftar={alamat_lokal} | "
            f"KDC={self.kdc_ip}:{self.kdc_port} | "
            f"pasangan={self.peer} | session_key={'(belum ada)' if not k else repr(k)} "
            f"sidik={P.sidik(k) if k else '-'} | auth={self.auth_ok}"
        )
