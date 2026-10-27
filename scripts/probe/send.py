"""Kirim satu pesan TCP dan tampilkan balasannya."""
import argparse
import socket


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--to", required=True, help="IP tujuan (perangkat lain)")
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--text", default="PING-TCP")
    a = p.parse_args()

    try:
        sock = socket.create_connection((a.to, a.port), timeout=6)
    except Exception as e:
        print(f"[KIRIM] GAGAL ke {a.to}:{a.port} -> {type(e).__name__}: {e}", flush=True)
        raise SystemExit(1)

    sock.sendall(a.text.encode("ascii") + b"\n")
    echo = sock.recv(4096)
    print(f"[KIRIM] {a.text!r} ke {a.to}:{a.port} -> balasan {echo!r}", flush=True)
    sock.close()


if __name__ == "__main__":
    main()
