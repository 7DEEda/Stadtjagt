#!/usr/bin/env python3
"""
Funde 2 bis 16 der Bugjagd vom 03.10.2026 im Prüfstand, ohne Datenbank.

    python tools/pruefstand/bugjagd2.py          alle
    python tools/pruefstand/bugjagd2.py 5 8      nur diese Funde

Spiel (app.html mit mock.js, Port 8832), Geräte-Test (geraete-test.html, Port 8833, device_test_save abgefangen)
und tools/testlaeufe.py mit erfundenen Zeilen. Die Datenbank-Seite der Funde 9, 12, 14 und 16 prüft
bugjagd2_db.py. Im Vordergrund mit Timeout aufrufen. Am Ende steht OK oder FEHLER.
"""
import contextlib
import functools
import http.server
import io
import json
import pathlib
import re
import sys
import tempfile
import threading

sys.stdout.reconfigure(encoding="utf-8")
HIER = pathlib.Path(__file__).resolve().parent
REPO = HIER.parent.parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(REPO / "tools"))
import shoot  # noqa: E402

shoot.bauen()
from playwright.sync_api import sync_playwright  # noqa: E402


class Leise(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8832), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
srv2 = http.server.ThreadingHTTPServer(("127.0.0.1", 8833), functools.partial(Leise, directory=str(REPO)))
threading.Thread(target=srv2.serve_forever, daemon=True).start()
APP = "http://127.0.0.1:8832/app.html?szenario="
fehler = []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def neu(b, szenario, breit=False, vorher=None, uhr=False):
    pg = b.new_page(viewport={"width": 1180, "height": 820} if breit else {"width": 390, "height": 844})
    pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: err.append(f"{szenario}: {e}"))
    if vorher:
        pg.add_init_script(vorher)
    if uhr:
        pg.clock.install()
    pg.goto(APP + szenario)
    pg.wait_for_function("window.__fertig === true", timeout=30000)
    return pg


def bearbeiten(pg, sid):
    pg.click(f"[data-act=a-edit][data-id='{sid}']")
    pg.wait_for_selector("#e-lat")


NUR = set(sys.argv[1:])   # etwa "python bugjagd2.py 5 8": nur diese Funde


def an(*nummern):
    return not NUR or any(str(n) in NUR for n in nummern)


