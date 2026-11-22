#!/usr/bin/env python3
"""One glossy strawberry, drawn pixel by pixel with the standard library.

Writes a single 1024x1024 PNG to /output/entry.png (or $ENTRY_OUTPUT).
No assets, no network, fully deterministic: every pixel is a pure
function of its coordinates, so repeated runs are byte-identical.
"""

import math
import os
import struct
import zlib

SIZE = 1024
OUTPUT = os.environ.get("ENTRY_OUTPUT", "/output/entry.png")

# ---- berry geometry -----------------------------------------------------
CX = 512.0
TOP = 205.0
BOT = 942.0
HALF_W = 330.0

# ---- palette ------------------------------------------------------------
BG_CENTER = (255, 246, 232)
BG_EDGE = (240, 216, 178)
SHADOW_RGB = (112, 82, 50)
RED_TOP = (224, 54, 50)
RED_MID = (199, 30, 38)
RED_DEEP = (148, 15, 27)
GLOSS_RGB = (255, 148, 108)
SEED_RGB = (247, 217, 134)
SEED_SHADE = (118, 15, 21)
LEAF_BASE = (46, 118, 52)
LEAF_TIP = (96, 178, 88)
LEAF_VEIN = (150, 205, 120)


def clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def smoothstep(a, b, x):
    t = clamp01((x - a) / (b - a))
    return t * t * (3.0 - 2.0 * t)


def mix(c1, c2, t):
    return (c1[0] + (c2[0] - c1[0]) * t,
            c1[1] + (c2[1] - c1[1]) * t,
            c1[2] + (c2[2] - c1[2]) * t)


def body_half_width(t):
    """Half-width of the berry at normalised height t (0 top, 1 point).

    Plump upper body: full width holds through the shoulders, then the
    sides curve in steeply toward the point at the bottom.
    """
    shoulder = 1.0 - smoothstep(0.30, 1.0, t) ** 1.2
    top_round = 0.78 + 0.22 * smoothstep(0.0, 0.12, t)
    return HALF_W * shoulder * top_round


# ---- calyx leaves: (angle from straight up, length, half width) ---------
LEAVES = [
    (-72.0, 148.0, 30.0),
    (-36.0, 166.0, 34.0),
    (0.0, 182.0, 36.0),
    (36.0, 166.0, 34.0),
    (72.0, 148.0, 30.0),
]
LEAF_BASE_PT = (512.0, 222.0)
LEAF_TRIG = [(math.sin(math.radians(a)), math.cos(math.radians(a)), ln, wd)
             for (a, ln, wd) in LEAVES]


def leaf_profile(s, length, half_w):
    u = s / length
    if u <= 0.0 or u >= 1.0:
        return 0.0
    return half_w * (math.sin(math.pi * u ** 0.9) ** 0.7)


# ---- achene (seed) rows --------------------------------------------------
# Each row: (centre y, first seed x, seed count). Seeds sit in staggered
# rows, only where the berry is wide enough to hold them.
SEED_ROWS = []
for _r in range(10):
    _ys = 300.0 + _r * 60.0
    _t = (_ys - TOP) / (BOT - TOP)
    _hw = body_half_width(_t)
    _stag = 34.0 if _r % 2 else 0.0
    _x0 = CX - _hw + 42.0 + _stag
    _x1 = CX + _hw - 42.0
    _n = int((_x1 - _x0) / 68.0) + 1
    if _n > 0:
        SEED_ROWS.append((_ys, _x0, _n))


