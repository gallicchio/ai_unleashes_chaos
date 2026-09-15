#!/usr/bin/env python3
"""A small QR encoder, written out because the build must not need one.

The board carries two URLs on its back.  Nothing in KiCad draws QR codes and
the build is meant to work from a bare clone with nothing but Python and
KiCad, so the encoder lives here: byte mode, versions 1-10, error correction
level L or M, which is everything a URL of this length needs.

Run this file directly to self-test it -- it re-decodes what it encodes,
checks the Reed-Solomon syndromes of every block, and compares the format
information against the published table.
"""

# ---------------------------------------------------------------- GF(256) --
EXP = [0] * 512
LOG = [0] * 256
_x = 1
for _i in range(255):
    EXP[_i] = _x
    LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D                      # the QR field's primitive polynomial
for _i in range(255, 512):
    EXP[_i] = EXP[_i - 255]


def gf_mul(a, b):
    return 0 if a == 0 or b == 0 else EXP[LOG[a] + LOG[b]]


def rs_generator(n):
    """Generator polynomial for n error-correction codewords."""
    g = [1]
    for i in range(n):
        g = poly_mul(g, [1, EXP[i]])
    return g


def poly_mul(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, av in enumerate(a):
        if av:
            for j, bv in enumerate(b):
                out[i + j] ^= gf_mul(av, bv)
    return out


def rs_encode(data, n):
    """The n Reed-Solomon check codewords for one block."""
    g = rs_generator(n)
    rem = [0] * n
    for d in data:
        factor = d ^ rem[0]
        rem = rem[1:] + [0]
        if factor:
            for i, gv in enumerate(g[1:]):
                rem[i] ^= gf_mul(gv, factor)
    return rem


def rs_syndromes(block, n):
    """Zero for every syndrome means the block is a valid RS codeword."""
    out = []
    for i in range(n):
        acc = 0
        for c in block:
            acc = gf_mul(acc, EXP[i]) ^ c
        out.append(acc)
    return out


# -------------------------------------------------------------- QR tables --
# Total codewords in the symbol, and how they split into Reed-Solomon blocks.
TOTAL = {1: 26, 2: 44, 3: 70, 4: 100, 5: 134, 6: 172}
# (version, level) -> (error-correction codewords per block,
#                      [(number of blocks, data codewords in each)])
BLOCKS = {
    (1, "L"): (7,  [(1, 19)]),   (1, "M"): (10, [(1, 16)]),
    (2, "L"): (10, [(1, 34)]),   (2, "M"): (16, [(1, 28)]),
    (3, "L"): (15, [(1, 55)]),   (3, "M"): (26, [(1, 44)]),
    (4, "L"): (20, [(1, 80)]),   (4, "M"): (18, [(2, 32)]),
    (5, "L"): (26, [(1, 108)]),  (5, "M"): (24, [(2, 43)]),
    (6, "L"): (18, [(2, 68)]),   (6, "M"): (16, [(4, 27)]),
}
ALIGN = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34],
         7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50]}
EC_BITS = {"L": 0b01, "M": 0b00, "Q": 0b11, "H": 0b10}

# Only version 7 and up carry a version block, and nothing here goes that far;
# the rest of the code would need it, so refuse rather than emit a bad symbol.
MAX_VERSION = 6


def capacity(version, level):
    ec, groups = BLOCKS[(version, level)]
    assert sum(b * (d + ec) for (b, d) in groups) == TOTAL[version]
    return sum(b * d for (b, d) in groups)


def pick_version(nbytes, level):
    for v in range(1, MAX_VERSION + 1):
        # 4 bits of mode + 8 bits of length for versions 1..9
        if capacity(v, level) >= nbytes + 2:
            return v
    raise ValueError(f"{nbytes} bytes does not fit in a version "
                     f"{MAX_VERSION} level-{level} symbol")


# ------------------------------------------------------------- bit stream --
class Bits:
    def __init__(self):
        self.bits = []

    def put(self, value, width):
        for i in range(width - 1, -1, -1):
            self.bits.append((value >> i) & 1)

    def bytes(self):
        pad = (-len(self.bits)) % 8
        bits = self.bits + [0] * pad
        return [int("".join(str(b) for b in bits[i:i + 8]), 2)
                for i in range(0, len(bits), 8)]


