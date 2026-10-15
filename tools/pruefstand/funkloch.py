#!/usr/bin/env python3
"""
Ausfallsicherheit, Abschnitt 3: Eingaben im Funkloch, Serverfehler wie Funkloch.

    python tools/pruefstand/funkloch.py          alle
    python tools/pruefstand/funkloch.py 2 3      nur diese Teile

Spiel (app.html mit mock.js, Port 8868). mock.js bildet die Regeln der Migration 20261016090000 nach (last_wrong,
p_position, Check-in ohne neue Entfernung) und kennt den Schalter window.__netz: "weg" (Anfrage kommt nie an),
"antwort-weg" (Server führt aus, Antwort geht verloren), "503" (Server weg, HTML), "html" (Seite statt JSON).
Der 10-s-Abruf läuft über die Playwright-Uhr. Ohne Leaflet-Seite. Im Vordergrund mit Timeout aufrufen.
Am Ende steht OK oder FEHLT.
"""
import base64
import functools
import http.server
import pathlib
import sys
import threading

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


PORT = 8868
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
APP = f"http://127.0.0.1:{PORT}/app.html?szenario="
NUR = {int(x) for x in sys.argv[1:] if x.isdigit()}
an = lambda n: not NUR or n in NUR  # noqa: E731
fehler, err = [], []
OHNE = "Keine Verbindung. Tippt noch mal, sobald ihr Netz habt. Doppelt zählt nichts."
WIEDER = "Wieder Netz. Tippt noch mal."


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def neu(b, szenario):
    pg = b.new_page(viewport={"width": 390, "height": 844})
    pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: err.append(f"{szenario}: {e}"))
    pg.clock.install()
    pg.goto(APP + szenario)
    pg.wait_for_function("window.__fertig === true", timeout=30000)
    return pg


def takt(pg):
    """Ein 10-s-Abruf: Uhr vorstellen, Antworten abwarten."""
    pg.clock.fast_forward(10000)
    pg.wait_for_timeout(700)


def leiste(pg):
    m = pg.locator("#leiste .msg")
    return m.first.inner_text().strip() if m.count() else ""


def meldung(pg):
    m = pg.locator("#app .msg")
    return " | ".join(x.strip() for x in m.all_inner_texts())


def tippen(pg, sel):
    pg.click(sel)
    pg.wait_for_function(f"!document.querySelector('{sel}') || !document.querySelector('{sel}').disabled", timeout=20000)
    pg.wait_for_timeout(200)


