"""Socket TCP + framing satu baris ASCII.

Satu pesan = satu baris diakhiri \\n, isinya teks ASCII (field ciphertext berupa heks),
jadi semuanya tetap terbaca manusia di Wireshark.
"""

import socket
import threading


def to_ascii(text: str) -> bytes:
    try:
        return text.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"pesan harus ASCII (0-127), tidak bisa: {text!r} ({exc})") from exc


def send_line(sock: socket.socket, text: str):
    sock.sendall(to_ascii(text) + b"\n")


def read_line(rfile) -> str:
    baris = rfile.readline()
    if not baris:
        raise ConnectionError("koneksi ditutup pihak lain")
    return baris.decode("ascii", errors="replace").rstrip("\r\n")


def connect(ip: str, port: int, timeout: float = 8.0):
    sock = socket.create_connection((ip, int(port)), timeout=timeout)
    sock.settimeout(timeout)
    return sock


def one_shot(ip: str, port: int, text: str, timeout: float = 10.0) -> str:
    """Kirim satu pesan ke layanan, tunggu satu balasan, tutup. Balasan = isi pesan berikutnya."""
    with connect(ip, port, timeout) as s:
        s.sendall(to_ascii(text) + b"\n")
        return read_line(s.makefile("rb"))


class Listener(threading.Thread):
    """Terima koneksi sambil program tetap bisa dipakai (bukti Alice/Bob bisa jadi receiver)."""

    def __init__(self, port: int, handler, nama: str = ""):
        super().__init__(daemon=True, name=f"listener-{nama}")
        self.port = int(port)
        self.handler = handler
        self.nama = nama
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", self.port))
        srv.listen(8)
        self._srv = srv
        self._berhenti = threading.Event()

    def run(self):
        while not self._berhenti.is_set():
            try:
                conn, addr = self._srv.accept()
            except OSError:
                break
            threading.Thread(target=self._layani, args=(conn, addr), daemon=True).start()

    def _layani(self, conn, addr):
        try:
            conn.settimeout(120)
            rf = conn.makefile("rb")
            while True:
                try:
                    baris = read_line(rf)
                except (ConnectionError, socket.timeout, UnicodeDecodeError):
                    break
                try:
                    jawaban = self.handler(baris, addr, conn)
                except Exception as exc:  # jangan matikan listener karena satu pesan rusak
                    jawaban = f"ERR|{type(exc).__name__}:{exc}"
                if jawaban is not None:
                    send_line(conn, jawaban)
        finally:
            conn.close()

    def stop(self):
        self._berhenti.set()
        self._srv.close()


def ip_yang_dipakai_untuk(target_ip: str) -> str:
    """Tebak IP lokal yang akan dipakai keluar ke target, tanpa hardcode."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((target_ip, 9))
        return s.getsockname()[0]
    except OSError:
        return socket.gethostbyname(socket.gethostname())
    finally:
        s.close()