def encode_data(payload, version, level):
    """Mode, length, payload, terminator and the alternating pad bytes."""
    total = capacity(version, level)
    b = Bits()
    b.put(0b0100, 4)                     # byte mode
    b.put(len(payload), 8)               # versions 1-9: an 8-bit count
    for ch in payload:
        b.put(ch, 8)
    b.put(0, min(4, total * 8 - len(b.bits)))          # terminator
    data = b.bytes()
    for i in range(total - len(data)):
        data.append(0xEC if i % 2 == 0 else 0x11)
    return data


def interleave(data, version, level):
    ec_len, groups = BLOCKS[(version, level)]
    blocks, pos = [], 0
    for (count, size) in groups:
        for _ in range(count):
            blocks.append(data[pos:pos + size])
            pos += size
    assert pos == len(data), (pos, len(data))
    ecs = [rs_encode(bl, ec_len) for bl in blocks]
    out = []
    for i in range(max(len(bl) for bl in blocks)):
        for bl in blocks:
            if i < len(bl):
                out.append(bl[i])
    for i in range(ec_len):
        for e in ecs:
            out.append(e[i])
    return out


def deinterleave(codewords, version, level):
    """The inverse of interleave(), for the self-test."""
    ec_len, groups = BLOCKS[(version, level)]
    sizes = []
    for (count, size) in groups:
        sizes += [size] * count
    blocks = [[0] * s for s in sizes]
    pos = 0
    for i in range(max(sizes)):
        for b, s in enumerate(sizes):
            if i < s:
                blocks[b][i] = codewords[pos]
                pos += 1
    ecs = [[0] * ec_len for _ in sizes]
    for i in range(ec_len):
        for b in range(len(sizes)):
            ecs[b][i] = codewords[pos]
            pos += 1
    return blocks, ecs


# ---------------------------------------------------------- the matrix -----
def new_matrix(version):
    size = 17 + 4 * version
    m = [[0] * size for _ in range(size)]
    fixed = [[False] * size for _ in range(size)]

    def finder(r0, c0):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = r0 + dr, c0 + dc
                if not (0 <= r < size and 0 <= c < size):
                    continue
                ring = max(abs(dr - 3), abs(dc - 3))
                m[r][c] = 1 if (ring <= 1 or ring == 3) else 0
                fixed[r][c] = True

    for (r0, c0) in ((0, 0), (0, size - 7), (size - 7, 0)):
        finder(r0, c0)
    for i in range(size):
        if not fixed[6][i]:
            m[6][i] = 1 - (i % 2)
            fixed[6][i] = True
        if not fixed[i][6]:
            m[i][6] = 1 - (i % 2)
            fixed[i][6] = True
    for r0 in ALIGN[version]:
        for c0 in ALIGN[version]:
            if fixed[r0][c0]:
                continue                 # the three corners already have finders
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    ring = max(abs(dr), abs(dc))
                    m[r0 + dr][c0 + dc] = 1 if ring != 1 else 0
                    fixed[r0 + dr][c0 + dc] = True
    m[size - 8][8] = 1                   # the always-dark module
    fixed[size - 8][8] = True
    for (r, c) in format_cells(size):    # reserved, written after masking
        fixed[r][c] = True
    return m, fixed


def format_cells(size):
    """The 15 format-information cells, twice over, most significant first."""
    first = [(8, i) for i in range(6)] + [(8, 7), (8, 8), (7, 8)] + \
            [(5 - i, 8) for i in range(6)]
    second = [(size - 1 - i, 8) for i in range(7)] + \
             [(8, size - 15 + i) for i in range(7, 15)]
    return first + second


def bch_format(data5):
    """The 15-bit format information word: BCH(15,5) then the fixed mask."""
    d = data5 << 10
    g = 0b10100110111
    while d.bit_length() > 10:
        d ^= g << (d.bit_length() - 11)
    return ((data5 << 10) | d) ^ 0b101010000010010


MASKS = [
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]


