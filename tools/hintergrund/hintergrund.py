"""Erzeugt drei Hintergrund-Varianten für die Stadtjagd als SVG und eine Vergleichsseite.

A  Wanderkarte fein     erzeugtes Gelände, Höhenlinien, Bäche, Wald, Gitter, Höhenpunkte
B  Prag-Stadtplan       OpenStreetMap-Daten (prag.json, relfull.json), Moldau, Straßen, Route
C  OL-Karte             erzeugtes Gelände in Orientierungslauf-Zeichensprache, Bahnaufdruck

Alle Formen liegen im Koordinatensystem viewBox 0 0 400 900 wie der bisherige Hintergrund.

Aufruf (aus dem Projektordner):
    python tools/hintergrund/hintergrund.py mockups/hintergrund
    python tools/hintergrund/vergleich.py mockups/hintergrund mockups/hintergrund-varianten.html

Braucht numpy, scipy und scikit-image. A und C sind mit festen Seeds erzeugt und
kommen bei jedem Lauf gleich heraus. B liest die OSM-Daten aus prag.json und
relfull.json neben diesem Skript; beide sind groß und stehen nicht im Repo.
Neu laden mit den Abfragen in osm-abfrage.txt und osm-flaechen.txt, etwa:
    curl -A "Stadtjagd-Hintergrund/1.0" --data-urlencode data@osm-abfrage.txt          https://overpass.private.coffee/api/interpreter -o prag.json
    curl -A "Stadtjagd-Hintergrund/1.0" --data-urlencode data@osm-flaechen.txt          https://overpass.private.coffee/api/interpreter -o relfull.json
overpass-api.de war am 18.09.2026 überlastet (504), der Ersatzserver lief.
"""
import json, math, os, sys
import numpy as np
from scipy import ndimage
from skimage import measure

W, H = 400, 900
HIER = os.path.dirname(os.path.abspath(__file__))
ZIEL = sys.argv[1] if len(sys.argv) > 1 else HIER

# ---------------------------------------------------------------- Pfad-Helfer
def rdp(pts, eps):
    """Douglas-Peucker, iterativ."""
    pts = np.asarray(pts, float)
    if len(pts) < 3:
        return pts
    keep = np.zeros(len(pts), bool); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        p, q = pts[a], pts[b]
        seg = pts[a + 1:b]
        d = q - p
        n = math.hypot(*d)
        if n == 0:
            dist = np.hypot(*(seg - p).T)
        else:
            dist = np.abs(d[0] * (seg[:, 1] - p[1]) - d[1] * (seg[:, 0] - p[0])) / n
        i = int(np.argmax(dist))
        if dist[i] > eps:
            k = a + 1 + i
            keep[k] = True
            stack += [(a, k), (k, b)]
    return pts[keep]

def num(v):
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    if s in ("-0",):
        s = "0"
    if s.startswith("0.") :
        s = s[1:]
    elif s.startswith("-0."):
        s = "-" + s[2:]
    return s

def glue(tokens):
    out = ""
    for t in tokens:
        if out and not t.startswith("-") and out[-1] not in "MmLlZzCc":
            out += " "
        out += t
    return out

def pfad(pts, eps=0.5, zu=False):
    """Punktliste -> relativer SVG-Pfad mit einer Nachkommastelle."""
    pts = rdp(pts, eps) if eps else np.asarray(pts, float)
    if len(pts) < 2:
        return ""
    r = np.round(np.asarray(pts, float), 1)
    tok = ["M", num(r[0][0]), num(r[0][1]), "l"]
    for (x0, y0), (x1, y1) in zip(r[:-1], r[1:]):
        dx, dy = round(x1 - x0, 1), round(y1 - y0, 1)
        if dx == 0 and dy == 0:
            continue
        tok += [num(dx), num(dy)]
    if zu:
        tok.append("z")
    return glue(tok)

def laenge(pts):
    p = np.asarray(pts, float)
    return float(np.sum(np.hypot(*np.diff(p, axis=0).T))) if len(p) > 1 else 0.0

