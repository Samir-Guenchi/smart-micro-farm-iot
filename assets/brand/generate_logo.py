"""Generate the GreenLoop Farm logo SVGs.

The idea: the "l" of greenloop is written as one cursive pen stroke, and the
loop of that "l" is a leaf. It grows out of a seed, rises as a hairline,
turns at a sharp tip, comes down heavy and crosses itself, so the same shape
reads as the letter, a leaf and a closed loop. The rest of the word is
hand-lettered monoline. The leaf-l on its own is the symbol.

Small, seeded, low-frequency wobble keeps every stroke looking drawn.

    python3 generate_logo.py [out_dir]
"""
import math, random, sys, os

random.seed(11)
OUT = sys.argv[1] if len(sys.argv) > 1 else "."

PALETTES = {
    "light": dict(ink="#24452B", leaf="#5E9B45", seed="#D9772B", text="#24452B", sub="#7A8B6C"),
    "dark": dict(ink="#B9D99F", leaf="#6FAE55", seed="#F0A35E", text="#ECE7D8", sub="#A9B59A"),
}


def f(v):
    s = f"{v:.1f}"
    return "0" if s in ("0.0", "-0.0") else s.rstrip("0").rstrip(".")


def wobble(n_terms=2, amp=1.0):
    terms = [(random.uniform(0.6, 1.8), random.uniform(0, 2 * math.pi), random.uniform(0.4, 1)) for _ in range(n_terms)]
    tot = sum(t[2] for t in terms)
    return lambda s: amp * sum(a * math.sin(2 * math.pi * fr * s + ph) for fr, ph, a in terms) / tot


def poly_path(pts, closed=False):
    d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts)
    return d + ("Z" if closed else "")


def bez(p0, p1, p2, p3, n=60):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def seg_hit(a, b, c, d):
    r = (b[0] - a[0], b[1] - a[1])
    s = (d[0] - c[0], d[1] - c[1])
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-9:
        return None
    t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / den
    u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
    return (t, u) if 0 <= t <= 1 and 0 <= u <= 1 else None


# ---------------------------------------------------------------- the leaf-l

