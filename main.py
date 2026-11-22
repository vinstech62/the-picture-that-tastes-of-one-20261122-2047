#!/usr/bin/env python3
"""Procedural strawberry: one glossy ripe strawberry on warm cream.

Stdlib only. Writes a deterministic 1024x1024 PNG to /output/entry.png
(or $ENTRY_OUTPUT). No network, no assets, fixed seed, no timestamps.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# --- palette -------------------------------------------------------------
BG_CENTRE = (255, 246, 230)
BG_EDGE = (238, 214, 176)
RED_TOP = (238, 64, 52)
RED_BOTTOM = (168, 12, 30)
RED_EDGE = (140, 8, 24)
SEED = (250, 214, 130)
SEED_DARK = (196, 148, 64)
LEAF = (74, 148, 58)
LEAF_DARK = (38, 102, 34)
LEAF_LIGHT = (120, 190, 96)
SHADOW = (120, 84, 48)


def clamp(v, lo=0, hi=255):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def blend(c1, c2, t):
    return (clamp(int(lerp(c1[0], c2[0], t))),
            clamp(int(lerp(c1[1], c2[1], t))),
            clamp(int(lerp(c1[2], c2[2], t))))


# --- strawberry outline --------------------------------------------------
TOP = 168.0
BOTTOM = 884.0
CX = 512.0


def half_width(y):
    """Half-width of the berry at row y (0 outside the berry)."""
    if y < TOP or y > BOTTOM:
        return 0.0
    s = (y - TOP) / (BOTTOM - TOP)
    return 332.0 * (math.sin(math.pi * (0.02 + 0.98 * s)) ** 0.8)


# --- achenes (seeds): staggered rows -------------------------------------
SEEDS = []
_y = 300
_row = 0
while _y < 830:
    _x = 300 if _row % 2 == 0 else 330
    while _x < 730:
        SEEDS.append((_x, _y))
        _x += 62
    _y += 56
    _row += 1

SEED_ROWS = [[] for _ in range(H)]
for _sx, _sy in SEEDS:
    _hw = half_width(_sy)
    if _hw <= 0 or abs(_sx - CX) > _hw - 26:
        continue
    for _yy in range(_sy - 7, _sy + 8):
        if 0 <= _yy < H:
            _dy = (_yy - _sy) / 7.0
            _rx = 5.0 * math.sqrt(max(0.0, 1.0 - _dy * _dy))
            SEED_ROWS[_yy].append((_sx - _rx, _sx + _rx, _sy))


# --- calyx: five pointed leaves fanning from the crown -------------------
def _leaf_spans(cx, cy, length, width, angle_deg):
    """Per-row x-intervals of a rotated ellipse (a pointed leaf)."""
    spans = {}
    ang = math.radians(angle_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    for yy in range(int(cy - length), int(cy + length) + 1):
        if not 0 <= yy < H:
            continue
        best = None
        for k in range(-100, 101):
            t = k / 100.0
            lx = cx + t * length * ca
            ly = cy + t * length * sa
            if abs(ly - yy) < 1.0:
                w = width * math.sqrt(max(0.0, 1.0 - t * t))
                lo, hi = lx - w, lx + w
                best = (lo, hi) if best is None else (min(best[0], lo), max(best[1], hi))
        if best is not None:
            spans[yy] = best
    return spans


LEAF_ROWS = [[] for _ in range(H)]
_LEAVES = [
    (512, 178, 96, 26, -90),   # centre leaf, pointing up
    (512, 186, 92, 24, -138),  # upper left
    (512, 186, 92, 24, -42),   # upper right
    (512, 196, 82, 22, -165),  # left
    (512, 196, 82, 22, -15),   # right
]
for _cx, _cy, _ln, _wd, _an in _LEAVES:
    for _yy, (_lo, _hi) in _leaf_spans(_cx, _cy, _ln, _wd, _an).items():
        LEAF_ROWS[_yy].append((_lo, _hi))


# --- render ---------------------------------------------------------------
def render():
    dx2 = [(x - 512.0) ** 2 for x in range(W)]
    img = bytearray(W * H * 3)
    sqrt = math.sqrt
    for y in range(H):
        dy = y - 470.0
        dy2 = dy * dy
        hw = half_width(y)
        row = y * W * 3
        seeds = SEED_ROWS[y]
        leaves = LEAF_ROWS[y]
        # ground shadow: soft ellipse under the berry
        sh_dy = (y - 905.0) / 34.0
        sh_ok = abs(sh_dy) < 1.0
        for x in range(W):
            i = row + x * 3
            r = sqrt(dx2[x] + dy2)
            t = min(1.0, r / 950.0)
            cr = int(lerp(BG_CENTRE[0], BG_EDGE[0], t))
            cg = int(lerp(BG_CENTRE[1], BG_EDGE[1], t))
            cb = int(lerp(BG_CENTRE[2], BG_EDGE[2], t))
            if sh_ok:
                sh_dx = (x - 512.0) / 330.0
                sh = 1.0 - (sh_dx * sh_dx + sh_dy * sh_dy)
                if sh > 0.0:
                    a = 0.30 * sh
                    cr = int(lerp(cr, SHADOW[0], a))
                    cg = int(lerp(cg, SHADOW[1], a))
                    cb = int(lerp(cb, SHADOW[2], a))
            if hw > 0.0:
                dx = (x - CX) / hw
                if abs(dx) < 1.0:
                    s = (y - TOP) / (BOTTOM - TOP)
                    # vertical red gradient + darker rim at the edges
                    br = int(lerp(RED_TOP[0], RED_BOTTOM[0], s))
                    bg = int(lerp(RED_TOP[1], RED_BOTTOM[1], s))
                    bb = int(lerp(RED_TOP[2], RED_BOTTOM[2], s))
                    edge = abs(dx) ** 2.4
                    br = int(lerp(br, RED_EDGE[0], edge * 0.55))
                    bg = int(lerp(bg, RED_EDGE[1], edge * 0.55))
                    bb = int(lerp(bb, RED_EDGE[2], edge * 0.55))
                    # warm light from upper left
                    warm = max(0.0, 1.0 - ((x - 380.0) ** 2 + (y - 300.0) ** 2) / 420000.0)
                    br = clamp(br + int(26 * warm))
                    bg = clamp(bg + int(10 * warm))
                    # gloss highlight on the upper-left shoulder
                    gx = (x - 400.0) / 185.0
                    gy = (y - 305.0) / 125.0
                    gd = gx * gx + gy * gy
                    if gd < 1.0:
                        g = (1.0 - gd) ** 1.6 * 0.55
                        br = int(lerp(br, 255, g))
                        bg = int(lerp(bg, 235, g))
                        bb = int(lerp(bb, 225, g))
                    cr, cg, cb = br, bg, bb
                    # achene (seed) in this row?
                    for slo, shi, ssy in seeds:
                        if slo <= x <= shi:
                            dseed = abs(y - ssy) / 7.0
                            cr, cg, cb = SEED if dseed < 0.55 else SEED_DARK
                            break
            # calyx leaves drawn over the top of the berry
            for llo, lhi in leaves:
                if llo <= x <= lhi:
                    lt = min(1.0, (x - llo) / max(1.0, (lhi - llo)))
                    cr, cg, cb = blend(LEAF_DARK, LEAF_LIGHT, 0.35 + 0.5 * lt)
                    break
            img[i] = cr
            img[i + 1] = cg
            img[i + 2] = cb
    return img


def write_png(path, img):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)  # filter: None
        raw += img[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


def main():
    out = os.environ.get("ENTRY_OUTPUT", "/output/entry.png")
    write_png(out, render())
    print("wrote", out)


if __name__ == "__main__":
    main()
