#!/usr/bin/env python3
"""
Umsetzung der UI-Kritik vom 01.10.2026 im Prüfstand prüfen, ohne Datenbank.

    python tools/pruefstand/kritik.py

Hochformat-Hinweis (Handy quer, nicht beim Einmessen, nicht bei der Spielleitung),
„Wir sind da“ außerhalb des Radius, Zifferntastatur bei Zahlenlösungen, Route bei
offenem Selfie, abgesetzte Schlussziffer, Rückfrage beim Testmodus im laufenden
Spiel, Kontrast der Knopfschrift. Im Vordergrund mit Timeout aufrufen.
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


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8812), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
SHOTS = str(HIER / "shots") + "/kritik-"
fehler = []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def kontrast(a, b):
    def l(h):
        h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c]
        return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]
    x, y = sorted([l(a), l(b)], reverse=True)
    return (x + .05) / (y + .05)


with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)
    url = lambda s: f"http://127.0.0.1:8812/app.html?szenario={s}"
    # Handy: Finger als Zeiger, damit die Regeln für pointer:coarse greifen
    c = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
    pg = c.new_page(); pg.set_default_timeout(15000); err = []
    pg.on("pageerror", lambda e: err.append(str(e)))

    print("Handy quer")
    pg.goto(url("leitung-unterwegs-standort")); pg.wait_for_function("typeof S !== 'undefined' && S.gps.pos")
    pruef(pg.locator("#quer").is_hidden(), "hochkant: kein Hinweis")
    pg.set_viewport_size({"width": 844, "height": 390}); pg.wait_for_timeout(250)
    pruef(pg.locator("#quer").is_hidden(), "nach 0,25 s quer: noch kein Hinweis")
    pg.wait_for_timeout(500)
    pruef(pg.locator("#quer").is_visible(), "nach 0,75 s quer: Hinweis da")
    pg.screenshot(path=SHOTS + "quer.png")
    pg.set_viewport_size({"width": 390, "height": 844}); pg.wait_for_timeout(200)
    pruef(pg.locator("#quer").is_hidden(), "wieder hochkant: Hinweis weg")
    pg.evaluate("kalStart(); render()"); pg.set_viewport_size({"width": 844, "height": 390}); pg.wait_for_timeout(800)
    pruef(pg.locator("#quer").is_hidden(), "beim Einmessen: kein Hinweis")
    pg.evaluate("kalEnde(false); render()"); pg.set_viewport_size({"width": 390, "height": 844}); pg.wait_for_timeout(200)

    print("Wir sind da")
    t = pg.inner_text("#tcheck"); weit = "weit" in pg.get_attribute("#tcheck", "class")
    pruef(weit and t.startswith("Noch") and "Einchecken" in t, f"245 m entfernt: {t!r}, Nebenknopf {weit}")
    pg.evaluate("window.__gps(50.104441 + 30 / 111320, 14.419553, 8)"); pg.wait_for_timeout(300)
    t = pg.inner_text("#tcheck"); weit = "weit" in pg.get_attribute("#tcheck", "class")
    pruef(t == "Wir sind da" and not weit, f"30 m entfernt: {t!r}, Hauptknopf")
    fg = pg.evaluate("getComputedStyle(document.querySelector('#tcheck')).color")
    pruef(fg == "rgb(15, 27, 24)", f"Knopfschrift dunkel ({fg}), Kontrast {kontrast('#0F1B18', '#EE5F1B'):.1f}:1")
    pg.screenshot(path=SHOTS + "nah.png", full_page=True)

    print("Ziffern und Route")
    pruef(pg.locator(".lock .wheel.schluss").count() == 1 and "Schlussziffer" in pg.inner_text("#app"), "sechste Ziffer abgesetzt und erklärt")
    pg.goto(url("selfie-offen")); pg.wait_for_selector("[data-act=t-selfie]")
    done = pg.locator(".route b.done").count(); fest = pg.evaluate("S.team.state.digits.filter(d => d != null).length")
    pruef(done == fest == 2, f"offenes Selfie: {done} Punkte erledigt, {fest} Ziffern")

    print("Zifferntastatur")
    pg.goto(url("leitung-raetsel")); pg.wait_for_selector("#tans")
    im = pg.get_attribute("#tans", "inputmode"); num = pg.evaluate("S.team.state.station.numeric")
    pruef(num and im == "numeric", f"Lösung 1098: numeric={num}, inputmode={im}")

    print("Testmodus im laufenden Spiel")
    pg.set_viewport_size({"width": 1180, "height": 820})
    # ohne Platz: mit Platz lehnt der Server das Einschalten ab (Nachtrag 32, geprüft in bugjagd2.py)
    pg.goto(url("admin-stationen-ohne-platz")); pg.wait_for_selector("[data-act=a-test]")
    pg.click("[data-act=a-test]"); pg.wait_for_selector(".dialog")
    pruef("laufenden Spiel" in pg.inner_text(".dialog") and not pg.evaluate("S.admin.state.testMode"), "Rückfrage statt sofort einschalten")
    pg.click("#dlgok"); pg.wait_for_function("!S.admin.confirm")
    pruef("Testmodus ist an" in pg.inner_text("#app"), "nach Bestätigen: eingeschaltet")
    pg.set_viewport_size({"width": 844, "height": 390}); pg.wait_for_timeout(800)
    pruef(pg.locator("#quer").is_hidden(), "Spielleitung quer: kein Hinweis")
    pruef(not err, f"keine Skriptfehler {err[:2]}")
    b.close()
srv.shutdown()
print("FEHLER: " + str(len(fehler)) if fehler else "OK")
sys.exit(1 if fehler else 0)