vorher = abschluss.merken()
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)

    if an(1):
        print("1 Einchecken")
        pg = neu(b, "funkloch-station")
        pg.wait_for_selector("[data-act=t-check]:not([disabled])")
        pg.evaluate("window.__netz = 'weg'")
        tippen(pg, "[data-act=t-check]")
        pruef(leiste(pg) == OHNE, f"Funkloch: Meldung in der Leiste ({leiste(pg)!r})")
        pruef(pg.locator("[data-act=t-check]").count() == 1 and not pg.is_disabled("[data-act=t-check]"), "Knopf gleich wieder frei")
        pg.evaluate("window.__netz = null"); takt(pg)
        pruef(leiste(pg) == WIEDER, f"Netz zurück, nichts angekommen: {WIEDER!r} ({leiste(pg)!r})")
        pruef(pg.locator("#leiste .msg.info").count() == 1, "als Hinweis, nicht als Fehler")
        pg.evaluate("window.__netz = 'antwort-weg'")
        tippen(pg, "[data-act=t-check]")
        pruef(leiste(pg) == OHNE, "Antwort verloren: dieselbe Meldung")
        pg.evaluate("window.__netz = null"); takt(pg)
        pruef(leiste(pg) == "Angekommen. Das Rätsel ist frei.", f"Abgleich: Check-in kam an ({leiste(pg)!r})")
        pruef(pg.locator("#tans").count() == 1, "Rätsel ist frei")
        pg.close()

        print("1b Check-in wiederholt, GPS ist inzwischen gesprungen")
        pg = neu(b, "funkloch-station")
        pg.wait_for_selector("[data-act=t-check]:not([disabled])")
        pg.evaluate("window.__netz = 'antwort-weg'")
        tippen(pg, "[data-act=t-check]")
        pg.evaluate("window.__netz = null; window.__gps(50.10894, 14.419553, 8)")
        pg.wait_for_timeout(300)
        if pg.locator("[data-act=t-check]").count():
            tippen(pg, "[data-act=t-check]")
        pruef(leiste(pg) == "Angekommen. Das Rätsel ist frei.", f"Wiederholung 500 m weiter: Angekommen ({leiste(pg)!r})")
        pg.close()

    if an(2):
        print("2 Falsche Antwort")
        pg = neu(b, "leitung-raetsel")
        pg.evaluate("window.__netz = 'weg'")
        pg.fill("#tans", "12"); tippen(pg, "[data-act=t-answer]")
        pruef(leiste(pg) == OHNE, f"Funkloch: Meldung ({leiste(pg)!r})")
        pruef(pg.input_value("#tans") == "12", "Getipptes bleibt im Feld")
        pg.evaluate("window.__netz = null"); takt(pg)
        pruef(leiste(pg) == WIEDER, f"Netz zurück, nichts angekommen ({leiste(pg)!r})")
        pruef(pg.input_value("#tans") == "12", "Getipptes bleibt auch nach dem Abruf")
        pg.evaluate("window.__netz = 'antwort-weg'")
        tippen(pg, "[data-act=t-answer]")
        pruef(leiste(pg) == OHNE, "Antwort verloren: dieselbe Meldung")
        pg.evaluate("window.__netz = null"); takt(pg)
        pruef(leiste(pg) == WIEDER, f"Abgleich ohne Phasenwechsel: {WIEDER!r} ({leiste(pg)!r})")
        pruef(pg.evaluate("S.team.state.failedAttempts") == 1, "die falsche Antwort zählt einmal")
        tippen(pg, "[data-act=t-answer]")
        pruef(leiste(pg) == "Leider falsch. Noch 2 Versuche.", f"nochmal getippt: wie beim ersten Mal ({leiste(pg)!r})")
        pruef(pg.evaluate("S.team.state.failedAttempts") == 1, "dieselbe falsche Antwort zweimal zählt einmal")
        pg.close()

    if an(3):
        print("3 Richtige Antwort, Antwort geht verloren")
        pg = neu(b, "leitung-raetsel")
        pg.evaluate("window.__netz = 'antwort-weg'")
        pg.fill("#tans", "1098"); tippen(pg, "[data-act=t-answer]")
        pruef(leiste(pg) == OHNE, "Meldung")
        pruef((pg.evaluate("window.__ANTWORTEN") or [{}])[-1].get("p_position") == 2, "Antwort nennt die Station (p_position 2)")
        pg.evaluate("window.__netz = null"); takt(pg)
        pruef(leiste(pg) == "Richtig. Station 2 gelöst, eure Ziffer: 7.", f"Abgleich: Erfolg mit Ziffer ({leiste(pg)!r})")
        pruef(pg.evaluate("!!S.neueZiffer && S.neueZiffer.i === 1"), "neue Ziffer markiert")
        pg.close()

        print("3b Richtige Antwort wiederholt, bevor der Abruf kam")
        pg = neu(b, "leitung-raetsel")
        pg.evaluate("window.__netz = 'antwort-weg'")
        pg.fill("#tans", "1098"); tippen(pg, "[data-act=t-answer]")
        pg.evaluate("window.__netz = null")
        tippen(pg, "[data-act=t-answer]")
        pruef(leiste(pg) == "Richtig. Station 2 gelöst, eure Ziffer: 7.", f"Erfolg statt 'Erst am Ort einchecken' ({leiste(pg)!r})")
        pruef("einchecken" not in meldung(pg), "kein 'Erst am Ort einchecken'")
        takt(pg)
        pruef(leiste(pg) == "Richtig. Station 2 gelöst, eure Ziffer: 7.", f"der nächste Abruf überschreibt den Erfolg nicht ({leiste(pg)!r})")
        pg.close()

        print("3c Datenbank ohne Migration (PGRST202)")
        pg = neu(b, "leitung-raetsel")
        pg.evaluate("window.__ALTE_DB = true")
        pg.fill("#tans", "1098"); tippen(pg, "[data-act=t-answer]")
        pruef(leiste(pg) == "Richtig. Station 2 gelöst, eure Ziffer: 7.", f"Rückfall ohne p_position ({leiste(pg)!r})")
        pg.close()

    if an(4):
        print("4 Koffer-Code, Antwort geht verloren")
        pg = neu(b, "funkloch-koffer")
        pg.wait_for_selector("#tfin")
        pg.evaluate("window.__netz = 'antwort-weg'")
        pg.fill("#tfin", "371955"); tippen(pg, "[data-act=t-final]")
        pruef(leiste(pg) == OHNE, f"Meldung ({leiste(pg)!r})")
        pg.evaluate("window.__netz = null"); takt(pg)
        t = meldung(pg)
        pruef("Platz 2" in t and "Koffer" in t, f"Abgleich: Platz-Meldung ({t!r})")
        pg.close()

    if an(5):
        print("5 Serverfehler wie Funkloch")
        pg = neu(b, "leitung-unterwegs")
        for art in ("503", "html"):
            pg.evaluate(f"window.__netz = '{art}'; window.__fehler = null; rpc('team_state', {{ p_code: 'FUCHS-4821' }}).catch(e => window.__fehler = {{ text: e.message, netz: !!e.netz }})")
            pg.wait_for_function("window.__fehler !== null")
            f = pg.evaluate("window.__fehler")
            pruef(f["netz"] and f["text"].startswith("Keine Verbindung"), f"{art}: wie Funkloch ({f})")
        pg.evaluate("window.__netz = null"); takt(pg)
        z0 = pg.evaluate("S.zuletzt")
        pg.evaluate("window.__netz = '503'")
        for _ in range(4):
            takt(pg)
        pruef(pg.evaluate("S.zuletzt") == z0, "Serverfehler setzt S.zuletzt nicht")
        pg.evaluate("document.querySelector('[data-act=pub-hoch]') || 0"); pg.clock.fast_forward(1000); pg.wait_for_timeout(300)
        stand = pg.locator("#stand")
        pruef(stand.count() == 1 and stand.is_visible() and stand.inner_text().startswith("Stand "), "oben steht 'Stand hh:mm'")
        pg.evaluate("refresh()"); pg.wait_for_timeout(500)
        pruef("Keine Verbindung" in meldung(pg) and pg.evaluate("S.msg && S.msg.kind") == "netz", "Neuladen bei Serverfehler: Meldung Keine Verbindung")
        pg.evaluate("window.__netz = null"); takt(pg)
        pruef("Keine Verbindung" not in meldung(pg), "nach dem nächsten guten Abruf ist sie weg")
        pg.evaluate("window.__fehler = null; window.__haengt = null; rpc('nicht_da', {}).catch(e => window.__fehler = { text: e.message, netz: !!e.netz })")
        pg.wait_for_function("window.__fehler !== null")
        pruef(not pg.evaluate("window.__fehler.netz"), "ein 4xx mit JSON bleibt ein normaler Fehler")
        pg.close()

    if an(6):
        print("6 Selfie hängt nicht auf 'Erneut senden'")
        pg = neu(b, "selfie-offen")
        jpg = base64.b64decode(pg.evaluate("""() => { const c = document.createElement("canvas"); c.width = 800; c.height = 600; const g = c.getContext("2d");
          g.fillStyle = "#4a8"; g.fillRect(0, 0, 800, 600); return c.toDataURL("image/jpeg", .9).split(",")[1]; }"""))
        with pg.expect_file_chooser() as fc:
            pg.click("[data-act=t-selfie]")
        fc.value.set_files({"name": "selfie.jpg", "mimeType": "image/jpeg", "buffer": jpg})
        pg.wait_for_selector("img.foto")
        pg.evaluate("window.__netz = 'antwort-weg'")
        tippen(pg, "[data-act=t-selfie-ok]")
        pruef("Erneut senden" in pg.inner_text("#app"), "Funkloch: Erneut senden steht da")
        pruef(pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('sj.foto.')).length") == 1, "Foto liegt auf dem Handy (Erkennung über e.netz)")
        pg.evaluate("window.__netz = null"); takt(pg)
        pruef("Erneut senden" not in pg.inner_text("#app") and pg.evaluate("S.selfie") is None, "Abruf zeigt das Foto: Erneut senden ist weg")
        pruef(meldung(pg).startswith("Foto ist drin."), f"Meldung 'Foto ist drin.' ({meldung(pg)!r})")
        pg.close()

        print("6b Ohne Foto weiter, Foto wartet")
        pg = neu(b, "selfie-offen")
        with pg.expect_file_chooser() as fc:
            pg.click("[data-act=t-selfie]")
        fc.value.set_files({"name": "selfie.jpg", "mimeType": "image/jpeg", "buffer": jpg})
        pg.wait_for_selector("img.foto")
        pg.evaluate("window.__funkloch = true")
        tippen(pg, "[data-act=t-selfie-ok]")
        pg.evaluate("window.__funkloch = 'nur-foto'")
        tippen(pg, "[data-act=t-selfie-skip]")
        t = meldung(pg)
        pruef(t.endswith("Das Foto wird nachgereicht, sobald das Netz reicht."), f"Text ohne 'wir' ({t!r})")
        pg.close()

    if an(7):
        print("7 Andere Aktionen behalten ihre Meldung")
        pg = neu(b, "leitung-raetsel")
        pg.evaluate("window.__netz = 'weg'; S.team.state.station.tipAvailable = true; render()")
        if pg.locator("[data-act=t-tip]").count():
            tippen(pg, "[data-act=t-tip]")
            pruef("Keine Verbindung. Wartet kurz und tippt noch mal." in meldung(pg), f"Tipp: bisherige Meldung ({meldung(pg)!r})")
        pruef(pg.evaluate("S.offen") is None, "kein Abgleich für andere Aktionen")
        pg.close()

    pruef(not err, "keine Fehler auf der Seite" + (f": {err[:3]}" if err else ""))
    print("FEHLT:\n  " + "\n  ".join(fehler) if fehler else "OK")
    abschluss.ende(fehler, vorher)