err = []
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)

    if an(2):
        print("Fund 2: Koordinatenpaar im Feld Breite")
        pg = neu(b, "admin-stationen", breit=True)
        pg.click("[data-act=a-tab][data-tab=stations]")
        bearbeiten(pg, "s3")
        pruef(pg.input_value("#e-lng") == "14.420089", "Länge steht vorbelegt (Wasserturm Letná)")
        pg.click("[data-act=a-cancel]")
        for eingabe, lat, lng, text in (("50.101000, 14.425000", 50.101, 14.425, "Paar mit Punkt"),
                                         ("50,101000, 14,425000", 50.101, 14.425, "Paar mit Komma"),
                                         ("50,0875", 50.0875, 14.420089, "einzelne deutsche Zahl, Länge aus dem Feld")):
            bearbeiten(pg, "s3")
            # der Prüfstand übernimmt jedes Speichern: die alte Länge für jeden Fall wieder hineinschreiben
            pg.fill("#e-lng", "14.420089"); pg.fill("#e-lat", eingabe)
            mitte = pg.evaluate("ekMitte()")
            pruef(mitte and abs(mitte[0] - lat) < 1e-6 and abs(mitte[1] - lng) < 1e-6, f"{text}: ekMitte {mitte}")
            pg.evaluate("window.__GESPEICHERT = null")
            pg.click("[data-act=a-save]"); pg.wait_for_function("window.__GESPEICHERT")
            g = pg.evaluate("window.__GESPEICHERT")
            pruef(abs(g["p_lat"] - lat) < 1e-6 and abs(g["p_lng"] - lng) < 1e-6, f"{text}: gespeichert {g['p_lat']}, {g['p_lng']}")
        pg.close()
        pg = neu(b, "admin-teststation", breit=True)
        pg.click("[data-act=a-tab][data-tab=stations]"); pg.wait_for_selector("#teststation [data-act=a-edit]")
        pg.click("#teststation [data-act=a-edit]"); pg.wait_for_selector("#e-lat")
        pg.fill("#e-lat", "52.47100, 13.46300"); pg.evaluate("window.__GESPEICHERT = null")
        pg.click("[data-act=a-save]"); pg.wait_for_function("window.__GESPEICHERT")
        g = pg.evaluate("window.__GESPEICHERT")
        pruef(abs(g["p_lat"] - 52.471) < 1e-6 and abs(g["p_lng"] - 13.463) < 1e-6, f"Teststation: Paar gewinnt ({g['p_lat']}, {g['p_lng']})")
        pg.close()

    if an(3):
        print("Fund 3: Enter im Stationsformular speichert")
        pg = neu(b, "admin-stationen", breit=True)
        pg.click("[data-act=a-tab][data-tab=stations]")
        bearbeiten(pg, "s1")
        pruef(pg.evaluate("S.admin.karte && S.admin.karte.aus") is True, "Station ohne Verschlüsselung (Normalfall)")
        pg.fill("#e-name", "Planetarium Prag Nord"); pg.evaluate("window.__GESPEICHERT = null")
        pg.focus("#e-name"); pg.keyboard.press("Enter"); pg.wait_for_timeout(600)
        g = pg.evaluate("window.__GESPEICHERT")
        pruef(bool(g) and g["p_name"] == "Planetarium Prag Nord" and g["p_reveal_start"] is None,
              f"Enter in Name speichert ohne Verschlüsselung ({g and (g['p_name'], g['p_reveal_start'])})")
        pg.click("[data-act=a-startpkt-edit][data-route=echt]"); pg.wait_for_selector("#sp-name")
        pg.fill("#sp-name", "Hoteleingang"); pg.evaluate("window.__START = null")
        pg.focus("#sp-name"); pg.keyboard.press("Enter"); pg.wait_for_timeout(600)
        pruef((pg.evaluate("window.__START") or {}).get("p_name") == "Hoteleingang", "Enter im Startpunkt speichert")
        pg.close()

    if an(4):
        print("Fund 4: veralteter felderFrisch-Merker")
        pg = neu(b, "admin-stationen", breit=True)
        pg.click("[data-act=a-tab][data-tab=stations]")
        bearbeiten(pg, "s3")
        pg.fill("#e-name", "Getippter Name"); pg.click("[data-act=a-here]"); pg.wait_for_timeout(500)
        pg.evaluate("render()")
        pruef(pg.input_value("#e-name") == "Getippter Name", f"nach Standort übernehmen und Neuzeichnen steht das Getippte ({pg.input_value('#e-name')!r})")
        pg.close()
        pg = neu(b, "anmeldung-leer")
        pg.fill("#pname", "Max Muster"); pg.click("[data-act=thema]"); pg.evaluate("render()")
        pruef(pg.input_value("#pname") == "Max Muster", "nach Hell/Dunkel und Neuzeichnen steht der Name")
        pg.close()

    if an(5):
        print("Fund 5: leitungOhneCode im Funkloch")
        pg = neu(b, "leitung-ohne-code", vorher="window.__funkloch = true")
        t = pg.inner_text("#app")
        pruef("Keine Verbindung" in t, "Netzfehler steht als Meldung da")
        pruef("Du leitest gerade kein Team" not in t, "kein falsches „Du leitest gerade kein Team“")
        pg.evaluate("window.__funkloch = false")
        try:
            pg.wait_for_function("S.team.code === 'FUCHS-4821'", timeout=13000)
            pruef(True, "im 10-s-Takt neu versucht, Code ist da")
        except Exception:
            pruef(False, "im 10-s-Takt neu versucht, Code ist da")
        pg.close()

    if an(6):
        print("Fund 6: rpc mit Zeitlimit")
        pg = neu(b, "leitung-raetsel", uhr=True)
        pg.evaluate("window.__haengt = ['submit_answer']")
        pg.fill("#tans", "1960"); pg.click("[data-act=t-answer]"); pg.wait_for_timeout(300)
        pruef(pg.is_disabled("[data-act=t-answer]"), "Knopf gesperrt, solange die Anfrage hängt")
        pg.clock.fast_forward(14000); pg.wait_for_timeout(300)
        pruef(pg.is_disabled("[data-act=t-answer]"), "nach 14 s noch gesperrt")
        pg.clock.fast_forward(2000); pg.wait_for_timeout(500)
        pruef(not pg.is_disabled("[data-act=t-answer]") and "Keine Verbindung" in pg.inner_text("#app"),
              "nach 15 s abgebrochen wie ein Netzfehler, Knopf wieder frei")
        pg.close()
        pg = neu(b, "leitung-unterwegs-standort", uhr=True)
        pg.evaluate("window.__haengt = ['report_position']; S.gps.lastSent = 0; S.gps.lastSentPos = null; maybeReport(); 0")
        pg.wait_for_timeout(200)
        pruef(pg.evaluate("S.gps.meldet") is True, "maybeReport wartet auf die Antwort")
        pg.clock.fast_forward(16000); pg.wait_for_timeout(300)
        pruef(pg.evaluate("S.gps.meldet") is False, "maybeReport nach dem Zeitlimit wieder frei")
        pg.close()
        pg = neu(b, "admin-fotos", breit=True, uhr=True)
        pg.evaluate("window.__haengt = ['admin_photos']; window.__ausgang = null; rpc('admin_photos', { p_pin: '4711' }).then(() => window.__ausgang = 'ok', e => window.__ausgang = e.message); 0")
        pg.clock.fast_forward(20000); pg.wait_for_timeout(200)
        pruef(pg.evaluate("window.__ausgang") is None, "Foto-Aufruf nach 20 s noch nicht abgebrochen")
        pg.clock.fast_forward(41000); pg.wait_for_timeout(300)
        pruef("Keine Verbindung" in str(pg.evaluate("window.__ausgang")), f"Foto-Aufruf nach 60 s abgebrochen ({pg.evaluate('window.__ausgang')})")
        pg.close()

    if an(8):
        print("Fund 8: Meldung „Keine Verbindung“ verschwindet")
        pg = neu(b, "leitung-unterwegs", vorher="window.__funkloch = true")
        pruef("Keine Verbindung" in pg.inner_text("#app"), "erster Abruf scheitert: Meldung steht da")
        pg.evaluate("window.__funkloch = false")
        try:
            pg.wait_for_function("S.team.state && !/Keine Verbindung/.test(document.getElementById('app').textContent)", timeout=13000)
            pruef(True, "nach dem nächsten erfolgreichen Abruf ist die Meldung weg")
        except Exception:
            pruef(False, "nach dem nächsten erfolgreichen Abruf ist die Meldung weg")
        pg.close()

    if an(9):
        print("Fund 9: Anmeldung im Funkloch wiederholbar")
        pg = neu(b, "anmeldung-leer")
        pg.evaluate("window.__verlieren = ['register_participant']")
        pg.fill("#pname", "Neue Person"); pg.click("[data-act=pub-reg]"); pg.wait_for_timeout(500)
        tok = pg.evaluate("localStorage.getItem('sj.token')")
        pruef(bool(tok) and re.fullmatch(r"[0-9a-f]{64}", tok or "") is not None, f"Schlüssel liegt vor dem Aufruf auf dem Handy ({tok and tok[:8]}…)")
        pruef("Keine Verbindung" in pg.inner_text("#app"), "verlorene Antwort: Netzfehler")
        pg.evaluate("window.__verlieren = null")
        pg.fill("#pname", "Neue Person"); pg.click("[data-act=pub-reg]"); pg.wait_for_timeout(700)
        reg = pg.evaluate("window.__REG")
        pruef(pg.evaluate("localStorage.getItem('sj.name')") == "Neue Person", f"zweiter Versuch: angemeldet ({pg.inner_text('#app')[:80]!r})")
        pruef(len(reg) == 2 and reg[0].get("p_token") == tok and reg[1].get("p_token") == tok, "beide Versuche mit demselben Schlüssel")
        pruef(pg.evaluate("localStorage.getItem('sj.token')") == tok, "Schlüssel bleibt")
        pg.close()
        pg = neu(b, "anmeldung-leer")
        pg.fill("#pname", "Jonas Keller"); pg.click("[data-act=pub-reg]"); pg.wait_for_timeout(500)
        pruef("schon angemeldet" in pg.inner_text("#app"), "fremder Name: weiter abgelehnt")
        pruef(pg.evaluate("localStorage.getItem('sj.token')") is None, "abgelehnt: kein Schlüssel bleibt liegen")
        pg.close()
        pg = neu(b, "anmeldung-leer", vorher="window.__ALTE_DB = true")
        pg.fill("#pname", "Alte Datenbank"); pg.click("[data-act=pub-reg]"); pg.wait_for_timeout(700)
        pruef(pg.evaluate("[localStorage.getItem('sj.name'), localStorage.getItem('sj.token')]") == ["Alte Datenbank", "tok-neu"],
              "Datenbank ohne Nachtrag 32: zweiter Aufruf ohne p_token, Schlüssel vom Server")
        pg.close()

    if an(10):
        print("Fund 10: watchPosition Code 2")
        pg = neu(b, "leitung-unterwegs-standort")
        pruef(pg.evaluate("S.gps.on && !!S.gps.pos"), "Standort läuft")
        pg.evaluate("window.__gpsFehler(2)"); pg.wait_for_timeout(200)
        z = pg.evaluate("[S.gps.on, !!S.gps.pos, !!S.gps.posAt, S.gps.err]")
        pruef(z[0] and z[1] and z[2] and bool(z[3]), f"mit Standort: Beobachter bleibt, Position bleibt, Hinweis ({z})")
        pg.close()
        pg = neu(b, "leitung-unterwegs")
        pg.click("[data-act=t-gps]"); pg.wait_for_timeout(400)
        pg.evaluate("window.__gpsFehler(2)"); pg.wait_for_timeout(200)
        z = pg.evaluate("[S.gps.on, S.gps.err]")
        pruef(z[0] is False and "keinen Standort" in (z[1] or ""), f"ohne je einen Standort: wie bisher beendet ({z})")
        pg.close()

    if an(15):
        print("Fund 15: Merker je Route und Spielbeginn")
        pg = neu(b, "name-geheim-ohne-gps")
        r = pg.evaluate("""() => { const st = S.team.state, s = st.station;
          const test = Object.assign({}, st, { testMode: true, startedAt: '2026-10-03T10:00:00.000Z' });
          const echt = Object.assign({}, st, { testMode: false, startedAt: '2026-10-04T08:00:00.000Z' });
          geheimStand(test, s); for (const k in geheimSim) geheimSim[k] = Date.now() - 60000;
          const a = geheimStand(test, s), e = geheimStand(echt, s);
          fotoMerken(test, { pos: 1, foto: 'x', thumb: 'y' });
          return [a.offen, a.n, e.offen, LS.getItem(fotoSchluessel(echt, 1)), fotoSchluessel(test, 1) !== fotoSchluessel(echt, 1)]; }""")
        pruef(r[0] == r[1] and r[1] > 0, f"Testlauf entschlüsselt ganz ({r[0]} von {r[1]})")
        pruef(r[2] == 0, f"echte Route nach dem Testlauf: Name wieder verschlüsselt ({r[2]})")
        pruef(r[3] is None and r[4], "Testfoto wird nicht als Foto der echten Station nachgereicht")
        pg.close()

    if an(16):
        print("Fund 16: leere Antwort")
        pg = neu(b, "leitung-raetsel")
        pg.evaluate("window.__RPC_LOG.length = 0")
        pg.click("[data-act=t-answer]"); pg.wait_for_timeout(500)
        pruef("submit_answer" not in pg.evaluate("window.__RPC_LOG"), "leeres Feld: nichts gesendet")
        pruef("Bitte gebt eine Antwort ein." in pg.inner_text("#app"), "Hinweis steht da")
        pruef(pg.evaluate("S.team.state.failedAttempts") == 0, "kein Fehlversuch")
        pg.close()
        pg = neu(b, "testmodus-raetsel")
        pg.evaluate("window.__RPC_LOG.length = 0")
        pg.click("[data-act=t-answer]"); pg.wait_for_timeout(600)
        pruef("submit_answer" in pg.evaluate("window.__RPC_LOG") and pg.evaluate("S.team.state.solvedCount") == 2,
              "Testmodus: leeres Feld zählt weiter als richtig")
        pg.close()

    if an(14):
        print("Fund 14: Testmodus ausschalten mit Plätzen")
        pg = neu(b, "admin-teststation", breit=True)
        pg.click("[data-act=a-tab][data-tab=stations]"); pg.wait_for_selector("[data-act=a-test]")
        pg.click("[data-act=a-test]"); pg.wait_for_timeout(600)
        t = pg.inner_text("[data-act=a-test] >> xpath=..")
        pruef("Im Testlauf gibt es schon Plätze" in t, f"Meldung des Servers steht beim Knopf ({t[-120:]!r})")
        pruef(pg.evaluate("S.admin.state.testMode") is True, "Testmodus bleibt an")
        pg.close()
        # Entscheidung 04.10.2026: im laufenden Spiel mit Plätzen auch nicht einschalten (Adler hat Platz 1)
        pg = neu(b, "admin-stationen", breit=True)
        pg.click("[data-act=a-tab][data-tab=stations]"); pg.wait_for_selector("[data-act=a-test]")
        pg.click("[data-act=a-test]"); pg.wait_for_selector("#dlgok"); pg.click("#dlgok"); pg.wait_for_timeout(600)
        t = pg.inner_text("#app")
        pruef("Im laufenden Spiel gibt es schon Plätze" in t, "Einschalten mit Plätzen: Meldung des Servers steht da")
        pruef(pg.evaluate("S.admin.state.testMode") is False, "Testmodus bleibt aus")
        pg.close()

    if an(11, 13):
        print("Fund 11 und 13: Geräte-Test")
        for ua, soll, text in ((shoot.UA_IPAD, "Tablet", "iPad mit mobiler Kennung ist ein Tablet"), (shoot.UA_IPHONE, "Telefon", "iPhone bleibt ein Telefon")):
            ctx = b.new_context(viewport={"width": 820, "height": 1180}, user_agent=ua)
            ctx.add_init_script("Object.defineProperty(Navigator.prototype, 'userAgentData', { get: () => undefined })")
            pg = ctx.new_page(); pg.on("pageerror", lambda e: err.append(f"geraete-test {soll}: {e}"))
            pg.goto("http://127.0.0.1:8833/geraete-test.html")
            r = pg.evaluate("GT_TESTS.tests.find(t => t.id === 'umgebung').lauf().then(x => x.mess['Geräteart'])")
            pruef(r == soll, f"{text} ({r})")
            ctx.close()
        ctx = b.new_context(viewport={"width": 390, "height": 844})
        ctx.add_init_script("Object.defineProperty(window, 'localStorage', { get() { throw new DOMException('gesperrt', 'SecurityError'); } })")
        pg = ctx.new_page(); pg.on("pageerror", lambda e: err.append(f"geraete-test gesperrt: {e}"))
        gesendet = []

        def speichern(route):
            gesendet.append(json.loads(route.request.post_data))
            route.fulfill(json={"ok": True, "serverTime": "2026-10-04T12:00:00Z"})
        pg.route("**/rest/v1/rpc/device_test_save", speichern)
        pg.goto("http://127.0.0.1:8833/geraete-test.html")
        pg.evaluate("lauf.begonnen = new Date().toISOString(); speichern()")
        pg.wait_for_timeout(1500)
        pruef(len(gesendet) == 1 and gesendet[0]["p_key"] == pg.evaluate("lauf.key"), f"gesperrter Speicher: der laufende Lauf geht trotzdem raus ({len(gesendet)})")
        pruef(pg.evaluate("document.getElementById('speicher').className") == "ok", "Stand: gespeichert")
        ctx.close()
    pruef(not err, f"keine Skriptfehler {err[:3]}")
    b.close()