def leaf_l(hair=2.0, swell=7.0):
    """Leaf-l in a box where the tip sits at y=0 and the baseline at y=100."""
    S = (6, 96)        # seed / pen down
    T = (52, 0)        # leaf tip
    B = (44, 100)      # bottom of the downstroke
    E = (74, 86)       # exit flick
    up = bez(S, (40, 104), (78, 44), T, 90)
    down = bez(T, (22, 34), (22, 86), B, 90)[1:]
    out = bez(B, (52, 106), (64, 98), E, 30)[1:]
    line = up + down + out
    n_up = len(up)

    # find where the downstroke crosses the upstroke: that closes the leaf
    cross = None
    for j in range(n_up, len(line) - 1):
        for i in range(n_up - 1):
            h = seg_hit(line[i], line[i + 1], line[j], line[j + 1])
            if h:
                cross = (i, j, h)
        if cross:
            break
    i, j, (t, _) = cross
    cp = (line[i][0] + (line[i + 1][0] - line[i][0]) * t, line[i][1] + (line[i + 1][1] - line[i][1]) * t)
    leaf = [cp] + line[i + 1:j + 1]

    # pointed-pen contrast: hairline going up, swelling on the way down
    N = len(line)
    wn = wobble(3, 0.5)
    left, right = [], []
    for k, (x, y) in enumerate(line):
        a, b = line[max(0, k - 1)], line[min(N - 1, k + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        down_amt = max(0.0, dy / L)
        s = k / (N - 1)
        w = hair + swell * down_amt ** 1.3 + wn(s)
        if k >= n_up + 60:  # ease off the pressure into the exit
            w = hair + (w - hair) * max(0, 1 - (k - n_up - 60) / 35)
        tip = math.hypot(x - T[0], y - T[1])
        w = max(1.2, w * min(1.0, 0.12 + tip / 26))
        w *= min(1.0, 0.35 + (N - 1 - k) / 14)  # lift the pen at the end
        nx, ny = -dy / L, dx / L
        left.append((x + nx * w / 2, y + ny * w / 2))
        right.append((x - nx * w / 2, y - ny * w / 2))
    stroke = left + right[::-1]

    # midrib from just above the crossing toward the tip
    rib = [(cp[0] + (T[0] - cp[0]) * u + 3.2 * math.sin(math.pi * u), cp[1] + (T[1] - cp[1]) * u)
           for u in [0.1 + 0.62 * k / 30 for k in range(31)]]

    sn = wobble(2, 0.5)
    sr = 6.4
    seed = [(S[0] - 1.5 + (sr + sn(k / 40)) * math.cos(2 * math.pi * k / 40),
             S[1] + 1 + (sr + sn(k / 40)) * math.sin(2 * math.pi * k / 40) * 0.92) for k in range(40)]
    return dict(stroke=stroke, leaf=leaf, rib=rib, seed=seed, width=E[0] + 4)


LEAF_L = leaf_l()
random.seed(11)
LEAF_L_WORD = leaf_l(hair=4.4, swell=8.5)


def leaf_l_svg(p, tx, ty, sc, mid, shape=None):
    """The leaf-l placed with its tip at (tx, ty) and scaled by sc (100 units tall)."""
    LEAF_L = shape or globals()["LEAF_L"]

    def tr(pts):
        return [(tx + x * sc, ty + y * sc) for x, y in pts]
    rib = poly_path(tr(LEAF_L["rib"]))
    return (f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="-1000" y="-1000" width="3000" height="3000">'
            f'<rect x="-1000" y="-1000" width="3000" height="3000" fill="#fff"/>'
            f'<path d="{rib}" fill="none" stroke="#000" stroke-width="{f(2.4 * sc)}" stroke-linecap="round"/></mask>'
            f'<path d="{poly_path(tr(LEAF_L["leaf"]), True)}" fill="{p["leaf"]}" mask="url(#{mid})"/>'
            f'<path d="{poly_path(tr(LEAF_L["stroke"]), True)}" fill="{p["ink"]}"/>'
            f'<path d="{poly_path(tr(LEAF_L["seed"]), True)}" fill="{p["seed"]}"/>')


# ---------------------------------------------------------------- lettering

def arc(cx, cy, rx, ry, a0, a1, step=4):
    n = max(2, int(abs(a1 - a0) / step))
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def line(*pts, step=2.0):
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n)]
    out.append(pts[-1])
    return out


LOWER = {
    "g": (31, [arc(14, -14, 12.5, 14, -20, 345), line((26.5, -27), (26.5, 5)) + arc(14.5, 5, 12, 11, 0, 150)[1:]]),
    "r": (22, [line((4, -28), (4, 0)), arc(17, -15, 13, 13, 183, 282)]),
    "e": (29, [line((2.5, -14.5), (27, -14.5)) + arc(14.5, -14, 12.5, 14, -2, -318)[1:]]),
    "n": (31, [line((4, -28), (4, 0)), arc(15.2, -15, 11.2, 12.5, 182, 360) + line((26.4, -15), (26.4, 0))[1:]]),
    "o": (30, [arc(14.5, -14, 13, 14.5, -100, 268)]),
    "p": (31, [line((4, -28), (4, 17)), arc(16.5, -14, 12, 14, 175, 545)]),
}

CAPS = {
    "F": (10, [line((0, 0), (0, -14)), line((0, -14), (9, -14)), line((0, -7.5), (7, -7.5))]),
    "A": (12, [line((0, 0), (6, -14), (12, 0)), line((2.5, -5), (9.5, -5))]),
    "R": (11, [line((0, 0), (0, -14), (5, -14)) + arc(5, -10.6, 4, 3.4, -90, 90)[1:] + line((5, -7.2), (0, -7.2))[1:],
               line((4.5, -7.2), (10.5, 0))]),
    "M": (14, [line((0, 0), (0, -14), (7, -4), (14, -14), (14, 0))]),
}


