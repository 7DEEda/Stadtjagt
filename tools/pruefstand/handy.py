"""Handy-Durchsicht (01.11.2026): Übergabe-Fenster, Leitung im Kopf, Kompass-Hinweis, Akku-Zeile, Ende, Fehlversuch,
Marke im Team-Reiter, Zähler der Reiter. Port 8874, alles bei 360 px Breite.

Im Wegwerf-Container aufrufen (Regel vom 31.10.2026). Am Ende steht OK oder FEHLT.
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


PORT = 8874
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
APP = f"http://127.0.0.1:{PORT}/app.html?szenario="
fehler, err = [], []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def neu(b, szenario):
    pg = b.new_page(viewport={"width": 360, "height": 780})
    pg.set_default_timeout(15000)
    pg.route("**/vendor/leaflet-1.9.4/**", lambda r: r.abort())
    pg.on("pageerror", lambda e: err.append(f"{szenario}: {e}"))
    pg.goto(APP + szenario)
    pg.wait_for_function("window.__fertig === true", timeout=30000)
    return pg


def text(pg, sel="#app"):
    return pg.inner_text(sel).replace(" ", " ")


with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)

    print("1 Übergabe-Fenster")
    pg = neu(b, "akku-leitung")
    pg.click(".ftabs [data-tab=team]")
    pg.click("[data-act=t-abgeben-frage]")
    z = pg.evaluate("waehlbar(S.team.state).map(g => [g.name, g.verbunden, g.akku, g.laedt])")
    pruef(z[0][0] == "Emre Demir" and z[0][3], f"ein ladendes Handy steht vorn ({z[0]})")
    pruef(all(a[1] or not c[1] for a, c in zip(z, z[1:])), "offene Handys vor nicht offenen")
    pruef(pg.locator(".wahl button[aria-pressed=true] em").inner_text() == "beste Wahl", "vorgewählt und mit „beste Wahl“ markiert")
    pruef(text(pg, "#tabgeben") == "An Emre übergeben" and not pg.locator("#tabgeben").is_disabled(), "Knopf nennt die Person")
    pruef(pg.locator(".wahl button.aus").count() >= 1 and "aus" in pg.locator(".wahl button").last.get_attribute("class"), "„Handy nicht offen“ gedämpft und unten")
    pg.click(".wahl button:has-text('Jonas')")
    pruef(text(pg, "#tabgeben") == "An Jonas übergeben", "eigene Wahl ändert den Knopf")
    pg.evaluate("__AKKUS['Emre Demir'] = { akku: 99, laedt: true, at: Date.now() }; uebergabeListeNachziehen(S.team.state)")
    pruef(pg.evaluate("S.team.wahl") == "Jonas Keller", "eigene Wahl bleibt, wenn sich die Liste ändert")
    pg.keyboard.press("Escape")
    # Niemand mit belegbar gutem Akku: nichts vorwählen
    pg.evaluate("""S.team.state.geraete = S.team.state.geraete.map(g => ({ ...g, akku: null, laedt: null })); S.team.uebergabe = null; render()""")
    pg.click("[data-act=t-abgeben-frage]")
    pruef(pg.evaluate("S.team.wahl") is None and pg.locator("#tabgeben").is_disabled() and text(pg, "#tabgeben") == "Übergeben", "ohne Akkustände keine Vorwahl")
    pruef(pg.locator(".wahl em").count() == 0, "ohne Akkustände keine „beste Wahl“")
    pg.close()

    print("2 Leitung im Kopf")
    pg = neu(b, "mitglied-auf-teamleitung")
    pg.close()
    pg = neu(b, "leitung-unterwegs")
    z = pg.evaluate("""() => { S.myName = 'Jemand'; S.team.state.team.leaderName = 'Maximilian-Alexander Schröder'; render();
      const e = document.querySelector('.kopf .sub'); return [e.textContent, e.scrollWidth <= e.clientWidth, document.documentElement.scrollWidth <= innerWidth]; }""")
    pruef(z[0] == "Maximilian-Alexander Schröder leitet", f"Name zuerst ({z[0]})")
    pruef(z[1] and z[2], f"nichts abgeschnitten, kein Seitenüberlauf ({z})")
    pg.close()

    print("3 Kompass-Hinweis")
    pg = neu(b, "leitung-unterwegs")
    pg.evaluate("S.gps.on = true; S.gps.kompass = 'abgelehnt'; render()")
    t = text(pg, "#inhalt")
    pruef(pg.locator("#kchip").is_hidden(), "keine Plakette")
    pruef("Erlauben" in t and "Laufrichtung" in t and "beenden" not in t, "Kasten ohne den Browser-Satz")
    h = pg.evaluate("[...document.querySelectorAll('#inhalt .msg.info')].find(e => e.textContent.includes('Erlauben')).firstChild.parentElement.getBoundingClientRect().height")
    pruef(h < 150, f"Kasten kurz ({h:.0f} px, mit Knopf)")
    pg.click("[data-act=t-hilfe]")
    pruef("Browser ganz beenden" in text(pg, ".blatt"), "Browser-Satz steht im Hilfe-Blatt")
    pg.close()

    print("4 Akku-Zeile")
    pg = neu(b, "akku-leitung")
    pg.evaluate("window.__akku && window.__akku(18)")
    pg.wait_for_function("S.team.uebergabe === 'akku20'")
    pg.click(".blatt .row2 .btn.alt")
    z = pg.evaluate("""() => { const e = document.querySelector('#akkuhinweis'), k = e.querySelector('.btn');
      return [e.getBoundingClientRect().height, k.getBoundingClientRect().height, k.textContent, k.getAttribute('aria-label')]; }""")
    pruef(z[1] >= 44 and z[2] == "Abgeben" and z[3] == "Leitung abgeben", f"Knopf ({z})")
    pruef(z[0] <= 90, f"Zeile statt Kasten ({z[0]:.0f} px)")
    pg.close()

    print("5 Ende")
    pg = neu(b, "leitung-beendet")
    pg.wait_for_function("document.querySelector('tr.eigen')")
    t = text(pg)
    pruef("Euer Stand: 4 von 5 Ziffern, nicht im Ziel." in t, "Stand in der Karte")
    z = pg.evaluate("[document.querySelector('.panel h2').textContent, document.querySelector('tr.eigen').textContent.includes('(ihr)')]")
    pruef(z[0] == "Das Spiel ist vorbei" and z[1], f"Karte oben, eigene Zeile hervorgehoben ({z})")
    pg.evaluate("S.team.state.solvedCount = 0; render()")
    pruef("Euer Stand: keine Ziffer, nicht im Ziel." in text(pg), "ohne Ziffern")
    pg.close()
    pg = neu(b, "leitung-platz5")
    pg.close()

    print("6 Fehlversuch")
    pg = neu(b, "leitung-raetsel")
    pruef("Fehlversuche: 0 von 3, dann 2 Minuten Pause" in text(pg, "#leiste"), "Regel steht vor dem ersten Fehlversuch")
    pg.fill("#tans", "falsch")
    pg.click("[data-act=t-answer]")
    pg.wait_for_selector("#leiste .msg.err")
    t = text(pg, "#leiste")
    pruef("Leider falsch. Noch 2 Versuche, dann 2 Minuten Pause." in t and "Fehlversuche:" not in t, f"nur der rote Satz ({t!r})")
    pg.close()

    print("7 und 9 Team-Reiter und Zähler")
    pg = neu(b, "leitung-unterwegs")
    pg.click(".ftabs [data-tab=team]")
    z = pg.evaluate("""() => { const c = document.querySelector('.names .chip.leit'); const l = c.parentElement;
      return [c.textContent, c.getBoundingClientRect().top >= l.firstChild.parentElement.getBoundingClientRect().top + 15]; }""")
    pruef(z[0] == "Leitung" and z[1], f"Marke unter dem Namen ({z})")
    z = pg.evaluate("[...document.querySelectorAll('.ftabs .badge')].map(e => [getComputedStyle(e).fontSize, e.getBoundingClientRect().right <= e.parentElement.getBoundingClientRect().right])")
    pruef(all(x == ["13px", True] for x in z), f"Zähler 13 px und innerhalb des Reiters ({z})")
    pg.close()
    b.close()

pruef(not err, f"keine Seitenfehler {err}")
srv.shutdown()
print("FEHLT: " + "; ".join(fehler) if fehler else "OK")
sys.exit(1 if fehler else 0)
