"""Dengar satu koneksi TCP dan balas. Dipakai buat cek konektivitas antar perangkat."""
import argparse
import socket
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bind", default="0.0.0.0", help="IP lokal, 0.0.0.0 = semua interface")
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--seconds", type=float, default=25)
    a = p.parse_args()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((a.bind, a.port))
    srv.listen(1)
    srv.settimeout(1.0)
    print(f"[LISTEN] bind={a.bind}:{a.port} timeout={a.seconds}s", flush=True)

    deadline = time.time() + a.seconds
    while time.time() < deadline:
        try:
            conn, addr = srv.accept()
        except socket.timeout:
            continue
        conn.settimeout(3)
        data = conn.recv(4096)
        print(f"[LISTEN] masuk dari {addr[0]}:{addr[1]} -> {data!r}", flush=True)
        conn.sendall(b"OK-TERIMA-DARI-LISTENER\n")
        conn.close()
        break
    else:
        print("[LISTEN] selesai, tidak ada yang konek", flush=True)
    srv.close()


if __name__ == "__main__":
    main()
