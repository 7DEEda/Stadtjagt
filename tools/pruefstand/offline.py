#!/usr/bin/env python3
"""
Ausfallsicherheit, Abschnitt 1: Service Worker, App startet ohne Netz, letzter Stand, Version, Notausgang.

    python tools/pruefstand/offline.py

Baut in einem Temp-Ordner unter Stadtjagt/ eine index.html mit mock.js INLINE (nicht als script src: sonst fehlte
der Mock nach dem Serverstopp, und die App liefe mit config.js gegen das echte Supabase), dazu sw.js, config.js,
kompass-waechter.js, vendor/, hintergrund/. Der Prüfserver (Port 8869) liefert den Ordner unter /Stadtjagt/ aus, so
wie GitHub Pages, und lässt sich stoppen und wieder starten. mock.js ersetzt window.fetch im Fenster: RPCs erreichen
den Service Worker nie. Darum liefert der Server zusätzlich /Stadtjagt/rest/v1/rpc/x mit Zähler aus; nach dem Stopp
muss dieser Abruf scheitern statt aus dem Cache zu kommen. Ohne Leaflet-Seite. Im Vordergrund mit Timeout aufrufen.
Am Ende steht OK oder FEHLT.
"""
import http.server
import json
import os
import pathlib
import shutil
import sys
import tempfile
import threading
import time
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
HIER = pathlib.Path(__file__).resolve().parent
REPO = HIER.parent.parent
sys.path.insert(0, str(HIER))
import abschluss  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

# außerhalb von OneDrive: dort sperrt die Synchronisation frisch angelegte Ordner. Reste früherer Läufe weg.
for alt in pathlib.Path(tempfile.gettempdir()).glob("stadtjagd-offline-*"):
    shutil.rmtree(alt, ignore_errors=True)
WURZEL = pathlib.Path(tempfile.mkdtemp(prefix="stadtjagd-offline-"))
APP = WURZEL / "Stadtjagt"
PORT = 8869
BASIS = f"http://127.0.0.1:{PORT}/Stadtjagt/"
SCHRIFTEN = sorted(p.name for p in (REPO / "vendor" / "fonts").glob("*.woff2"))
fehler, err = [], []
Z = {"rpc": 0, "langsam": False}


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def bauen():
    APP.mkdir(parents=True)
    src = (REPO / "index.html").read_text(encoding="utf-8")
    mock = (HIER / "mock.js").read_text(encoding="utf-8")
    assert "</script" not in mock
    i = src.index("<script")
    (APP / "index.html").write_text(src[:i] + "<script>\n" + mock + "\n</script>\n" + src[i:], encoding="utf-8", newline="\n")
    for f in ["sw.js", "config.js", "kompass-waechter.js"]:
        shutil.copy(REPO / f, APP / f)
    shutil.copytree(REPO / "vendor", APP / "vendor")
    shutil.copytree(REPO / "hintergrund", APP / "hintergrund")
    (APP / "andere.html").write_text("<!doctype html><meta charset=utf-8><title>andere</title><p>andere Seite im selben Ordner</p>", encoding="utf-8")
    (WURZEL / "fremd").mkdir()
    (WURZEL / "fremd" / "index.html").write_text("<!doctype html><meta charset=utf-8><title>fremd</title><p>anderes Pages-Projekt</p>", encoding="utf-8")


