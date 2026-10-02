"""Prototype de faisabilite : extraction de la geometrie d'un plan PDF vectoriel
et separation hachures / traits de mur.

Sortie : un SVG par couche pour verification visuelle.
"""
from __future__ import annotations

import math
import sys
from collections import Counter

from pypdf import PdfReader


def mat_mul(a, b):
    a0, a1, a2, a3, a4, a5 = a
    b0, b1, b2, b3, b4, b5 = b
    return (
        a0 * b0 + a1 * b2,
        a0 * b1 + a1 * b3,
        a2 * b0 + a3 * b2,
        a2 * b1 + a3 * b3,
        a4 * b0 + a5 * b2 + b4,
        a4 * b1 + a5 * b3 + b5,
    )


def apply(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def parse(path):
    reader = PdfReader(path)
    page = reader.pages[0]
    data = page.get_contents().get_data().decode("latin-1")
    toks = data.split()

    ctm = (1, 0, 0, 1, 0, 0)
    stack = []
    width = 1.0
    color = (0.0, 0.0, 0.0)
    cx = cy = sxp = syp = 0.0
    path_segs = []
    out = []

    def num(t):
        try:
            return float(t)
        except ValueError:
            return 0.0

    i = 0
    n = len(toks)
    while i < n:
        t = toks[i]
        if t == "q":
            stack.append((ctm, width, color))
        elif t == "Q":
            if stack:
                ctm, width, color = stack.pop()
        elif t == "cm" and i >= 6:
            m = tuple(num(toks[i - k]) for k in (6, 5, 4, 3, 2, 1))
            ctm = mat_mul(m, ctm)
        elif t == "w" and i >= 1:
            width = num(toks[i - 1])
        elif t == "RG" and i >= 3:
            color = tuple(num(toks[i - k]) for k in (3, 2, 1))
        elif t in ("G", "g") and i >= 1:
            v = num(toks[i - 1])
            color = (v, v, v)
        elif t == "m" and i >= 2:
            cx, cy = num(toks[i - 2]), num(toks[i - 1])
            sxp, syp = cx, cy
        elif t == "l" and i >= 2:
            nx, ny = num(toks[i - 2]), num(toks[i - 1])
            path_segs.append((cx, cy, nx, ny))
            cx, cy = nx, ny
        elif t == "h":
            path_segs.append((cx, cy, sxp, syp))
            cx, cy = sxp, syp
        elif t == "re" and i >= 4:
            x, y, w, h = (num(toks[i - k]) for k in (4, 3, 2, 1))
            path_segs.extend(
                [(x, y, x + w, y), (x + w, y, x + w, y + h), (x + w, y + h, x, y + h), (x, y + h, x, y)]
            )
        elif t in ("S", "s", "f", "F", "f*", "B", "B*", "b", "b*", "n"):
            # echelle du CTM pour convertir la largeur de trait en points page
            scale = math.sqrt(abs(ctm[0] * ctm[3] - ctm[1] * ctm[2])) or 1.0
            wpt = width * scale
            for (x1, y1, x2, y2) in path_segs:
                ax, ay = apply(ctm, x1, y1)
                bx, by = apply(ctm, x2, y2)
                out.append((ax, ay, bx, by, wpt, color, t))
            path_segs = []
        i += 1
    return out, float(page.mediabox.width), float(page.mediabox.height)


def orient(seg):
    dx, dy = seg[2] - seg[0], seg[3] - seg[1]
    return math.degrees(math.atan2(dy, dx)) % 180.0


def length(seg):
    return math.hypot(seg[2] - seg[0], seg[3] - seg[1])


def svg(segs, w, h, path, color="#000", swidth=None):
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}">',
        f'<rect width="{w:.0f}" height="{h:.0f}" fill="#fff"/>',
        f'<g stroke="{color}" fill="none" stroke-linecap="round">',
    ]
    for s in segs:
        sw = swidth if swidth is not None else max(s[4], 0.3)
        lines.append(
            f'<line x1="{s[0]:.1f}" y1="{h - s[1]:.1f}" x2="{s[2]:.1f}" y2="{h - s[3]:.1f}" stroke-width="{sw:.2f}"/>'
        )
    lines.append("</g></svg>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main(pdf, outdir):
    segs, w, h = parse(pdf)
    print(f"segments transformes : {len(segs)}")
    wcount = Counter(round(s[4], 2) for s in segs)
    print("largeurs page (pt) :", wcount.most_common(8))

    xs = [v for s in segs for v in (s[0], s[2])]
    ys = [v for s in segs for v in (s[1], s[3])]
    print(f"bbox page : {min(xs):.0f},{min(ys):.0f} -> {max(xs):.0f},{max(ys):.0f}")

    hatch = [s for s in segs if 30 < orient(s) < 60 or 120 < orient(s) < 150]
    ortho = [s for s in segs if orient(s) < 3 or orient(s) > 177 or 87 < orient(s) < 93]
    print(f"hachures 45/135 : {len(hatch)}  |  orthogonaux : {len(ortho)}")

    hlen = sorted(length(s) for s in hatch)
    if hlen:
        print(f"longueur hachures pt : p50={hlen[len(hlen)//2]:.2f} p90={hlen[int(len(hlen)*.9)]:.2f}")

    epais = [s for s in ortho if s[4] >= 0.6 and length(s) >= 3]
    print(f"orthogonaux epais et longs (candidats faces de mur) : {len(epais)}")

    import pickle
    with open(f"{outdir}/segs.pkl", "wb") as fh:
        pickle.dump((segs, w, h), fh)
    png(segs, w, h, f"{outdir}/00_tout.png")
    png(hatch, w, h, f"{outdir}/01_hachures.png", color=(200, 0, 0))
    png(epais, w, h, f"{outdir}/02_candidats_murs.png", color=(0, 80, 200))
    print("PNG ecrits dans", outdir)


def png(segs, w, h, path, color=(0, 0, 0), k=1.5):
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (int(w * k), int(h * k)), "white")
    d = ImageDraw.Draw(img)
    for s in segs:
        d.line(
            [(s[0] * k, (h - s[1]) * k), (s[2] * k, (h - s[3]) * k)],
            fill=color,
            width=max(1, int(round(s[4] * k))),
        )
    img.save(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
