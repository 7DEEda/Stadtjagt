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
    pg.set_viewport_size({"width": 390, "height": 260})
    pg.evaluate("render()")
    pg.evaluate("document.querySelector('#inhalt').scrollTop = 60")
    pg.click(".ftabs [data-tab=ziffern]")
    sz = pg.evaluate("(() => { const i = document.querySelector('#inhalt'); return [i.scrollHeight, i.clientHeight]; })()")
    pruef(sz[0] > sz[1], f"Tab Ziffern ist scrollbar {sz}")
    pruef(pg.evaluate("document.querySelector('#inhalt').scrollTop") == 0, "nach Tabwechsel beginnt der neue Inhalt oben")
    pg.evaluate("document.querySelector('#inhalt').scrollTop = 30"); pg.evaluate("render()")
    pruef(pg.evaluate("document.querySelector('#inhalt').scrollTop") == 30, "im neuen Tab bleibt der Stand nach render()")
    pg.click(".ftabs [data-tab=weg]")
    pruef(pg.evaluate("document.querySelector('#inhalt').scrollTop") == 0, "zurück im Tab Weg oben")

    print("Aktionsleiste")
    pg.set_viewport_size({"width": 390, "height": 844})
    pg.goto(f"{BASIS}/app.html?szenario=leitung-unterwegs"); pg.wait_for_selector(".ph")
    pruef(pg.locator("#leiste [data-act=t-gps]").count() == 1 and pg.locator("#inhalt [data-act=t-gps]").count() == 0, "ohne Standort: Freigabe steht in der Leiste")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-unterwegs-standort"); pg.wait_for_selector("#leiste #tcheck")
    pruef(pg.locator("#leiste #tcheck").count() == 1 and pg.locator("#inhalt #tcheck").count() == 0, "Einchecken steht in der Leiste")
    pg.click(".ftabs [data-tab=team]")
    pruef(pg.locator("#leiste #tcheck").count() == 1, "Leiste bleibt in jedem Tab")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-raetsel"); pg.wait_for_selector("#leiste #tans")
    pg.click("#tans"); pg.keyboard.type("527")
    r = pg.locator("#tans").bounding_box()
    pruef(r["y"] + r["height"] <= 844 and pg.evaluate("document.documentElement.scrollWidth") <= 390, "Antwortfeld sichtbar, nichts seitlich verschoben")
    pg.evaluate("render()")
    pruef(pg.input_value("#tans") == "527", "Getipptes übersteht render()")
    pg.goto(f"{BASIS}/app.html?szenario=mitglied-raetsel"); pg.wait_for_selector(".ph")
    pruef(pg.locator("#leiste input").count() == 0 and "gibt" in pg.inner_text("#leiste"), "Mitlesende: keine Eingabe, Leiste sagt wer eingibt")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-koffer"); pg.wait_for_selector("#leiste #tfin")
    pruef(pg.locator("#inhalt #tfin").count() == 0 and pg.locator("#leiste [data-act=t-final]").count() == 1, "Koffer-Code steht in der Leiste")
    for sz in ["leitung-startklar", "leitung-koffer", "leitung-platz2", "leitung-beendet", "selfie-offen"]:
        pg.goto(f"{BASIS}/app.html?szenario={sz}"); pg.wait_for_selector("#app > *")
        leer = pg.evaluate("(() => { const l = document.querySelector('#leiste'); return !!l && l.innerText.trim() === '' && getComputedStyle(l).display !== 'none'; })()")
        pruef(not leer and not err, f"{sz}: keine leere Leiste, keine Fehler")

    pruef(not err, f"keine Seitenfehler {err[:2]}")
    b.close()

print("\nOK" if not fehler else "\nFEHLT: " + "; ".join(fehler))
sys.exit(1 if fehler else 0)