def data_cells(size, fixed):
    """The zigzag the data codewords are written into, most significant first."""
    out = []
    col = size - 1
    upward = True
    while col > 0:
        if col == 6:                     # the vertical timing line is not data
            col -= 1
        for i in range(size):
            r = (size - 1 - i) if upward else i
            for c in (col, col - 1):
                if not fixed[r][c]:
                    out.append((r, c))
        col -= 2
        upward = not upward
    return out


N3_PATTERN = bytes((1, 0, 1, 1, 1, 0, 1))


def _n3(seq, size):
    """Rule 3: the 1:1:3:1:1 pattern with a light area beside it, 40 each.

    A pattern touching the edge of the symbol counts too -- outside the symbol
    is quiet zone, which is light -- which is what ISO/IEC 18004:2015 says and
    what makes this agree with a reference scorer.
    """
    count, idx = 0, seq.find(N3_PATTERN)
    while idx != -1:
        offset = idx + 7
        if (idx in (0, size - 7)
                or not any(seq[max(idx - 4, 0):idx])
                or not any(seq[offset:offset + 4])):
            count += 40
        else:
            offset = idx + 4          # the next place a match could start
        idx = seq.find(N3_PATTERN, offset)
    return count


def penalty(m):
    """The four mask penalty scores of ISO/IEC 18004, added up."""
    size = len(m)
    rows = [bytes(r) for r in m]
    cols = [bytes(c) for c in zip(*m)]
    score = 0
    for line in rows + cols:                                  # N1
        run, prev = 1, line[0]
        for v in line[1:]:
            if v == prev:
                run += 1
            else:
                score += (run - 2) if run >= 5 else 0
                run, prev = 1, v
        score += (run - 2) if run >= 5 else 0
    for r in range(size - 1):                                 # N2
        for c in range(size - 1):
            q = m[r][c] + m[r][c + 1] + m[r + 1][c] + m[r + 1][c + 1]
            if q in (0, 4):
                score += 3
    for line in rows + cols:                                  # N3
        score += _n3(line, size)
    dark = sum(sum(row) for row in m)                         # N4
    score += 10 * int(abs(dark * 100.0 / (size * size) - 50) / 5)
    return score


def encode(text, level="M", version=None):
    """Return the QR matrix for `text` as a list of rows of 0/1."""
    payload = text.encode("utf-8") if isinstance(text, str) else text
    version = version or pick_version(len(payload), level)
    data = encode_data(payload, version, level)
    codewords = interleave(data, version, level)
    m, fixed = new_matrix(version)
    size = len(m)
    cells = data_cells(size, fixed)
    bits = [(cw >> (7 - i)) & 1 for cw in codewords for i in range(8)]
    assert len(bits) >= len(cells) - 7, (len(bits), len(cells))
    for (r, c), bit in zip(cells, bits):
        m[r][c] = bit

    # The mask is chosen by penalty score.  The format cells are left light
    # while scoring -- their contents depend on the mask being scored, so the
    # reference implementations settle the circularity by ignoring them, and
    # this one has to agree or it picks a different mask.
    best = None
    for mask in range(8):
        cand = [row[:] for row in m]
        for (r, c) in cells:
            if MASKS[mask](r, c):
                cand[r][c] ^= 1
        for (r, c) in format_cells(size):
            cand[r][c] = 0
        p = penalty(cand)
        if best is None or p < best[0]:
            best = (p, mask, cand)
    _, mask, out = best
    fmt = bch_format((EC_BITS[level] << 3) | mask)
    for i, (r, c) in enumerate(format_cells(size)):
        out[r][c] = (fmt >> (14 - i % 15)) & 1
    out[size - 8][8] = 1                 # the always-dark module
    return out


