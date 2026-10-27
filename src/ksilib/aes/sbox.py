"""S-Box AES dibangkitkan sendiri (inverse di GF(2^8) + transformasi affine), bukan tabel salinan.

S-Box[x] = affine(x^-1) dengan affine(y) = y ^ rotl(y,1) ^ rotl(y,2) ^ rotl(y,3) ^ rotl(y,4) ^ 0x63
Referensi: FIPS-197(section 5.1.1).
"""


def gmul(a: int, b: int) -> int:
    """Perkalian dua byte di GF(2^8) dengan polynomial 0x11B."""
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        tinggi = a & 0x80
        a = (a << 1) & 0xFF
        if tinggi:
            a ^= 0x1B
        b >>= 1
    return p


def _rotl8(v: int, n: int) -> int:
    return ((v << n) | (v >> (8 - n))) & 0xFF


def _build():
    # Tabel eksponen/log dengan generator 3 supaya inversi byte jadi murah.
    exp = [0] * 512
    log = [0] * 256
    p = 1
    for i in range(255):
        exp[i] = p
        log[p] = i
        p = gmul(p, 3)

    def inverse(v: int) -> int:
        if v == 0:
            return 0
        return exp[(255 - log[v]) % 255]

    box = []
    for i in range(256):
        y = inverse(i)
        box.append(
            y
            ^ _rotl8(y, 1)
            ^ _rotl8(y, 2)
            ^ _rotl8(y, 3)
            ^ _rotl8(y, 4)
            ^ 0x63
        )
    box = tuple(box)
    inv_box = [0] * 256
    for i, v in enumerate(box):
        inv_box[v] = i
    return tuple(box), tuple(inv_box)


SBOX, INV_SBOX = _build()

# Rcon dihitung sampai 14 round (cukup untuk AES-256).
RCON = []
_r = 1
for _ in range(14):
    RCON.append(_r)
    _r <<= 1
    if _r & 0x100:
        _r ^= 0x11B
RCON = tuple(RCON)
