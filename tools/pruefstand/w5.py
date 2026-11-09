#!/usr/bin/env python3
"""
W5 (03.11.2026): Eingaben nur noch mit dem Geräte-Schlüssel der Teamleitung oder, am Notweg-Tablet, mit der Admin-PIN.
Ohne Datenbank, gegen mock.js (Port 8877). Der Probelauf gegen die Datenbank ist w5_eingaben_db.py.

    python tools/pruefstand/w5.py          alle
    python tools/pruefstand/w5.py 2 4      nur diese Teile

Teile: 1 Teamleitung mit Schlüssel (alle acht Eingaben tragen p_token, keine PIN), 2 Notweg: Code von Hand braucht die
PIN (leer, falsch, richtig), 3 Notweg mit PIN schon im Tab: kein PIN-Feld, 4 Notweg-Tablet nach Neustart des Browsers
(Seite "Admin-PIN fehlt"), 5 Teamleitung tippt den eigenen Code: ohne PIN, 6 Datenbank ohne die Migration (PGRST202:
einmal ohne p_token und p_pin), 7 Quelltext: keine der acht Eingaben ruft rpc() direkt, 8 Bildschirmfotos,
9 Sicherheitsprüfung 07.11.: Leitungs-Handy mit PIN im Tab schickt sie nicht (H4), geänderte PIN am Notweg-Tablet
führt zur Seite "Admin-PIN fehlt" (S2), Abmelden nimmt die PIN mit (beides auf einer Datenbank ohne Notweg-Schlüssel),
Text der Ablehnung mit "App neu laden" (H1), 10 Notweg-Schlüssel (09.11.): Schlüssel übersteht den Neustart des
Browsers, abgelaufener Schlüssel führt zur Seite "Admin-PIN fehlt", neues Team holt einen neuen Schlüssel, Abmelden
löscht ihn auf dem Server, Datenbank ohne admin_notweg: PIN im Tab wie vorher.
Seit dem Notweg-Schlüssel (09.11.) tauscht der Notweg die PIN gegen einen Schlüssel für ein Team (sj.notweg); die PIN
bleibt nicht im Tab (Teile 2 bis 4).
Haken in mock.js: window.__W5 (prüft wie der Server), __OHNE_W5 (Datenbank ohne Migration), __OHNE_NOTWEG (ohne
admin_notweg), __NOTWEG (gültige Schlüssel), __EINGABE_ARGS.
Im Vordergrund mit Timeout aufrufen, etwa `timeout 300 python tools/pruefstand/w5.py`. Am Ende steht OK oder FEHLT.
"""
import functools
import http.server
import pathlib
import re
import sys
import threading

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


PORT = 8877
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
APP = f"http://127.0.0.1:{PORT}/app.html?szenario="
NUR = {int(x) for x in sys.argv[1:] if x.isdigit()}
an = lambda n: not NUR or n in NUR  # noqa: E731
fehler, err = [], []
QUELLE = (REPO / "index.html").read_text(encoding="utf-8")
W5 = "Eingeben kann nur die Teamleitung auf ihrem eigenen Handy. Wenn du die Leitung bist: App neu laden."
EINGABEN = ["check_in", "submit_answer", "reveal_tip", "submit_final", "team_selfie", "team_selfie_skip",
            "team_set_leader", "report_position"]
SHOTS = HIER / "shots"
SHOTS.mkdir(exist_ok=True)

