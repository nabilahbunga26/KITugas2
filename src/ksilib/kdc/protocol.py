"""Bentuk pesan protokol KDC (Needham-Schroeder) + AES. Semua field ASCII, ciphertext heks."""

import random

SEP = "|"


def build(jenis: str, *field) -> str:
    return SEP.join((jenis, *(str(f) for f in field)))


def parse(baris: str):
    bagian = baris.split(SEP)
    return bagian[0], bagian[1:]


def sidik(key: str) -> str:
    """Checksum 4 heks untuk menguji kedua sisi pakai key yang sama (bukan fungsi rahasia)."""
    total = 0
    for ch in key.encode("ascii"):
        total = (total * 131 + ch) & 0xFFFFFFFF
    return f"{total:08x}"[-4:]


def bangkitkan_session_key(panjang: int = 16) -> str:
    huruf = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(random.SystemRandom().choice(huruf) for _ in range(panjang))


def nonce() -> str:
    return f"{random.SystemRandom().randrange(10**6):06d}"


def inner(d: dict) -> str:
    return SEP.join(f"{k}={v}" for k, v in d.items())


def outer(teks: str) -> dict:
    hasil = {}
    for bagian in teks.split(SEP):
        if "=" in bagian:
            k, v = bagian.split("=", 1)
            hasil[k] = v
    return hasil
