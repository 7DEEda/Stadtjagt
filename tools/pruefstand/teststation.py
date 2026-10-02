#!/usr/bin/env python3
"""
Teststation im Prüfstand, ohne Datenbank.

    python tools/pruefstand/teststation.py

Spielleitung: Abschnitt Teststation sichtbar und bearbeitbar (Formular, Karte mit Kreisen),
Speichern schickt die id der Teststation, die Prager Liste bleibt. Im Vordergrund mit Timeout.
"""
import functools
import http.server
import pathlib
import sys
import threading

sys.stdout.reconfigure(encoding="utf-8")
HIER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import shoot  # noqa: E402

shoot.bauen()
from playwright.sync_api import sync_playwright  # noqa: E402


class Leise(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8822), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
fehler = []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1180, "height": 820}); pg.set_default_timeout(15000); err = []
    pg.on("pageerror", lambda e: err.append(str(e)))

    print("Spielleitung, Reiter Stationen")
    pg.goto("http://127.0.0.1:8822/app.html?szenario=admin-teststation"); pg.wait_for_selector(".tabs")
    pg.click("[data-act=a-tab][data-tab=stations]"); pg.wait_for_selector("[data-act=a-edit]")
    t = pg.inner_text("#teststation")
    pruef("EDEKA Grenzallee" in t and "Testmodus an: alle Teams spielen nur die Teststation" in t, f"Abschnitt Teststation: {t[:80]!r}")
    pruef(pg.locator("[data-act=a-edit]").count() == 6, "sechs Bearbeiten-Knöpfe (Teststation und fünf Stationen)")
    pg.click("#teststation [data-act=a-edit]"); pg.wait_for_selector("#emap .leaflet-marker-icon", timeout=25000)
    pruef(pg.input_value("#e-name") == "EDEKA Grenzallee", "Formular zeigt die Teststation")
    pruef("TSE Berlin" in pg.inner_text("#e-etappe"), f"Etappe beginnt bei der TSE: {pg.inner_text('#e-etappe')[:60]!r}")
    pg.fill("#e-radius", "40"); pg.evaluate("window.__GESPEICHERT = null")
    pg.click("[data-act=a-save]"); pg.wait_for_function("window.__GESPEICHERT")
    g = pg.evaluate("window.__GESPEICHERT")
    pruef(g["p_id"] == "st" and g["p_radius"] == 40, f"Speichern mit id der Teststation ({g['p_id']}, {g['p_radius']})")
    pruef(len(pg.evaluate("S.admin.state.stations")) == 5, "Prager Liste unverändert fünf Stationen")
    print("Auslosen mit einer Person im Testmodus")
    pg.goto("http://127.0.0.1:8822/app.html?szenario=admin-auslosen-allein"); pg.wait_for_selector(".tabs")
    pg.click("[data-act=a-tab][data-tab=teams]"); pg.wait_for_selector("#dval")
    pruef(not pg.locator(".panel [data-act=a-draw]").last.is_disabled(), "Auslosen-Knopf aktiv bei einer Person im Testmodus")
    print("Team, eine Station")
    pg.set_viewport_size({"width": 390, "height": 844})
    pg.goto("http://127.0.0.1:8822/app.html?szenario=teststation"); pg.wait_for_selector(".lock")
    pruef(pg.locator(".lock .wheel").count() == 2, f"Schloss mit zwei Rädern ({pg.locator('.lock .wheel').count()})")
    t = pg.inner_text("#app")
    pruef("Station 1 von 1" in t and "EDEKA Grenzallee" in t, "Station 1 von 1, EDEKA")
    pruef("fünf" not in t and "sechs" not in t, "keine Rede von fünf oder sechs Ziffern")
    pg.goto("http://127.0.0.1:8822/app.html?szenario=teststation-koffer"); pg.wait_for_selector("#tfin")
    pruef(pg.get_attribute("#tfin", "maxlength") == "2", f"Koffer-Feld zwei Ziffern ({pg.get_attribute('#tfin', 'maxlength')})")
    t = pg.inner_text("#app")
    pruef("zwei Ziffern" in t and "sechs" not in t, "Koffer-Text nennt zwei Ziffern")
    pruef("6 Stellen" not in t and "2 Stellen" in t, "Feldbeschriftung nennt 2 Stellen")
    pruef(not err, f"keine Skriptfehler {err[:2]}")
    b.close()
srv.shutdown()
print("FEHLER: " + str(len(fehler)) if fehler else "OK")
sys.exit(1 if fehler else 0)
