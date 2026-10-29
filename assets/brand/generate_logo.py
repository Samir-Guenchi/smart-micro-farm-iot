"""Generate the GreenLoop Farm logo SVGs.

The mark is an open brush loop (an enso) whose tail turns into a leaf, with a
seed-like dot inside. The wordmark is hand-lettered monoline. Small, seeded,
low-frequency wobble is applied so the strokes feel drawn, not typeset.
"""
import math, random, sys, os

random.seed(7)
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
SEED = tuple(float(v) for v in os.environ.get("SEED", "54,63.5,5.6").split(","))

PALETTES = {
    "light": dict(ink="#2E5634", leaf="#4C8A3F", seed="#D9772B", text="#2E5634", sub="#6B7F5E"),
    "dark": dict(ink="#A9CF8E", leaf="#7DBA62", seed="#F0A35E", text="#E9E4D4", sub="#A9B59A"),
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


# ---------------------------------------------------------------- mark

def mark_paths():
    cx, cy = 54, 64
    th0, th1 = math.radians(18), math.radians(318)
    N = 220
    wn = wobble(3, 0.9)
    rn = wobble(2, 1.1)
    center, widths = [], []
    for i in range(N + 1):
        t = i / N
        th = th0 + (th1 - th0) * t
        r = 33 + 3.5 * t ** 1.6 + rn(t)
        center.append((cx + r * math.cos(th), cy + r * math.sin(th)))
        # brush pressure: quick attack, heavy through the bottom-left, lifts into the stem
        attack = min(1, t / 0.22) ** 0.9
        body = 7.6 - 3.6 * max(0, t - 0.55) / 0.45 - 1.2 * abs(t - 0.42)
        widths.append(max(0.6, attack * body + wn(t) * 0.5))
    left, right = [], []
    for i, (x, y) in enumerate(center):
        a = center[max(0, i - 1)]
        b = center[min(N, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        nx, ny = -dy / L, dx / L
        w = widths[i] / 2
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    loop = poly_path(left + right[::-1], closed=True)

    # leaf grows from the end of the stroke, kicked outward a little
    ex, ey = center[-1]
    px, py = center[-4]
    ang = math.atan2(ey - py, ex - px) + math.radians(-8)
    ux, uy = math.cos(ang), math.sin(ang)
    vx, vy = -uy, ux
    Lf, Wf, bend = 31, 15, 3.5
    M = 60
    side_a, side_b, rib = [], [], []
    for i in range(M + 1):
        s = i / M
        ax = s * Lf
        off = bend * math.sin(math.pi * s) * 0.9
        h = (Wf / 2) * math.sin(math.pi * s ** 0.9) ** 1.05
        bx, by = ex + ux * (ax - 2.5) + vx * off, ey + uy * (ax - 2.5) + vy * off
        side_a.append((bx + vx * h * 1.08, by + vy * h * 1.08))
        side_b.append((bx - vx * h * 0.92, by - vy * h * 0.92))
        if 0.1 <= s <= 0.78:
            rib.append((bx, by))
    leaf = poly_path(side_a + side_b[::-1], closed=True)
    ribd = poly_path(rib)

    # seed: a slightly lopsided dot
    sx, sy, sr = SEED
    sn = wobble(2, 0.45)
    seed = [(sx + (sr + sn(k / 40)) * math.cos(2 * math.pi * k / 40) * 0.96,
             sy + (sr + sn(k / 40)) * math.sin(2 * math.pi * k / 40)) for k in range(40)]
    seedd = poly_path(seed, closed=True)
    return loop, leaf, ribd, seedd


def mark_group(p, ox=0, oy=0, scale=1, mid="leafrib"):
    loop, leaf, rib, seed = MARK
    return (f'<g transform="translate({f(ox)} {f(oy)}) scale({scale})">'
            f'<defs><mask id="{mid}" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">'
            f'<rect width="120" height="120" fill="#fff"/>'
            f'<path d="{rib}" fill="none" stroke="#000" stroke-width="1.7" stroke-linecap="round"/></mask></defs>'
            f'<path d="{loop}" fill="{p["ink"]}"/>'
            f'<path d="{leaf}" fill="{p["leaf"]}" mask="url(#{mid})"/>'
            f'<path d="{seed}" fill="{p["seed"]}"/></g>')


# ---------------------------------------------------------------- lettering

def arc(cx, cy, rx, ry, a0, a1, step=4):
    n = max(2, int(abs(a1 - a0) / step))
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def line(*pts, step=2.0):
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n + (0 if out or False else 0))]
    out.append(pts[-1])
    return out


LOWER = {
    "g": (31, [arc(14, -14, 12.5, 14, -20, 345), line((26.5, -27), (26.5, 5)) + arc(14.5, 5, 12, 11, 0, 150)[1:]]),
    "r": (22, [line((4, -28), (4, 0)), arc(17, -15, 13, 13, 183, 282)]),
    "e": (29, [line((2.5, -14.5), (27, -14.5)) + arc(14.5, -14, 12.5, 14, -2, -318)[1:]]),
    "n": (31, [line((4, -28), (4, 0)), arc(15.2, -15, 11.2, 12.5, 182, 360) + line((26.4, -15), (26.4, 0))[1:]]),
    "l": (15, [line((4, -46), (4, -7)) + arc(11, -7, 7, 7, 180, 95)[1:]]),
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


def letter_strokes(table, text, x0, y0, gap, size=1.0, jitter=0.35, tilt=1.2):
    strokes = []
    x = x0
    for ch in text:
        adv, sts = table[ch]
        rot = math.radians(random.uniform(-tilt, tilt))
        dy = random.uniform(-0.5, 0.5) * size
        for st in sts:
            wn = wobble(2, jitter)
            pts = []
            n = len(st)
            for i, (px, py) in enumerate(st):
                s = i / max(1, n - 1)
                a, b = st[max(0, i - 1)], st[min(n - 1, i + 1)]
                dx, dyy = b[0] - a[0], b[1] - a[1]
                L = math.hypot(dx, dyy) or 1
                nx, ny = -dyy / L, dx / L
                w = wn(s)
                qx, qy = px + nx * w, py + ny * w
                qx, qy = qx * math.cos(rot) - qy * math.sin(rot), qx * math.sin(rot) + qy * math.cos(rot)
                pts.append((x + qx * size, y0 + dy + qy * size))
            strokes.append(pts)
        x += (adv + gap) * size
    return strokes, x


def strokes_path(strokes):
    return " ".join(poly_path(s) for s in strokes)


# ---------------------------------------------------------------- compose

MARK = mark_paths()
WORD, wend = letter_strokes(LOWER, "greenloop", 0, 0, 5.5, jitter=0.45, tilt=1.8)
FARM, fend = letter_strokes(CAPS, "FARM", 0, 0, 7.5, jitter=0.18, tilt=0.8)


def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(w)} {f(h)}" width="{f(w)}" height="{f(h)}" '
            f'role="img" aria-label="{title}"><title>{title}</title>{body}</svg>\n')


