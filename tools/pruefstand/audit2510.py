#!/usr/bin/env python3
"""
Code-Audit 25.10.2026: zehn Befunde der App, ohne Datenbank, gegen mock.js.

    python tools/pruefstand/audit2510.py          alle
    python tools/pruefstand/audit2510.py 2 6      nur diese Teile

Teile: 1 Notweg Team-Code, 2 veraltete Abruf-Antwort, 3 Spielleitung ohne Netz und falsche PIN, 4 syncTracks doppelt,
5 voller Speicher, 6 Denkpause bei falscher Handyuhr, 7 Umkreis-Text, 8 Team-Karte nach Funkloch, 9 toter Code,
10 Team-Codes mit vier und sechs Ziffern. Haken in mock.js: window.__halten (Antwort wartet auf __freigeben()),
window.__weg (nur diese Aufrufe scheitern), window.__serverJetzt (Uhr des "Servers", wenn die Handyuhr schief steht).
Port 8871. Im Vordergrund mit Timeout aufrufen. Am Ende steht OK oder FEHLT.
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


PORT = 8871
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
APP = f"http://127.0.0.1:{PORT}/app.html?szenario="
NUR = {int(x) for x in sys.argv[1:] if x.isdigit()}
an = lambda n: not NUR or n in NUR  # noqa: E731
fehler, err = [], []
QUELLE = (REPO / "index.html").read_text(encoding="utf-8")


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def neu(b, szenario, vorab=None, uhr=True):
    pg = b.new_page(viewport={"width": 390, "height": 844})
    pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: err.append(f"{szenario}: {e}"))
    if vorab:
        pg.add_init_script(vorab)
    if uhr:
        pg.clock.install()
    pg.goto(APP + szenario)
    pg.wait_for_function("window.__fertig === true", timeout=30000)
    return pg


def takt(pg, ms=10000):
    pg.clock.fast_forward(ms)
    pg.wait_for_timeout(700)


def tippen(pg, sel):
    pg.click(sel)
    pg.wait_for_function(f"!document.querySelector('{sel}') || !document.querySelector('{sel}').disabled", timeout=20000)
    pg.wait_for_timeout(200)


def zaehl(pg, fn):
    return pg.evaluate(f"window.__RPC_LOG.filter(x => x === '{fn}').length")


vorher = abschluss.merken()
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)
    tiger = None

    if an(1):
        print("1 Notweg Team-Code (Gerät mit Schlüssel, Code von Hand)")
        pg = neu(b, "mitglied-auf-teamleitung")
        pg.click("[data-act=t-codefeld]")
        pg.fill("#tcode", "FUCHS-4821")
        tippen(pg, "[data-act=t-login]")
        pruef(pg.evaluate("S.team.code") == "FUCHS-4821", "von Hand eingegeben: Code steht")
        takt(pg)
        takt(pg)
        pruef(pg.evaluate("S.team.code") == "FUCHS-4821", f"nach zwei Abrufen noch angemeldet ({pg.evaluate('S.team.code')!r})")
        pg.evaluate("ACT['t-logout']()")
        pruef(pg.evaluate("localStorage.getItem('sj.hand')") is None, "Abmelden löscht den Merker")
        pg.close()

    if an(2):
        print("2 Veraltete Abruf-Antwort")
        pg = neu(b, "funkloch-station")
        pg.wait_for_selector("[data-act=t-check]:not([disabled])")
        n0 = zaehl(pg, "team_state")
        pg.evaluate("window.__halten = ['team_state']")
        takt(pg)
        takt(pg)
        pruef(zaehl(pg, "team_state") - n0 == 1, f"Takt startet keinen zweiten Abruf, solange der erste läuft ({zaehl(pg, 'team_state') - n0} Abrufe)")
        tippen(pg, "[data-act=t-check]")
        pruef(pg.evaluate("S.team.state.checkedIn") is True, "Check-in angekommen")
        pg.evaluate("window.__halten = null; window.__freigeben()")
        pg.wait_for_timeout(700)
        pruef(pg.evaluate("S.team.state.checkedIn") is True, "die verspätete Antwort überschreibt den neuen Stand nicht")
        takt(pg)
        pruef(pg.evaluate("S.team.state.checkedIn") is True and zaehl(pg, "team_state") >= 2, "der nächste Takt läuft wieder")
        pg.close()

        pg = neu(b, "admin-teams")
        n0 = zaehl(pg, "admin_state")
        pg.evaluate("window.__halten = ['admin_state']")
        takt(pg)
        takt(pg)
        pruef(zaehl(pg, "admin_state") - n0 == 1, f"Spielleitung: kein zweiter Abruf ({zaehl(pg, 'admin_state') - n0})")
        pg.evaluate("S.admin.state = Object.assign({}, S.admin.state, { marker: 1 })")
        pg.evaluate("window.__halten = null; window.__freigeben()")
        pg.wait_for_timeout(700)
        pruef(pg.evaluate("S.admin.state.marker") == 1, "Spielleitung: veraltete Antwort verworfen")
        pg.close()

        pg = neu(b, "teamkarte-mitglied")
        n0 = zaehl(pg, "public_state")
        pg.evaluate("window.__halten = ['public_state']")
        takt(pg)
        takt(pg)
        pruef(zaehl(pg, "public_state") - n0 == 1, f"Mitlesen: kein zweiter Abruf ({zaehl(pg, 'public_state') - n0})")
        pg.close()

    if an(3) or an(10):
        print("3 Spielleitung ohne Netz, falsche PIN")
        pg = neu(b, "admin-teams")
        tiger = pg.evaluate("S.admin.state.teams.find(t => t.name === 'Tiger').code")
        if an(3):
            pg.evaluate("window.__netz = 'weg'")
            for _ in range(5):
                takt(pg, 10000)
            takt(pg, 1500)
            sd = pg.locator("#stand")
            pruef(sd.count() == 1 and sd.is_visible(), "Kopf der Spielleitung zeigt den Stand-Chip")
            pruef(sd.count() == 1 and sd.inner_text().startswith("Stand "), "mit Uhrzeit des letzten Kontakts")
            pg.evaluate("window.__netz = null; S.admin.pin = '0000'")
            takt(pg)
            pruef(pg.evaluate("S.admin.pin") is None, "falsche PIN im Takt: abgemeldet")
            pruef(pg.locator("#pin, [data-act=a-login]").count() > 0, "Anmeldung der Spielleitung ist zu sehen")
        pg.close()

    if an(4):
        print("4 syncTracks läuft einmal")
        pg = neu(b, "admin-teams")
        pg.evaluate("window.__halten = ['admin_tracks']")
        n0 = zaehl(pg, "admin_tracks")
        pg.click("[data-act=a-tab][data-tab=zeit]")
        pg.wait_for_timeout(300)
        takt(pg)
        n = zaehl(pg, "admin_tracks") - n0
        pruef(n == 1, f"Tab-Wechsel und Takt zusammen: ein Abruf ({n})")
        pg.evaluate("window.__halten = null; window.__freigeben()")
        pg.close()

    if an(5):
        print("5 Voller Speicher")
        pg = neu(b, "selfie-offen")
        pg.evaluate("(() => { const o = Storage.prototype.setItem; Storage.prototype.setItem = function (k, v) { if (String(k).startsWith('sj.')) throw new DOMException('voll', 'QuotaExceededError'); return o.call(this, k, v); }; })()")
        pruef(pg.evaluate("(() => { try { LS.setItem('sj.x', '1'); return true; } catch { return false; } })()"),
              "LS.setItem wirft bei vollem Speicher nicht")
        pg.close()
        for voll in (True, False):
            pg = neu(b, "selfie-offen")
            pg.evaluate("""(() => { const p = S.team.state.selfie.pending.position;
              S.selfie = { pos: p, foto: 'x', thumb: 'y', url: 'data:image/gif;base64,R0lGODlhAQABAAAAACw=', status: 'vorschau' }; render(); })()""")
            if voll:
                pg.evaluate("(() => { const o = Storage.prototype.setItem; Storage.prototype.setItem = function (k, v) { if (String(k).startsWith('sj.')) throw new DOMException('voll', 'QuotaExceededError'); return o.call(this, k, v); }; })()")
            pg.evaluate("window.__netz = 'weg'")
            tippen(pg, "[data-act=t-selfie-ok]")
            t = pg.inner_text("#app")
            pruef(("nachgereicht" not in t) if voll else ("nachgereicht" in t),
                  "Speicher voll: kein Versprechen 'wird nachgereicht'" if voll else "Speicher ok: Hinweis 'wird nachgereicht' steht")
            pg.close()

    if an(6):
        print("6 Denkpause bei falscher Handyuhr")
        pg = neu(b, "leitung-raetsel", "window.__serverJetzt = Date.now.bind(Date); (function () { const r = Date.now.bind(Date); Date.now = () => r() + (window.__skew || 0); })();", uhr=False)
        pg.evaluate("window.__skew = -3600000")
        for a in ("1", "2", "3"):
            pg.fill("#tans", a)
            if a == "3":
                pg.click("[data-act=t-answer]")
                pg.wait_for_selector("#pause")
            else:
                tippen(pg, "[data-act=t-answer]")
        t = pg.locator("#pause").inner_text() if pg.locator("#pause").count() else ""
        m = re.search(r"noch (\d+) Sekunden", t)
        rest = int(m.group(1)) if m else None
        pruef(rest is not None and 100 <= rest <= 120, f"Handyuhr eine Stunde zurück: höchstens 120 Sekunden ({t!r})")
        pruef(pg.is_disabled("#tans"), "Feld gesperrt")
        pg.close()

    if an(7):
        print("7 Umkreis-Text")
        pg = neu(b, "funkloch-station")
        pg.wait_for_selector("[data-act=t-check]")
        pruef(pg.locator("#umkreis").count() == 0, "kein zweiter Umkreis-Text neben dem Knopf")
        pruef(pg.evaluate("typeof umkreisHTML") == "undefined", "umkreisHTML ist weg")
        pg.close()

    if an(8):
        print("8 Team-Karte nach Funkloch")
        pg = neu(b, "teamkarte-mitglied", "window.__weg = ['lookup_participant'];")
        pruef(pg.evaluate("S.autoLook") is False, "Suche gescheitert: autoLook zurückgesetzt")
        pg.evaluate("window.__weg = null")
        takt(pg)
        pruef(pg.evaluate("!!S.lookup"), "nächster Takt holt das eigene Team")
        pg.close()

    if an(9):
        print("9 Toter Code")
        for n in ("viewSetup", "cfg-save", '"a-unlock"', "sj.url", "sj.key", "const fmtClock", "FUCHS-1234\""):
            pruef(n not in QUELLE, f"{n} steht nicht mehr im Quelltext")

    if an(10):
        print("10 Team-Codes mit vier und sechs Ziffern")
        pruef(re.search(r'placeholder="[A-Z]+-\d{6}"', QUELLE) is not None, "Beispiel im Eingabefeld hat sechs Ziffern")
        pruef("etwa FUCHS-123456" in QUELLE, "Fehlermeldung nennt die sechsstellige Schreibweise")
        for code in ("FUCHS-4821", tiger):
            if not code:
                continue
            pg = neu(b, "leitung-login")
            pg.click("[data-act=t-codefeld]")
            pg.fill("#tcode", code.lower())
            tippen(pg, "[data-act=t-login]")
            pruef(pg.evaluate("S.team.code") == code, f"Anmelden mit {code} (kleingeschrieben getippt)")
            pruef(pg.evaluate("S.team.state.team.code") == code, f"{code} kommt vollständig im Stand an")
            pg.close()
        pruef(tiger is not None and re.fullmatch(r"TIGER-\d{6}", tiger) is not None, f"Prüfstand-Teams haben sechs Ziffern ({tiger})")

    if an(11):
        print("11 Nachtrag der Datenbank: Leitung abgeben abgelehnt, Löschdatum lokal")
        pg = neu(b, "leitung-raetsel")
        pg.click("[data-act=t-tab][data-tab=team]")
        pg.click("[data-act=t-abgeben-frage]")
        pg.select_option("#tneu", "Tobias Neumann")
        tippen(pg, "[data-act=t-abgeben]")
        t = pg.inner_text("#app")
        pruef("kann nicht eingeben" in t, "Meldung des Servers steht unter dem Feld")
        pruef(pg.evaluate("S.team.code") == "FUCHS-4821" and pg.evaluate("S.team.state !== null"), "Handy bleibt angemeldet")
        pg.close()
        pg = neu(b, "admin-fotos-heute")
        pruef("heute oder schon vorbei" in pg.inner_text("#app") or pg.evaluate("document.body.innerText").count("heute oder schon vorbei") > 0,
              "Löschdatum von heute (lokal) warnt")
        pg.close()

    pruef(not err, "keine Fehler auf der Seite" + (f": {err[:3]}" if err else ""))
    print("FEHLT:\n  " + "\n  ".join(fehler) if fehler else "OK")
    abschluss.ende(fehler, vorher)
