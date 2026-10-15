#!/usr/bin/env python3
"""
Ausfallsicherheit, Abschnitt 4: sichtbare Version und "Neue Version laden".

    python tools/pruefstand/version.py

Spiel (app.html mit mock.js, Port 8864). Die Version ist der Last-Modified-Kopf der geladenen Seite; der
Prüfserver setzt ihn aus der Änderungszeit von app.html, die das Skript gezielt verstellt. Ohne Leaflet-Seite.
Im Vordergrund mit Timeout aufrufen. Am Ende steht OK oder FEHLT.
"""
import functools
import http.server
import os
import pathlib
import sys
import threading
import time
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
HIER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import shoot  # noqa: E402
import abschluss  # noqa: E402

shoot.bauen()
from playwright.sync_api import sync_playwright  # noqa: E402


class Leise(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


PORT = 8864
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
APP = f"http://127.0.0.1:{PORT}/app.html?szenario="
DATEI = HIER / "app.html"
fehler, err = [], []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def stellen(sekunden_her):
    """Änderungszeit von app.html auf jetzt minus sekunden_her (volle Sekunde), gibt die erwartete Zeile zurück."""
    t = int(time.time()) - sekunden_her
    os.utime(DATEI, (t, t))
    d = datetime.fromtimestamp(t)
    return f"Version {d:%d.%m.}, {d:%H:%M}"


def zeile(pg):
    v = pg.locator(".version")
    return v.first.inner_text().strip() if v.count() else ""


vorher = abschluss.merken()
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)

    print("Versionszeile unter der Navigation")
    erwartet = stellen(3 * 3600)
    pg = b.new_page(viewport={"width": 390, "height": 844})
    pg.on("pageerror", lambda e: err.append(str(e)))
    pg.goto(APP + "anmeldung-leer"); pg.wait_for_function("window.__fertig === true", timeout=30000)
    pruef(zeile(pg) == erwartet, f"Anmeldeseite: '{erwartet}' ({zeile(pg)!r})")
    pruef(pg.locator(".nav + .version").count() == 1, "Zeile steht direkt unter der Navigation")
    pruef(pg.evaluate("(() => { const e = document.querySelector('.version .nw'); return e && getComputedStyle(e).whiteSpace; })()") == "nowrap", "Zeile bricht nicht um")
    pruef(pg.locator(".version [data-act=neu-laden]").count() == 0, "ohne neuere Version kein Link")
    pruef(pg.evaluate("document.documentElement.scrollWidth") <= 390, "kein seitliches Scrollen")

    pg.goto(APP + "leitung-unterwegs"); pg.wait_for_function("window.__fertig === true", timeout=30000)
    pg.click(".ftabs [data-tab=team]")
    pruef(zeile(pg) == erwartet, f"Teamleitung, Tab Team ({zeile(pg)!r})")
    pg.goto(APP + "admin-teilnehmende"); pg.wait_for_function("window.__fertig === true", timeout=30000)
    pruef(zeile(pg) == erwartet, f"Spielleitung ({zeile(pg)!r})")

    print("Neue Version beim Zurückkehren in die App")
    pg.goto(APP + "anmeldung-leer"); pg.wait_for_function("window.__fertig === true", timeout=30000)
    pg.evaluate("window.__heads = 0; const f = window.fetch; window.fetch = (u, o) => { if (o && o.method === 'HEAD') window.__heads++; return f(u, o); }")
    neu = stellen(3 * 3600 - 120)
    pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    try:
        pg.wait_for_selector(".version [data-act=neu-laden]", timeout=5000)
    except Exception:
        pass
    link = pg.locator(".version [data-act=neu-laden]")
    pruef(link.count() == 1 and link.inner_text() == "Neue Version laden", "Link 'Neue Version laden' erscheint")
    pruef(pg.evaluate("window.__heads") == 1, f"genau eine HEAD-Anfrage ({pg.evaluate('window.__heads')})")
    pruef(zeile(pg).startswith(erwartet), "Versionszeile zeigt weiter die geladene Version")
    pg.evaluate("render()")
    pruef(pg.locator(".version [data-act=neu-laden]").count() == 1, "Link bleibt nach dem Neuzeichnen")
    if link.count():
        with pg.expect_navigation():
            link.click()
        pg.wait_for_function("window.__fertig === true", timeout=30000)
        pruef(zeile(pg) == neu, f"nach dem Tipp: neue Version ({zeile(pg)!r})")
        pruef(pg.locator(".version [data-act=neu-laden]").count() == 0, "danach kein Link mehr")

    print("Gleiche Version: kein Link")
    pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    pg.wait_for_timeout(800)
    pruef(pg.locator(".version [data-act=neu-laden]").count() == 0, "gleiche Zeit: kein Link")

    print("Prüfung im 10-s-Takt höchstens alle 10 Minuten")
    pg.close()
    stellen(3 * 3600)
    pg = b.new_page(viewport={"width": 390, "height": 844})
    pg.on("pageerror", lambda e: err.append(str(e)))
    pg.clock.install()
    pg.goto(APP + "anmeldung-leer"); pg.wait_for_function("window.__fertig === true", timeout=30000)
    pg.evaluate("window.__heads = 0; const f = window.fetch; window.fetch = (u, o) => { if (o && o.method === 'HEAD') window.__heads++; return f(u, o); }")
    stellen(3 * 3600 - 60)
    for _ in range(5):
        pg.clock.fast_forward(10000); pg.wait_for_timeout(150)
    pruef(pg.evaluate("window.__heads") == 0, f"in den ersten Minuten keine Prüfung ({pg.evaluate('window.__heads')})")
    pg.clock.fast_forward(10 * 60 * 1000); pg.wait_for_timeout(300)
    pg.clock.fast_forward(10000); pg.wait_for_timeout(800)
    pruef(pg.evaluate("window.__heads") == 1, f"nach 10 Minuten eine Prüfung ({pg.evaluate('window.__heads')})")
    pruef(pg.locator(".version [data-act=neu-laden]").count() == 1, "Link erscheint aus dem Takt")

    print("Ohne brauchbaren Last-Modified: keine Zeile")
    pg.close()
    stellen(1)
    pg = b.new_page(viewport={"width": 390, "height": 844})
    pg.on("pageerror", lambda e: err.append(str(e)))
    pg.goto(APP + "anmeldung-leer"); pg.wait_for_function("window.__fertig === true", timeout=30000)
    pruef(pg.locator(".version").count() == 0, f"Änderungszeit eben erst: keine Zeile ({zeile(pg)!r})")

    pruef(not err, "keine Fehler auf der Seite" + (f": {err[:3]}" if err else ""))
    print("FEHLT:\n  " + "\n  ".join(fehler) if fehler else "OK")
    sys.stdout.flush()
    abschluss.ende(fehler, vorher)   # Chrome hängt hier manchmal beim Schließen
