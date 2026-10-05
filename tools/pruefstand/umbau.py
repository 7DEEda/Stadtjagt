#!/usr/bin/env python3
"""
Umbau Weiterentwicklung im Prüfstand, ohne Datenbank.

    python tools/pruefstand/umbau.py

Handy-Hülle (390x844): Kopf, Inhalt, drei Tabs unten. Im Vordergrund mit Timeout starten.
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


PORT = 8840
BASIS = f"http://127.0.0.1:{PORT}"
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
fehler = []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000); err = []
    pg.on("pageerror", lambda e: err.append(str(e)))

    print("Handy, Teamleitung unterwegs")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-unterwegs"); pg.wait_for_selector(".ph")
    pruef(pg.locator(".ph > .kopf").count() == 1 and pg.locator(".ph > .inhalt").count() == 1, "Hülle mit Kopf und Inhalt")
    tabs = pg.locator(".ftabs [role=tab]")
    pruef(tabs.count() == 3 and [tabs.nth(i).inner_text().split("\n")[0] for i in range(3)] == ["Weg", "Ziffern", "Team"], "drei Tabs Weg, Ziffern, Team")
    pruef(pg.locator("#needle").count() == 1 and pg.locator("#dist").count() == 1, "Kompass und Entfernung im Tab Weg")
    pg.click(".ftabs [data-tab=team]")
    pruef(pg.locator("#needle").count() == 0, "Tab Team ohne Kompass")
    pg.evaluate("render()")                      # die 10-s-Abfrage zeichnet neu
    pruef(pg.get_attribute(".ftabs [data-tab=team]", "aria-selected") == "true", "Tab bleibt nach render() gewählt")
    box = pg.locator(".ftabs").bounding_box()
    pruef(abs(box["y"] + box["height"] - 844) < 2, "Tabs kleben unten")
    pruef(pg.evaluate("document.documentElement.scrollWidth") <= 390, "kein seitliches Scrollen")
    print("Handy, Teamleitung Rätsel")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-raetsel"); pg.wait_for_selector(".ph")
    pruef(pg.inner_text(".ftabs [data-tab=weg]").startswith("Rätsel"), "erster Tab heißt im Rätsel 'Rätsel'")

    print("Scrollstand im Inhalt")
    pg.set_viewport_size({"width": 390, "height": 420})
    pg.goto(f"{BASIS}/app.html?szenario=leitung-raetsel"); pg.wait_for_selector(".ph")
    pg.evaluate("document.querySelector('#inhalt').scrollTop = 60")
    h0 = pg.evaluate("document.querySelector('#inhalt').scrollTop")
    pruef(h0 > 0, f"Inhalt lässt sich scrollen ({h0})")
    pg.evaluate("render()")
    pruef(pg.evaluate("document.querySelector('#inhalt').scrollTop") == h0, "Scrollstand bleibt nach render()")
    pg.click(".ftabs [data-tab=ziffern]"); pg.click(".ftabs [data-tab=weg]")
    pruef(pg.evaluate("document.querySelector('#inhalt').scrollTop") == 0, "nach Tabwechsel beginnt der Inhalt oben")

    pruef(not err, f"keine Seitenfehler {err[:2]}")
    b.close()

print("\nOK" if not fehler else "\nFEHLT: " + "; ".join(fehler))
sys.exit(1 if fehler else 0)