# ------------------------------------------------------------ the decoder --
def decode(m, level="M"):
    """Read a matrix back, for the self-test.  Returns (text, mask, version)."""
    size = len(m)
    version = (size - 17) // 4
    fmt = 0
    for (r, c) in format_cells(size)[:15]:
        fmt = (fmt << 1) | m[r][c]
    raw = fmt ^ 0b101010000010010
    # a valid format word is divisible by the BCH generator
    d, g = raw, 0b10100110111
    while d.bit_length() > 10:
        d ^= g << (d.bit_length() - 11)
    if d:
        raise ValueError("format information fails its BCH check")
    ecbits, mask = raw >> 13, (raw >> 10) & 7
    lvl = {v: k for k, v in EC_BITS.items()}[ecbits]
    if lvl != level:
        raise ValueError(f"error-correction level reads back as {lvl}")

    _, fixed = new_matrix(version)
    cells = data_cells(size, fixed)
    bits = []
    for (r, c) in cells:
        bits.append(m[r][c] ^ (1 if MASKS[mask](r, c) else 0))
    ec_len, _ = BLOCKS[(version, level)]
    ncw = TOTAL[version]
    words = [int("".join(str(b) for b in bits[i:i + 8]), 2)
             for i in range(0, ncw * 8, 8)]
    blocks, ecs = deinterleave(words, version, level)
    for bl, ec in zip(blocks, ecs):
        s = rs_syndromes(bl + ec, ec_len)
        if any(s):
            raise ValueError("a Reed-Solomon block does not check out")
    data = [b for bl in blocks for b in bl]
    stream = "".join(f"{b:08b}" for b in data)
    if stream[:4] != "0100":
        raise ValueError("not byte mode")
    n = int(stream[4:12], 2)
    payload = bytes(int(stream[12 + 8 * i:20 + 8 * i], 2) for i in range(n))
    return payload.decode("utf-8"), mask, version


# -------------------------------------------------------------- self-test --
def _selftest():
    ok = 0
    # 1. the published format-information strings
    table = {
        ("L", 0): "111011111000100", ("L", 1): "111001011110011",
        ("L", 2): "111110110101010", ("L", 3): "111100010011101",
        ("L", 4): "110011000101111", ("L", 5): "110001100011000",
        ("L", 6): "110110001000001", ("L", 7): "110100101110110",
        ("M", 0): "101010000010010", ("M", 1): "101000100100101",
        ("M", 2): "101111001111100", ("M", 3): "101101101001011",
        ("M", 4): "100010111111001", ("M", 5): "100000011001110",
        ("M", 6): "100111110010111", ("M", 7): "100101010100000",
        ("Q", 0): "011010101011111", ("Q", 1): "011000001101000",
        ("Q", 2): "011111100110001", ("Q", 3): "011101000000110",
        ("Q", 4): "010010010110100", ("Q", 5): "010000110000011",
        ("Q", 6): "010111011011010", ("Q", 7): "010101111101101",
        ("H", 0): "001011010001001", ("H", 1): "001001110111110",
        ("H", 2): "001110011100111", ("H", 3): "001100111010000",
        ("H", 4): "000011101100010", ("H", 5): "000001001010101",
        ("H", 6): "000110100001100", ("H", 7): "000100000111011",
    }
    for (lvl, mask), want in sorted(table.items()):
        got = f"{bch_format((EC_BITS[lvl] << 3) | mask):015b}"
        assert got == want, f"format {lvl}/{mask}: {got} != {want}"
        ok += 1
    print(f"  format information: {ok} published words reproduced")

    # 2. round-trip every version and level we support
    n = 0
    for level in ("L", "M"):
        for version in range(1, MAX_VERSION + 1):
            cap = capacity(version, level) - 2
            for text in (b"A" * min(cap, 1), b"x" * cap,
                         b"https://github.com/gallicchio/ai_unleashes_chaos"
                         [:cap]):
                if not text:
                    continue
                m = encode(text, level, version)
                back, mask, v = decode(m, level)
                assert back.encode() == text, (back, text)
                assert v == version
                n += 1
    print(f"  round trip: {n} symbols encoded, re-decoded and RS-checked")

    # 3. the three finder patterns really are 1:1:3:1:1 on every scan line
    m = encode("https://seti.harvard.edu/unusual_stuff/misc/lorenz.htm", "M")
    size = len(m)
    for (r0, c0) in ((0, 0), (0, size - 7), (size - 7, 0)):
        for dr in range(7):
            row = m[r0 + dr][c0:c0 + 7]
            want = [1, 1, 1, 1, 1, 1, 1] if dr in (0, 6) else (
                [1, 0, 0, 0, 0, 0, 1] if dr in (1, 5) else [1, 0, 1, 1, 1, 0, 1])
            assert row == want, (r0, c0, dr, row)
    print(f"  finder patterns intact in a {size}x{size} symbol")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
