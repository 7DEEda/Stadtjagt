#!/usr/bin/env python3
"""
Ausfallsicherheit, Abschnitt 2: Leaflet und Schriften liegen im Repo, nichts kommt von unpkg oder Google Fonts.

    python tools/pruefstand/lokal.py

Spiel (app.html mit mock.js, Port 8863). Anfragen an fremde Rechner (außer Kartenkacheln) werden abgebrochen und
mitgeschrieben: lädt die App etwas von unpkg oder Google, fehlt es hier und die Prüfung meldet es. Öffnet die
Leaflet-Karte der Spielleitung: Chrome 155 hängt danach beim Schließen, darum steht OK oder FEHLT vorher.
Im Vordergrund mit Timeout aufrufen.
"""
import functools
import http.server
import pathlib
import re
import sys
import threading
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8")
HIER = pathlib.Path(__file__).resolve().parent
REPO = HIER.parent.parent
sys.path.insert(0, str(HIER))
import shoot  # noqa: E402
import abschluss  # noqa: E402

shoot.bauen()
from playwright.sync_api import sync_playwright  # noqa: E402


class Leise(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


PORT = 8863
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
APP = f"http://127.0.0.1:{PORT}/app.html?szenario="
fehler, err, fremd, geladen = [], [], [], []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def wache(route):
    host = urlparse(route.request.url).hostname or ""
    if host in ("127.0.0.1", "localhost") or route.request.url.startswith("data:"):
        geladen.append(route.request.url)
        return route.continue_()
    if host.endswith("tile.openstreetmap.org"):
        return route.abort()   # Kacheln sind nicht Teil der App, im Prüfstand nicht nötig
    fremd.append(route.request.url)
    route.abort()


print("Dateien im Repo")
html = (REPO / "index.html").read_text(encoding="utf-8")
pruef(not re.search(r"fonts\.googleapis|fonts\.gstatic|unpkg\.com", html), "index.html nennt weder Google Fonts noch unpkg")
L = REPO / "vendor" / "leaflet-1.9.4"
for f in ["leaflet.js", "leaflet.css", "LICENSE", "images/layers.png", "images/layers-2x.png", "images/marker-icon.png",
          "images/marker-icon-2x.png", "images/marker-shadow.png"]:
    pruef((L / f).is_file(), f"vendor/leaflet-1.9.4/{f}")
F = REPO / "vendor" / "fonts"
woff = sorted(p.name for p in F.glob("*.woff2")) if F.is_dir() else []
pruef(len(woff) == 14, f"14 Schriftdateien in vendor/fonts ({len(woff)})")
pruef((F / "OFL.txt").is_file(), "vendor/fonts/OFL.txt")
for n in woff:
    pruef(f"vendor/fonts/{n}" in html, f"@font-face nennt {n}")
pruef(html.count("font-display:swap") + html.count("font-display: swap") >= 14, "font-display: swap in jeder Regel")

vorher = abschluss.merken()
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)

    print("Handy: Anmeldeseite mit tschechischem Namen")
    pg = b.new_page(viewport={"width": 390, "height": 844})
    pg.route("**/*", wache)
    pg.on("pageerror", lambda e: err.append(str(e)))
    pg.goto(APP + "anmeldung-leer")
    pg.wait_for_function("window.__fertig === true", timeout=30000)
    pg.evaluate("() => { const p = document.createElement('p'); p.textContent = 'Křižíkova fontána'; p.style.fontFamily = 'Barlow'; document.body.appendChild(p); }")
    pg.evaluate("document.fonts.ready")
    pg.wait_for_timeout(400)
    for f, gew in [("Barlow", 400), ("Barlow", 600), ("Barlow Semi Condensed", 700)]:
        pg.evaluate(f"document.fonts.load('{gew} 16px \"{f}\"', 'Křižík')")
        pruef(pg.evaluate(f"document.fonts.check('{gew} 16px \"{f}\"', 'Křižík')"), f"{f} {gew} geladen (auch latin-ext)")
    geladene = pg.evaluate("[...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/\"/g, '') + ' ' + f.weight)")
    pruef("Barlow 400" in geladene and "Barlow Semi Condensed 700" in geladene, f"Schriften aus den @font-face-Regeln geladen ({sorted(set(geladene))})")
    pruef(any("vendor/fonts/barlow-400-latin-ext.woff2" in u for u in geladen), "latin-ext für ř aus vendor/fonts")
    pruef(any("vendor/fonts/barlow-semi-condensed-700-latin.woff2" in u for u in geladen), "Überschrift aus vendor/fonts")
    pg.close()

    print("Spielleitung: Karte mit Leaflet aus vendor/")
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.route("**/*", wache)
    pg.on("pageerror", lambda e: err.append(str(e)))
    pg.goto(APP + "admin-karte")
    pg.wait_for_function("window.__fertig === true", timeout=30000)
    try:
        pg.wait_for_selector("#map .leaflet-marker-icon, #map .leaflet-interactive", timeout=20000)
        karte = True
    except Exception:
        karte = False
    pruef(karte, "Karte mit Markern steht")
    pruef(pg.evaluate("!!window.L && L.version === '1.9.4'"), "Leaflet 1.9.4 geladen")
    pruef(any(u.endswith("vendor/leaflet-1.9.4/leaflet.js") for u in geladen), "leaflet.js aus vendor/leaflet-1.9.4")
    pruef(any(u.endswith("vendor/leaflet-1.9.4/leaflet.css") for u in geladen), "leaflet.css aus vendor/leaflet-1.9.4")
    pruef(pg.evaluate("getComputedStyle(document.querySelector('#map')).position") == "relative"
          or pg.evaluate("document.querySelector('#map').classList.contains('leaflet-container')"), "Leaflet-Stile greifen")
    pruef(pg.evaluate("document.fonts.check('600 16px \"Barlow Semi Condensed\"')"), "Schrift auch am Tablet")

    pruef(not fremd, "keine Anfrage an fremde Rechner" + (f": {sorted(set(fremd))[:5]}" if fremd else ""))
    pruef(not err, "keine Fehler auf der Seite" + (f": {err[:3]}" if err else ""))
    print("FEHLT:\n  " + "\n  ".join(fehler) if fehler else "OK")
    sys.stdout.flush()
    abschluss.ende(fehler, vorher)   # Chrome 155 hängt nach einer Leaflet-Seite beim Schließen