def stellen(sekunden_her):
    t = int(time.time()) - sekunden_her
    os.utime(APP / "index.html", (t, t))
    d = datetime.fromtimestamp(t)
    return f"Version {d:%d.%m.}, {d:%H:%M}"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(WURZEL), **k)

    def log_message(self, *a):
        pass

    def end_headers(self):
        # Kein HTTP-Cache im Prüfstand: was ohne Server lädt, kommt dann sicher aus dem Service Worker
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        pfad = self.path.split("?")[0]
        if pfad == "/Stadtjagt/rest/v1/rpc/x":
            Z["rpc"] += 1
            body = json.dumps({"n": Z["rpc"]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if Z["langsam"] and pfad in ("/Stadtjagt/", "/Stadtjagt/index.html"):
            time.sleep(6)
        super().do_GET()


SRV = {}


def starten():
    s = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    s.daemon_threads = True
    threading.Thread(target=s.serve_forever, daemon=True).start()
    SRV["s"] = s


def stoppen():
    s = SRV.pop("s")
    s.shutdown()
    s.server_close()


def laden(pg, szenario, hash=""):
    try:
        pg.goto(BASIS + "?szenario=" + szenario + hash)
    except Exception as e:   # von einer Fehlerseite aus bricht Chrome die erste Navigation manchmal ab
        print("  (neuer Versuch:", str(e).splitlines()[0][:90] + ")")
        pg.wait_for_timeout(500)
        pg.goto(BASIS + "?szenario=" + szenario + hash)
    pg.wait_for_function("window.__fertig === true", timeout=30000)


def zeile(pg):
    v = pg.locator(".version")
    return v.first.inner_text().strip() if v.count() else ""


def xhr(pg):
    return pg.evaluate("""() => new Promise(fertig => { const x = new XMLHttpRequest(); x.open('GET', 'rest/v1/rpc/x');
      x.onload = () => fertig({ status: x.status, text: x.responseText }); x.onerror = () => fertig({ status: 0, text: '' }); x.send(); })""")


CACHE = """async () => { const out = {}; for (const n of await caches.keys()) { const c = await caches.open(n);
  out[n] = (await c.keys()).map(r => r.url); } return out; }"""

bauen()
v1 = stellen(2 * 3600)
starten()
vorher = abschluss.merken()
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)
    ctx = b.new_context(viewport={"width": 390, "height": 844}, service_workers="allow")
    anfragen = []
    ctx.on("request", lambda r: anfragen.append(r.url))
    pg = ctx.new_page()
    pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: err.append(str(e)))
    konsole = []
    pg.on("console", lambda m: konsole.append(m.text) if m.type == "error" else None)

    print("1 Erster Besuch: Service Worker und Vorab-Cache")
    pg.goto(f"http://127.0.0.1:{PORT}/fremd/")
    pg.evaluate("caches.open('fremd-test').then(c => c.put('/fremd/x', new Response('1')))")
    pg.goto(f"http://127.0.0.1:{PORT}/Stadtjagt/andere.html")
    pg.evaluate("caches.open('sj-alt-0').then(c => c.put('/Stadtjagt/alt', new Response('alt')))")
    laden(pg, "anmeldung-leer")
    try:
        pg.wait_for_function("!!navigator.serviceWorker && !!navigator.serviceWorker.controller", timeout=15000)
        pruef(True, "Service Worker aktiv und steuert die Seite")
    except Exception:
        pruef(False, "Service Worker aktiv und steuert die Seite")
    pg.wait_for_timeout(500)
    c = pg.evaluate(CACHE)
    h, d = c.get("sj-huelle-1", []), c.get("sj-dauer-1", [])
    pruef(BASIS in h and BASIS + "config.js" in h and BASIS + "kompass-waechter.js" in h, f"Hülle im Cache: ./, config.js, kompass-waechter.js ({h})")
    pruef(all(BASIS + "vendor/fonts/" + n in d for n in SCHRIFTEN), f"alle {len(SCHRIFTEN)} Schriften im Cache")
    pruef(all(BASIS + f"hintergrund/{x}.svg" in d for x in "abc"), "Hintergründe a, b, c im Cache")
    pruef("fremd-test" in c, "fremder Cache desselben Origins bleibt")
    pruef("sj-alt-0" not in c, "alte eigene Fassung (sj-*) ist aufgeräumt")
    pruef(not any("andere.html" in u for u in h + d), "andere Seite im Ordner nicht im Cache")
    pruef(xhr(pg)["text"] == '{"n": 1}', "RPC-Pfad mit Netz: Antwort vom Server")
    reg = pg.evaluate("navigator.serviceWorker.getRegistration().then(r => r && r.scope)")
    pruef(reg == BASIS, f"Scope {reg}")

    print("2 Keine fremden Rechner")
    pruef(not [u for u in anfragen if any(x in u for x in ("googleapis", "gstatic", "unpkg"))], "keine Anfrage an Google Fonts oder unpkg")

    print("3 Server weg: App startet aus dem Cache")
    stoppen()
    konsole.clear()
    laden(pg, "anmeldung-leer")
    pruef(pg.locator("#pname").count() == 1, "Anmeldeseite steht")
    pg.evaluate("document.fonts.ready")
    geladen = pg.evaluate("""async () => { const r = [];
      for (const f of ['400 16px Barlow', '600 16px Barlow', '700 16px "Barlow Semi Condensed"', '700 16px "JetBrains Mono"'])
        r.push((await document.fonts.load(f, 'Křižík')).filter(x => x.status === 'loaded').length);
      return r; }""")
    pruef(all(n >= 1 for n in geladen), f"Schriften aus dem Cache geladen ({geladen})")
    pruef(zeile(pg) == v1, f"Version aus der gespeicherten Antwort ({zeile(pg)!r})")
    pruef(not konsole, f"keine Fehler in der Konsole ({konsole[:3]})")
    x = xhr(pg)
    pruef(x["status"] == 0 and Z["rpc"] == 1, f"RPC-Pfad ohne Server scheitert, nicht aus dem Cache ({x}, Zähler {Z['rpc']})")
    try:
        pg.goto(BASIS + "andere.html", timeout=8000)
        pruef(False, "andere Seite im Ordner kommt nicht aus dem Cache")
    except Exception:
        pruef(True, "andere Seite im Ordner kommt nicht aus dem Cache")

    print("4 Teamleitung unterwegs: letzter Stand")
    starten()
    laden(pg, "leitung-unterwegs")
    m = pg.evaluate("JSON.parse(localStorage.getItem('sj.letzter.team') || 'null')")
    pruef(bool(m) and m.get("code") == "FUCHS-4821" and m.get("state", {}).get("station", {}).get("name") == "Rudolfstollen", "Stand gemerkt (sj.letzter.team)")
    vor = int(time.time() * 1000) - 5 * 60000
    if m:
        pg.evaluate(f"(() => {{ const m = JSON.parse(localStorage.getItem('sj.letzter.team')); m.at = {vor}; localStorage.setItem('sj.letzter.team', JSON.stringify(m)); }})()")
    stoppen()
    pg2 = ctx.new_page()
    pg2.set_default_timeout(15000)
    pg2.on("pageerror", lambda e: err.append(str(e)))
    pg2.add_init_script("window.__behalten = true; window.__netz = 'weg';")
    pg.close()
    laden(pg2, "leitung-unterwegs", "#/team")   # wie auf dem Handy: die Adresse trägt die Ansicht
    pg2.wait_for_timeout(1500)
    t = pg2.inner_text("#app")
    pruef("Rudolfstollen" in t or "Station 2" in t, "Station steht da")
    pruef(pg2.locator("#dist").count() == 1, "Entfernung steht da")
    sd = pg2.locator("#stand")
    stand = datetime.fromtimestamp(vor / 1000).strftime("%H:%M")
    pruef(sd.count() == 1 and sd.is_visible() and sd.inner_text() == f"Stand {stand}", f"oben 'Stand {stand}' ({sd.inner_text() if sd.count() else ''!r})")
    pg2.evaluate("localStorage.setItem('sj.code', 'ANDERS-1')")
    pg2.reload(); pg2.wait_for_function("window.__fertig === true", timeout=30000)
    pruef("Rudolfstollen" not in pg2.inner_text("#app"), "anderer Team-Code: kein gemerkter Stand")
    pg2.evaluate("localStorage.setItem('sj.code', 'FUCHS-4821'); (() => { const m = JSON.parse(localStorage.getItem('sj.letzter.team')); m.at = Date.now() - 13 * 3600000; localStorage.setItem('sj.letzter.team', JSON.stringify(m)); })()")
    pg2.reload(); pg2.wait_for_function("window.__fertig === true", timeout=30000)
    pruef("Rudolfstollen" not in pg2.inner_text("#app"), "älter als 12 h: kein gemerkter Stand")
    pg2.close()

    print("4b Mitlesen: letzter Stand")
    starten()
    pg = ctx.new_page(); pg.set_default_timeout(15000); pg.on("pageerror", lambda e: err.append(str(e)))
    laden(pg, "mitglied-unterwegs")
    pruef(bool(pg.evaluate("localStorage.getItem('sj.letzter.mit')")), "Stand gemerkt (sj.letzter.mit)")
    text_mit = pg.inner_text("#app")
    stoppen()
    pg2 = ctx.new_page(); pg2.set_default_timeout(15000); pg2.on("pageerror", lambda e: err.append(str(e)))
    pg2.add_init_script("window.__behalten = true; window.__netz = 'weg';")
    pg.close()
    laden(pg2, "mitglied-unterwegs")
    pruef("Rudolfstollen" in pg2.inner_text("#app") or "Station 2" in pg2.inner_text("#app"), "Mitlesen: Station steht da")
    pruef("Lade …" not in pg2.inner_text("#app"), "nicht nur 'Lade …'")
    pg2.close()

    print("4c Gemerkter Stand wird gelöscht")
    starten()
    pg = ctx.new_page(); pg.set_default_timeout(15000); pg.on("pageerror", lambda e: err.append(str(e)))
    laden(pg, "leitung-unterwegs")
    for name, js in [("codeUngueltig", "codeUngueltig()"), ("Abmelden", "ACT['t-logout']()"),
                     ("Leitung gewechselt", "localStorage.setItem('sj.token', 'tok-x'); window.rpc = async () => { throw new Error('Du bist gerade keine Teamleitung.'); }; leitungNochDa({ team: { leaderName: 'Jemand Anders', name: 'Fuchs' } })")]:
        pg.evaluate("localStorage.setItem('sj.letzter.team', '{}'); localStorage.setItem('sj.letzter.mit', '{}')")
        pg.evaluate(f"(async () => {{ await {js}; }})()")
        pg.wait_for_timeout(200)
        pruef(pg.evaluate("localStorage.getItem('sj.letzter.team')") is None, f"{name}: gemerkter Stand gelöscht")
    pg.close()

    print("5 Neue index.html: Netz zuerst")
    pg = ctx.new_page(); pg.set_default_timeout(15000); pg.on("pageerror", lambda e: err.append(str(e)))
    v2 = stellen(3600)
    laden(pg, "anmeldung-leer")
    pruef(zeile(pg) == v2, f"Versionszeile zeigt die neue Zeit ({zeile(pg)!r}, erwartet {v2!r})")

    print("6 Neue Version, Seite offen")
    v3 = stellen(1800)
    pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    try:
        pg.wait_for_selector(".version [data-act=neu-laden]", timeout=5000)
    except Exception:
        pass
    pruef(pg.locator(".version [data-act=neu-laden]").count() == 1, "Link 'Neue Version laden' erscheint")

    print("7 Langsames Netz: nach 4 s die Kopie")
    Z["langsam"] = True
    t0 = time.time()
    laden(pg, "anmeldung-leer")
    dauer = time.time() - t0
    pruef(dauer < 5.8, f"Seite nach {dauer:.1f} s da (Grenze 4 s plus Start)")
    pruef(zeile(pg) == v2, f"zeigt die Kopie ({zeile(pg)!r})")
    pg.wait_for_timeout(4000)
    Z["langsam"] = False
    stoppen()
    laden(pg, "anmeldung-leer")
    pruef(zeile(pg) == v3, f"der weiterlaufende Abruf hat die neue Fassung abgelegt ({zeile(pg)!r})")
    starten()

    print("8 Notausgang tools/sw-aus.js")
    shutil.copy(REPO / "tools" / "sw-aus.js", APP / "sw.js")
    laden(pg, "anmeldung-leer")
    # die Navigation stößt die Prüfung von sw.js an; die neue Fassung räumt auf und meldet sich ab
    for _ in range(30):
        regs = pg.evaluate("navigator.serviceWorker.getRegistrations().then(r => r.length)")
        if regs == 0:
            break
        pg.wait_for_timeout(500)
    pruef(regs == 0, f"Service Worker abgemeldet ({regs})")
    c = pg.evaluate(CACHE)
    pruef(not [n for n in c if n.startswith("sj-")], f"eigene Caches gelöscht ({list(c)})")
    pruef("fremd-test" in c, "fremder Cache bleibt")
    laden(pg, "anmeldung-leer")
    pruef(pg.locator("#pname").count() == 1, "App läuft wie ohne Service Worker")
    stoppen()
    try:
        pg.goto(BASIS + "?szenario=anmeldung-leer", timeout=8000)
        pruef(False, "ohne Server kein Start aus dem Cache mehr")
    except Exception:
        pruef(True, "ohne Server kein Start aus dem Cache mehr")

    pruef(not err, "keine Fehler auf der Seite" + (f": {err[:3]}" if err else ""))
    print("FEHLT:\n  " + "\n  ".join(fehler) if fehler else "OK")
    shutil.rmtree(WURZEL, ignore_errors=True)
    abschluss.ende(fehler, vorher)
