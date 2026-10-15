#!/usr/bin/env python3
"""
Vektorkarte von Prag für die Rückblick-Show, aus OpenStreetMap-Daten, in den Farben der Stadtjagd.

    python tools/rueckblick/karte.py [ziel.js]

Liest `prag-karte.json` neben diesem Skript (groß, nicht im Repo; neu laden mit der Abfrage in
`osm-karte.txt`):
    curl -A "Stadtjagd-Rueckblick/1.0" --data-urlencode data@osm-karte.txt \
         https://overpass-api.de/api/interpreter -o prag-karte.json
Schreibt eine JS-Datei mit `window.PRAG_KARTE = { quelle, lagen: { name: "<SVG-Pfad>" } }`, ein Pfad je
Ebene, Koordinaten in Metern im System der Show: x = (lng - LNG0) * KX, y = (LAT0 - lat) * KY (wie `P()` in
mockups/rueckblick/index.html). Farben setzt die Seite über ihre Token (hell und dunkel), nicht diese Datei.
Ohne Netz nutzbar, keine Kartenkacheln. Daten: © OpenStreetMap-Mitwirkende, ODbL; die Show nennt das.
"""
import json, math, pathlib, sys

HIER = pathlib.Path(__file__).resolve().parent
ZIEL = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HIER.parent.parent / "mockups" / "rueckblick" / "prag-karte.js"
LAT0, LNG0, KX, KY = 50.1000, 14.4235, 71520, 111200

# Ebenen in Zeichenreihenfolge, mit Vereinfachung (Meter)
PARK = {"park", "garden", "pitch", "playground", "sports_centre"}
GRUEN = {"forest", "grass", "meadow", "cemetery", "recreation_ground", "allotments"}
HAUPT = {"motorway", "trunk", "primary", "secondary", "tertiary"}
NEBEN = {"residential", "unclassified", "living_street", "pedestrian"}
WEG = {"footway", "path", "steps", "cycleway", "track"}


def P(lat, lng):
    return ((lng - LNG0) * KX, (LAT0 - lat) * KY)


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1; n = math.hypot(dx, dy) or 1e-9
        best, bi = -1, -1
        for i in range(a + 1, b):
            x0, y0 = pts[i]
            d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / n if n > 1e-9 else math.hypot(x0 - x1, y0 - y1)
            if d > best:
                best, bi = d, i
        if best > eps:
            keep[bi] = True; stack += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]


def stuecke(geom):
    """Geometrie einer Way in Stücke ohne Lücken (Overpass setzt Knoten außerhalb des Ausschnitts auf null)."""
    teil = []
    for g in geom or []:
        if g is None:
            if len(teil) > 1:
                yield teil
            teil = []
        else:
            teil.append(P(g["lat"], g["lon"]))
    if len(teil) > 1:
        yield teil


def d_linie(pts, eps, zu=False):
    pts = rdp(pts, eps)
    if len(pts) < 2 or (zu and len(pts) < 4):
        return ""
    s = "M" + " ".join(f"{x:.0f} {y:.0f}" for x, y in pts)
    return s + ("Z" if zu else "")


def ringe(member_geoms):
    """Mitglieds-Ways einer Multipolygon-Relation zu geschlossenen Ringen zusammensetzen."""
    offen = [list(g) for g in member_geoms if len(g) > 1]
    fertig = []
    while offen:
        ring = offen.pop()
        verlaengert = True
        while verlaengert and ring[0] != ring[-1]:
            verlaengert = False
            for i, w in enumerate(offen):
                if w[0] == ring[-1]: ring += w[1:]
                elif w[-1] == ring[-1]: ring += w[::-1][1:]
                elif w[-1] == ring[0]: ring = w + ring[1:]
                elif w[0] == ring[0]: ring = w[::-1] + ring[1:]
                else: continue
                offen.pop(i); verlaengert = True; break
        fertig.append(ring)
    return fertig


def main():
    daten = json.loads((HIER / "prag-karte.json").read_text(encoding="utf-8"))["elements"]
    lagen = {k: [] for k in ("gruen", "park", "wasser", "gebaeude", "weg", "bahn", "neben", "haupt")}
    fluesse = []
    for e in daten:
        t = e.get("tags", {})
        if e["type"] == "relation":
            mg = [list(s) for m in e.get("members", []) if m.get("type") == "way" for s in stuecke(m.get("geometry"))]
            ziel = "wasser" if t.get("natural") == "water" else "park" if t.get("leisure") == "park" else "gruen"
            for r in ringe(mg):
                lagen[ziel].append(d_linie(r, 2.0, zu=True))
            continue
        for st in stuecke(e.get("geometry")):
            zu = len(st) > 3 and st[0] == st[-1]
            if "building" in t:
                if zu: lagen["gebaeude"].append(d_linie(st, 0.9, zu=True))
            elif t.get("natural") == "water" or t.get("waterway") == "riverbank":
                if zu: lagen["wasser"].append(d_linie(st, 2.0, zu=True))
            elif t.get("waterway") in ("river", "canal", "stream"):
                fluesse.append(d_linie(st, 2.0))
            elif t.get("leisure") in PARK:
                if zu: lagen["park"].append(d_linie(st, 1.5, zu=True))
            elif t.get("landuse") in GRUEN or t.get("natural") in ("wood", "scrub"):
                if zu: lagen["gruen"].append(d_linie(st, 1.5, zu=True))
            elif t.get("railway") == "rail":
                lagen["bahn"].append(d_linie(st, 1.5))
            elif t.get("highway") in HAUPT:
                lagen["haupt"].append(d_linie(st, 1.2))
            elif t.get("highway") in NEBEN or (t.get("highway") == "service" and t.get("service") is None):
                lagen["neben"].append(d_linie(st, 1.2))
            elif t.get("highway") in WEG:
                lagen["weg"].append(d_linie(st, 1.2))
    aus = {k: "".join(x for x in v if x) for k, v in lagen.items()}
    aus["flusslinie"] = "".join(x for x in fluesse if x)   # nur Bäche/Kanäle ohne Fläche; die Moldau kommt als Fläche
    js = ("// Erzeugt von tools/rueckblick/karte.py aus OpenStreetMap-Daten (© OpenStreetMap-Mitwirkende, ODbL).\n"
          "// Nicht von Hand ändern. Koordinaten in Metern, System der Show (P()).\n"
          "window.PRAG_KARTE = " + json.dumps({"quelle": "© OpenStreetMap-Mitwirkende", "lat0": LAT0, "lng0": LNG0,
                                                  "kx": KX, "ky": KY, "lagen": aus}, ensure_ascii=False, separators=(",", ":")) + ";\n")
    ZIEL.write_text(js, encoding="utf-8", newline="\n")
    print(f"geschrieben: {ZIEL} ({len(js) // 1024} KB)")
    for k, v in aus.items():
        print(f"  {k:10} {len(v) // 1024:5} KB")


if __name__ == "__main__":
    main()
