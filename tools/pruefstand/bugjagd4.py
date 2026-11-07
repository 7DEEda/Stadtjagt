#!/usr/bin/env python3
"""
Funde der Bugjagd vom 07.11.2026 (SPIEL.md §25), soweit sie die Oberfläche betreffen. Ohne Datenbank, gegen mock.js
(Port 8879). Die Serverseite der Funde 2, 3 und 7 prüft der Probelauf bugjagd4_db.py.

    python tools/pruefstand/bugjagd4.py          alle
    python tools/pruefstand/bugjagd4.py 1 2      nur diese Teile

Teile:
  1  Fund 1: Rückfrage "Testmodus im laufenden Spiel einschalten" und Reiter Einstellungen nennen den Wechsel auf die
     Teststation, den Rückweg über "Fortschritt zurücksetzen" und "Freischalten"
  2  Funde 2 und 3: Beenden und Zurücksetzen prüfen den frischen Status (zweites Leitungsgerät), sonst wie bisher
  3  Fund 4: Ziffer-Rückfrage nur für Stationen der aktiven Route, im Testmodus "Ziffer der Teststation ändern"
  4  Fund 5: Escape im Ziffer-Dialog holt das Getippte zurück wie "Abbrechen"
  5  Fund 6: später Standort-Rückruf schreibt nicht ins Formular einer anderen Station, kein Fehler ohne Formular;
     Startpunkt ebenso; ein pünktlicher Rückruf schreibt weiter
  6  Fund 7: Koordinaten nur als ganze Dezimalzahl (DMS, "N 50.08", 500 abgelehnt), leer bleibt erlaubt
  7  Fund 12: Rückfragen "Fortschritt zurücksetzen" und "Alle Teilnehmenden löschen" nennen die Gruppenfotos
Haken in mock.js: window.__WELT (Spielstand im Speicher der Seite). Im Vordergrund mit Timeout aufrufen, etwa
`timeout 240 python tools/pruefstand/bugjagd4.py`. Am Ende steht OK oder FEHLT.
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
import abschluss  # noqa: E402

shoot.bauen()
from playwright.sync_api import sync_playwright  # noqa: E402


class Leise(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


PORT = 8879
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
APP = f"http://127.0.0.1:{PORT}/app.html?szenario="
NUR = {int(x) for x in sys.argv[1:] if x.isdigit()}
an = lambda n: not NUR or n in NUR  # noqa: E731
fehler, err = [], []

# Ortung von Hand auslösen: getCurrentPosition (das Objekt aus mock.js) merkt sich die Rückrufe, __geoFix(i) ruft den
# i-ten auf. Nach dem Laden setzen, mock.js legt navigator.geolocation selbst an.
GEO = """() => {
window.__geo = [];
navigator.geolocation.getCurrentPosition = (ok, nein) => { window.__geo.push({ ok, nein }); };
window.__geoFix = (i, lat, lng) => window.__geo[i].ok({ coords: { latitude: lat, longitude: lng, accuracy: 5 } });
}"""


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def neu(b, szenario, vorab=None, breite=1180):
    pg = b.new_page(viewport={"width": breite, "height": 860})
    pg.set_default_timeout(15000)
    pg.route("**/vendor/leaflet-1.9.4/**", lambda r: r.abort())
    pg.on("pageerror", lambda e: err.append(f"{szenario}: {e}"))
    if vorab:
        pg.add_init_script(vorab)
    pg.goto(APP + szenario)
    pg.wait_for_function("window.__fertig === true", timeout=30000)
    return pg


def warte(pg, js, ms=8000):
    try:
        pg.wait_for_function(js, timeout=ms)
        return True
    except Exception:
        return False


def dialog(pg):
    return pg.inner_text(".dialog") if pg.locator(".dialog").count() else ""


def reiter(pg, tab):
    pg.click(f"[data-act=a-tab][data-tab={tab}]")
    pg.wait_for_timeout(300)


def bearbeiten(pg, sid):
    pg.click(f"[data-act=a-edit][data-id='{sid}']")
    pg.wait_for_selector("#e-digit")


def log(pg, fn):
    return pg.evaluate(f"window.__RPC_LOG.filter(x => x === '{fn}').length")


vorher = abschluss.merken()
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)

    if an(1):
        print("1 Testmodus im laufenden Spiel (Fund 1, nur Texte)")
        pg = neu(b, "admin-stationen-ohne-platz")
        pruef(pg.evaluate("!!S.admin.state.testStation && S.admin.state.status === 'running' && !S.admin.state.testMode"),
              "Ausgangslage: Spiel läuft, Testmodus aus, Teststation da")
        t = pg.inner_text("#app")
        pruef("Alle Teams spielen dann nur die Teststation" in t and "nur „Fortschritt zurücksetzen“ zurück" in t
              and "„Freischalten“ im Reiter Karte und Teams" in t, "Reiter Einstellungen nennt Teststation, Rückweg und Freischalten")
        pg.click("[data-act=a-test][data-on='1']")
        pg.wait_for_selector(".dialog")
        d = dialog(pg)
        pruef("Testmodus im laufenden Spiel einschalten" in d, "Rückfrage erscheint")
        pruef("Alle Teams wechseln sofort auf die Teststation und sehen ihre echte Station nicht mehr" in d, "Rückfrage nennt den Wechsel auf die Teststation")
        pruef("führt nur „Fortschritt zurücksetzen“ zurück" in d and "alle Gruppenfotos" in d, "Rückfrage nennt den Rückweg und was er löscht")
        pruef("„Freischalten“ nehmen" in d and "Karte und Teams" in d, "Rückfrage verweist bei GPS-Problemen auf Freischalten")
        pruef("–" not in d and "—" not in d, "keine Gedankenstriche")
        pg.click("#dlgok")
        pruef(warte(pg, "window.__RPC_LOG.includes('admin_set_test_mode')"), "Einschalten nach der Rückfrage geht weiter")
        # ohne Teststation: der alte Text
        pg.evaluate("S.admin.state = Object.assign({}, S.admin.state, { testStation: null, testMode: false }); render()")
        pg.click("[data-act=a-test][data-on='1']")
        pg.wait_for_selector(".dialog")
        d = dialog(pg)
        pruef("Jedes Team kann überall einchecken" in d and "Teststation" not in d, "ohne Teststation der bisherige Text")
        pruef("Alle Teams spielen dann nur die Teststation" not in pg.inner_text("#app"), "Einstellungen ohne Teststation ohne den Satz")
        pg.close()

    if an(2):
        print("2 Beenden und Zurücksetzen mit frischem Status (Funde 2 und 3)")
        pg = neu(b, "admin-stationen")
        pg.click("[data-act=a-finish]")
        pg.wait_for_selector(".dialog")
        pg.evaluate("window.__WELT.status = 'drawn'")       # Gerät B hat inzwischen zurückgesetzt
        pg.click("#dlgok")
        pruef(warte(pg, "!S.admin.confirm"), "Dialog geht zu")
        pruef(log(pg, "admin_finish") == 0, "admin_finish nicht aufgerufen")
        t = pg.evaluate("S.msg && S.msg.text") or ""
        pruef(t.startswith("Nichts beendet: das Spiel läuft nicht mehr.") and pg.evaluate("S.msg.type") == "err", f"Meldung: {t!r}")
        pruef(pg.evaluate("S.admin.state.status") == "drawn" and pg.locator("[data-act=a-finish]").count() == 0,
              "frischer Stand übernommen, kein Beenden-Knopf mehr")
        pg.close()

        pg = neu(b, "admin-stationen")
        pg.click("[data-act=a-finish]")
        pg.wait_for_selector(".dialog")
        pg.click("#dlgok")
        pruef(warte(pg, "window.__RPC_LOG.includes('admin_finish')"), "laufendes Spiel: admin_finish wie bisher")
        pg.close()

        for status, soll in (("registration", 0), ("running", 1)):
            pg = neu(b, "admin-stationen")
            reiter(pg, "danger")
            pg.click(".btn[data-act=a-danger][data-key=reset]")
            pg.wait_for_selector("#dlgword")
            pg.fill("#dlgword", "LÖSCHEN")
            pg.evaluate(f"window.__WELT.status = '{status}'")
            pg.click("#dlgok")
            warte(pg, "!S.admin.confirm")
            pg.wait_for_timeout(300)
            pruef(log(pg, "admin_reset") == soll, f"Zurücksetzen, Stand inzwischen {status}: admin_reset {'aufgerufen' if soll else 'nicht aufgerufen'}")
            if not soll:
                t = pg.evaluate("S.msg && S.msg.text") or ""
                pruef(t.startswith("Nichts zurückgesetzt") and pg.evaluate("S.msg.type") == "err", f"Meldung: {t!r}")
            pg.close()

    if an(3):
        print("3 Ziffer-Rückfrage nur für die aktive Route (Fund 4)")
        pg = neu(b, "admin-stationen")
        ts = pg.evaluate("S.admin.state.testStation")
        echt1 = pg.evaluate("S.admin.state.stations[0]")
        pruef(pg.evaluate("S.admin.state.route") == "echt" and ts["position"] == 1, "Ausgangslage: echte Route aktiv, Teststation auf Position 1")
        pruef(pg.evaluate("S.admin.state.teams.filter(t => (t.solved || 0) >= 1).length") > 0, "Teams haben Station 1 gelöst")
        bearbeiten(pg, ts["id"])
        pg.fill("#e-digit", str((ts["digit"] + 3) % 10))
        pg.evaluate("window.__GESPEICHERT = null")
        pg.click("[data-act=a-save]")
        pruef(warte(pg, "window.__GESPEICHERT"), "Teststation bei echter Route: gespeichert")
        pruef(pg.locator(".dialog").count() == 0, "Teststation bei echter Route: keine Rückfrage")
        # Testmodus an: jetzt zählt solved die Teststation
        pg.evaluate("S.admin.state = Object.assign({}, S.admin.state, { route: 'test', testMode: true }); render()")
        bearbeiten(pg, echt1["id"])
        pg.fill("#e-digit", str((echt1["digit"] + 3) % 10))
        pg.evaluate("window.__GESPEICHERT = null")
        pg.click("[data-act=a-save]")
        pruef(warte(pg, "window.__GESPEICHERT") and pg.locator(".dialog").count() == 0, "echte Station 1 im Testmodus: keine Rückfrage")
        ts = pg.evaluate("S.admin.state.testStation")
        pg.evaluate("S.admin.state = Object.assign({}, S.admin.state, { route: 'test', testMode: true }); render()")
        bearbeiten(pg, ts["id"])
        pg.fill("#e-digit", str((ts["digit"] + 4) % 10))
        pg.click("[data-act=a-save]")
        pruef(warte(pg, "!!document.querySelector('.dialog')"), "Teststation im Testmodus: Rückfrage")
        d = dialog(pg)
        pruef("Ziffer der Teststation ändern" in d and "die Teststation schon gelöst" in d and "Station 1" not in d, f"Text nennt die Teststation ({d[:120]!r})")
        pg.close()

    if an(4):
        print("4 Escape im Ziffer-Dialog (Fund 5)")
        pg = neu(b, "admin-stationen")
        s1 = pg.evaluate("S.admin.state.stations[0]")
        bearbeiten(pg, s1["id"])
        neu_z = str((s1["digit"] + 5) % 10)
        pg.fill("#e-digit", neu_z)
        pg.fill("#e-hint", "Neuer Hinweis Escape")
        pg.fill("#e-riddle", "Neues Rätsel Escape")
        pg.click("[data-act=a-save]")
        pg.wait_for_selector(".dialog")
        pg.keyboard.press("Escape")
        pg.wait_for_selector(".dialog", state="detached")
        pruef(pg.input_value("#e-digit") == neu_z and pg.input_value("#e-hint") == "Neuer Hinweis Escape"
              and pg.input_value("#e-riddle") == "Neues Rätsel Escape", "Escape: Getipptes steht noch")
        pruef(pg.evaluate("S.admin.edit") == s1["id"], "Formular bleibt offen")
        pg.close()

    if an(5):
        print("5 Später Standort-Rückruf (Fund 6)")
        pg = neu(b, "admin-stationen")
        pg.evaluate(GEO)
        st = pg.evaluate("S.admin.state.stations.map(s => ({ id: s.id, lat: s.lat, lng: s.lng }))")
        bearbeiten(pg, st[0]["id"])
        pg.click("[data-act=a-here]")
        pg.click("[data-act=a-cancel]")
        pg.wait_for_timeout(200)
        bearbeiten(pg, st[1]["id"])
        lat2 = pg.input_value("#e-lat")
        pg.evaluate("__geoFix(0, 48.1, 11.5)")
        pg.wait_for_timeout(200)
        pruef(pg.input_value("#e-lat") == lat2 and "48.1" not in pg.input_value("#e-lng"), "Station 2 behält ihre Koordinaten")
        pg.click("[data-act=a-here]")
        pg.click("[data-act=a-cancel]")
        pg.wait_for_timeout(200)
        bearbeiten(pg, st[1]["id"])                       # dieselbe Station neu geöffnet
        pg.evaluate("__geoFix(1, 48.2, 11.6)")
        pg.wait_for_timeout(200)
        pruef(pg.input_value("#e-lat") == lat2, "neu geöffnetes Formular derselben Station bleibt unberührt")
        pg.click("[data-act=a-here]")
        pg.click("[data-act=a-cancel]")
        pg.wait_for_timeout(200)
        n_err = len(err)
        pg.evaluate("__geoFix(2, 48.3, 11.7)")           # kein Formular offen
        pg.wait_for_timeout(200)
        pruef(len(err) == n_err, "ohne Formular kein Fehler")
        bearbeiten(pg, st[0]["id"])
        pg.click("[data-act=a-here]")
        pg.evaluate("__geoFix(3, 50.111111, 14.222222)")   # pünktlich
        pg.wait_for_timeout(200)
        pruef(pg.input_value("#e-lat") == "50.111111" and pg.input_value("#e-lng") == "14.222222", "pünktlicher Rückruf schreibt weiter")
        # Startpunkt
        pg.click("[data-act=a-cancel]")
        pg.wait_for_timeout(200)
        if pg.locator("[data-act=a-startpkt-edit]").count():
            pg.locator("[data-act=a-startpkt-edit]").first.click()
            pg.wait_for_selector("#sp-lat")
            pg.click("[data-act=a-startpkt-hier]")
            pg.click("[data-act=a-startpkt-cancel]")
            pg.wait_for_timeout(200)
            n_err = len(err)
            pg.evaluate("__geoFix(4, 48.4, 11.8)")
            pg.wait_for_timeout(200)
            pruef(len(err) == n_err, "Startpunkt: später Rückruf ohne Formular ohne Fehler")
            pg.locator("[data-act=a-startpkt-edit]").first.click()
            pg.wait_for_selector("#sp-lat")
            pg.click("[data-act=a-startpkt-hier]")
            pg.evaluate("__geoFix(5, 50.333333, 14.444444)")
            pg.wait_for_timeout(200)
            pruef(pg.input_value("#sp-lat") == "50.333333", "Startpunkt: pünktlicher Rückruf schreibt weiter")
        else:
            pruef(False, "Knopf a-startpkt-edit fehlt")
        pg.close()

    if an(6):
        print("6 Koordinaten nur als Dezimalzahl (Fund 7)")
        pg = neu(b, "admin-stationen")
        s1 = pg.evaluate("S.admin.state.stations[0]")
        bearbeiten(pg, s1["id"])
        for lat, lng, art, name in (("50°05'15.0\"N", "14.4212", "zahl", "Grad, Minuten, Sekunden"), ("N 50.0875", "14.4212", "zahl", "„N 50.0875“"),
                                    ("50.0875", "14.4212 E", "zahl", "Länge mit E"), ("500", "14.4212", "bereich", "Breite 500"),
                                    ("50.0875", "-200", "bereich", "Länge -200"), ("50.0875", "", "zahl", "Länge leer")):
            pg.fill("#e-lat", lat)
            pg.fill("#e-lng", lng)
            pg.evaluate("window.__GESPEICHERT = null")
            pg.click("[data-act=a-save]")
            pg.wait_for_timeout(300)
            t = pg.evaluate("S.msg && S.msg.text") or ""
            soll = "Grad, Minuten und Sekunden gehen nicht" if art == "zahl" else "zwischen -90 und 90"
            pruef(pg.evaluate("window.__GESPEICHERT") is None and soll in t and pg.evaluate("S.msg.type") == "err", f"{name}: abgelehnt ({t[:70]!r})")
            pruef(pg.input_value("#e-lat") == lat, f"{name}: Eingabe bleibt stehen")
        for lat, lng, soll, name in (("50,0875", "14,4212", [50.0875, 14.4212], "deutsche Kommazahlen"),
                                     ("50.0875, 14.4212", "", [50.0875, 14.4212], "Paar im Feld Breite"),
                                     ("-33.8", "151.2", [-33.8, 151.2], "negative Breite"), ("", "", [None, None], "beide leer")):
            if pg.locator("#e-lat").count() == 0:
                bearbeiten(pg, s1["id"])
            pg.fill("#e-lat", lat)
            pg.fill("#e-lng", lng)
            pg.evaluate("window.__GESPEICHERT = null")
            pg.click("[data-act=a-save]")
            ok = warte(pg, "window.__GESPEICHERT", 4000)
            g = pg.evaluate("window.__GESPEICHERT") or {}
            pruef(ok and [g.get("p_lat"), g.get("p_lng")] == soll, f"{name}: gespeichert als {[g.get('p_lat'), g.get('p_lng')]}")
        pg.close()

    if an(7):
        print("7 Rückfragen nennen die Gruppenfotos (Fund 12)")
        pg = neu(b, "admin-fotos")
        n = pg.evaluate("S.admin.state.photoCount")
        pruef(n > 0, f"Ausgangslage: {n} Fotos")
        reiter(pg, "danger")
        t = pg.inner_text("#app")
        pruef("Gruppenfotos" in t and f"{n}" in t, "Tabelle „Was gerade gespeichert ist“ führt die Fotos")
        for key in ("reset", "people"):
            pg.click(f".btn[data-act=a-danger][data-key={key}]")
            pg.wait_for_selector(".dialog")
            d = dialog(pg)
            foto = "das Gruppenfoto" if n == 1 else f"alle {n} Gruppenfotos"
            pruef(foto in d and "Lade die Fotos vorher im Reiter Fotos herunter" in d, f"{key}: Rückfrage nennt {foto} und das Herunterladen")
            pg.click("[data-act=a-dlg-cancel]")
            pg.wait_for_selector(".dialog", state="detached")
        pg.close()
        pg = neu(b, "admin-stationen")
        if pg.evaluate("S.admin.state.photoCount || 0") == 0:
            reiter(pg, "danger")
            pg.click(".btn[data-act=a-danger][data-key=reset]")
            pg.wait_for_selector(".dialog")
            pruef("Gruppenfoto" not in dialog(pg), "ohne Fotos kein Fotohinweis")
        pg.close()

    for e in err:
        pruef(False, "Fehler auf der Seite: " + e)
    print("OK" if not fehler else f"FEHLT ({len(fehler)})")
    abschluss.ende(fehler, vorher)
