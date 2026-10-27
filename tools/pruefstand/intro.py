#!/usr/bin/env python3
"""
Startbild beim ersten Öffnen (27.10.2026): Kompass sucht Norden, landet im Kopf der Seite.

    python tools/pruefstand/intro.py

Spiel (app.html mit mock.js, Port 8872). mock.js merkt das Intro als gesehen, damit es die anderen Prüfungen nicht
verdeckt; mit &intro=1 in der Adresse kommt es wie beim ersten Öffnen. Im Vordergrund mit Timeout aufrufen. Am Ende
steht OK oder FEHLT.
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


PORT = 8872
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
APP = f"http://127.0.0.1:{PORT}/app.html?szenario="
fehler, err = [], []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def rect(pg, sel):
    return pg.evaluate(f"(() => {{ const e = document.querySelector({sel!r}); if (!e) return null; const r = e.getBoundingClientRect();"
                       " return [r.left, r.top, r.width, r.height]; })()")


def nah(a, b, tol=1.0):
    return a and b and all(abs(x - y) <= tol for x, y in zip(a, b))


def seite(b, **kw):
    pg = b.new_page(viewport={"width": 390, "height": 844}, **kw)
    pg.on("pageerror", lambda e: err.append(str(e)))
    return pg


vorher = abschluss.merken()
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)

    print("Erstes Öffnen: Intro, danach die Anmeldeseite")
    pg = seite(b)
    pg.goto(APP + "anmeldung-leer&intro=1")
    pg.wait_for_selector("#intro", state="attached", timeout=3000)
    pruef(pg.evaluate("getComputedStyle(document.getElementById('app')).visibility") == "hidden", "die App wartet unsichtbar hinter dem Intro")
    pruef(pg.evaluate("localStorage.getItem('sj.intro')") == "1", "das Handy merkt sich das Intro sofort")
    # die Bewegung beginnt 1 s nach dem vollständigen Laden, bis dahin steht das erste Bild
    pg.wait_for_function("document.readyState === 'complete'", timeout=10000)
    geladen = pg.evaluate("performance.getEntriesByType('navigation')[0].loadEventEnd")
    pg.wait_for_timeout(500)
    stand = pg.evaluate("[getComputedStyle(document.querySelector('#intro .kompass')).opacity, document.getAnimations().filter(a => a.playState === 'running').length]")
    pruef(stand == ["0", 0], f"bis 1 s nach dem Laden steht alles still, der Kompass ist noch nicht da ({stand})")
    pruef(pg.locator("#intro .grund").evaluate("e => getComputedStyle(e).transform") != "none", "die Papierfläche deckt die Seite schon ab")
    pg.wait_for_function(f"performance.now() > {geladen} + 1000 + 900", timeout=5000)   # die Nadel startet 0,6 s nach dem Start
    w1 =pg.evaluate("getComputedStyle(document.querySelector('#intro .nadel')).transform"); pg.wait_for_timeout(300)
    w2 = pg.evaluate("getComputedStyle(document.querySelector('#intro .nadel')).transform")
    pruef(w1 != w2, "die Nadel pendelt")
    # flüssig am Handy: nur transform und opacity auf eigenen Ebenen, keine Linie der Karte wird einzeln gezeichnet
    arten = pg.evaluate("""document.getAnimations().map(a => [a.effect.target.closest('#topo') ? 'topo' : 'intro',
      ...new Set(a.effect.getKeyframes().flatMap(k => Object.keys(k).filter(x => !['offset', 'easing', 'composite', 'computedOffset'].includes(x))))])""")
    pruef(not any(a[0] == "topo" for a in arten), "die Karte selbst wird nicht animiert")
    andere = sorted({x for a in arten for x in a[1:] if x not in ("transform", "opacity")})
    pruef(set(andere) <= {"strokeDasharray", "strokeDashoffset"}, f"sonst nur transform und opacity, außer dem kleinen Ring ({andere})")
    pg.wait_for_function("document.body.classList.contains('intro-landet')", timeout=8000)
    pg.wait_for_timeout(1150)   # Flug (1 s) vorbei, Übergabe noch nicht
    pruef(pg.locator("#intro").count() == 1, "kurz vor der Übergabe steht das Intro noch")
    k, z = rect(pg, "#intro .kompass"), rect(pg, "#app .flag")
    pruef(nah(k, z), f"Kompass landet genau auf dem Logo ({k} / {z})")
    wo, wz = rect(pg, "#intro .wort"), rect(pg, "#app .brand h1")
    pruef(nah(wo[:2], wz[:2], 1.5) and abs(wo[3] - wz[3]) <= 1.5, f"Schriftzug landet auf der Überschrift ({wo} / {wz})")
    pg.wait_for_function("!document.getElementById('intro')", timeout=3000)
    ende = pg.evaluate("performance.now()") - geladen
    pruef(5800 < ende < 7500, f"vorbei rund 1 + 5 Sekunden nach dem Laden ({ende / 1000:.1f} s)")
    pruef(pg.evaluate("getComputedStyle(document.querySelector('#app .flag')).visibility") == "visible", "danach ist das echte Logo zu sehen")
    pruef(not pg.evaluate("document.body.className.includes('intro')"), "keine Intro-Klasse bleibt am body")
    pruef(pg.locator(".brand .small").count() == 0, "Kopf der Anmeldeseite ohne Unterzeile")
    pg.fill("#pname", "Anna Beispiel")
    pruef(pg.input_value("#pname") == "Anna Beispiel", "das Namensfeld nimmt Eingaben an")

    print("Zweites Öffnen: kein Intro")
    pg.add_init_script("window.__behalten = true")
    pg.reload(); pg.wait_for_function("window.__fertig === true", timeout=30000)
    pruef(pg.locator("#intro").count() == 0, "beim zweiten Öffnen kein Intro")
    pg.close()

    print("Tippen überspringt")
    pg = seite(b)
    pg.goto(APP + "anmeldung-leer&intro=1")
    pg.wait_for_selector("#intro", state="attached", timeout=3000); pg.wait_for_timeout(900)
    pg.mouse.click(200, 600); pg.wait_for_timeout(150)
    pruef(pg.locator("#intro").count() == 0, "ein Tipp beendet das Intro sofort")
    pruef(pg.evaluate("getComputedStyle(document.getElementById('app')).visibility") == "visible", "die Seite steht danach sofort da")
    pg.close()

    print("Andere Ansichten")
    for sz, wer, soll in (("admin-teilnehmende", "Spielleitung", 0), ("leitung-unterwegs", "Teamleitung", 1), ("mitglied-unterwegs", "Mitglied", 1)):
        pg = seite(b)
        pg.goto(APP + sz + "&intro=1"); pg.wait_for_timeout(600)
        pruef(pg.locator("#intro").count() == soll, f"{wer}: {'Intro' if soll else 'kein Intro'}")
        if soll:
            pg.wait_for_function("!document.getElementById('intro')", timeout=8000)
            pruef(not pg.evaluate("document.body.className.includes('intro')"), f"{wer}: danach keine Intro-Klasse")
        pg.close()
    pg = seite(b)
    pg.goto(APP + "anmeldung-leer"); pg.wait_for_function("window.__fertig === true", timeout=30000)
    pruef(pg.locator("#intro").count() == 0, "Prüfstand ohne &intro: kein Intro")
    pg.close()

    print("Bewegung reduzieren: nur Überblenden")
    pg = seite(b, reduced_motion="reduce")
    pg.goto(APP + "anmeldung-leer&intro=1")
    pg.wait_for_selector("#intro", state="attached", timeout=3000)
    pg.wait_for_function("!document.getElementById('intro')", timeout=6000)
    pruef(True, "Intro ist nach höchstens 6 s weg")
    pg.close()

    pruef(not err, "keine Fehler auf der Seite" + (f": {err[:3]}" if err else ""))
    print("FEHLT:\n  " + "\n  ".join(fehler) if fehler else "OK")
    sys.stdout.flush()
    abschluss.ende(fehler, vorher)   # Chrome hängt hier manchmal beim Schließen