def render_row(y):
    out = bytearray()
    # seed row that can affect this scanline (at most one: rows are 60 apart)
    seed = None
    sr = int(round((y - 300.0) / 60.0))
    if 0 <= sr < len(SEED_ROWS):
        ys, x0, n = SEED_ROWS[sr]
        if abs(y - ys) <= 18.0:
            seed = (ys, x0, n)
    in_body = TOP - 2.0 <= y <= BOT
    if in_body:
        t = (y - TOP) / (BOT - TOP)
        if t < 0.0:
            t = 0.0
        elif t > 1.0:
            t = 1.0
        hw = body_half_width(t)
    else:
        t = 0.0
        hw = 0.0
    in_leaf = 38 <= y <= 234
    in_stem = 96 <= y <= 222
    for x in range(SIZE):
        # warm cream radial background
        dx = x - 512.0
        dy = y - 430.0
        d = math.sqrt(dx * dx + dy * dy) / 700.0
        r, g, b = mix(BG_CENTER, BG_EDGE, smoothstep(0.08, 1.0, d))
        # soft ground shadow under the berry
        qx = dx / 330.0
        qy = (y - 958.0) / 30.0
        q = qx * qx + qy * qy
        if q < 1.0:
            f = (1.0 - q) ** 1.5 * 0.20
            r = r + (SHADOW_RGB[0] - r) * f
            g = g + (SHADOW_RGB[1] - g) * f
            b = b + (SHADOW_RGB[2] - b) * f
        # berry body
        if in_body:
            ax = abs(x - CX)
            if ax <= hw + 1.5:
                if t < 0.45:
                    base = mix(RED_TOP, RED_MID, t / 0.45)
                else:
                    base = mix(RED_MID, RED_DEEP, (t - 0.45) / 0.55)
                u = (x - CX) / hw if hw > 0.0 else 0.0
                edge = u * u
                dark = 1.0 - 0.30 * edge ** 1.5
                if dark < 0.0:
                    dark = 0.0
                base = (base[0] * dark, base[1] * dark, base[2] * dark)
                # warm gloss on the upper-left shoulder
                gx = (x - 400.0) / 380.0
                gy = (y - 320.0) / 380.0
                glow = 1.0 - (gx * gx + gy * gy)
                if glow > 0.0:
                    base = mix(base, GLOSS_RGB, glow * 0.55)
                # achenes
                if seed is not None:
                    ys, x0, n = seed
                    k = int(round((x - x0) / 68.0))
                    if 0 <= k < n:
                        xs = x0 + k * 68.0
                        sdx = (x - xs) / 11.0
                        sdy = (y - ys) / 15.0
                        sd = math.sqrt(sdx * sdx + sdy * sdy)
                        if sd < 1.2:
                            cov = clamp01((1.15 - sd) / 0.30)
                            base = mix(base, SEED_RGB, cov)
                        else:
                            sdx2 = (x - xs) / 14.0
                            sdy2 = (y - ys - 4.0) / 18.0
                            sd2 = math.sqrt(sdx2 * sdx2 + sdy2 * sdy2)
                            if sd2 < 1.0:
                                base = mix(base, SEED_SHADE, 0.45 * (1.0 - sd2))
                # antialiased body edge
                cov = clamp01(0.5 + (hw - ax) / 2.0)
                r = base[0] * cov + r * (1.0 - cov)
                g = base[1] * cov + g * (1.0 - cov)
                b = base[2] * cov + b * (1.0 - cov)
        # stem rising behind the calyx
        if in_stem:
            scx = 512.0 + (y - 222.0) * 0.05
            if abs(x - scx) <= 7.0:
                f = clamp01((222.0 - y) / 126.0)
                r, g, b = mix((70.0, 60.0, 34.0), (126.0, 108.0, 62.0), f)
        # calyx leaves on top
        if in_leaf:
            dxl = x - LEAF_BASE_PT[0]
            dyl = y - LEAF_BASE_PT[1]
            for sa, ca, length, half_w in LEAF_TRIG:
                s = dxl * sa - dyl * ca
                if 0.0 < s < length:
                    w = dxl * ca + dyl * sa
                    prof = leaf_profile(s, length, half_w)
                    aw = abs(w)
                    if aw < prof + 1.5:
                        leaf = mix(LEAF_BASE, LEAF_TIP, smoothstep(0.0, 0.75, s / length))
                        if aw < 3.0 and 8.0 < s < length - 12.0:
                            leaf = mix(leaf, LEAF_VEIN, 0.75)
                        ratio = aw / prof if prof > 0.0 else 0.0
                        if ratio > 1.0:
                            ratio = 1.0
                        leaf = tuple(c * (1.0 - 0.18 * ratio * ratio) for c in leaf)
                        cov = clamp01((prof - aw) / 2.0 + 0.5)
                        r = leaf[0] * cov + r * (1.0 - cov)
                        g = leaf[1] * cov + g * (1.0 - cov)
                        b = leaf[2] * cov + b * (1.0 - cov)
                        break
        out.append(max(0, min(255, int(r))))
        out.append(max(0, min(255, int(g))))
        out.append(max(0, min(255, int(b))))
    return out


def render_png():
    raw = bytearray()
    for y in range(SIZE):
        raw.append(0)  # filter: none
        raw.extend(render_row(y))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def main():
    png = render_png()
    parent = os.path.dirname(OUTPUT)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(OUTPUT, "wb") as f:
        f.write(png)
    print(f"wrote {OUTPUT}: {len(png)} bytes")


if __name__ == "__main__":
    main()
