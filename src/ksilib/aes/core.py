"""AES blok 128-bit, implementasi manual (tanpa library kripto).

State disusun column-major: byte ke-i dari blok masuk ke state[i % 4][i // 4],
jadi di list datar indeks = baris + 4*kolom. Itu sumber bug paling sering, jadi
dibuat eksplisit di fungsi _mix_column di bawah.
"""

from .sbox import INV_SBOX, RCON, SBOX, gmul

BLOCK = 16


class AESKeyError(ValueError):
    pass


def expand_key(key: bytes):
    """Key ASCII (16/24/32 byte) -> (daftar round key, jumlah round)."""
    if len(key) not in (16, 24, 32):
        raise AESKeyError(f"key harus 16/24/32 karakter ASCII, dapat {len(key)}")
    nk = len(key) // 4
    nr = nk + 6
    w = [key[4 * i : 4 * i + 4] for i in range(nk)]
    total = 4 * (nr + 1)
    while len(w) < total:
        t = w[-1]
        if len(w) % nk == 0:
            t = bytes(SBOX[b] for b in t[1:4] + t[0:1])
            t = bytes([t[0] ^ RCON[len(w) // nk - 1]]) + t[1:]
        elif nk > 6 and len(w) % nk == 4:
            t = bytes(SBOX[b] for b in t)
        prev = w[len(w) - nk]
        w.append(bytes(a ^ b for a, b in zip(prev, t)))
    round_keys = [b"".join(w[4 * i : 4 * i + 4]) for i in range(nr + 1)]
    return round_keys, nr


def _sub_bytes(s):
    return [SBOX[b] for b in s]


def _inv_sub_bytes(s):
    return [INV_SBOX[b] for b in s]


def _shift_rows(s, inverse=False):
    out = list(s)
    for r in range(1, 4):
        row = [s[r + 4 * c] for c in range(4)]
        if inverse:
            row = row[-r:] + row[:-r]
        else:
            row = row[r:] + row[:r]
        for c in range(4):
            out[r + 4 * c] = row[c]
    return out


def _mix_column(col):
    a0, a1, a2, a3 = col
    return [
        gmul(a0, 2) ^ gmul(a1, 3) ^ a2 ^ a3,
        a0 ^ gmul(a1, 2) ^ gmul(a2, 3) ^ a3,
        a0 ^ a1 ^ gmul(a2, 2) ^ gmul(a3, 3),
        gmul(a0, 3) ^ a1 ^ a2 ^ gmul(a3, 2),
    ]


def _inv_mix_column(col):
    a0, a1, a2, a3 = col
    return [
        gmul(a0, 14) ^ gmul(a1, 11) ^ gmul(a2, 13) ^ gmul(a3, 9),
        gmul(a0, 9) ^ gmul(a1, 14) ^ gmul(a2, 11) ^ gmul(a3, 13),
        gmul(a0, 13) ^ gmul(a1, 9) ^ gmul(a2, 14) ^ gmul(a3, 11),
        gmul(a0, 11) ^ gmul(a1, 13) ^ gmul(a2, 9) ^ gmul(a3, 14),
    ]


def _mix_columns(s, inverse=False):
    out = []
    for c in range(4):
        col = s[4 * c : 4 * c + 4]
        out += _inv_mix_column(col) if inverse else _mix_column(col)
    return out


def _add_round_key(s, rk):
    return [a ^ b for a, b in zip(s, rk)]


def encrypt_block(key: bytes, block: bytes) -> bytes:
    assert len(block) == BLOCK, "blok harus 16 byte"
    rk, nr = expand_key(key)
    s = _add_round_key(list(block), rk[0])
    for rnd in range(1, nr):
        s = _add_round_key(_mix_columns(_shift_rows(_sub_bytes(s))), rk[rnd])
    s = _add_round_key(_shift_rows(_sub_bytes(s)), rk[nr])  # round terakhir: tanpa MixColumns
    return bytes(s)


def decrypt_block(key: bytes, block: bytes) -> bytes:
    assert len(block) == BLOCK, "blok harus 16 byte"
    rk, nr = expand_key(key)
    s = _add_round_key(list(block), rk[nr])
    for rnd in range(nr - 1, 0, -1):
        s = _shift_rows(_inv_sub_bytes(s), inverse=True)
        s = _add_round_key(s, rk[rnd])
        s = _mix_columns(s, inverse=True)
    s = _add_round_key(_shift_rows(_inv_sub_bytes(s), inverse=True), rk[0])
    return bytes(s)


def pad(data: bytes) -> bytes:
    """PKCS#7 untuk blok 16: sisa 0 byte -> tambah 1 blok penuh 0x10."""
    n = BLOCK - (len(data) % BLOCK)
    return data + bytes([n] * n)


def unpad(data: bytes) -> bytes:
    if not data or len(data) % BLOCK:
        raise ValueError("ciphertext tidak valid (panjang bukan kelipatan 16)")
    n = data[-1]
    if n < 1 or n > BLOCK or data[-n:] != bytes([n] * n):
        raise ValueError("padding PKCS#7 salah: key tidak cocok atau data rusak")
    return data[:-n]


def encrypt_hex(ascii_key: str, ascii_text: str) -> str:
    """ASCII key + ASCII plaintext -> ciphertext HEKS (ECB, PKCS#7)."""
    key = to_ascii(ascii_key)
    data = pad(to_ascii(ascii_text))
    out = b"".join(encrypt_block(key, data[i : i + BLOCK]) for i in range(0, len(data), BLOCK))
    return out.hex()


def decrypt_hex(ascii_key: str, hex_text: str) -> str:
    key = to_ascii(ascii_key)
    raw = bytes.fromhex(_check_hex(hex_text))
    out = b"".join(decrypt_block(key, raw[i : i + BLOCK]) for i in range(0, len(raw), BLOCK))
    return unpad(out).decode("ascii")


def to_ascii(text: str) -> bytes:
    try:
        return text.encode("ascii")
    except UnicodeEncodeError as e:
        raise AESKeyError(f"harus ASCII (0-127): {text!r} -> {e}") from e


def _check_hex(h: str) -> str:
    h = h.strip()
    if len(h) % 2 or any(c not in "0123456789abcdefABCDEF" for c in h):
        raise AESKeyError(f"bukan heks valid: {h!r}")
    return h
