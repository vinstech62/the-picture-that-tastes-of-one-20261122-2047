#!/usr/bin/env python3
"""Procedural strawberry hero image — one single glossy ripe strawberry.

Python 3.13, standard library only. Encodes the PNG by hand (zlib + struct).
Writes /output/entry.png (1024x1024, <= 1 MiB) by default; honour
ENTRY_OUTPUT env override for local testing. Fully deterministic: fixed
seed, no timestamps, no time-based randomness.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- helpers

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(a, b, x):
    if x <= a:
        return 0.0
    if x >= b:
        return 1.0
    t = (x - a) / (b - a)
    return t * t * (3.0 - 2.0 * t)


def hash2(ix, iy):
    """Deterministic smooth-ish pseudo random in [0, 1) from integer cell."""
    h = (ix * 374761393 + iy * 668265263) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    h = (h ^ (h >> 16)) & 0xFFFFFFFF
    return h / 4294967296.0


def vnoise(x, y):
    """Low-frequency value noise, smooth, deterministic. Returns ~[-1, 1]."""
    cx = math.floor(x / 24.0)
    cy = math.floor(y / 24.0)
    fx = x / 24.0 - cx
    fy = y / 24.0 - cy
    sx = fx * fx * (3.0 - 2.0 * fx)
    sy = fy * fy * (3.0 - 2.0 * fy)
    a = hash2(cx, cy)
    b = hash2(cx + 1, cy)
    c = hash2(cx, cy + 1)
    d = hash2(cx + 1, cy + 1)
    top = a + (b - a) * sx
    bot = c + (d - c) * sx
    return (top + (bot - top) * sy) * 2.0 - 1.0


# ---------------------------------------------------------------- geometry
# Strawberry body: teardrop centred at (512, 540).
# v in [-1, 1] maps y 240..840; u in [-1, 1] maps x 202..822 at full width.
# Width narrows toward the bottom tip via f(v).

CX = 512.0
CY = 540.0
RY = 300.0
RX = 310.0


def body_e(x, y):
    """Elliptical body test value; < 1 means inside the berry."""
    v = (y - CY) / RY
    u = (x - CX) / RX
    f = 1.0 - 0.72 * smoothstep(0.05, 1.0, v)
    uu = u / f
    vv = (v + 0.08) / 1.02
    return uu * uu + vv * vv, v, u, f


def half_width_at(y):
    """Half width of the body at row y (0 if outside vertical range)."""
    v = (y - CY) / RY
    if v < -1.10 or v > 1.02:
        return 0.0
    f = 1.0 - 0.72 * smoothstep(0.05, 1.0, v)
    vv = (v + 0.08) / 1.02
    inside = 1.0 - vv * vv
    if inside <= 0.0:
        return 0.0
    return RX * f * math.sqrt(inside)


# ---------------------------------------------------------------- leaves
# Five pointed calyx leaves fanning from the top centre (512, 318).
# Each leaf is a rotated ellipse (pointed by tapering the far end).

LEAVES = []
for _i in range(5):
    ang = math.radians(-135 + _i * 22.5)  # fan upward-outward across the top
    # leaf centre offset from crown, length, width, green shade
    LEAVES.append((ang, 165.0, 34.0, _i))


def leaf_hit(x, y):
    """Return leaf green shade (0..1, 0 = not a leaf) for pixel (x, y)."""
    dx = x - CX
    dy = y - 318.0
    best = 0.0
    for ang, length, width, idx in LEAVES:
        ca = math.cos(ang)
        sa = math.sin(ang)
        # rotate point into leaf frame: leaf extends along +x in its frame
        lx = dx * ca + dy * sa
        ly = -dx * sa + dy * ca
        if lx < -18.0 or lx > length:
            continue
        # pointed leaf: width tapers to a point at the tip
        taper = 1.0 - smoothstep(length * 0.55, length, lx)
        halfw = width * (0.35 + 0.65 * taper) * math.sqrt(
            max(0.0, 1.0 - ((lx - length * 0.42) / (length * 0.62)) ** 2)
        )
        if abs(ly) < halfw:
            # soft edge + centre vein highlight
            edge = 1.0 - smoothstep(halfw * 0.55, halfw, abs(ly))
            shade = 0.55 + 0.45 * edge
            if idx == 2:
                shade *= 1.08
            if shade > best:
                best = shade
    return best


# ---------------------------------------------------------------- seeds
# Achenes: rows down the body, positions follow the body curvature.

SEEDS = []
_t = 0.0
_row = 0
while _t <= 1.0:
    y = 330.0 + _t * 470.0
    hw = half_width_at(y)
    if hw > 40.0:
        n = int(hw / 52.0)
        offset = 0.5 if (_row % 2 == 0) else 0.0
        for k in range(-n, n + 1):
            s = (k + offset) / max(1, n)
            if abs(s) > 0.86:
                continue
            sx = CX + s * hw * 0.97
            # slight tilt following the body slope
            tilt = s * 0.45
            SEEDS.append((sx, y, tilt))
    _t += 0.092
    _row += 1


def draw_seed(buf, sx, sy, tilt):
    """Draw one achene (dark pit + pale seed) into the RGB bytearray."""
    ca = math.cos(tilt)
    sa = math.sin(tilt)
    for oy in range(-13, 14):
        yy = int(sy) + oy
        if yy < 0 or yy >= H:
            continue
        for ox in range(-11, 12):
            xx = int(sx) + ox
            if xx < 0 or xx >= W:
                continue
            # rotate into seed frame
            rx = ox * ca + oy * sa
            ry = -ox * sa + oy * ca
            # pit: dark red ellipse, slightly larger, offset down 2px
            px = rx
            py = ry - 2.0
            pit = (px / 9.5) ** 2 + (py / 12.5) ** 2
            seed = (rx / 6.0) ** 2 + (ry / 9.0) ** 2
            idx = (yy * W + xx) * 3
            if pit < 1.0 and seed >= 1.0:
                a = 0.55 * (1.0 - smoothstep(0.55, 1.0, pit))
                buf[idx] = int(lerp(buf[idx], 122, a))
                buf[idx + 1] = int(lerp(buf[idx + 1], 18, a))
                buf[idx + 2] = int(lerp(buf[idx + 2], 30, a))
            if seed < 1.0:
                a = 1.0 - smoothstep(0.45, 1.0, seed)
                # pale golden seed, lighter toward its top-left
                g = 232 + int(18 * (1.0 - max(0.0, ry / 9.0)))
                buf[idx] = int(lerp(buf[idx], 255, a))
                buf[idx + 1] = int(lerp(buf[idx + 1], g, a))
                buf[idx + 2] = int(lerp(buf[idx + 2], 150, a))


# ---------------------------------------------------------------- render

def render():
    buf = bytearray(W * H * 3)
    for y in range(H):
        row = y * W * 3
        # background: warm cream radial gradient, brighter upper-left
        for x in range(W):
            dx = (x - 430.0) / 720.0
            dy = (y - 380.0) / 720.0
            d = math.sqrt(dx * dx + dy * dy)
            t = clamp(d, 0.0, 1.0)
            r = lerp(255, 238, t)
            g = lerp(246, 214, t)
            b = lerp(232, 178, t)
            buf[row + x * 3] = int(r)
            buf[row + x * 3 + 1] = int(g)
            buf[row + x * 3 + 2] = int(b)

        # soft ground shadow under the berry
        if 780 <= y <= 960:
            for x in range(W):
                dx = (x - 512.0) / 330.0
                dy = (y - 872.0) / 62.0
                e = dx * dx + dy * dy
                if e < 1.0:
                    a = 0.20 * (1.0 - smoothstep(0.35, 1.0, e))
                    i = row + x * 3
                    buf[i] = int(lerp(buf[i], 176, a))
                    buf[i + 1] = int(lerp(buf[i + 1], 138, a))
                    buf[i + 2] = int(lerp(buf[i + 2], 102, a))

        # strawberry body
        hw = half_width_at(y)
        if hw > 0.0:
            x0 = max(0, int(CX - hw) - 2)
            x1 = min(W - 1, int(CX + hw) + 2)
            for x in range(x0, x1 + 1):
                e, v, u, f = body_e(x, y)
                if e >= 1.0:
                    continue
                i = row + x * 3
                # warm light from upper-left: brightness by position
                light = 1.0 - 0.22 * u - 0.10 * v
                # roundness: darken toward the rim
                rim = 1.0 - 0.38 * smoothstep(0.55, 1.0, e)
                # vertical shading: bright shoulders, deep red base
                vert = 1.0 - 0.16 * smoothstep(0.2, 1.0, v)
                # subtle skin variation, low frequency only (keeps PNG small)
                n = vnoise(x, y) * 0.045
                bright = clamp(light * rim * vert + n, 0.45, 1.25)
                # base red: vivid strawberry, slightly orange toward light
                r = clamp(226 * bright + 14, 0, 255)
                g = clamp(52 * bright + 6, 0, 255)
                b = clamp(66 * bright + 4, 0, 255)
                # glossy highlight, upper-left shoulder
                hx = (x - 405.0) / 165.0
                hy = (y - 420.0) / 120.0
                he = hx * hx + hy * hy
                if he < 1.0:
                    a = 0.42 * (1.0 - smoothstep(0.25, 1.0, he))
                    r = lerp(r, 255, a)
                    g = lerp(g, 205, a)
                    b = lerp(b, 205, a)
                # small bright specular spot
                sx = (x - 432.0) / 40.0
                sy = (y - 398.0) / 30.0
                se = sx * sx + sy * sy
                if se < 1.0:
                    a = 0.55 * (1.0 - smoothstep(0.2, 1.0, se))
                    r = lerp(r, 255, a)
                    g = lerp(g, 235, a)
                    b = lerp(b, 235, a)
                buf[i] = int(r)
                buf[i + 1] = int(g)
                buf[i + 2] = int(b)

        # calyx leaves over the top of the berry
        if 140 <= y <= 430:
            for x in range(300, 725):
                shade = leaf_hit(x, y)
                if shade > 0.0:
                    i = row + x * 3
                    a = clamp(shade, 0.0, 1.0) * 0.96
                    # green gradient: light centre, deep edge
                    gr = lerp(38, 96, shade)
                    gg = lerp(112, 168, shade)
                    gb = lerp(44, 66, shade)
                    buf[i] = int(lerp(buf[i], gr, a))
                    buf[i + 1] = int(lerp(buf[i + 1], gg, a))
                    buf[i + 2] = int(lerp(buf[i + 2], gb, a))

    # achenes on top of the body
    for sx, sy, tilt in SEEDS:
        draw_seed(buf, sx, sy, tilt)
    return buf


# ---------------------------------------------------------------- PNG encode

def chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def write_png(buf, path):
    raw = bytearray()
    for y in range(H):
        raw.append(2)  # filter: Up
        start = y * W * 3
        if y == 0:
            raw += buf[start:start + W * 3]
        else:
            prev = (y - 1) * W * 3
            for k in range(W * 3):
                raw.append((buf[start + k] - buf[prev + k]) & 0xFF)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png)


def main():
    out = os.environ.get("ENTRY_OUTPUT", "/output/entry.png")
    buf = render()
    size = write_png(buf, out)
    print(f"wrote {out} ({size} bytes)")


if __name__ == "__main__":
    main()
