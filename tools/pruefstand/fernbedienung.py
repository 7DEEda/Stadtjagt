#!/usr/bin/env python3
"""
Fernbedienung der Rückblick-Show (Nachtrag 37, SPIEL.md §17): Show-Seite (app.html mit mock.js, Szenario rueckblick,
also der echte Rückblick mit PIN 4711) und Handy-Seite (rueckblick-fernbedienung.html, 390x844) gleichzeitig. Die
fünf RPCs rb_* laufen in beiden Seiten über page.route auf dasselbe Python-Objekt (DB unten, nach der Migration
20261017090000_rueckblick_steuerung.sql), damit beide denselben Zustand sehen. Alle übrigen RPCs beantwortet mock.js.

    python tools/pruefstand/fernbedienung.py

Prüft: PIN am Handy, Start aus Vorbereiten, Weiter wie die Taste, Doppeltipp gesperrt, Zurück, Pause, Schwarzbild,
Zum Ende (mit Rückfrage), Status am Handy folgt der Show (auch bei Tasten am Laptop), Moderation vor Platz 3 nur am
Handy, "Handy verbunden" am Laptop, "Keine Show gefunden" nach 6 s ohne Herzschlag, alte Befehle wirken nach dem
Öffnen nicht, rb_ende beim Verlassen, Netzfehler stören die Show nicht, Bildrate mit aktiver Fernbedienung, Probe mit
Fernbedienung (PIN im Block aktivieren, Moderation mit den Demo-Teams, PIN geändert), Handy-Seite bei 390 und 360 px ohne seitliches Scrollen, Tippziele, hell und dunkel, Texte ohne
Gedankenstrich und Mittelpunkt, Service Worker lässt die Seite in Ruhe.
Port 8865. Ergebnis VOR dem Schließen (abschluss.py). Im Vordergrund mit Timeout, etwa
`timeout 590 python tools/pruefstand/fernbedienung.py`. Bildschirmfotos nach FERN_SHOTS oder tools/pruefstand/shots.
"""
import functools
import http.server
import json
import os
import pathlib
import re
import sys
import threading
import time
from urllib.parse import urlparse

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


PORT = 8865
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASIS = f"http://127.0.0.1:{PORT}/"
SHOTS = pathlib.Path(os.environ.get("FERN_SHOTS") or (HIER / "shots"))
SHOTS.mkdir(parents=True, exist_ok=True)
fehler, err, fremd = [], [], []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text, flush=True)
    if not ok:
        fehler.append(text)


class Fehler(Exception):
    pass


class DB:
    """Die Tabelle rueckblick_steuerung mit den fünf Funktionen, wie in der Migration (Zeit in Sekunden)."""
    def __init__(self):
        self.nr, self.befehl, self.befehl_um = 0, None, None
        self.status, self.status_um, self.handy_um = None, None, None
        self.log = []          # (Funktion, Argumente ohne PIN, Ergebnis)
        self.kaputt = set()    # Funktionen, die mit HTTP 500 antworten ("*": alle)
        self.pin = "4711"      # admin_pin in game_state

    def rufen(self, fn, a):
        jetzt = time.time()
        if str(a.get("p_pin") or "").strip() != self.pin:
            raise Fehler("Falsche PIN.")
        if fn == "rb_befehl":
            if a.get("p_befehl") not in ("weiter", "zurueck", "pause", "schwarz", "start", "ende"):
                raise Fehler("Unbekannter Befehl.")
            if self.befehl_um is not None and self.befehl_um > jetzt - 0.25:
                return {"ok": False, "nr": self.nr}
            self.nr += 1
            self.befehl, self.befehl_um = a["p_befehl"], jetzt
            return {"ok": True, "nr": self.nr}
        if fn == "rb_poll":
            seit = a.get("p_seit")
            if seit is None or self.nr < seit:
                return {"nr": self.nr, "befehl": None}
            if self.nr == seit:
                return None
            if self.befehl_um is None or self.befehl_um < jetzt - 30:
                return {"nr": self.nr, "befehl": None}
            return {"nr": self.nr, "befehl": self.befehl}
        if fn == "rb_status_setzen":
            st = a.get("p_status")
            if not isinstance(st, dict):
                raise Fehler("Der Status fehlt.")
            if len(json.dumps(st, ensure_ascii=False).encode("utf-8")) > 20480:
                raise Fehler("Der Status ist zu groß.")
            self.status, self.status_um = st, jetzt
            return {"ok": True, "handy_alter_s": None if self.handy_um is None else round(jetzt - self.handy_um, 1)}
        if fn == "rb_status_holen":
            self.handy_um = jetzt
            return {"status": self.status, "alter_s": None if self.status_um is None else round(jetzt - self.status_um, 1)}
        if fn == "rb_ende":
            self.status = self.status_um = self.befehl = self.befehl_um = self.handy_um = None
            return {"ok": True}
        raise Fehler("unbekannt")

    def route(self, route):
        fn = urlparse(route.request.url).path.rsplit("/", 1)[-1]
        kopf = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
        if route.request.method == "OPTIONS":
            return route.fulfill(status=204, headers=kopf)
        if "*" in self.kaputt or fn in self.kaputt:
            return route.fulfill(status=500, headers=kopf, content_type="text/html", body="<html>500</html>")
        try:
            a = json.loads(route.request.post_data or "{}")
        except ValueError:
            a = {}
        try:
            r = self.rufen(fn, a)
            self.log.append((fn, {k: v for k, v in a.items() if k != "p_pin"}, r))
            route.fulfill(status=200, headers=kopf, content_type="application/json", body=json.dumps(r))
        except Fehler as e:
            self.log.append((fn, {k: v for k, v in a.items() if k != "p_pin"}, "Fehler: " + str(e)))
            route.fulfill(status=400, headers=kopf, content_type="application/json", body=json.dumps({"code": "P0001", "message": str(e)}))

    def angenommen(self):
        return [x for x in self.log if x[0] == "rb_befehl" and isinstance(x[2], dict) and x[2].get("ok")]