# Alle acht Eingaben über den Helfer der App, mit Argumenten, die der Mock versteht; gesammelt wird der Fehlertext
ALLE_JS = """async () => {
  const c = S.team.code, raus = {};
  const rufe = {
    check_in: { p_code: c, p_lat: 50.1, p_lng: 14.4, p_acc: 8 },
    submit_answer: { p_code: c, p_answer: 'x', p_position: 2 },
    reveal_tip: { p_code: c },
    submit_final: { p_code: c, p_value: '0', p_lat: 50.1, p_lng: 14.4, p_acc: 8 },
    team_selfie: { p_code: c, p_position: 1, p_photo: 'x', p_thumb: 'x' },
    team_selfie_skip: { p_code: c, p_position: 1 },
    team_set_leader: { p_code: c, p_name: (S.team.state && S.team.state.team.leaderName) || 'Anna Berger' },
    report_position: { p_code: c, p_lat: 50.1, p_lng: 14.4, p_acc: 8, p_kompass: null } };
  for (const [fn, a] of Object.entries(rufe)) {
    try { await eingabeRpc(fn, a); raus[fn] = null; } catch (e) { raus[fn] = String(e.message); }
  }
  return raus;
}"""


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def neu(b, szenario, vorab="window.__W5 = true;"):
    pg = b.new_page(viewport={"width": 390, "height": 844})
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


def args(pg, fn=None):
    a = pg.evaluate("window.__EINGABE_ARGS || []")
    return [x for x in a if fn is None or x["fn"] == fn]


def notweg_oeffnen(pg):
    pg.click("[data-act=t-codefeld]")
    pg.fill("#tcode", "FUCHS-4821")