def letter_strokes(table, text, x0, y0, gap, jitter=0.35, tilt=1.2):
    strokes, x = [], x0
    for ch in text:
        adv, sts = table[ch]
        rot = math.radians(random.uniform(-tilt, tilt))
        dy = random.uniform(-0.5, 0.5)
        for st in sts:
            wn = wobble(2, jitter)
            pts, n = [], len(st)
            for i, (px, py) in enumerate(st):
                a, b = st[max(0, i - 1)], st[min(n - 1, i + 1)]
                L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
                nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
                w = wn(i / max(1, n - 1))
                qx, qy = px + nx * w, py + ny * w
                qx, qy = qx * math.cos(rot) - qy * math.sin(rot), qx * math.sin(rot) + qy * math.cos(rot)
                pts.append((x + qx, y0 + dy + qy))
            strokes.append(pts)
        x += adv + gap
    return strokes, x


def strokes_path(strokes):
    return " ".join(poly_path(s) for s in strokes)


# ---------------------------------------------------------------- compose

def svg(x, y, w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{f(x)} {f(y)} {f(w)} {f(h)}" width="{f(w)}" height="{f(h)}" '
            f'role="img" aria-label="{title}"><title>{title}</title>{body}</svg>\n')


GAP = 5.5
GREEN, gx = letter_strokes(LOWER, "green", 0, 0, GAP, jitter=0.45, tilt=1.8)
L_SC = 0.56                      # leaf-l is 100 units tall -> 52 in word units
L_X = gx - 1                     # where the leaf-l box starts
OOP, ox = letter_strokes(LOWER, "oop", L_X + LEAF_L["width"] * L_SC - 4, 0, GAP, jitter=0.45, tilt=1.8)
FARM, fx = letter_strokes(CAPS, "FARM", 0, 0, 7.5, jitter=0.18, tilt=0.8)


def wordmark(p, mid):
    body = (f'<g fill="none" stroke="{p["text"]}" stroke-width="5.4" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="{strokes_path(GREEN)}"/><path d="{strokes_path(OOP)}"/></g>')
    body += leaf_l_svg(p, L_X, -56, L_SC, mid, LEAF_L_WORD)
    return body


def lockup(p):
    body = wordmark(p, "rib-lockup")
    fy = 40
    body += (f'<g transform="translate({f(ox - GAP - fx + 7.5)} {fy})" fill="none" stroke="{p["seed"]}" stroke-width="2.6" '
             f'stroke-linecap="round" stroke-linejoin="round"><path d="{strokes_path(FARM)}"/></g>')
    rule = line((2, 0), (ox - GAP - fx - 4, 0), step=3)
    rn = wobble(2, 0.6)
    rule = [(x, fy - 7 + rn(i / len(rule))) for i, (x, _) in enumerate(rule)]
    body += f'<path d="{poly_path(rule)}" fill="none" stroke="{p["sub"]}" stroke-width="1.6" stroke-linecap="round"/>'
    return svg(-8, -60, ox - GAP + 14, 108, body, "GreenLoop Farm")


def mark_only(p):
    w = LEAF_L["width"]
    pad = 12
    body = leaf_l_svg(p, (110 - w) / 2 + 2, 6, 1.0, "rib-mark")
    return svg(0, 0, 110, 110 + pad - 12, body, "GreenLoop Farm")


os.makedirs(OUT, exist_ok=True)
for name, p in PALETTES.items():
    open(os.path.join(OUT, f"greenloop-logo-{name}.svg"), "w").write(lockup(p))
    open(os.path.join(OUT, f"greenloop-mark-{name}.svg"), "w").write(mark_only(p))
print("ok")