db = DB()


def wache(route):
    host = urlparse(route.request.url).hostname or ""
    if host in ("127.0.0.1", "localhost"):
        route.continue_()
    elif host.endswith("tile.openstreetmap.org"):
        route.abort()
    else:
        fremd.append(route.request.url)
        route.abort()


WAKE = """(() => { window.__wl = 0; window.__vib = 0;
  Object.defineProperty(navigator, 'wakeLock', { configurable: true, value: { request: async () => { window.__wl++;
    return { released: false, release() { this.released = true; }, addEventListener() {} }; } } });
  Object.defineProperty(navigator, 'vibrate', { configurable: true, value: () => { window.__vib++; return true; } }); })();"""

FPS = """(dauer) => new Promise(fertig => { let n = 0, schlimm = 0; const t0 = performance.now(); let letzt = t0;
  const f = t => { n++; schlimm = Math.max(schlimm, t - letzt); letzt = t;
    if (t - t0 < dauer) requestAnimationFrame(f); else fertig({ fps: n / ((t - t0) / 1000), schlimm }); };
  requestAnimationFrame(f); })"""

# Tippziele (sichtbare Knöpfe, Felder, Links) und seitliches Scrollen
MASSE = """() => { const klein = [];
  document.querySelectorAll('button, input, a, [role=button]').forEach(e => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    if (!r.width || cs.visibility === 'hidden' || e.closest('[hidden]')) return;
    if (r.width < 48 || r.height < 48) klein.push((e.id || e.dataset.befehl || e.textContent.trim().slice(0, 16)) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height)); });
  return { klein, sw: document.documentElement.scrollWidth, vw: innerWidth, text: document.body.innerText,
    bg: getComputedStyle(document.body).backgroundColor }; }"""


# sichtbarer Text der Bühne: Elemente mit Deckkraft unter 0,5 (noch verdeckte Namen) zählen nicht
SICHTBAR = """() => { const st = document.querySelector('#rueckblick'), out = [];
  const w = document.createTreeWalker(st, NodeFilter.SHOW_TEXT); let n;
  while ((n = w.nextNode())) { const t = n.nodeValue.trim(); if (!t) continue;
    let o = 1, x = n.parentElement;
    while (x && x !== st.parentElement) { const cs = getComputedStyle(x); o *= +cs.opacity; if (cs.display === 'none' || cs.visibility === 'hidden') { o = 0; break; } x = x.parentElement; }
    if (o >= 0.5) out.push(t); }
  return out.join(' '); }"""


def show_seite(b, szenario="rueckblick", w=1280, h=720, rb=True, extra=""):
    c = b.new_context(viewport={"width": w, "height": h})
    pg = c.new_page()
    pg.set_default_timeout(30000)
    pg.on("pageerror", lambda e: err.append(f"show: {e}"))
    pg.on("dialog", lambda d: d.accept())
    pg.route("**/*", wache)
    pg.route("**/rest/v1/rpc/rb_*", db.route)   # zuletzt angemeldet, gilt zuerst
    pg.add_init_script(WAKE + ("window.__rbEcht = true;" if rb else "") + extra)
    pg.goto(BASIS + "app.html?szenario=" + szenario)
    pg.wait_for_function("window.__fertig === true", timeout=40000)
    return pg