vorher = abschluss.merken()
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)

    if an(1):
        print("1 Teamleitung mit Geräte-Schlüssel")
        pg = neu(b, "leitung-ohne-code")
        pruef(warte(pg, "S.team.code === 'FUCHS-4821' && S.team.state"), "Anna holt den Code über den Schlüssel")
        anna = pg.evaluate("localStorage.getItem('sj.token')")
        pg.evaluate("window.__EINGABE_ARGS = []")
        raus = pg.evaluate(ALLE_JS)
        pruef(all(v != W5 for v in raus.values()), f"keine der acht Eingaben an W5 gescheitert ({raus})")
        a = args(pg)
        pruef(sorted({x["fn"] for x in a}) == sorted(EINGABEN), f"alle acht gesendet ({sorted({x['fn'] for x in a})})")
        pruef(anna and all(x.get("p_token") == anna for x in a), "jede Eingabe trägt den Schlüssel der Leitung")
        pruef(all("p_pin" in x and x["p_pin"] is None for x in a), "keine PIN vom Handy der Leitung")
        # echter Weg über die Oberfläche: Tipp und GPS-Meldung
        pg.evaluate("window.__EINGABE_ARGS = []")
        pg.evaluate("ACT['t-tip']().then(render)")
        pruef(warte(pg, "(window.__EINGABE_ARGS || []).some(x => x.fn === 'reveal_tip')"), "Tipp über die Oberfläche geht raus")
        pruef(all(x.get("p_token") == anna for x in args(pg, "reveal_tip")), "Tipp mit Schlüssel")
        pg.close()

    if an(2):
        print("2 Notweg: Team-Code von Hand braucht die Admin-PIN")
        pg = neu(b, "mitglied-auf-teamleitung")
        notweg_oeffnen(pg)
        pruef(pg.locator("#tpin").count() == 1, "PIN-Feld unter dem Team-Code")
        pruef("Eingeben geht nur mit der Admin-PIN." in pg.inner_text("#app"), "Hinweis auf die PIN")
        pg.click("[data-act=t-login]")
        pruef(warte(pg, "S.msg && /Admin-PIN eingeben/.test(S.msg.text)"), "ohne PIN: Meldung, nicht angemeldet")
        pruef(pg.evaluate("S.team.code") is None and pg.evaluate("localStorage.getItem('sj.code')") is None, "ohne PIN kein Code gemerkt")
        pg.fill("#tcode", "FUCHS-4821")
        pg.fill("#tpin", "1234")
        pg.click("[data-act=t-login]")
        pruef(warte(pg, "S.msg && S.msg.text === 'Die Admin-PIN stimmt nicht.'"), "falsche PIN: Meldung")
        pruef(pg.evaluate("S.team.code") is None and pg.evaluate("sessionStorage.getItem('sj.pin')") is None, "falsche PIN: nichts gemerkt")
        pg.fill("#tcode", "FUCHS-4821")
        pg.fill("#tpin", "4711")
        pg.click("[data-act=t-login]")
        pruef(warte(pg, "S.team.code === 'FUCHS-4821' && S.team.state"), "richtige PIN: angemeldet")
        pruef(pg.evaluate("localStorage.getItem('sj.hand')") == "1", "Merker sj.hand gesetzt")
        nw = pg.evaluate("localStorage.getItem('sj.notweg')")
        pruef(bool(nw) and nw.startswith("nw-"), f"Notweg-Schlüssel gemerkt ({nw!r})")
        pruef(pg.evaluate("sessionStorage.getItem('sj.pin')") is None and pg.evaluate("localStorage.getItem('sj.pin')") is None
              and pg.evaluate("S.admin.pin") is None, "die PIN bleibt nicht im Tab (S1)")
        pg.evaluate("window.__EINGABE_ARGS = []")
        raus = pg.evaluate(ALLE_JS)
        pruef(all(v is None for v in raus.values()), f"mit dem Schlüssel gehen alle acht durch ({raus})")
        pruef(all(x.get("p_token") == nw and x.get("p_pin") is None for x in args(pg)), "jede Eingabe trägt den Schlüssel, keine PIN")
        pg.evaluate("location.hash = '#/admin'")
        pruef(warte(pg, "document.querySelector('#apin')"), "#/admin im selben Tab fragt nach der PIN")
        pg.close()

        # Ohne PIN von Hand in die Leitungsansicht gezwungen: der Server (hier der Mock) lehnt ab
        pg = neu(b, "mitglied-auf-teamleitung")
        pg.evaluate("S.team.code = 'FUCHS-4821'; localStorage.setItem('sj.code', 'FUCHS-4821')")
        raus = pg.evaluate(ALLE_JS)
        pruef(all(v == W5 for v in raus.values()), f"Mitglied mit Code, ohne PIN: alle acht abgelehnt ({set(raus.values())})")
        pg.close()

    if an(3):
        print("3 Notweg mit PIN schon im Tab")
        pg = neu(b, "mitglied-auf-teamleitung")
        # wie nach der Anmeldung der Spielleitung in diesem Tab (mock.js setzt den sessionStorage je Szenario neu)
        pg.evaluate("sessionStorage.setItem('sj.pin', '4711'); S.admin.pin = SS.getItem('sj.pin'); render()")
        pruef(pg.evaluate("S.admin.pin") == "4711", "PIN der Spielleitung im Tab")
        notweg_oeffnen(pg)
        pruef(pg.locator("#tpin").count() == 0, "kein PIN-Feld, die PIN ist schon da")
        pg.click("[data-act=t-login]")
        pruef(warte(pg, "S.team.code === 'FUCHS-4821' && S.team.state"), "angemeldet ohne zweite PIN")
        pruef(str(pg.evaluate("localStorage.getItem('sj.notweg')") or "").startswith("nw-"), "PIN aus dem Tab gegen den Schlüssel getauscht")
        pg.evaluate("window.__EINGABE_ARGS = []")
        pg.evaluate(ALLE_JS)
        pruef(all(x.get("p_pin") is None and str(x.get("p_token")).startswith("nw-") for x in args(pg)), "Eingaben mit Schlüssel, ohne PIN")
        pg.close()

    if an(4):
        print("4 Notweg-Tablet nach Neustart des Browsers")
        pg = neu(b, "leitung-unterwegs")
        pruef(warte(pg, "document.querySelector('.ph')"), "Leitungsansicht steht")
        pg.evaluate("localStorage.setItem('sj.hand', '1'); S.admin.pin = null; sessionStorage.removeItem('sj.pin'); render()")
        pruef(pg.locator(".ph").count() == 0 and "Admin-PIN fehlt" in pg.inner_text("#app"), "ohne PIN: Seite Admin-PIN fehlt statt der Ansicht")
        pruef(pg.locator("#tpin").count() == 1 and pg.locator("[data-act=t-logout]").count() == 1, "PIN-Feld und Abmelden")
        if True:
            pg.screenshot(path=str(SHOTS / "w5-pin-fehlt.png"))
        pg.fill("#tpin", "falsch")
        pg.click("[data-act=t-pin]")
        pruef(warte(pg, "S.msg && S.msg.text === 'Die Admin-PIN stimmt nicht.'") and pg.locator(".ph").count() == 0, "falsche PIN: bleibt stehen")
        pg.fill("#tpin", "4711")
        pg.press("#tpin", "Enter")
        pruef(warte(pg, "document.querySelector('.ph')"), "richtige PIN (Enter): Ansicht wieder da")
        pruef(pg.evaluate("S.msg") is None, "Meldung weg")
        pruef(str(pg.evaluate("localStorage.getItem('sj.notweg')") or "").startswith("nw-") and pg.evaluate("S.admin.pin") is None,
              "Schlüssel statt PIN")
        pg.evaluate("localStorage.removeItem('sj.notweg'); S.admin.pin = null; render()")
        pg.click("[data-act=t-logout]")
        pruef(pg.evaluate("S.team.code") is None and pg.evaluate("localStorage.getItem('sj.hand')") is None, "Abmelden von der PIN-Seite")
        pg.close()

    if an(5):
        print("5 Teamleitung tippt den eigenen Code")
        pg = neu(b, "leitung-ohne-code")
        pg.wait_for_function("S.team.code === 'FUCHS-4821'")
        pg.evaluate("ACT['t-logout'](); render()")
        notweg_oeffnen(pg)
        pg.click("[data-act=t-login]")
        pruef(warte(pg, "S.team.code === 'FUCHS-4821' && S.team.state"), "ohne PIN angemeldet (eigenes Handy, Schlüssel)")
        pruef(pg.evaluate("localStorage.getItem('sj.hand')") is None and pg.evaluate("S.admin.pin") is None, "kein Merker, keine PIN")
        raus = pg.evaluate(ALLE_JS)
        pruef(all(v != W5 for v in raus.values()), f"Eingaben gehen mit dem Schlüssel ({raus})")
        pg.close()

    if an(6):
        print("6 Datenbank ohne die Migration")
        pg = neu(b, "leitung-ohne-code", "window.__OHNE_W5 = true;")
        pg.wait_for_function("S.team.code === 'FUCHS-4821' && S.team.state")
        pg.evaluate("window.__EINGABE_ARGS = []")
        raus = pg.evaluate(ALLE_JS)
        pruef(all(v is None or "Could not find" not in v for v in raus.values()), f"keine Eingabe scheitert an PGRST202 ({raus})")
        a = args(pg, "reveal_tip")
        pruef(len(a) == 2 and "p_token" in a[0] and "p_token" not in a[1] and "p_pin" not in a[1],
              f"erst mit, dann einmal ohne Schlüssel ({[sorted(x) for x in a]})")
        pg.close()

        # Noch ältere Datenbank (ohne p_position und p_kompass): die eigenen Rückfälle von Antwort und Position greifen weiter
        pg = neu(b, "leitung-raetsel", "window.__ALTE_DB = true;")
        pg.wait_for_function("S.team.state && S.team.state.checkedIn")
        pg.evaluate("window.__EINGABE_ARGS = []")
        pg.fill("#tans", "falsch")
        pg.click("[data-act=t-answer]")
        pruef(warte(pg, "S.msg && S.msg.ort === 'leiste'"), "Antwort kommt an")
        pruef("Could not find" not in str(pg.evaluate("S.msg && S.msg.text")), f"keine PGRST202 in der Meldung ({pg.evaluate('S.msg && S.msg.text')!r})")
        a = args(pg, "submit_answer")
        pruef(a and "p_position" not in a[-1] and "p_token" not in a[-1], f"submit_answer zuletzt ohne p_position und p_token ({len(a)} Versuche)")
        pg.evaluate("S.gps.pos = { lat: 50.1, lng: 14.4 }; S.gps.acc = 8; S.gps.lastSent = 0; S.gps.lastSentPos = null")
        pg.evaluate("maybeReport()")
        pruef(warte(pg, "window.__REPORT_ARGS.length > 0"), "Position kommt an")
        a = args(pg, "report_position")
        pruef(a and "p_kompass" not in a[-1] and "p_token" not in a[-1], f"report_position zuletzt ohne p_kompass und p_token ({len(a)} Versuche)")
        pg.close()

    if an(7):
        print("7 Quelltext")
        direkt = re.findall(r'\brpc\("(' + "|".join(EINGABEN) + r')"', QUELLE)
        pruef(not direkt, f"keine Eingabe ruft rpc() direkt ({direkt})")
        pruef(QUELLE.count("eingabeRpc(\"") >= 10, "Eingaben laufen über eingabeRpc")
        pruef("W5 (03.11.2026)" in QUELLE, "Kommentar zu W5 im Quelltext")

    if an(8):
        print("8 Bildschirmfoto Notweg mit PIN-Feld")
        pg = neu(b, "mitglied-auf-teamleitung")
        notweg_oeffnen(pg)
        pg.screenshot(path=str(SHOTS / "w5-notweg.png"), full_page=True)
        pruef((SHOTS / "w5-notweg.png").exists(), "shots/w5-notweg.png")
        pg.close()

    if an(9):
        print("9 Sicherheitsprüfung 07.11.2026 (H4, S2, Abmelden, H1)")
        # H4: Handy der Teamleitung, das die PIN im Tab hat (etwa nach einem Blick in #/admin): keine PIN in den Eingaben
        pg = neu(b, "leitung-ohne-code")
        pruef(warte(pg, "S.team.code === 'FUCHS-4821' && S.team.state"), "Anna mit Schlüssel angemeldet")
        pg.evaluate("sessionStorage.setItem('sj.pin', '4711'); S.admin.pin = '4711'; window.__EINGABE_ARGS = []")
        raus = pg.evaluate(ALLE_JS)
        a = args(pg)
        pruef(a and all(x.get("p_pin") is None for x in a), "Leitungs-Handy mit PIN im Tab: keine PIN mitgeschickt")
        pruef(all(v != W5 for v in raus.values()), f"Eingaben gehen weiter mit dem Schlüssel ({raus})")
        pruef(pg.evaluate("S.admin.pin") == "4711", "PIN im Tab bleibt (nur nicht mitgeschickt)")
        pg.close()
        # S2: Notweg-Tablet, die PIN wurde inzwischen geändert (Datenbank ohne Notweg-Schlüssel: PIN im Tab)
        pg = neu(b, "mitglied-auf-teamleitung", "window.__W5 = true; window.__OHNE_NOTWEG = true;")
        notweg_oeffnen(pg)
        pg.fill("#tpin", "4711")
        pg.click("[data-act=t-login]")
        pruef(warte(pg, "S.team.code === 'FUCHS-4821' && S.team.state"), "Notweg mit PIN angemeldet")
        pg.evaluate("window.__EINGABE_ARGS = []")
        r = pg.evaluate("async () => { try { await eingabeRpc('reveal_tip', { p_code: S.team.code }); return 'ok'; } catch (e) { return e.message; } }")
        pruef(r == "ok" and args(pg, "reveal_tip")[-1].get("p_pin") == "4711", "Notweg schickt die PIN (sj.hand)")
        pg.evaluate("S.admin.pin = 'alt-geaendert'; sessionStorage.setItem('sj.pin', 'alt-geaendert')")
        r = pg.evaluate("async () => { try { await eingabeRpc('reveal_tip', { p_code: S.team.code }); return 'ok'; } catch (e) { return e.message; } }")
        pruef(r == "Falsche PIN.", f"geänderte PIN: Fehler kommt weiter an ({r!r})")
        pruef(pg.evaluate("S.admin.pin") is None and pg.evaluate("sessionStorage.getItem('sj.pin')") is None, "geänderte PIN: vergessen (pinWeg)")
        pg.evaluate("render()")
        pruef("Admin-PIN fehlt" in pg.inner_text("#app") and pg.locator("#tpin").count() == 1, "danach Seite „Admin-PIN fehlt“")
        pg.fill("#tpin", "4711")
        pg.click("[data-act=t-pin]")
        pruef(warte(pg, "document.querySelector('.ph')"), "neue PIN: Ansicht wieder da")
        # über die Oberfläche: Tipp mit falscher PIN
        pg.evaluate("S.admin.pin = 'alt-geaendert'")
        pg.evaluate("ACT['t-tip']().catch(e => { S.msg = { type: 'err', text: e.message }; }).then(render)")
        pruef(warte(pg, "!S.admin.pin && /Admin-PIN fehlt/.test(document.querySelector('#app').innerText)"), "Tipp mit alter PIN: Seite „Admin-PIN fehlt“")
        # Abmelden nimmt die PIN mit
        pg.fill("#tpin", "4711")
        pg.click("[data-act=t-pin]")
        warte(pg, "document.querySelector('.ph')")
        pg.evaluate("ACT['t-logout'](); render()")
        pruef(pg.evaluate("S.admin.pin") is None and pg.evaluate("sessionStorage.getItem('sj.pin')") is None
              and pg.evaluate("localStorage.getItem('sj.hand')") is None, "Abmelden am Notweg: PIN und Merker weg")
        pg.close()
        # Abmelden auf dem Leitungs-Handy (ohne sj.hand) fasst eine PIN im Tab nicht an
        pg = neu(b, "leitung-ohne-code")
        warte(pg, "S.team.code === 'FUCHS-4821'")
        pg.evaluate("sessionStorage.setItem('sj.pin', '4711'); S.admin.pin = '4711'; ACT['t-logout'](); render()")
        pruef(pg.evaluate("S.admin.pin") == "4711", "Abmelden ohne sj.hand: PIN bleibt")
        pg.close()
        # H1: Text der Ablehnung
        pg = neu(b, "mitglied-auf-teamleitung")
        pg.evaluate("S.team.code = 'FUCHS-4821'; localStorage.setItem('sj.code', 'FUCHS-4821')")
        r = pg.evaluate("async () => { try { await eingabeRpc('reveal_tip', { p_code: 'FUCHS-4821' }); return 'ok'; } catch (e) { return e.message; } }")
        pruef(r == W5 and r.endswith("Wenn du die Leitung bist: App neu laden."), f"Ablehnung mit Hinweis aufs Neuladen ({r!r})")
        pg.close()

    if an(10):
        print("10 Notweg-Schlüssel (09.11.2026)")
        pg = neu(b, "mitglied-auf-teamleitung")
        notweg_oeffnen(pg)
        pg.fill("#tpin", "4711")
        pg.click("[data-act=t-login]")
        pruef(warte(pg, "S.team.code === 'FUCHS-4821' && S.team.state"), "Notweg angemeldet")
        nw = pg.evaluate("localStorage.getItem('sj.notweg')")
        # Neustart des Browsers: sessionStorage und S.admin weg, localStorage bleibt
        pg.evaluate("sessionStorage.clear(); S.admin.pin = null; render()")
        pruef(pg.locator(".ph").count() == 1 and "Admin-PIN fehlt" not in pg.inner_text("#app"), "nach Neustart: Ansicht bleibt, keine PIN nötig")
        # Schlüssel abgelaufen (auf dem Server weg)
        pg.evaluate(f"delete window.__NOTWEG.gilt[{nw!r}]")
        r = pg.evaluate("async () => { try { await eingabeRpc('reveal_tip', { p_code: S.team.code }); return 'ok'; } catch (e) { return e.message; } }")
        pruef("Notweg-Schlüssel gilt nicht mehr" in r, f"abgelaufen: Meldung ({r!r})")
        pruef(pg.evaluate("localStorage.getItem('sj.notweg')") is None, "abgelaufener Schlüssel vergessen")
        pg.evaluate("render()")
        pruef("Admin-PIN fehlt" in pg.inner_text("#app") and pg.locator("#tpin").count() == 1, "danach Seite „Admin-PIN fehlt“")
        pg.fill("#tpin", "4711")
        pg.click("[data-act=t-pin]")
        pruef(warte(pg, "document.querySelector('.ph')"), "PIN: neuer Schlüssel, Ansicht wieder da")
        nw2 = pg.evaluate("localStorage.getItem('sj.notweg')")
        pruef(bool(nw2) and nw2 != nw, "neuer Schlüssel")
        # Schlüssel eines anderen Teams gilt hier nicht
        pg.evaluate("window.__NOTWEG.gilt['nw-fremd'] = 'ADLER-0000'; localStorage.setItem('sj.notweg', 'nw-fremd')")
        r = pg.evaluate("async () => { try { await eingabeRpc('reveal_tip', { p_code: S.team.code }); return 'ok'; } catch (e) { return e.message; } }")
        pruef("Notweg-Schlüssel gilt nicht mehr" in r, f"Schlüssel eines anderen Teams abgelehnt ({r!r})")
        pg.evaluate("render()")
        pg.fill("#tpin", "4711")
        pg.click("[data-act=t-pin]")
        warte(pg, "document.querySelector('.ph')")
        nw3 = pg.evaluate("localStorage.getItem('sj.notweg')")
        # Abmelden löscht den Schlüssel auf dem Server
        pg.evaluate("ACT['t-logout'](); render()")
        pruef(warte(pg, f"!({nw3!r} in window.__NOTWEG.gilt)"), "Abmelden: Schlüssel auf dem Server gelöscht")
        pruef(pg.evaluate("localStorage.getItem('sj.notweg')") is None and pg.evaluate("localStorage.getItem('sj.hand')") is None,
              "Abmelden: Schlüssel und Merker im Gerät weg")
        pg.close()
        # Die Teamleitung tippt danach ihren eigenen Code: ein alter Schlüssel fällt weg
        pg = neu(b, "leitung-ohne-code")
        warte(pg, "S.team.code === 'FUCHS-4821'")
        pg.evaluate("ACT['t-logout'](); localStorage.setItem('sj.notweg', 'nw-alt'); render()")
        notweg_oeffnen(pg)
        pg.click("[data-act=t-login]")
        pruef(warte(pg, "S.team.code === 'FUCHS-4821' && S.team.state"), "Leitung mit eigenem Code angemeldet")
        pruef(pg.evaluate("localStorage.getItem('sj.notweg')") is None, "kein Notweg-Schlüssel auf dem Leitungs-Handy")
        pg.close()
        # Datenbank ohne admin_notweg: wie vorher, die PIN im Tab
        pg = neu(b, "mitglied-auf-teamleitung", "window.__W5 = true; window.__OHNE_NOTWEG = true;")
        notweg_oeffnen(pg)
        pg.fill("#tpin", "4711")
        pg.click("[data-act=t-login]")
        pruef(warte(pg, "S.team.code === 'FUCHS-4821' && S.team.state"), "ohne admin_notweg: angemeldet")
        pruef(pg.evaluate("localStorage.getItem('sj.notweg')") is None and pg.evaluate("sessionStorage.getItem('sj.pin')") == "4711",
              "ohne admin_notweg: PIN im Tab wie vorher")
        pg.evaluate("window.__EINGABE_ARGS = []")
        raus = pg.evaluate(ALLE_JS)
        pruef(all(v is None for v in raus.values()) and all(x.get("p_pin") == "4711" for x in args(pg)), f"ohne admin_notweg: Eingaben mit PIN ({raus})")
        pg.close()
        # Falsche PIN beim Tausch
        pg = neu(b, "mitglied-auf-teamleitung")
        notweg_oeffnen(pg)
        pg.fill("#tpin", "1234")
        pg.click("[data-act=t-login]")
        pruef(warte(pg, "S.msg && S.msg.text === 'Die Admin-PIN stimmt nicht.'") and pg.evaluate("localStorage.getItem('sj.notweg')") is None,
              "falsche PIN: kein Schlüssel")
        pg.close()

    pruef(not err, "keine Fehler auf der Seite" + (f": {err[:3]}" if err else ""))
    print("FEHLT:\n  " + "\n  ".join(fehler) if fehler else "OK")
    abschluss.ende(fehler, vorher)
