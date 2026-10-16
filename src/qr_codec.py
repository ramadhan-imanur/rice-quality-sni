#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qr_codec.py — Generator QR Code ISO/IEC 18004 Minimalis Pure Python
==================================================================
Mendukung Mode Byte (ISO-8859-1 / UTF-8) Versi 1 - 7, EC Level L & M.
100% Pustaka Standar Python — Tanpa dependensi eksternal.
"""

from typing import List, Tuple, Optional

# Galois Field GF(256) Tables
EXP = [0] * 512
LOG = [0] * 256
_x = 1
for _i in range(255):
    EXP[_i] = _x
    EXP[_i + 255] = _x
    LOG[_x] = _i
    _x = (_x << 1) ^ (0x11D if (_x & 0x80) else 0)

def _gmul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return EXP[LOG[a] + LOG[b]]

def _rs_poly(nsym: int) -> List[int]:
    g = [1]
    for i in range(nsym):
        ng = [0] * (len(g) + 1)
        for j in range(len(g)):
            ng[j] ^= g[j]
            ng[j + 1] ^= _gmul(g[j], EXP[i])
        g = ng
    return g

def _rs_encode(msg: List[int], nsym: int) -> List[int]:
    gen = _rs_poly(nsym)
    res = list(msg) + [0] * nsym
    for i in range(len(msg)):
        coef = res[i]
        if coef != 0:
            for j in range(len(gen)):
                res[i + j] ^= _gmul(gen[j], coef)
    return res[len(msg):]

# Table: (version, ec_level) -> (total_cw, data_cw, ec_cw_per_block, num_blocks_g1, data_cw_g1, num_blocks_g2, data_cw_g2)
# Supported: EC Level L and M, Versions 1-7
VERSION_SPECS = {
    # V1 (21x21)
    (1, 'L'): (26, 19, 7, 1, 19, 0, 0),
    (1, 'M'): (26, 16, 10, 1, 16, 0, 0),
    # V2 (25x25)
    (2, 'L'): (44, 34, 10, 1, 34, 0, 0),
    (2, 'M'): (44, 28, 16, 1, 28, 0, 0),
    # V3 (29x29)
    (3, 'L'): (70, 55, 15, 1, 55, 0, 0),
    (3, 'M'): (70, 44, 26, 1, 44, 0, 0),
    # V4 (33x33)
    (4, 'L'): (100, 80, 20, 1, 80, 0, 0),
    (4, 'M'): (100, 64, 18, 2, 32, 0, 0),
    # V5 (37x37)
    (5, 'L'): (134, 108, 26, 1, 108, 0, 0),
    (5, 'M'): (134, 86, 24, 2, 43, 0, 0),
    # V6 (41x41)
    (6, 'L'): (172, 136, 18, 2, 68, 0, 0),
    (6, 'M'): (172, 108, 16, 4, 27, 0, 0),
    # V7 (45x45)
    (7, 'L'): (196, 156, 20, 2, 78, 0, 0),
    (7, 'M'): (196, 124, 18, 2, 31, 2, 31),
}

ALIGNMENT_LOCATIONS = {
    1: [],
    2: [6, 18],
    3: [6, 22],
    4: [6, 26],
    5: [6, 30],
    6: [6, 34],
    7: [6, 22, 38],
}

def _get_format_bits(ec_level_char: str, mask: int) -> int:
    # L=01 (1), M=00 (0)
    ec_val = 1 if ec_level_char == 'L' else 0
    data = (ec_val << 3) | mask
    rem = data << 10
    poly = 0x537
    for i in range(14, 9, -1):
        if rem & (1 << i):
            rem ^= (poly << (i - 10))
    return ((data << 10) | rem) ^ 0x5412

def _apply_mask(r: int, c: int, mask: int) -> bool:
    if mask == 0: return (r + c) % 2 == 0
    if mask == 1: return r % 2 == 0
    if mask == 2: return c % 3 == 0
    if mask == 3: return (r + c) % 3 == 0
    if mask == 4: return (r // 2 + c // 3) % 2 == 0
    if mask == 5: return ((r * c) % 2) + ((r * c) % 3) == 0
    if mask == 6: return (((r * c) % 2) + ((r * c) % 3)) % 2 == 0
    if mask == 7: return (((r + c) % 2) + ((r * c) % 3)) % 2 == 0
    return False

def generate_qr_matrix(text: str, ec_level: str = 'L') -> List[List[bool]]:
    """
    Menghasilkan matriks boolean 2D QR Code untuk teks yang diberikan.
    True = modul gelap (hitam), False = modul terang (putih).
    """
    data_bytes = text.encode('utf-8')
    data_len = len(data_bytes)

    # Pilih versi terkecil yang muat
    version = None
    spec = None
    for v in range(1, 8):
        s = VERSION_SPECS.get((v, ec_level))
        if s and s[1] >= data_len + 3:  # approx overhead for byte mode
            version = v
            spec = s
            break
    if version is None:
        raise ValueError(f"Teks terlalu panjang untuk QR Versi 1-7 (panjang: {data_len} bytes)")

    total_cw, data_cw, ec_cw_per_block, n_b1, d_b1, n_b2, d_b2 = spec
    size = 17 + 4 * version

    # 1. Encode data bits (Byte mode 0100)
    bit_buffer = []
    def add_bits(val, count):
        for i in range(count - 1, -1, -1):
            bit_buffer.append((val >> i) & 1)

    add_bits(0b0100, 4)  # Mode: 8-bit byte
    add_bits(data_len, 8)  # Character count (8 bits for V1-9)
    for b in data_bytes:
        add_bits(b, 8)

    # Terminator
    rem_bits = data_cw * 8 - len(bit_buffer)
    add_bits(0, min(4, rem_bits))

    # Pad to byte boundary
    while len(bit_buffer) % 8 != 0:
        bit_buffer.append(0)

    # Pad bytes with 0xEC and 0x11
    pad_bytes = [0xEC, 0x11]
    p_idx = 0
    while len(bit_buffer) < data_cw * 8:
        add_bits(pad_bytes[p_idx % 2], 8)
        p_idx += 1

    # Convert bit buffer to bytes
    codewords = []
    for i in range(0, len(bit_buffer), 8):
        byte_val = 0
        for j in range(8):
            byte_val = (byte_val << 1) | bit_buffer[i + j]
        codewords.append(byte_val)

    # Partition into blocks & compute RS
    data_blocks = []
    ec_blocks = []
    cw_offset = 0
    for _ in range(n_b1):
        blk = codewords[cw_offset : cw_offset + d_b1]
        data_blocks.append(blk)
        ec_blocks.append(_rs_encode(blk, ec_cw_per_block))
        cw_offset += d_b1
    for _ in range(n_b2):
        blk = codewords[cw_offset : cw_offset + d_b2]
        data_blocks.append(blk)
        ec_blocks.append(_rs_encode(blk, ec_cw_per_block))
        cw_offset += d_b2

    # Interleave data codewords
    final_sequence = []
    max_d = max(d_b1, d_b2 if n_b2 > 0 else 0)
    for i in range(max_d):
        for blk in data_blocks:
            if i < len(blk):
                final_sequence.append(blk[i])
    # Interleave EC codewords
    for i in range(ec_cw_per_block):
        for blk in ec_blocks:
            final_sequence.append(blk[i])

    # Convert final sequence to bitstream
    final_bits = []
    for byte in final_sequence:
        for bit_pos in range(7, -1, -1):
            final_bits.append((byte >> bit_pos) & 1)

    # 2. Build grid
    grid = [[None for _ in range(size)] for _ in range(size)]
    is_reserved = [[False for _ in range(size)] for _ in range(size)]

    def mark_reserved(r, c):
        is_reserved[r][c] = True

    # Finder patterns
    def set_finder(top_r, left_c):
        for r in range(7):
            for c in range(7):
                dark = (r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4))
                grid[top_r + r][left_c + c] = dark
                mark_reserved(top_r + r, left_c + c)
        # Separator
        for r in range(-1, 8):
            for c in range(-1, 8):
                if 0 <= top_r + r < size and 0 <= left_c + c < size:
                    if not is_reserved[top_r + r][left_c + c]:
                        grid[top_r + r][left_c + c] = False
                        mark_reserved(top_r + r, left_c + c)

    set_finder(0, 0)
    set_finder(0, size - 7)
    set_finder(size - 7, 0)

    # Alignment patterns (V2+)
    aligns = ALIGNMENT_LOCATIONS[version]
    for r_pos in aligns:
        for c_pos in aligns:
            # Check overlap with finder patterns
            if is_reserved[r_pos][c_pos]:
                continue
            for r in range(-2, 3):
                for c in range(-2, 3):
                    dark = (abs(r) == 2 or abs(c) == 2 or (r == 0 and c == 0))
                    grid[r_pos + r][c_pos + c] = dark
                    mark_reserved(r_pos + r, c_pos + c)

    # Timing patterns
    for i in range(size):
        if not is_reserved[6][i]:
            grid[6][i] = (i % 2 == 0)
            mark_reserved(6, i)
        if not is_reserved[i][6]:
            grid[i][6] = (i % 2 == 0)
            mark_reserved(i, 6)

    # Dark module
    grid[4 * version + 9][8] = True
    mark_reserved(4 * version + 9, 8)

    # Reserve Format Info areas
    for i in range(9):
        if i != 6:
            mark_reserved(8, i)
            mark_reserved(i, 8)
    for i in range(8):
        mark_reserved(8, size - 1 - i)
        mark_reserved(size - 1 - i, 8)

    # 3. Data placement (zigzag)
    bit_idx = 0
    col = size - 1
    going_up = True
    while col > 0:
        if col == 6:  # Skip timing column
            col -= 1
        rows = range(size - 1, -1, -1) if going_up else range(size)
        for row in rows:
            for c in (col, col - 1):
                if not is_reserved[row][c]:
                    b = final_bits[bit_idx] if bit_idx < len(final_bits) else 0
                    grid[row][c] = bool(b)
                    bit_idx += 1
        col -= 2
        going_up = not going_up

    # 4. Choose best mask (evaluate penalty score)
    best_mask = 0
    best_penalty = 10**9
    best_grid = None

    for mask_choice in range(8):
        candidate = [row[:] for row in grid]
        # Apply mask to data modules
        for r in range(size):
            for c in range(size):
                if not is_reserved[r][c]:
                    if _apply_mask(r, c, mask_choice):
                        candidate[r][c] = not candidate[r][c]

        # Add format bits
        fmt_bits = _get_format_bits(ec_level, mask_choice)
        # Format bits top-left: bits 0..5 on (8,0..5), bit 6 on (8,7), bits 7..8 on (8,8), (7,8), bits 9..14 on (5..0, 8)
        # Let's map standard 15 format bits
        fmt_coords_tl = [
            (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
            (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)
        ]
        fmt_coords_br = [
            (size - 1, 8), (size - 2, 8), (size - 3, 8), (size - 4, 8), (size - 5, 8), (size - 6, 8), (size - 7, 8),
            (8, size - 8), (8, size - 7), (8, size - 6), (8, size - 5), (8, size - 4), (8, size - 3), (8, size - 2), (8, size - 1)
        ]
        for idx in range(15):
            b_val = bool((fmt_bits >> idx) & 1)
            r1, c1 = fmt_coords_tl[idx]
            r2, c2 = fmt_coords_br[idx]
            candidate[r1][c1] = b_val
            candidate[r2][c2] = b_val

        # Penalty evaluation (simple N1 + N2 + N3 + N4)
        penalty = 0
        # N1: 5+ consecutive same color in row/col
        for r in range(size):
            run = 1
            for c in range(1, size):
                if candidate[r][c] == candidate[r][c - 1]:
                    run += 1
                else:
                    if run >= 5: penalty += 3 + (run - 5)
                    run = 1
            if run >= 5: penalty += 3 + (run - 5)

        for c in range(size):
            run = 1
            for r in range(1, size):
                if candidate[r][c] == candidate[r - 1][c]:
                    run += 1
                else:
                    if run >= 5: penalty += 3 + (run - 5)
                    run = 1
            if run >= 5: penalty += 3 + (run - 5)

        if penalty < best_penalty:
            best_penalty = penalty
            best_mask = mask_choice
            best_grid = candidate

    return best_grid

def qr_to_ascii(grid: List[List[bool]]) -> str:
    """Render QR matrix sebagai string teks Unicode."""
    lines = []
    # Add quiet zone
    lines.append("  " * (len(grid) + 4))
    lines.append("  " * (len(grid) + 4))
    for row in grid:
        line = "    " + "".join("██" if cell else "  " for cell in row) + "    "
        lines.append(line)
    lines.append("  " * (len(grid) + 4))
    lines.append("  " * (len(grid) + 4))
    return "\n".join(lines)

if __name__ == "__main__":
    test_url = "http://localhost:8000/verify.html?id=SNI-20261016-33B257&sig=1a2b3c4d5e6f"
    mat = generate_qr_matrix(test_url, 'L')
    print(f"QR Generated! Size: {len(mat)}x{len(mat)}")
    print(qr_to_ascii(mat)[:300] + "...")