def handy_seite(b, w=390, h=844, scheme="light"):
    c = b.new_context(viewport={"width": w, "height": h}, color_scheme=scheme, has_touch=True, is_mobile=True)
    pg = c.new_page()
    pg.set_default_timeout(30000)
    pg.on("pageerror", lambda e: err.append(f"handy: {e}"))
    pg.route("**/*", wache)
    pg.route("**/rest/v1/rpc/rb_*", db.route)
    pg.add_init_script(WAKE)
    pg.goto(BASIS + "rueckblick-fernbedienung.html")
    return pg


def einloggen(ph, pin="4711"):
    ph.fill("#pin", pin)
    ph.click("#pinOk")


def tippen(ph, befehl):
    ph.click(f"[data-befehl={befehl}]")


def zustand(pg):
    return pg.evaluate("RB.zustand()")


def warte(pg, js, ms=5000):
    try:
        pg.wait_for_function(js, timeout=ms)
        return True
    except Exception:
        return False


STRICHE = re.compile("[\u2013\u2014\u00b7]")

with sync_playwright() as pw:
    vorher = abschluss.merken()
    b = pw.chromium.launch(channel="chrome", headless=True)
    try:
        print("Gruppe 1: Datei, Service Worker, Texte")
        seite = REPO / "rueckblick-fernbedienung.html"
        pruef(seite.exists(), "rueckblick-fernbedienung.html liegt im Repo-Wurzelordner")
        quelle = seite.read_text(encoding="utf-8") if seite.exists() else ""
        pruef(quelle and not re.search(r"googleapis|gstatic|unpkg|jsdelivr|cdnjs|https?://(?!127)", re.sub(r"<!--.*?-->", "", quelle, flags=re.S)),
              "keine Adresse außerhalb (Schriften aus vendor/fonts, Zugang aus config.js)")
        pruef("vendor/fonts/" in quelle and 'src="config.js"' in quelle, "Schriften aus vendor/fonts, config.js eingebunden")
        sw = (REPO / "sw.js").read_text(encoding="utf-8")
        # rueckblick.py verlangt, dass "rueckblick" in sw.js gar nicht vorkommt; der Kommentar nennt sie "Fernbedienung"
        pruef('pfad === "" || pfad === "index.html"' in sw and "rueckblick" not in sw,
              "Service Worker: die Seite ist weder Hülle noch im Cache, Navigation geht unberührt ans Netz")
        pruef("Fernbedienung der Rückblick-Show" in sw, "Service Worker nennt die Seite in der Liste der anderen Seiten")

        print("Gruppe 2: alte Befehle wirken nach dem Öffnen nicht")
        db.nr, db.befehl, db.befehl_um = 7, "weiter", time.time() - 3
        pg = show_seite(b)
        pg.wait_for_selector("#rb-oStart", timeout=60000)
        pruef(warte(pg, "RB.fern && RB.fern().nr === 7", 5000), "Show übernimmt beim Öffnen den Zähler (7)")
        pg.wait_for_timeout(2500)
        pruef(zustand(pg)["phase"] == "vorbereiten", f"der Befehl von vorher startet nichts ({zustand(pg)['phase']})")
        pruef(pg.locator("#rb-fern").count() == 1 and pg.locator("#rb-fern svg").count() >= 1, "Vorbereiten: Block Handy als Fernbedienung mit QR-Code")
        ft = pg.inner_text("#rb-fern") if pg.locator("#rb-fern").count() else ""
        pruef("Handy als Fernbedienung" in ft and "PIN am Handy eingeben" in ft and "Handy verbunden" not in ft, f"Block nennt PIN, noch kein Handy ({ft!r})")
        link = pg.evaluate("RB.fern().link")
        pruef(link == BASIS + "rueckblick-fernbedienung.html", f"QR-Link zeigt auf die Handy-Seite, ohne PIN ({link})")

        print("Gruppe 3: PIN am Handy")
        ph = handy_seite(b)
        ph.wait_for_selector("#pin")
        pruef(ph.locator("#bedien").is_hidden(), "ohne PIN kein Bedienfeld")
        einloggen(ph, "0000")
        pruef(warte(ph, "document.querySelector('#pinFehler') && /Falsche PIN/.test(document.querySelector('#pinFehler').textContent)", 5000),
              "falsche PIN: Meldung")
        pruef(ph.evaluate("sessionStorage.getItem('sj.pin')") is None and ph.locator("#bedien").is_hidden(), "falsche PIN: nichts gemerkt, kein Bedienfeld")
        einloggen(ph)
        pruef(warte(ph, "!document.querySelector('#bedien').hidden", 5000), "richtige PIN: Bedienfeld")
        pruef(ph.evaluate("sessionStorage.getItem('sj.pin')") == "4711" and "4711" not in ph.url, "PIN im sessionStorage, nicht in der Adresse")
        pruef(ph.evaluate("localStorage.getItem('sj.pin')") is None, "PIN nicht im localStorage")
        pruef(warte(ph, "/Show verbunden/.test(document.querySelector('#verbindung').textContent)", 5000), "Handy: Show verbunden")
        pruef(warte(ph, "/Vorbereiten/.test(document.querySelector('#kapitel').textContent)", 5000), "Handy: Kapitel Vorbereiten")
        pruef(warte(pg, "/Handy verbunden/.test(document.querySelector('#rb-fern').textContent)", 7000), "Laptop: Handy verbunden")
        pruef(ph.evaluate("window.__wl") >= 1, "Handy: Wake Lock angefordert")
        pruef(ph.inner_text("[data-befehl=start]").strip() == "Start", "großer Knopf heißt in Vorbereiten Start")

        print("Gruppe 4: Start, Weiter, Doppeltipp, Zurück, Pause, Schwarzbild")
        n0 = len(db.angenommen())
        tippen(ph, "start")
        pruef(warte(pg, "RB.zustand().phase === 'show' && RB.zustand().id === 'vorspann'", 5000), "Start am Handy startet die Show")
        pruef(ph.evaluate("window.__vib") >= 1, "Tippen vibriert kurz")
        pruef(warte(ph, "/Vorspann/.test(document.querySelector('#kapitel').textContent)", 5000), "Handy: Kapitel Vorspann")
        pruef(warte(ph, "document.querySelector('[data-befehl=weiter]') && !document.querySelector('[data-befehl=weiter]').hidden", 3000),
              "großer Knopf heißt in der Show Weiter")
        pg.wait_for_timeout(800)
        tippen(ph, "weiter")
        pruef(warte(pg, "RB.zustand().id === 'fakten'", 5000), f"Weiter am Handy: nächstes Kapitel wie die Taste ({zustand(pg)['id']})")
        kap = pg.evaluate("RB.kapitel()")
        ids = [k["id"] for k in kap]
        aw = [i for i, k in enumerate(kap) if k["art"] == "award" and re.match(r"award\d", k["id"])]
        a1 = ids[aw[0]]
        pg.evaluate(f"RB.starten('{a1}', 1000)")
        pg.wait_for_timeout(900)
        n1 = len(db.angenommen())
        ph.click("[data-befehl=weiter]")
        ph.click("[data-befehl=weiter]", delay=0)
        pg.wait_for_timeout(3000)
        pruef(zustand(pg)["id"] == ids[aw[0] + 1], f"Doppeltipp: genau ein Schritt ({a1} -> {zustand(pg)['id']})")
        pruef(len(db.angenommen()) - n1 == 1, f"Doppeltipp: ein Befehl angenommen ({len(db.angenommen()) - n1})")
        pg.wait_for_function("RB.zustand().lokal > 2200", timeout=8000)
        a2 = zustand(pg)["id"]
        tippen(ph, "zurueck")
        pruef(warte(pg, f"RB.zustand().id === '{a2}' && RB.zustand().lokal < 1500", 5000), "Zurück am Handy: Kapitel von vorn wie die Taste")
        pg.wait_for_timeout(700)
        tippen(ph, "pause")
        pruef(warte(pg, "RB.zustand().spielt === false", 5000), "Pause am Handy hält die Show an")
        pruef(warte(ph, "/Abspielen/.test(document.querySelector('[data-befehl=pause]').textContent)", 5000), "Handy: Knopf heißt jetzt Abspielen")
        pruef(warte(ph, "/Pause/.test(document.querySelector('#zustand').textContent)", 5000), "Handy: Zustand Pause")
        pg.wait_for_timeout(400)
        tippen(ph, "pause")
        pruef(warte(pg, "RB.zustand().spielt === true", 5000), "Abspielen am Handy setzt fort")
        pg.wait_for_timeout(400)
        tippen(ph, "schwarz")
        pruef(warte(pg, "document.querySelector('#rb-schwarz').classList.contains('an')", 5000), "Schwarzbild am Handy")
        pruef(warte(ph, "/Schwarzbild/.test(document.querySelector('#zustand').textContent)", 5000), "Handy: Zustand Schwarzbild")
        pg.wait_for_timeout(400)
        id_vor = zustand(pg)["id"]
        tippen(ph, "weiter")
        pruef(warte(pg, "!document.querySelector('#rb-schwarz').classList.contains('an')", 5000) and zustand(pg)["id"] == id_vor,
              "Weiter im Schwarzbild holt erst das Bild zurück, wie jede Taste")

        print("Gruppe 5: Status folgt der Show, auch bei Tasten am Laptop")
        pg.evaluate("RB.starten('zeitraffer', 69500)")
        pg.wait_for_timeout(900)
        pg.keyboard.press("ArrowRight")
        pruef(warte(pg, "RB.zustand().id === 'rangliste'", 3000), "Taste am Laptop wirkt weiter")
        pruef(warte(ph, "/^Rangliste/.test(document.querySelector('#kapitel').textContent.trim())", 4000), "Handy zeigt das Kapitel nach der Taste")
        pruef(warte(ph, "/wartet auf Weiter/.test(document.querySelector('#zustand').textContent)", 6000), "Handy: Rangliste, wartet auf Weiter")
        pruef(ph.locator("#fort i").count() == 1, "Handy: Fortschrittsbalken")

        print("Gruppe 6: Moderation vor Platz 3")
        dritter = pg.evaluate("(() => { const t = RB.D().rang.find(t => t.place === 3); return { name: t.name, n: t.members.length, m: t.members.slice(0, 2) }; })()")
        pg.evaluate("RB.starten('platz3', 1000)")
        pruef(warte(ph, "/Als Nächstes wird Platz 3 aufgedeckt/.test(document.querySelector('#mod').textContent)", 5000), "Moderation: Als Nächstes wird Platz 3 aufgedeckt")
        mt = ph.inner_text("#mod")
        pruef(dritter["name"] in mt and f"{dritter['n']} Leute" in mt and all(m in mt for m in dritter["m"]), f"Moderation nennt Team, Zahl und Namen ({mt[:160]!r})")
        pruef(re.search(r"Zeit \d:\d\d:\d\d", mt) and "hinter dem Ersten" in mt and "Danach: Platz 2" in mt, "Moderation: Zeit, Abstand, Danach: Platz 2")
        sichtbar = pg.evaluate(SICHTBAR)
        # der Name selbst steht dort in der Reihe der noch verdeckten Teams (.sp-rest, ohne Platz): das ist so gewollt
        spalte = pg.evaluate("(() => { const n = document.querySelector('.sp-spalte[data-p=\"3\"] .sp-team .n'); return n ? +getComputedStyle(n).opacity : 0; })()")
        pruef("Als Nächstes" not in sichtbar and "Moderation" not in sichtbar and "hinter dem Ersten" not in sichtbar and spalte < 0.5,
              f"Moderation nie am Beamer, Platz 3 dort noch verdeckt ({spalte:.2f})")
        pruef(not STRICHE.search(mt), "Moderation ohne Gedankenstrich und Mittelpunkt")
        # nach dem Aufdecken: Kofferübergabe
        pg.evaluate("RB.starten('platz3', 'nach')")
        pruef(warte(ph, "/Koffer/.test(document.querySelector('#mod').textContent)", 5000), "Moderation nach dem Aufdecken: Kofferübergabe")
        # alle Kapitel: Texte ohne Striche und Mittelpunkt, Größe unter 20 KB
        alles, gross = [], 0
        for k in kap:
            for t_ in (0, max(0, k["dur"] - 50)) if not k["endlos"] else (0,):
                pg.evaluate(f"RB.zeige('{k['id']}', {t_})")
                st = pg.evaluate("RB.fernStatus()")
                gross = max(gross, len(json.dumps(st, ensure_ascii=False).encode("utf-8")))
                alles += st.get("mod") or []
        pruef(all(alles) and len(alles) >= len(kap), f"jedes Kapitel hat eine Moderation ({len(alles)} Zeilen)")
        pruef(not [x for x in alles if STRICHE.search(x)], f"Moderation ohne Striche {[x for x in alles if STRICHE.search(x)][:2]}")
        pruef(gross < 20480, f"Status bleibt unter 20 KB ({gross} Byte)")
        pruef(any("Läuft endlos" in x for x in alles) and any(x.startswith("Läuft. Gleich:") for x in alles), "Bausteine Zeitraffer und Abspann")

        print("Gruppe 7: Zum Ende mit Rückfrage")
        pg.evaluate("RB.starten('fakten', 1000)")
        pg.wait_for_timeout(1500)
        n2 = len(db.angenommen())
        tippen(ph, "ende")
        pg.wait_for_timeout(1500)
        pruef(len(db.angenommen()) == n2 and zustand(pg)["id"] == "fakten", "Zum Ende: erster Tipp fragt nur")
        pruef(ph.locator("#endeFrage").is_visible() and "Rangliste" in ph.inner_text("#endeFrage"), "Zum Ende: Rückfrage nennt die Rangliste")
        tippen(ph, "ende")
        pruef(warte(pg, "RB.zustand().id === 'rangliste'", 5000), "Zum Ende: zweiter Tipp springt zur Rangliste wie die Taste Ende")

        print("Gruppe 8: Bildrate mit aktiver Fernbedienung")
        for kid, ab in (("zeitraffer", 35000), ("abspann", 3000)):
            pg.evaluate(f"RB.starten('{kid}', {ab})")
            pg.wait_for_timeout(400)
            m = pg.evaluate(f"({FPS})(2500)")
            pruef(m["fps"] >= 50, f"{kid}: {m['fps']:.0f} Bilder/s mit Fernbedienung (schlimmstes Bild {m['schlimm']:.0f} ms)")
        n_poll = sum(1 for x in db.log if x[0] == "rb_poll")
        pruef(n_poll >= 10, f"die Show fragt laufend ab ({n_poll} rb_poll)")

        print("Gruppe 9: Netzfehler stören die Show nicht")
        db.kaputt = {"*"}
        pg.evaluate("RB.starten('zeitraffer', 3000)")
        l0 = zustand(pg)["lokal"]
        m = pg.evaluate(f"({FPS})(3000)")
        pruef(zustand(pg)["lokal"] > l0 + 2000 and m["fps"] >= 50, f"Server 500: Show läuft weiter ({m['fps']:.0f} Bilder/s)")
        pg.keyboard.press("ArrowRight")
        pruef(warte(pg, "RB.zustand().id === 'rangliste'", 3000), "Server 500: Tasten wirken")
        pruef(warte(ph, "/Keine Verbindung/.test(document.querySelector('#verbindung').textContent)", 5000), "Handy: Keine Verbindung zum Server")
        pruef(ph.locator("[data-befehl=weiter]").is_disabled(), "Handy: ohne Verbindung keine Befehle")
        ph.screenshot(path=str(SHOTS / "fern-390-hell-5-ohne-netz.png"))
        db.kaputt = set()
        pruef(warte(ph, "/Show verbunden/.test(document.querySelector('#verbindung').textContent)", 8000), "Handy: wieder verbunden")

        print("Gruppe 10: Keine Show gefunden nach 6 s ohne Herzschlag")
        db.kaputt = {"rb_status_setzen"}
        t0 = time.time()
        ok = warte(ph, "/Keine Show gefunden/.test(document.querySelector('#verbindung').textContent)", 12000)
        dt = time.time() - t0
        pruef(ok and dt >= 3, f"Herzschlag fehlt: Keine Show gefunden nach {dt:.1f} s")
        pruef(ph.locator("[data-befehl=weiter]").is_disabled(), "Keine Show: Befehle gesperrt")
        db.kaputt = set()
        pruef(warte(ph, "/Show verbunden/.test(document.querySelector('#verbindung').textContent)", 8000), "Herzschlag wieder da: Show verbunden")

        print("Gruppe 11: rb_ende beim Verlassen")
        pg.evaluate("location.hash = '#/admin'")
        pg.wait_for_function("!document.querySelector('#rueckblick')", timeout=15000)
        pg.wait_for_timeout(1500)
        pruef(any(x[0] == "rb_ende" for x in db.log), "Show verlassen: rb_ende")
        pruef(db.status is None, "Status gelöscht")
        pruef(warte(ph, "/Keine Show gefunden/.test(document.querySelector('#verbindung').textContent)", 5000), "Handy: Keine Show gefunden")
        n_poll = sum(1 for x in db.log if x[0] == "rb_poll")
        pg.wait_for_timeout(2500)
        pruef(sum(1 for x in db.log if x[0] == "rb_poll") == n_poll, "nach dem Verlassen keine Abfrage mehr")
        pg.context.close()

        print("Gruppe 12: Probe mit Fernbedienung (Friedrich 17.10.: den Demo-Rückblick vom Handy steuern)")
        laptop = lambda: sum(1 for x in db.log if x[0] in ("rb_poll", "rb_status_setzen", "rb_ende"))  # noqa: E731 (das Handy fragt weiter)
        vor = laptop()
        pp = show_seite(b, "rueckblick-probe", rb=True)
        pp.wait_for_selector("#rb-oStart", timeout=60000)
        pp.wait_for_timeout(2000)
        pruef(pp.locator("#rb-fern").count() == 1 and pp.locator("#rb-fern .v-qr svg").count() == 1 and pp.locator("#rb-fernPin").count() == 1,
              "Probe: Block mit QR-Code und PIN-Feld zum Aktivieren")
        pruef(laptop() == vor, f"Probe vor dem Aktivieren: keine Abfrage ({laptop() - vor})")
        pp.fill("#rb-fernPin", "0000")
        pp.keyboard.press("Enter")
        pruef(warte(pp, "/Falsche PIN/.test(document.querySelector('#rb-fern').textContent)", 5000) and pp.locator("#rb-fernPin").count() == 1,
              "Probe: falsche PIN, Meldung, Feld bleibt")
        pruef(zustand(pp)["phase"] == "vorbereiten" and pp.evaluate("sessionStorage.getItem('sj.pin')") is None, "Probe: Enter im PIN-Feld startet nichts, nichts gemerkt")
        pp.fill("#rb-fernPin", "4711")
        pp.click("#rb-fernForm button")
        pruef(warte(pp, "RB.fern().an && /PIN am Handy eingeben/.test(document.querySelector('#rb-fern').textContent)", 5000), "Probe: aktiviert")
        pruef(pp.evaluate("sessionStorage.getItem('sj.pin')") == "4711" and "4711" not in pp.url and pp.evaluate("localStorage.getItem('sj.pin')") is None,
              "Probe: PIN nur im sessionStorage")
        pruef(warte(ph, "/Vorbereiten/.test(document.querySelector('#kapitel').textContent) && /Probe/.test(document.querySelector('#sub').textContent)", 6000),
              "Handy: Probe im Vorbereiten, als Probe gekennzeichnet")
        tippen(ph, "start")
        pruef(warte(pp, "RB.zustand().phase === 'show'", 5000), "Handy startet die Probe")
        dritter = pp.evaluate("RB.D().rang.find(t => t.place === 3).name")
        pp.evaluate("RB.starten('platz3', 1000)")
        pruef(warte(ph, f"/Als Nächstes wird Platz 3 aufgedeckt: {dritter}/.test(document.querySelector('#mod').textContent)", 6000),
              f"Probe: Moderation mit den Demo-Teams ({dritter})")
        pp.wait_for_timeout(700)
        tippen(ph, "weiter")
        pruef(warte(pp, "RB.zustand().hNr === 1", 5000), "Probe: Weiter am Handy deckt Platz 3 auf")
        pp.evaluate("location.hash = '#/'")
        pp.wait_for_function("!document.querySelector('#rueckblick')", timeout=15000)
        pp.wait_for_timeout(1500)
        pruef(db.status is None, "Probe verlassen: rb_ende")
        pp.context.close()
        # die PIN der Spielleitung ändert sich, während die Probe läuft: die Fernbedienung geht aus, der Block fragt neu
        pf = show_seite(b, "rueckblick-probe", rb=True)
        pf.wait_for_selector("#rb-fernPin", timeout=60000)
        pf.fill("#rb-fernPin", "4711")
        pf.keyboard.press("Enter")
        warte(pf, "RB.fern().an", 5000)
        db.pin = "neu"
        pruef(warte(pf, "!RB.fern().an && !!document.querySelector('#rb-fernPin') && /Falsche PIN/.test(document.querySelector('#rb-fern').textContent)", 5000)
              and pf.evaluate("sessionStorage.getItem('sj.pin')") is None, "PIN geändert: Fernbedienung aus, Block fragt neu, alte PIN vergessen")
        db.pin = "4711"
        pf.context.close()
        # Datenbank ohne die Migration: die Show hört auf zu fragen und sagt es im Vorbereiten
        pm = show_seite(b, "rueckblick", rb=False, extra="window.__rbFehlt = true;")
        pm.wait_for_selector("#rb-oStart", timeout=60000)
        pruef(warte(pm, "/Datenbank/.test((document.querySelector('#rb-fern') || {}).textContent || '')", 5000), "ohne Migration: Hinweis im Block")
        pm.context.close()

        print("Gruppe 13: Handy-Seite, Größen, hell und dunkel, Bildschirmfotos")
        db.status, db.status_um = None, None
        pg = show_seite(b)
        pg.wait_for_selector("#rb-oStart", timeout=60000)
        pg.click("#rb-oStart")
        pg.wait_for_function("RB.zustand().phase === 'show'")
        for (w, h) in ((390, 844), (360, 740)):
            for scheme in ("light", "dark"):
                name = "hell" if scheme == "light" else "dunkel"
                p2 = handy_seite(b, w, h, scheme)
                p2.wait_for_selector("#pin")
                r = p2.evaluate(MASSE)
                pruef(r["sw"] <= r["vw"] and not r["klein"], f"{w} {name} PIN: kein seitliches Scrollen ({r['sw']}/{r['vw']}), Tippziele {r['klein']}")
                p2.screenshot(path=str(SHOTS / f"fern-{w}-{name}-1-pin.png"))
                einloggen(p2)
                p2.wait_for_function("!document.querySelector('#bedien').hidden")
                pg.evaluate("RB.starten('platz3', 1000)")
                warte(p2, "/Als Nächstes wird Platz 3/.test(document.querySelector('#mod').textContent)", 5000)
                p2.wait_for_timeout(200)
                r = p2.evaluate(MASSE)
                pruef(r["sw"] <= r["vw"] and not r["klein"], f"{w} {name} Bedienfeld: kein seitliches Scrollen ({r['sw']}/{r['vw']}), Tippziele {r['klein']}")
                pruef(not STRICHE.search(r["text"]), f"{w} {name}: Texte ohne Gedankenstrich und Mittelpunkt")
                hoch = p2.evaluate("document.querySelector('[data-befehl=weiter]').getBoundingClientRect().height")
                unten = p2.evaluate("innerHeight - document.querySelector('[data-befehl=weiter]').getBoundingClientRect().bottom")
                pruef(hoch >= 96 and 0 <= unten <= 40, f"{w} {name}: Weiter mindestens 96 px hoch ({hoch:.0f}), unten am Daumen ({unten:.0f} px Rand)")
                dunkel = p2.evaluate("(() => { const m = getComputedStyle(document.body).backgroundColor.match(/\\d+/g).map(Number); return (m[0] + m[1] + m[2]) / 3 < 80; })()")
                pruef(dunkel == (scheme == "dark"), f"{w} {name}: Hintergrund passt zum Schema")
                p2.screenshot(path=str(SHOTS / f"fern-{w}-{name}-2-moderation.png"))
                mod_unten = p2.evaluate("document.querySelector('#mod').getBoundingClientRect().bottom <= document.querySelector('.bedien').getBoundingClientRect().top + 1 || document.scrollingElement.scrollHeight > innerHeight")
                pruef(mod_unten, f"{w} {name}: Moderation nicht unter dem Bedienfeld verdeckt")
                pg.evaluate("RB.starten('fakten', 0)")
                warte(p2, "/Fun Facts/.test(document.querySelector('#kapitel').textContent)", 5000)
                p2.screenshot(path=str(SHOTS / f"fern-{w}-{name}-3-bedienfeld.png"))
                db.kaputt = {"rb_status_setzen"}
                warte(p2, "/Keine Show gefunden/.test(document.querySelector('#verbindung').textContent)", 12000)
                p2.screenshot(path=str(SHOTS / f"fern-{w}-{name}-4-keine-show.png"))
                db.kaputt = set()
                if w == 390 and scheme == "light":
                    p2.click("#thema")
                    pruef(p2.evaluate("document.documentElement.dataset.theme") == "dark", "Schalter hell/dunkel")
                    pruef(p2.evaluate("localStorage.getItem('sj.thema')") == "dark", "Schalter gilt wie in der App (sj.thema)")
                p2.context.close()
        pg.context.close()
    except Exception as e:  # noqa: BLE001
        pruef(False, f"Abbruch: {type(e).__name__}: {str(e)[:300]}")

    pruef(not err, f"keine Skriptfehler {err[:3]}")
    pruef(not fremd, f"keine Anfrage an fremde Rechner {fremd[:2]}")
    sys.stdout.flush()
    print("FEHLER: " + str(len(fehler)) if fehler else "OK")
    sys.stdout.flush()
    abschluss.ende(fehler, vorher)
