#!/usr/bin/env python3
"""
Funde der Bugjagd vom 03.11.2026 (SPIEL.md §24), soweit sie die Oberfläche betreffen. Ohne Datenbank, gegen mock.js
(Port 8878). Die Funde 3 und 7 (Datenbank) prüft der Probelauf bugjagd3_db.py, Fund 4 (Seed) steht dort ebenfalls.

    python tools/pruefstand/bugjagd3.py          alle
    python tools/pruefstand/bugjagd3.py 1 2      nur diese Teile

Teile:
  1  Fund 1: Leitung startet kalt in der Team-Ansicht (sj.code gemerkt), geht auf die öffentliche Seite und bleibt
     dort; S.leitungWar ist nach dem ersten team_state gesetzt
  2  Fund 2: Foto-ZIP, wenn Fotos inzwischen gelöscht sind (admin_photo liefert data null): keine 3-Byte-Datei,
     ehrliche Meldung, alle weg ohne Paket; ohne Lücke unverändert
  3  Fund 7: Start-Dialog nennt ein erreichtes Löschdatum der Gruppenfotos, ein spätes nicht
  4  Funde 5 und 6: geraete-test.html lädt Leaflet und Schriften aus vendor/, keine Anfrage an unpkg oder Google;
     der Schritt "karte" misst "Leaflet aus vendor in ms", "schrift" findet Barlow
Haken in mock.js: window.__fotoNull(a, t); Szenarien rolle-leitung-kalt, admin-start-loeschdatum(-spaet).
Im Vordergrund mit Timeout aufrufen, etwa `timeout 240 python tools/pruefstand/bugjagd3.py`. Am Ende steht OK oder FEHLT.
"""
import functools
import http.server
import io
import pathlib
import shutil
import sys
import threading
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
HIER = pathlib.Path(__file__).resolve().parent
REPO = HIER.parent.parent
sys.path.insert(0, str(HIER))
import shoot  # noqa: E402
import abschluss  # noqa: E402

shoot.bauen()
# Geräte-Test neben app.html (vendor/ und config.js legt shoot.bauen schon dorthin; beides ist in .gitignore)
for n in ("geraete-test.html", "geraete-tests.js"):
    shutil.copy(REPO / n, HIER / ("bj3-" + n))
(HIER / "bj3-geraete-test.html").write_text(
    (HIER / "bj3-geraete-test.html").read_text(encoding="utf-8").replace('src="geraete-tests.js"', 'src="bj3-geraete-tests.js"'),
    encoding="utf-8")
from playwright.sync_api import sync_playwright  # noqa: E402