def glatt(ctrl, schritte=10):
    """Catmull-Rom durch Kontrollpunkte -> dichte Punktliste."""
    c = [ctrl[0]] + list(ctrl) + [ctrl[-1]]
    out = []
    for i in range(1, len(c) - 2):
        p0, p1, p2, p3 = map(np.array, (c[i - 1], c[i], c[i + 1], c[i + 2]))
        for t in np.linspace(0, 1, schritte, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(np.array(c[-2]))
    return np.array(out)

# ---------------------------------------------------------------- Gelände
GS = 2.0  # Rasterweite in Karteneinheiten

def gelaende(seed, huegel, fluss=None, tal=45, rauh=(22, 7, 2.2)):
    rng = np.random.default_rng(seed)
    gh, gw = int(H / GS) + 1, int(W / GS) + 1
    ys, xs = np.mgrid[0:gh, 0:gw] * GS
    z = np.zeros((gh, gw))
    for cx, cy, sx, sy, h in huegel:
        z += h * np.exp(-(((xs - cx) / sx) ** 2 + ((ys - cy) / sy) ** 2) / 2)
    for sig, amp in zip((38, 14, 5), rauh):
        n = ndimage.gaussian_filter(rng.standard_normal((gh, gw)), sig)
        z += amp * n / n.std()
    if fluss is not None:
        m = np.ones((gh, gw), bool)
        for x, y in fluss:
            i, j = int(round(y / GS)), int(round(x / GS))
            if 0 <= i < gh and 0 <= j < gw:
                m[i, j] = False
        d = ndimage.distance_transform_edt(m) * GS
        z -= tal * np.exp(-(d / 38) ** 2) + 0.12 * tal * np.exp(-(d / 120) ** 2)
    return z

def hoehenlinien(z, schritt, eps=0.7, minlen=18):
    """-> Liste (ebene_index, punkte). Rand wird tief gepolstert, damit Linien geschlossen sind."""
    lo, hi = z.min(), z.max()
    ebenen = np.arange(math.ceil(lo / schritt) * schritt, hi, schritt)
    zp = np.pad(z, 1, mode="constant", constant_values=lo - 1000)
    out = []
    for lv in ebenen:
        for c in measure.find_contours(zp, lv):
            pts = np.column_stack(((c[:, 1] - 1) * GS, (c[:, 0] - 1) * GS))
            pts[:, 0] = np.clip(pts[:, 0], -4, W + 4)
            pts[:, 1] = np.clip(pts[:, 1], -4, H + 4)
            if laenge(pts) < minlen:
                continue
            out.append((int(round(lv / schritt)), pts))
    return out

def maske_umrisse(maske, eps=0.8, minlen=24, glaetten=1.5):
    m = ndimage.gaussian_filter(maske.astype(float), glaetten)
    mp = np.pad(m, 1, mode="constant", constant_values=0)
    out = []
    for c in measure.find_contours(mp, 0.5):
        pts = np.column_stack(((c[:, 1] - 1) * GS, (c[:, 0] - 1) * GS))
        pts[:, 0] = np.clip(pts[:, 0], -4, W + 4)
        pts[:, 1] = np.clip(pts[:, 1], -4, H + 4)
        if laenge(pts) >= minlen:
            out.append(pts)
    return out

def rauschen(seed, sig):
    rng = np.random.default_rng(seed)
    gh, gw = int(H / GS) + 1, int(W / GS) + 1
    n = ndimage.gaussian_filter(rng.standard_normal((gh, gw)), sig)
    return n / n.std()

def bach(z, start, ziel_maske, schritte=900):
    """Steilster Abstieg vom Quellpunkt bis ins Tal (Maske) oder an den Rand."""
    gz = ndimage.gaussian_filter(z, 2.5)
    gy, gx = np.gradient(gz)
    x, y = start
    pts = [(x, y)]
    for _ in range(schritte):
        i, j = int(y / GS), int(x / GS)
        if not (0 <= i < z.shape[0] and 0 <= j < z.shape[1]):
            break
        if ziel_maske[i, j]:
            break
        g = np.array([gx[i, j], gy[i, j]])
        n = np.hypot(*g)
        if n < 1e-6:
            break
        x -= 2.2 * g[0] / n
        y -= 2.2 * g[1] / n
        pts.append((x, y))
    return np.array(pts)

def lokale_gipfel(z, abstand=34, min_h=None):
    mx = ndimage.maximum_filter(z, size=abstand)
    kand = np.argwhere((z == mx) & (z > (min_h if min_h is not None else np.percentile(z, 85))))
    out = []
    for i, j in kand:
        x, y = j * GS, i * GS
        if 18 < x < W - 18 and 30 < y < H - 30:
            out.append((x, y, z[i, j]))
    return out

# ---------------------------------------------------------------- Variante A
def variante_a():
    fluss_ctrl = [(-20, 250), (60, 300), (150, 330), (205, 395), (215, 470), (180, 540), (205, 615), (280, 660), (330, 720), (400, 770), (430, 790)]
    fluss = glatt(fluss_ctrl, 14)
    z = gelaende(7, [(78, 150, 55, 45, 120), (330, 300, 60, 55, 110), (120, 620, 60, 50, 95),
                     (310, 800, 45, 40, 80), (330, 90, 50, 40, 70), (40, 470, 45, 70, 85),
                     (300, 520, 40, 40, 55), (60, 830, 50, 40, 60)], fluss=fluss)
    tal = np.zeros(z.shape, bool)
    for x, y in fluss:
        i, j = int(y / GS), int(x / GS)
        if 0 <= i < z.shape[0] and 0 <= j < z.shape[1]:
            tal[max(0, i - 2):i + 3, max(0, j - 2):j + 3] = True
    teile = []
    # Wald: Flecken aus Rauschen, nicht im Tal
    wald = (rauschen(21, 16) > 0.55) & (z > np.percentile(z, 30))
    wd = " ".join(pfad(p, 0.9, True) for p in maske_umrisse(wald))
    teile.append(f'<path class="wald" d="{wd}"/>')
    # Höhenlinien
    hl = hoehenlinien(z, 9, eps=0.75)
    c = " ".join(pfad(p, 0.75) for k, p in hl if k % 5)
    c5 = " ".join(pfad(p, 0.75) for k, p in hl if k % 5 == 0)
    teile.append(f'<path class="c" d="{c}"/><path class="c5" d="{c5}"/>')
    # Bäche
    quellen = [(40, 120), (120, 190), (300, 250), (380, 360), (110, 560), (160, 680), (60, 440), (330, 470), (260, 860), (350, 120)]
    bd = []
    for q in quellen:
        b = bach(z, q, tal)
        if laenge(b) > 30:
            bd.append(pfad(b, 0.6))
    teile.append(f'<path class="wl" d="{" ".join(bd)}"/>')
    teile.append(f'<path class="w" d="{pfad(fluss, 0.5)}"/>')
    # Wege
    wege = [
        [(-10, 697), (71, 653), (132, 578), (150, 496), (207, 443), (272, 402), (323, 327), (351, 249), (411, 205)],
        [(-12, 118), (71, 173), (146, 188), (200, 256), (271, 283), (345, 322)],
        [(150, 496), (95, 470), (40, 470), (-10, 430)],
        [(205, 615), (230, 700), (300, 800), (410, 860)],
        [(330, 90), (300, 150), (240, 200), (200, 256)],
    ]
    teile.append('<path class="t" d="' + " ".join(pfad(glatt(w, 8), 0.5) for w in wege[:2]) + '"/>')
    teile.append('<path class="t t2" d="' + " ".join(pfad(glatt(w, 8), 0.5) for w in wege[2:]) + '"/>')
    # Gitter mit Beschriftung am Rand
    g = " ".join(f"M{x} 0v900" for x in (100, 200, 300)) + " " + " ".join(f"M0 {y}h400" for y in range(100, 900, 100))
    teile.append(f'<path class="gitter" d="{g}"/>')
    lab = [f'<text class="gl" x="{x + 3}" y="12">{46 + x // 100}</text>' for x in (100, 200, 300)]
    lab += [f'<text class="gl" x="3" y="{y - 3}">{5553 - y // 100}</text>' for y in range(100, 900, 100)]
    teile.append("".join(lab))
    # Höhenpunkte
    hp = []
    for x, y, h in lokale_gipfel(z, 60)[:9]:
        hp.append(f'<path class="p" d="M{num(x)} {num(y - 4)}l3.5 6h-7z"/><text class="hz" x="{num(x + 6)}" y="{num(y + 3)}">{int(260 + h * 1.6)}</text>')
    teile.append("".join(hp))
    # Wegpunkte wie bisher
    teile.append('<path class="p" d="M330 293l7 12h-14z"/><path class="p" d="M120 612v14M115 617h10"/>'
                 '<path class="p" d="M209 457v-6l6-5 6 5v6z"/><circle class="p" cx="152" cy="330" r="6"/>'
                 '<circle class="pf" cx="152" cy="330" r="1.8"/><path class="p" d="M293 790h14M293 794h14M295 790v5M305 790v5"/>')
    # Nordpfeil und Maßstab
    teile.append('<g class="nord"><path d="M372 36l7 20-7-5-7 5z"/><text x="372" y="31">N</text></g>')
    teile.append('<g class="mass"><path d="M16 872h80M16 868v8M56 869v6M96 868v8"/><text x="16" y="864">0</text><text x="96" y="864">500 m</text></g>')
    return "".join(teile)

# ---------------------------------------------------------------- Variante C
def variante_c():
    fluss_ctrl = [(430, 140), (340, 190), (250, 175), (170, 230), (110, 330), (60, 420), (-20, 470)]
    fluss = glatt(fluss_ctrl, 14)
    z = gelaende(31, [(290, 380, 70, 55, 115), (120, 600, 70, 60, 105), (300, 700, 55, 50, 85),
                      (90, 110, 50, 40, 60), (330, 860, 60, 40, 70), (60, 790, 40, 50, 55),
                      (200, 470, 40, 30, 45)], fluss=fluss, tal=38, rauh=(20, 9, 3.2))
    tal = np.zeros(z.shape, bool)
    for x, y in fluss:
        i, j = int(y / GS), int(x / GS)
        if 0 <= i < z.shape[0] and 0 <= j < z.shape[1]:
            tal[max(0, i - 2):i + 3, max(0, j - 2):j + 3] = True
    teile = []
    # Freiflächen (gelb) und Dickicht (grün), Sumpf am Bach
    offen = rauschen(41, 13) > 0.85
    gruen = (rauschen(42, 9) > 0.7) & ~offen
    gruen2 = (rauschen(43, 6) > 1.25) & ~offen
    teile.append('<path class="ol-offen" d="' + " ".join(pfad(p, 0.9, True) for p in maske_umrisse(offen)) + '"/>')
    teile.append('<path class="ol-gruen" d="' + " ".join(pfad(p, 0.9, True) for p in maske_umrisse(gruen)) + '"/>')
    teile.append('<path class="ol-gruen2" d="' + " ".join(pfad(p, 0.9, True, ) for p in maske_umrisse(gruen2, minlen=14)) + '"/>')
    d = ndimage.distance_transform_edt(~tal) * GS
    sumpf = (d < 26) & (rauschen(44, 5) > 0.5)
    teile.append('<path class="ol-sumpf" d="' + " ".join(pfad(p, 0.9, True) for p in maske_umrisse(sumpf, minlen=14, glaetten=1)) + '"/>')
    # Höhenlinien braun, Zählkurven dicker, Formlinien gestrichelt
    hl = hoehenlinien(z, 7, eps=0.7)
    teile.append('<path class="ol-c" d="' + " ".join(pfad(p, 0.7) for k, p in hl if k % 5) + '"/>')
    teile.append('<path class="ol-c5" d="' + " ".join(pfad(p, 0.7) for k, p in hl if k % 5 == 0) + '"/>')
    fl = hoehenlinien(z + 3.5, 7, eps=0.7, minlen=40)
    teile.append('<path class="ol-form" d="' + " ".join(pfad(p, 0.7) for k, p in fl[::3]) + '"/>')
    # Bach und Nebenbäche
    teile.append(f'<path class="ol-w" d="{pfad(fluss, 0.5)}"/>')
    bd = [pfad(bach(z, q, tal), 0.6) for q in [(350, 300), (240, 330), (160, 520), (60, 300), (330, 90)]]
    teile.append('<path class="ol-wl" d="' + " ".join(b for b in bd if b) + '"/>')
    # Felsen: Findlinge an steilen Stellen, Felswände mit Zacken
    rng = np.random.default_rng(5)
    gy, gx = np.gradient(ndimage.gaussian_filter(z, 1.5))
    steil = np.hypot(gx, gy)
    kand = np.argwhere(steil > np.percentile(steil, 97))
    rng.shuffle(kand)
    steine, gesetzt = [], []
    for i, j in kand[:400]:
        x, y = j * GS, i * GS
        if all(math.hypot(x - a, y - b) > 22 for a, b in gesetzt):
            gesetzt.append((x, y))
            steine.append(f"M{num(x)} {num(y)}h.1")
        if len(gesetzt) >= 40:
            break
    teile.append(f'<path class="ol-stein" d="{"".join(steine)}"/>')
    waende = []
    for x, y in gesetzt[:12]:
        i, j = int(y / GS), int(x / GS)
        a = math.atan2(gy[i, j], gx[i, j]) + math.pi / 2
        dx, dy = math.cos(a) * 9, math.sin(a) * 9
        tx, ty = -math.sin(a) * 3.5, math.cos(a) * 3.5
        # Wandlinie und drei Zacken hangabwärts
        s = f"M{num(x - dx)} {num(y - dy)}l{num(2 * dx)} {num(2 * dy)}"
        for f in (-0.66, 0, 0.66):
            s += f"M{num(x + f * dx)} {num(y + f * dy)}l{num(-tx)} {num(-ty)}"
        waende.append(s)
    teile.append(f'<path class="ol-wand" d="{"".join(waende)}"/>')
    # Wege: Fahrweg, Pfad, Trampelpfad
    wege = {
        "ol-weg": [[(-10, 760), (80, 700), (150, 690), (230, 640), (300, 560), (360, 520), (410, 500)],
                   [(250, 175), (270, 260), (300, 330), (290, 420), (240, 520), (230, 640)]],
        "ol-pfad": [[(20, -10), (60, 80), (90, 110), (170, 230)], [(300, 560), (330, 640), (300, 700), (320, 800), (300, 910)],
                    [(110, 330), (150, 420), (200, 470), (240, 520)]],
        "ol-spur": [[(120, 600), (60, 640), (-10, 650)], [(360, 520), (390, 420), (410, 380)], [(90, 110), (160, 60), (260, 40), (410, 30)]],
    }
    for k, ws in wege.items():
        teile.append(f'<path class="{k}" d="' + " ".join(pfad(glatt(w, 8), 0.5) for w in ws) + '"/>')
    # Nordlinien
    teile.append('<path class="ol-nord" d="' + " ".join(f"M{x} 0v900" for x in range(45, 400, 62)) + '"/>')
    # Bahnaufdruck: Start, Posten 1 bis 5, Ziel (der Koffer)
    posten = [(200, 120), (95, 250), (215, 360), (325, 505), (150, 610), (275, 745), (190, 850)]
    auf = []
    sx, sy = posten[0]
    auf.append(f'<path class="bahn" d="M{sx} {sy - 11}l9.5 16.5h-19z"/>')
    for n, (x, y) in enumerate(posten[1:-1], 1):
        auf.append(f'<circle class="bahn" cx="{x}" cy="{y}" r="10"/>')
        auf.append(f'<text class="bahn-n" x="{x + 13}" y="{y - 8}">{n}</text>')
    fx, fy = posten[-1]
    auf.append(f'<circle class="bahn" cx="{fx}" cy="{fy}" r="7"/><circle class="bahn" cx="{fx}" cy="{fy}" r="11"/>')
    lin = []
    rad = [11] + [10] * 5 + [11]
    for (x0, y0), (x1, y1), r0, r1 in zip(posten[:-1], posten[1:], rad[:-1], rad[1:]):
        dx, dy = x1 - x0, y1 - y0
        n = math.hypot(dx, dy)
        ux, uy = dx / n, dy / n
        a, b = (x0 + ux * (r0 + 2), y0 + uy * (r0 + 2)), (x1 - ux * (r1 + 2), y1 - uy * (r1 + 2))
        lin.append(f"M{num(a[0])} {num(a[1])}L{num(b[0])} {num(b[1])}")
    auf.insert(0, f'<path class="bahn" d="{"".join(lin)}"/>')
    teile.append("".join(auf))
    return "".join(teile)

# ---------------------------------------------------------------- Variante B
# Ausschnitt: 400 Einheiten = 3,0 km Breite, Mitte auf der Route
LON0, LAT0 = 14.4115, 50.0855
KY = 900 / 0.0607
KX = KY * math.cos(math.radians(LAT0))

def proj(lat, lon):
    return ((lon - LON0) * KX + W / 2, (LAT0 - lat) * KY + H / 2)

def geo_linien(geom):
    """OSM-Geometrie mit Lücken (null) -> zusammenhängende Teilstücke in Karteneinheiten."""
    teile, cur = [], []
    for g in geom:
        if g is None:
            if len(cur) > 1:
                teile.append(cur)
            cur = []
        else:
            cur.append(proj(g["lat"], g["lon"]))
    if len(cur) > 1:
        teile.append(cur)
    return [np.array(t) for t in teile]

def klemm(p, rand=30):
    p = np.array(p, float)
    p[:, 0] = np.clip(p[:, 0], -rand, W + rand)
    p[:, 1] = np.clip(p[:, 1], -rand, H + rand)
    return p

def ringe(rel):
    """Multipolygon-Bestandteile an den Enden zusammensetzen."""
    wege = []
    for m in rel.get("members", []):
        g = m.get("geometry") or []
        pts = [(q["lat"], q["lon"]) for q in g if q]
        if len(pts) > 1:
            wege.append(pts)
    out = []
    while wege:
        r = wege.pop(0)
        for _ in range(len(wege) + 1):
            if r[0] == r[-1]:
                break
            for i, w in enumerate(wege):
                if w[0] == r[-1]:
                    r = r + w[1:]; wege.pop(i); break
                if w[-1] == r[-1]:
                    r = r + w[::-1][1:]; wege.pop(i); break
            else:
                break
        out.append(np.array([proj(a, b) for a, b in r]))
    return out

def flaeche(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def im_bild(p, rand=10):
    return (p[:, 0].max() > -rand and p[:, 0].min() < W + rand and p[:, 1].max() > -rand and p[:, 1].min() < H + rand)

def variante_b():
    d = json.load(open(os.path.join(HIER, "prag.json"), encoding="utf-8"))["elements"]
    rel = json.load(open(os.path.join(HIER, "relfull.json"), encoding="utf-8"))["elements"]
    teile = []
    # Grün
    gruen = []
    for e in d:
        t = e.get("tags", {})
        if e["type"] == "way" and (t.get("leisure") in ("park", "garden") or t.get("landuse") in ("forest", "grass", "meadow", "cemetery", "recreation_ground") or t.get("natural") in ("wood", "scrub")):
            for p in geo_linien(e.get("geometry", [])):
                if im_bild(p) and flaeche(p) > 120:
                    gruen.append(pfad(klemm(p), 0.9, True))
    for r in rel:
        t = r["tags"]
        if t.get("natural") != "water":
            for p in ringe(r):
                if im_bild(p) and flaeche(p) > 120:
                    gruen.append(pfad(klemm(p), 0.9, True))
    teile.append(f'<path class="park" d="{" ".join(gruen)}"/>')
    # Wasser
    wasser = []
    for r in rel:
        if r["tags"].get("natural") == "water":
            for p in ringe(r):
                if im_bild(p) and laenge(p) > 8:
                    wasser.append(pfad(klemm(p), 0.5, True))
    for e in d:
        t = e.get("tags", {})
        if e["type"] == "way" and t.get("natural") == "water":
            for p in geo_linien(e.get("geometry", [])):
                if im_bild(p) and laenge(p) > 8:
                    wasser.append(pfad(klemm(p), 0.5, True))
    teile.append(f'<path class="wasser" d="{" ".join(wasser)}"/>')
    # Moldau-Mittellinie für die Beschriftung
    fluss = [p for e in d if e["type"] == "way" and e.get("tags", {}).get("waterway") == "river" for p in geo_linien(e.get("geometry", []))]
    # Bäche
    baeche = [pfad(p, 0.5) for e in d if e["type"] == "way" and e.get("tags", {}).get("waterway") in ("stream", "canal") for p in geo_linien(e.get("geometry", []))]
    teile.append(f'<path class="bach" d="{" ".join(b for b in baeche if b)}"/>')
    # Bahn
    # nur Streckengleise, keine Abstell- und Rangiergleise
    bahn = [pfad(p, 1.0) for e in d if e["type"] == "way" and e.get("tags", {}).get("railway") == "rail"
            and "service" not in e.get("tags", {}) for p in geo_linien(e.get("geometry", []))]
    teile.append(f'<path class="bahn-gl" d="{" ".join(b for b in bahn if b)}"/>')
    # Straßen nach Rang
    rang = {
        "st-fuss": ("footway", "path", "steps"),
        "st": ("residential", "unclassified", "pedestrian", "living_street"),
        "st-mittel": ("tertiary",),
        "st-haupt": ("secondary", "primary", "trunk", "motorway"),
    }
    for kl, arten in rang.items():
        ds = []
        for e in d:
            t = e.get("tags", {}) if e["type"] == "way" else {}
            # Bürgersteige und Überwege verdoppeln nur die Straßen daneben
            if t.get("highway") in arten and t.get("footway") not in ("sidewalk", "crossing") and t.get("area") != "yes":
                for p in geo_linien(e.get("geometry", [])):
                    if kl == "st-fuss" and laenge(p) < 10:
                        continue
                    if im_bild(p):
                        ds.append(pfad(p, 0.6 if kl != "st-fuss" else 1.0))
        teile.append(f'<path class="{kl}" d="{"".join(x for x in ds if x)}"/>')
    # Beschriftung: Moldau entlang der Mittellinie, Viertel
    # Moldau: gedreht an zwei geraden Stellen, von unten nach oben lesbar
    for la, lo, w in ((50.0790, 14.4128, -84), (50.0640, 14.4148, -80)):
        x, y = proj(la, lo)
        teile.append(f'<text class="fl" x="{num(x)}" y="{num(y)}" transform="rotate({w} {num(x)} {num(y)})" text-anchor="middle">Vltava</text>')
    viertel = [("Staré Město", 50.0885, 14.4225), ("Malá Strana", 50.0880, 14.4020), ("Nové Město", 50.0775, 14.4230),
               ("Hradčany", 50.0925, 14.3960), ("Letná", 50.0985, 14.4230), ("Smíchov", 50.0715, 14.4040),
               ("Petřín", 50.0810, 14.3955), ("Josefov", 50.0905, 14.4170), ("Vyšehrad", 50.0645, 14.4200),
               ("Holešovice", 50.1060, 14.4300)]
    for name, la, lo in viertel:
        x, y = proj(la, lo)
        teile.append(f'<text class="vl" x="{num(x)}" y="{num(y)}">{name}</text>')
    # Route der Stadtjagd mit den fünf Stationen aus der Datenbank
    st = [(50.087500, 14.428060), (50.087000, 14.420440), (50.086360, 14.413740), (50.086330, 14.406830), (50.083440, 14.395000)]
    pts = [proj(a, b) for a, b in st]
    teile.append(f'<path class="route" d="{pfad(glatt(pts, 10), 0.4)}"/>')
    for n, (x, y) in enumerate(pts, 1):
        teile.append(f'<circle class="stn" cx="{num(x)}" cy="{num(y)}" r="7"/><text class="stn-n" x="{num(x)}" y="{num(y + 3.2)}">{n}</text>')
    teile.append('<text class="osm" x="396" y="895">Kartendaten © OpenStreetMap-Mitwirkende</text>')
    return "".join(teile)

# ---------------------------------------------------------------- Ausgabe
def svg(inhalt, extra_defs=""):
    return (f'<svg class="topo" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
            f'{extra_defs}{inhalt}</svg>')

if __name__ == "__main__":
    os.makedirs(ZIEL, exist_ok=True)
    defs = {
        "a": '<defs><pattern id="a-wald" width="9" height="9" patternUnits="userSpaceOnUse">'
             '<circle class="baum" cx="2.5" cy="2.5" r="1.3"/><circle class="baum" cx="7" cy="7" r="1.3"/></pattern></defs>',
        "b": "",
        "c": '<defs><pattern id="c-dicht" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(90)">'
             '<path class="dicht" d="M0 2.5h5"/></pattern>'
             '<pattern id="c-sumpf" width="10" height="4" patternUnits="userSpaceOnUse">'
             '<path class="sumpf" d="M1 2h6"/></pattern></defs>',
    }
    for name, f in (("a", variante_a), ("b", variante_b), ("c", variante_c)):
        s = svg(f(), defs[name])
        open(os.path.join(ZIEL, f"hintergrund-{name}.svg"), "w", encoding="utf-8").write(s)
        print(name, f"{len(s.encode('utf-8')) / 1024:.1f} KB")
