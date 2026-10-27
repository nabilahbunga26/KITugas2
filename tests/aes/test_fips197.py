"""Known-answer test AES pakai vektor resmi FIPS-197 Lampiran C.1."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ksilib.aes.core import decrypt_block, encrypt_block, expand_key  # noqa: E402
from src.ksilib.aes.sbox import INV_SBOX, RCON, SBOX, gmul  # noqa: E402

# key(hex), plaintext(hex), ciphertext(hex)
VEKTOR = [
    ("000102030405060708090a0b0c0d0e0f",
     "00112233445566778899aabbccddeeff",
     "69c4e0d86a7b0430d8cdb78070b4c55a"),
    ("000102030405060708090a0b0c0d0e0f1011121314151617",
     "00112233445566778899aabbccddeeff",
     "dda97ca4864cdfe06eaf70a0ec0d7191"),
    ("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
     "00112233445566778899aabbccddeeff",
     "8ea2b7ca516745bfeafc49904b496089"),
]


def test_sbox_dibangkitkan_benar():
    assert SBOX[0x00] == 0x63
    assert SBOX[0x53] == 0xED
    assert SBOX[0x01] == 0x7C
    assert INV_SBOX[SBOX[0x53]] == 0x53
    assert len(set(SBOX)) == 256


def test_rcon():
    assert RCON[:10] == (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)


def test_gf28():
    assert gmul(0x57, 0x83) == 0xC1
    assert gmul(0x57, 0x13) == 0xFE


def test_vektor_fips197():
    for kh, ph, ch in VEKTOR:
        key = bytes.fromhex(kh)
        blok = bytes.fromhex(ph)
        hasil = encrypt_block(key, blok)
        assert hasil.hex() == ch, f"encrypt {len(key)*8}-bit salah: {hasil.hex()}"
        assert decrypt_block(key, hasil) == blok, f"decrypt {len(key)*8}-bit salah"


def test_jumlah_round_key():
    for panjang, nr in ((16, 10), (24, 12), (32, 14)):
        key = b"A" * panjang
        rk, hitung = expand_key(key)
        assert hitung == nr
        assert len(rk) == nr + 1
        assert rk[0] == key[:16]  # round key pertama = 16 byte awal key


if __name__ == "__main__":
    for nama, fn in sorted(globals().items()):
        if nama.startswith("test_") and callable(fn):
            fn()
            print(f"LULUS {nama}")