def lockup(p):
    # mark at left, wordmark to the right, "FARM" set small under it
    wx, wy = 130, 74
    body = mark_group(p, 0, 0, 1.0)
    body += (f'<g transform="translate({wx} {wy})" fill="none" stroke="{p["text"]}" stroke-width="5.4" '
             f'stroke-linecap="round" stroke-linejoin="round"><path d="{strokes_path(WORD)}"/></g>')
    fx = wx + 2
    body += (f'<g transform="translate({fx} {wy + 36})" fill="none" stroke="{p["seed"]}" stroke-width="2.6" '
             f'stroke-linecap="round" stroke-linejoin="round"><path d="{strokes_path(FARM)}"/></g>')
    # a short hand-drawn rule running from FARM to the end of the word
    rx0 = fx + fend + 6
    rule = line((rx0, 0), (wx + wend - 8, 0), step=3)
    rn = wobble(2, 0.6)
    rule = [(x, wy + 29 + rn(i / len(rule))) for i, (x, _) in enumerate(rule)]
    body += (f'<path d="{poly_path(rule)}" fill="none" stroke="{p["sub"]}" stroke-width="1.6" '
             f'stroke-linecap="round"/>')
    return svg(wx + wend + 4, 128, body, "GreenLoop Farm")


def mark_only(p):
    return svg(120, 120, mark_group(p), "GreenLoop Farm")


os.makedirs(OUT, exist_ok=True)
for name, p in PALETTES.items():
    open(os.path.join(OUT, f"greenloop-logo-{name}.svg"), "w").write(lockup(p))
    open(os.path.join(OUT, f"greenloop-mark-{name}.svg"), "w").write(mark_only(p))
print("ok")