class Leise(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


PORT = 8878
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASIS = f"http://127.0.0.1:{PORT}/"
APP = BASIS + "app.html?szenario="
NUR = {int(x) for x in sys.argv[1:] if x.isdigit()}
an = lambda n: not NUR or n in NUR  # noqa: E731
fehler, err = [], []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def neu(b, szenario, vorab=None):
    pg = b.new_page(viewport={"width": 390, "height": 844}, accept_downloads=True)
    pg.set_default_timeout(15000)
    pg.route("**/vendor/leaflet-1.9.4/**", lambda r: r.abort())
    pg.on("pageerror", lambda e: err.append(f"{szenario}: {e}"))
    if vorab:
        pg.add_init_script(vorab)
    pg.clock.install()
    pg.goto(APP + szenario)
    pg.wait_for_function("window.__fertig === true", timeout=30000)
    return pg


def takt(pg, ms=10000):
    pg.clock.fast_forward(ms)
    pg.wait_for_timeout(700)


def warte(pg, js, ms=8000):
    try:
        pg.wait_for_function(js, timeout=ms)
        return True
    except Exception:
        return False


def kurz(pg):
    return pg.inner_text("#kurz") if pg.locator("#kurz").count() else ""


def zip_laden(pg):
    """Tippt "Alle herunterladen"; gibt (Namen, Größen) des Pakets zurück oder None ohne Download."""
    dl = []
    pg.on("download", lambda d: dl.append(d))
    pg.click("[data-act=a-fotos-zip]")
    warte(pg, "!document.querySelector('[data-act=a-fotos-zip][disabled]') && (S.msg && S.msg.ort === 'zip')", 15000)
    pg.wait_for_timeout(500)
    if not dl:
        return None
    z = zipfile.ZipFile(io.BytesIO(pathlib.Path(dl[0].path()).read_bytes()))
    return [(i.filename, i.file_size) for i in z.infolist()]


vorher = abschluss.merken()
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)

    if an(1):
        print("1 Leitung startet kalt in der Team-Ansicht (Fund 1)")
        pg = neu(b, "rolle-leitung-kalt")
        pruef(warte(pg, "S.view === 'team' && S.team.state && S.team.code === 'FUCHS-4821'"), "Anna startet mit gemerktem Code in der Team-Ansicht")
        pruef(pg.evaluate("S.leitungWar") is True, f"S.leitungWar nach dem ersten team_state gesetzt (ist {pg.evaluate('S.leitungWar')!r})")
        pg.evaluate("location.hash = '#/public'")
        pg.wait_for_timeout(900)
        pruef(pg.evaluate("S.view") == "public", "erster Wechsel auf #/public bleibt stehen")
        pruef("Du leitest jetzt" not in kurz(pg), f"kein Hinweis 'Du leitest jetzt' ({kurz(pg)!r})")
        takt(pg)
        takt(pg)
        pruef(pg.evaluate("S.view") == "public" and pg.evaluate("location.hash") == "#/public", "auch nach zwei Takten noch auf der öffentlichen Seite")
        pruef(pg.evaluate("localStorage.getItem('sj.code')") == "FUCHS-4821", "Code bleibt gemerkt (Rückweg in die Teamleitung)")
        pg.evaluate("location.hash = '#/team'")
        pruef(warte(pg, "S.view === 'team' && S.team.state"), "zurück in die Teamleitung geht weiter")
        pg.close()


    if an(2):
        print("2 Foto-ZIP mit inzwischen gelöschten Fotos (Fund 2)")
        pg = neu(b, "admin-fotos")
        pruef(warte(pg, "S.admin.fotos && S.admin.fotos.length >= 2"), "Fotoliste geladen")
        n = pg.evaluate("S.admin.fotos.length")
        inhalt = zip_laden(pg)
        pruef(inhalt is not None and len(inhalt) == n and all(g > 100 for _, g in inhalt), f"ohne Lücke: {n} Fotos im Paket, alle echt groß")
        pruef(pg.evaluate("S.msg && S.msg.type") == "ok" and pg.evaluate("S.msg.text") == f"{n} Fotos als stadtjagd-fotos.zip heruntergeladen.",
              f"Meldung unverändert: {pg.evaluate('S.msg && S.msg.text')!r}")
        # das erste Foto verschwindet während des Herunterladens
        erstes = pg.evaluate("[S.admin.fotos[0].teamId, S.admin.fotos[0].position]")
        pg.evaluate("([t, p]) => { window.__fotoNull = a => a.p_team === t && a.p_position === p; }", erstes)
        vor = pg.evaluate("window.__RPC_LOG.filter(x => x === 'admin_photos').length")
        inhalt = zip_laden(pg)
        pruef(inhalt is not None and len(inhalt) == n - 1, f"ein Foto weg: {n - 1} Dateien im Paket ({len(inhalt) if inhalt else None})")
        pruef(inhalt is not None and all(g > 100 for _, g in inhalt), "keine 3-Byte-Datei im Paket")
        t = pg.evaluate("S.msg && S.msg.text") or ""
        pruef(t == f"{n - 1} von {n} Fotos als stadtjagd-fotos.zip heruntergeladen, 1 inzwischen gelöscht." and pg.evaluate("S.msg.type") == "err",
              f"Meldung ehrlich und rot: {t!r}")
        pruef(pg.evaluate("window.__RPC_LOG.filter(x => x === 'admin_photos').length") > vor, "Fotoliste danach neu geladen")
        pruef(t in pg.inner_text("#app"), "Meldung steht beim Knopf")
        # alle weg
        pg.evaluate("() => { window.__fotoNull = () => true; }")
        inhalt = zip_laden(pg)
        pruef(inhalt is None, "alle weg: kein (leeres) Paket")
        t = pg.evaluate("S.msg && S.msg.text") or ""
        pruef(t == "Die Fotos sind inzwischen gelöscht, es gibt nichts herunterzuladen." and pg.evaluate("S.msg.type") == "err", f"Meldung: {t!r}")
        pg.close()

    if an(3):
        print("3 Start-Dialog mit erreichtem Löschdatum (Fund 7)")
        for sz, soll in (("admin-start-loeschdatum", True), ("admin-start-loeschdatum-spaet", False)):
            pg = neu(b, sz)
            warte(pg, "S.admin.state")
            pg.click("[data-act=a-start]")
            pg.wait_for_timeout(400)
            t = pg.inner_text("#app")
            hat = "Das Löschdatum der Gruppenfotos ist erreicht" in t
            pruef(hat == soll, f"{sz}: Hinweis im Start-Dialog {'da' if soll else 'nicht da'}")
            pg.close()

    if an(4):
        print("4 Geräte-Test lädt Leaflet und Schriften aus vendor/ (Funde 5 und 6)")
        pg = b.new_page(viewport={"width": 390, "height": 844})
        anfragen = []
        pg.on("request", lambda r: anfragen.append(r.url))
        pg.route("**/*supabase.co/**", lambda r: r.abort())          # nie die Live-Datenbank
        pg.route("**/*openstreetmap.org/**", lambda r: r.fulfill(status=200, content_type="image/png",
                 body=bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                                    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")))
        pg.on("pageerror", lambda e: err.append(f"geraete-test: {e}"))
        pg.goto(BASIS + "bj3-geraete-test.html")
        pg.wait_for_function("window.GT_TESTS && window.GT_TESTS.tests", timeout=15000)
        pg.wait_for_timeout(800)
        pruef(pg.evaluate("GT_TESTS.version") == 22, "Suite-Version 22")
        karte = pg.evaluate("GT_TESTS.tests.find(t => t.id === 'karte').lauf({})")
        pruef(karte["art"] in ("ok", "warn") and isinstance(karte["mess"].get("Leaflet aus vendor in ms"), (int, float)),
              f"karte: {karte}")
        pruef(not any("unpkg" in k for k in karte["mess"]), "kein Messschlüssel mit unpkg")
        schrift = pg.evaluate("GT_TESTS.tests.find(t => t.id === 'schrift').lauf({})")
        pruef(schrift["art"] == "ok" and schrift["wert"] == "Barlow", f"schrift: {schrift}")
        fremd = [u for u in anfragen if any(x in u for x in ("googleapis", "gstatic", "unpkg"))]
        pruef(not fremd, f"keine Anfrage an Google Fonts oder unpkg ({fremd[:3]})")
        pruef(any("/vendor/fonts/barlow" in u for u in anfragen) and any("/vendor/leaflet-1.9.4/leaflet.js" in u for u in anfragen),
              "Schriften und Leaflet kamen aus vendor/")
        pg.close()

    for e in err:
        pruef(False, "Fehler auf der Seite: " + e)
    print("OK" if not fehler else f"FEHLT ({len(fehler)})")
    abschluss.ende(fehler, vorher)