srv.shutdown(); srv2.shutdown()

if an(12):
    print("Fund 12: testlaeufe.py mit kaputten Zeilen")
    import sql  # noqa: E402
    import testlaeufe  # noqa: E402

    GUT = {"suite": 20, "label": "Telefon", "ua": "x", "bilanz": {"ok": 1}, "tests": {"umgebung": {"art": "ok", "wert": "Telefon"}}}
    ZEILEN = [
        {"run_key": "GUTGUTGUT001", "created_at": "2026-10-04T10:00:00Z", "updated_at": "", "suite_version": 20, "label": "Telefon", "payload": GUT},
        {"run_key": "KAPUTT000001", "created_at": "2026-10-04T10:01:00Z", "updated_at": "", "suite_version": 0, "label": "", "payload": {"tests": "x"}},
        {"run_key": "KAPUTT000002", "created_at": "2026-10-04T10:02:00Z", "updated_at": "", "suite_version": 0, "label": "", "payload": {"bilanz": "x", "tests": {}}},
        {"run_key": "KAPUTT000003", "created_at": "2026-10-04T10:03:00Z", "updated_at": "", "suite_version": 0, "label": "", "payload": {"tests": {"umgebung": "x"}, "bilanz": {}}},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        alt = (sql.ausfuehren, testlaeufe.ZIEL)
        sql.ausfuehren = lambda *a, **k: json.loads(json.dumps(ZEILEN))
        testlaeufe.ZIEL = pathlib.Path(tmp)
        aus = io.StringIO()
        try:
            with contextlib.redirect_stdout(aus):
                testlaeufe.main()
            abbruch = None
        except Exception as e:  # noqa: BLE001
            abbruch = repr(e)
        finally:
            sql.ausfuehren, testlaeufe.ZIEL = alt
        pruef(abbruch is None, f"läuft durch ({abbruch})")
        ue = pathlib.Path(tmp, "UEBERSICHT.md")
        pruef(ue.exists() and "GUTG" in ue.read_text(encoding="utf-8"), "Übersicht mit dem guten Lauf geschrieben")
        pruef(all(k in aus.getvalue() for k in ("KAPUTT000001", "KAPUTT000002", "KAPUTT000003")), f"kaputte Zeilen gemeldet ({aus.getvalue().strip()[:200]!r})")

print("FEHLER: " + str(len(fehler)) if fehler else "OK")
sys.exit(1 if fehler else 0)
