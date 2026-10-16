#!/usr/bin/env python3
"""
Rückblick-Show (Spezifikation 2026-10-15-rueckblick-show-design.md, SPIEL.md §16) im Prüfstand, ohne Datenbank.

    python tools/pruefstand/rueckblick.py          alle
    python tools/pruefstand/rueckblick.py 3 5      nur diese Gruppen

Gruppen: 1 Texte der App (Datenschutz, Löschdatum, Knopf), 2 Sperren und PIN, 3 Laden und Vorbereiten, 4 Kapitel,
5 Aufbereiten (Sprungfilter, Grenzen, Team ohne Check-in), 6 Tasten und Ablauf, 7 Schutz vor dem Neuzeichnen,
8 Läuft ohne Netz (Karte, Schriften, Version), 9 Auswahl von Fotos und Fehler beim Laden, 10 Bühne (Schrift, Rand,
Striche, Bildschirmfotos), 11 Probe, 12 Verlassen.
Spiel (app.html mit mock.js, Port 8864). Das Ergebnis steht VOR dem Schließen (Chrome 155 hängt sonst, siehe
abschluss.py). Im Vordergrund mit Timeout aufrufen, etwa `timeout 500 python tools/pruefstand/rueckblick.py`.
"""
import functools
import http.server
import json
import pathlib
import re
import sys
import threading
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


PORT = 8864
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
APP = f"http://127.0.0.1:{PORT}/app.html?szenario="
SHOTS = HIER / "shots"
SHOTS.mkdir(exist_ok=True)
NUR = {int(x) for x in sys.argv[1:] if x.isdigit()}
an = lambda n: not NUR or n in NUR
fehler, err, fremd = [], [], []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def wache(route):
    host = urlparse(route.request.url).hostname or ""
    if host in ("127.0.0.1", "localhost"):
        route.continue_()
    elif host.endswith("tile.openstreetmap.org"):   # Kacheln der Spielleitungskarte, nicht der Show
        route.abort()
    else:
        fremd.append(route.request.url)
        route.abort()


def neu(b, szenario, w=390, h=844, scheme="light", init=None, abbrechen=()):
    c = b.new_context(viewport={"width": w, "height": h}, color_scheme=scheme)
    pg = c.new_page()
    pg.set_default_timeout(30000)
    pg.on("pageerror", lambda e: err.append(f"{szenario}: {e}"))
    pg.route("**/*", wache)
    for muster in abbrechen:
        pg.route(muster, lambda r: r.abort())
    if init:
        pg.add_init_script(init)
    pg.goto(APP + szenario)
    pg.wait_for_function("window.__fertig === true", timeout=40000)
    return pg


def show(b, szenario, **kw):
    """Show öffnen und bis Vorbereiten warten."""
    pg = neu(b, szenario, w=kw.pop("w", 1920), h=kw.pop("h", 1080), **kw)
    pg.wait_for_selector("#rb-oStart", timeout=60000)
    return pg


def text(pg, sel="#app"):
    return pg.inner_text(sel)


WAKE = """(() => { window.__wl = 0; window.__sperren = [];
  Object.defineProperty(navigator, 'wakeLock', { configurable: true, value: { request: async () => { window.__wl++;
    const s = { released: false, release() { this.released = true; }, addEventListener() {} }; window.__sperren.push(s); return s; } } }); })();"""

# prüft Schriftgröße (auf dem Bildschirm), Rand und Striche aller sichtbaren Texte der Bühne
SCAN = """() => {
  const st = document.querySelector('#rb-buehne'), r0 = st.getBoundingClientRect(), s = r0.width / 1920;
  const out = { klein: [], raus: [], text: st.innerText, striche: [] };
  const w = document.createTreeWalker(st, NodeFilter.SHOW_TEXT), seen = new Set(); let n;
  while ((n = w.nextNode())) {
    const t = n.nodeValue.trim(); if (!t) continue;
    if (/[\\u2013\\u2014\\u00b7]/.test(t)) out.striche.push(t.slice(0, 40));
    const e = n.parentElement; if (seen.has(e)) continue; seen.add(e);
    if (e.closest('.rolle') || e.closest('.walze')) continue;
    let o = 1, x = e;
    while (x && x !== st) { const cs = getComputedStyle(x); o *= +cs.opacity; if (cs.display === 'none' || cs.visibility === 'hidden') { o = 0; break; } x = x.parentElement; }
    if (o < 0.5) continue;
    const fs = parseFloat(getComputedStyle(e).fontSize) * s;
    if (fs < 19.5) out.klein.push((e.className.baseVal !== undefined ? e.className.baseVal : e.className) + ':' + t.slice(0, 24) + ':' + fs.toFixed(1));
    const r = e.getBoundingClientRect();
    if (r.width && (r.left < r0.left - 1 || r.right > r0.right + 1 || r.top < r0.top - 1 || r.bottom > r0.bottom + 1))
      out.raus.push(t.slice(0, 24) + ' ' + [r.left, r.top, r.right, r.bottom].map(Math.round).join(','));
  }
  return out;
}"""

# Gruppen 5: Rohdaten für Aufbereiten, ein Team spielt, ein paar nicht
ROH = """(opt) => {
  const T0 = Date.UTC(2026, 9, 17, 12, 0, 0), M = 60000, iso = t => new Date(t).toISOString();
  const sts = [1, 2, 3].map(p => ({ id: 's' + p, position: p, name: 'S' + p, lat: 50.1 + p * 0.001, lng: 14.4235, radiusM: 50 }));
  const teams = opt.teams.map((t, i) => ({ id: 't' + i, name: t.name, members: [], place: null, finishedAt: null }));
  const tracks = opt.teams.map((t, i) => ({ id: 't' + i, name: t.name, points: t.points || [], stations: (t.solved || []).map((m, k) => ({ position: k + 1, checkedInAt: iso(T0 + (m - 2) * M), solvedAt: iso(T0 + m * M) })) }));
  return { state: { status: 'finished', startedAt: iso(T0), finishedAt: iso(T0 + opt.ende * M), prizeCount: 3, start: { name: 'Start', lat: 50.1, lng: 14.4235 }, stations: sts, teams },
    tracks: { finishedAt: iso(T0 + opt.ende * M), teams: tracks }, photos: [], T0 };
}"""


with sync_playwright() as pw:
    vorher = abschluss.merken()
    b = pw.chromium.launch(channel="chrome", headless=True)

    # ------------------------------------------------------------------ 1
    if an(1):
        print("Gruppe 1: Texte der App")
        pg = neu(b, "selfie-anmeldung")
        t = text(pg)
        pruef("beim Abendessen alle im Rückblick" in t and "nur euer Team" not in t, "Anmeldung: Fotos sieht auch das Abendessen")
        pruef("werden alle Fotos gelöscht" in t and "löschen wir" not in t, "Anmeldung: 'werden alle Fotos gelöscht' statt 'löschen wir'")
        pg = neu(b, "selfie-offen")
        t = text(pg)
        pruef("Das Foto sehen euer Team, die Spielleitung und beim Abendessen alle im Rückblick." in t, "Selfie-Schritt: neuer Satz")
        pg = neu(b, "selfie-album")
        t = text(pg)
        pruef("werden alle Fotos gelöscht" in t and "löschen wir" not in t, "Album: 'werden alle Fotos gelöscht'")
        pg = neu(b, "leitung-unterwegs-standort")
        pg.wait_for_selector(".share", timeout=15000)
        t = text(pg, ".share")
        pruef("Standort wird mit der Spielleitung geteilt" in t and "Euer Weg erscheint beim Abendessen im Rückblick." in t, f"Standort-Zeile nennt den Rückblick ({t.strip()[:100]})")
        pg = neu(b, "admin-fotos", w=900, h=900)
        t = text(pg)
        pruef("beim Abendessen alle im Rückblick" in t and "nur das eigene Team" not in t, "Reiter Fotos: Zusage geändert")
        quelle = (REPO / "index.html").read_text(encoding="utf-8")
        pruef("löschen wir" not in quelle and "sehen nur euer Team" not in quelle and "Sehen können es nur" not in quelle and "sehen nur das eigene Team" not in quelle,
              "index.html enthält die alten Zusagen nicht mehr")
        pg = neu(b, "admin-fotos-heute", w=900, h=900)
        pruef("Ein Datum nach dem Abendessen wählen" in text(pg), "Löschdatum heute: Warnung schon im laufenden Spiel")
        pg = neu(b, "admin-fotos-spaet", w=900, h=900)
        pruef("Ein Datum nach dem Abendessen wählen" not in text(pg), "Löschdatum später: keine Warnung")
        pg = neu(b, "admin-karte", w=1100, h=900)
        pruef(pg.locator("[data-act=a-rueckblick]").count() == 0, "Spiel läuft: kein Rückblick-Knopf")
        pg = neu(b, "admin-beendet", w=1100, h=900)
        pruef(pg.locator(".bar [data-act=a-rueckblick]").count() == 1 and "Rückblick" in text(pg, "[data-act=a-rueckblick]"), "Spiel beendet: Knopf Rückblick im Kopf")
        pg.click("[data-act=a-tab][data-tab=zeit]")
        pg.wait_for_selector("#tlrows")
        pruef(pg.locator("[data-act=a-rueckblick]").count() == 2, "Reiter Zeitachse: zweiter Knopf unter der Zeitachse")
        pg.locator("[data-act=a-rueckblick]").nth(1).click()
        pg.wait_for_selector("#rb-oStart", timeout=60000)
        pruef(pg.evaluate("location.hash") == "#/rueckblick", "Knopf öffnet #/rueckblick mit der PIN aus der Spielleitung")

    # ------------------------------------------------------------------ 2
    if an(2):
        print("Gruppe 2: Sperren und PIN")
        pg = neu(b, "rueckblick-laeuft", w=1280, h=720)
        pg.wait_for_selector(".rb-fehler", timeout=30000)
        pruef("startet nach dem Spielende" in text(pg, "#rueckblick") and pg.locator("#rb-oStart").count() == 0, "Spiel läuft: Sperre, kein Startknopf")
        pg = neu(b, "rueckblick-test", w=1280, h=720)
        pg.wait_for_selector(".rb-fehler", timeout=30000)
        pruef("Testmodus ist an" in text(pg, "#rueckblick") and pg.locator("#rb-oStart").count() == 0, "Testmodus: Sperre mit Schritt")
        pg = neu(b, "rueckblick-ohne-pin", w=1280, h=720)
        pg.wait_for_selector("#rb-pin", timeout=30000)
        pg.fill("#rb-pin", "0000")
        pg.keyboard.press("Enter")
        pg.wait_for_selector(".rb-fehler", timeout=30000)
        pruef("Falsche PIN" in text(pg, "#rueckblick") and pg.locator("#rb-pin").count() == 1, "falsche PIN: Meldung, Feld bleibt")
        pg.fill("#rb-pin", "4711")
        pg.keyboard.press("Enter")
        pg.wait_for_selector("#rb-oStart", timeout=60000)
        pruef(pg.evaluate("sessionStorage.getItem('sj.pin')") == "4711", "richtige PIN: Vorbereiten, PIN im sessionStorage")
        # Tippen der PIN darf keine Show-Taste auslösen (n, k, f, t, h, b, p ...)
        pg = neu(b, "rueckblick-ohne-pin", w=1280, h=720)
        pg.wait_for_selector("#rb-pin", timeout=30000)
        pg.type("#rb-pin", "kfnthbp")
        pruef(pg.input_value("#rb-pin") == "kfnthbp" and pg.locator("#rb-hilfeBox").count() == 0, "PIN-Feld nimmt Buchstaben an, Tasten der Show schlafen")

    # ------------------------------------------------------------------ 3 .. 10 am Hauptszenario
    if any(an(n) for n in (3, 4, 5, 6, 7, 8, 9, 10)):
        pg = show(b, "rueckblick", init=WAKE)
        D = pg.evaluate("(() => { const d = RB.D(); return { fotos: d.fotos.length, teams: d.teams.length, ratio: d.fotos.map(f => f.ratio) }; })()")
        KAP = pg.evaluate("RB.kapitel()")
        log = pg.evaluate("window.__RPC_LOG")
        vt = text(pg, "#rueckblick")

        if an(3):
            print("Gruppe 3: Laden und Vorbereiten")
            pruef(all(x in log for x in ("admin_state", "admin_tracks", "admin_photos", "admin_photo")), "alle vier Abrufe der Show liefen")
            n_foto = log.count("admin_photo")
            pruef(n_foto == D["fotos"] and D["fotos"] > 40, f"{D['fotos']} Fotos aus {n_foto} Abrufen (je Foto einer)")
            pruef(set(pg.evaluate("window.__FOTO_ROUTE")) == {"echt"}, "nur Fotos der echten Route geholt (Teststation bleibt draußen)")
            pruef("7 von 12 Teams im Ziel" in vt, "Vorbereiten: Teams im Ziel")
            pruef("Beim Spielende unterwegs:" in vt and "Delfin" in vt, "Vorbereiten: wer unterwegs war")
            pruef("Delfin ohne Check-in: bleibt am Start" in vt, "Vorbereiten: Team ohne Check-in")
            pruef(f"{D['fotos']} Gruppenfotos geladen" in vt, "Vorbereiten: Zahl der Fotos")
            pruef("Gelöscht am 31.10.2026" in vt, "Vorbereiten: Löschdatum")
            pruef("Alles geladen, die Show läuft jetzt auch ohne Netz" in vt, "Vorbereiten: Alles geladen")
            pruef(min(D["ratio"]) < 1 < max(D["ratio"]), "Hoch- und Querformat aus dem geladenen Bild erkannt")
            pruef("Dauer etwa" in vt and "Rückblick starten" in vt, "Vorbereiten: Dauer und Startknopf")
            pruef(pg.evaluate("window.__wl") >= 1, "Wake Lock beim Öffnen angefordert")
            pg.evaluate("window.__sperren.forEach(s => s.released = true)")
            pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            pg.wait_for_timeout(300)
            pruef(pg.evaluate("window.__wl") >= 2, "Wake Lock nach visibilitychange neu angefordert")
            speicher = pg.evaluate("JSON.stringify([localStorage, sessionStorage].map(s => Object.keys(s).map(k => s.getItem(k))))")
            pruef("/9j/" not in speicher and len(speicher) < 4000, "keine Bilddaten in localStorage oder sessionStorage")
            pruef(pg.evaluate("document.querySelector('#app').inert") is True, "App dahinter ist nicht bedienbar (inert)")

        if an(4):
            print("Gruppe 4: Kapitel")
            kap = KAP
            ids = [k["id"] for k in kap]
            print("      " + " ".join(ids))
            pruef(ids[0] == "vorspann" and ids[1] == "start", "Vorspann, Start")
            pruef(ids[-1] == "abspann" and ids[-2] == "alle", "Alle Teams, Abspann am Ende")
            pruef(ids.index("platz3") < ids.index("platz2") < ids.index("platz1") < ids.index("alle"), "Finale rückwärts 3, 2, 1")
            pruef(all(k["fotos"] > 0 for k in kap if k["art"] == "fotos") and any(k["art"] == "fotos" for k in kap), "kein leeres Fotokapitel")
            pruef([i for i in ids if i.startswith("weg")] == ["weg1", "weg2", "weg3", "weg4", "weg5"], "Wege zu allen fünf Stationen")
            sp = pg.evaluate("RB.D().teams.find(t => t.name === 'Pinguin').sts.length")
            pruef(sp == 5, "Mock-Stand: Pinguin hat alle Stationen")
            gesamt = pg.evaluate("RB.gesamt()") / 1000
            pruef(180 <= gesamt <= 330, f"Gesamtdauer {gesamt:.0f} s liegt zwischen 3 und 5,5 min")
            pg2 = show(b, "rueckblick-ohne-fotos")
            k2 = pg2.evaluate("RB.kapitel()")
            pruef(not any(k["art"] == "fotos" for k in k2) and pg2.locator("#rb-oFotos").count() == 0 and "Gruppenfoto" not in text(pg2, "#rueckblick"),
                  "ohne Fotos: keine Fotokapitel, keine Fotozeile")
            pruef(all(k["dur"] == 24000 for k in k2 if k["id"].startswith("weg")), "ohne Fotos: Wege 24 s")
            pg3 = show(b, "rueckblick-station3-leer")
            k3 = [k["id"] for k in pg3.evaluate("RB.kapitel()")]
            pruef("fotos3" not in k3 and "fotos2" in k3 and "weg3" in k3, "Station ohne ein Foto: kein Fotokapitel, Weg bleibt")
            pg3.context.close()
            pg2.context.close()

        if an(5):
            print("Gruppe 5: Aufbereiten")
            roh = lambda **o: pg.evaluate(f"({ROH})({json.dumps(o)})")
            # Sprungfilter: einzelner Ausreißer fällt weg, Tram- oder Taxifahrt bleibt ganz
            r = pg.evaluate("""() => {
              const p = (x, t) => ({ x, y: 0, t: t * 15000 });
              const spitze = [p(0, 0), p(10, 1), p(20, 2), p(3000, 3), p(40, 4), p(50, 5), p(60, 6)];
              const tram = Array.from({ length: 30 }, (_, i) => p(i * 90, i));       // 6 m/s, über 15 km/h, aber stetig
              const zwei = [p(0, 0), p(10, 1), p(3000, 2), p(3010, 3), p(20, 4), p(30, 5)];
              return { spitze: RB.test.ohneAusreisser(spitze).length, tram: RB.test.ohneAusreisser(tram).length, zwei: RB.test.ohneAusreisser(zwei).length }; }""")
            pruef(r["spitze"] == 6, f"einzelner Sprung verworfen ({r['spitze']} von 7 Punkten)")
            pruef(r["tram"] == 30, f"Tramfahrt kaskadiert nicht ({r['tram']} von 30 Punkten bleiben)")
            # Grenzen: Hälfte der Teams mit Fortschritt; Team ohne Check-in zählt nicht mit
            def grenzen(teams, ende):
                return pg.evaluate("""([roh, ende]) => { const d = RB.test.aufbereiten(roh); return { g: d.grenzen.map(t => (t - roh.T0) / 60000), ende }; }""",
                                   [roh(teams=teams, ende=ende), ende])
            ts = [{"name": "A", "solved": [10, 30, 50]}, {"name": "B", "solved": [20, 40, 60]}, {"name": "C", "solved": [50, 70, 90]},
                  {"name": "X"}, {"name": "Y"}, {"name": "Z"}]
            g = grenzen(ts, 120)["g"]
            pruef(abs(g[1] - 20) < .01, f"Team ohne Check-in zählt bei der Hälfte-Regel nicht mit (Grenze 1 bei {g[1]:.0f} min, erwartet 20)")
            g = grenzen([{"name": "A", "solved": [10, 11, 12]}], 120)["g"]
            pruef(g[1] == 10 and g[2] >= 12 and g[3] >= 14, f"mindestens 2 min zwischen den Grenzen ({g})")
            g = grenzen([{"name": "A", "solved": [10, 40, 100]}], 50)["g"]
            pruef(g[-1] <= 50 and all(g[i] <= g[i + 1] for i in range(len(g) - 1)), f"Grenzen klemmen am Spielende und bleiben monoton ({g})")
            k = pg.evaluate("""([roh]) => { const d = RB.test.aufbereiten(roh); return RB.test.kapitel(d, { fotos: true, aus: new Set() }).filter(k => k.art === 'karte').map(k => [k.id, (k.bis - k.von) / 60000]); }""",
                            [roh(teams=[{"name": "A", "solved": [10, 40, 100]}], ende=50)])
            pruef(all(x[1] >= 0 for x in k), f"Kapitel enden bei finishedAt, keines läuft rückwärts ({k})")
            # Team ganz ohne Check-in: Ring am Start, "0 von 3 Stationen"
            d = pg.evaluate("""() => { const d = RB.D(), t = d.teams.find(x => x.name === 'Delfin'); return { sts: t.sts.length, gps: t.ohneGps, pts: t.pts.length, nah: Math.hypot(t.pts[0].x - d.start.xy[0], t.pts[0].y - d.start.xy[1]) }; }""")
            pruef(d["sts"] == 0 and d["gps"] and d["pts"] == 1 and d["nah"] < 1, f"Delfin ohne Check-in steht am Start ({d})")
            pg.evaluate("RB.zeige('alle', 9000)")
            alle = text(pg, "#rueckblick")
            pruef("0 von 5 Stationen" in alle and "ohne GPS" in alle, "Alle Teams: '0 von 5 Stationen' und 'ohne GPS' für Delfin")

        if an(6):
            print("Gruppe 6: Tasten und Ablauf")
            z = lambda: pg.evaluate("RB.zustand()")
            pg.evaluate("RB.vorbereiten()")   # Gruppe 5 hat die Bühne verstellt
            pg.click("#rb-oStart")
            pg.wait_for_function("RB.zustand().phase === 'show'")
            pruef(z()["id"] == "vorspann" and z()["spielt"], "Start: Vorspann läuft")
            pg.keyboard.press("Space"); pruef(not z()["spielt"], "Leertaste: Pause")
            pg.keyboard.press("Space"); pruef(z()["spielt"], "Leertaste: weiter")
            pg.keyboard.press("ArrowRight"); pruef(z()["id"] == "start", "Pfeil rechts: nächstes Kapitel")
            pg.keyboard.press("ArrowLeft"); pruef(z()["id"] == "vorspann", "Pfeil links in den ersten 1,5 s: Kapitel davor")
            pg.keyboard.press("PageDown"); pg.keyboard.press("n"); pruef(z()["id"] == "weg1", "Bild ab und N: weiter")
            pg.keyboard.press("End"); pruef(z()["id"] == "platz3", "Ende: Platz 3")
            pg.keyboard.press("Home"); pruef(z()["id"] == "vorspann", "Pos1: Anfang")
            pg.keyboard.press("End")
            pg.wait_for_function("RB.zustand().haelt === true", timeout=15000)
            pruef(z()["haelt"] and z()["id"] == "platz3", "Halt vor dem Aufdecken")
            lok = z()["lokal"]; pg.wait_for_timeout(800)
            pruef(abs(z()["lokal"] - lok) < 5, "während des Halts steht das Kapitel")
            pg.keyboard.press("Space"); pruef(not z()["haelt"] and z()["spielt"], "Leertaste deckt auf")
            pg.keyboard.press("b"); pruef(pg.evaluate("document.querySelector('#rb-schwarz').classList.contains('an')") and not z()["spielt"], "B: Bild schwarz und Pause")
            pg.keyboard.press("x"); pruef(not pg.evaluate("document.querySelector('#rb-schwarz').classList.contains('an')"), "jede Taste holt das Bild zurück")
            pg.keyboard.press("h"); pruef(pg.locator("#rb-hilfeBox").count() == 1, "H: Tastenhilfe")
            pg.keyboard.press("Escape"); pruef(pg.locator("#rb-hilfeBox").count() == 0, "Esc schließt die Hilfe")
            pg.evaluate("window.__marker = 1")
            pg.keyboard.press("F5"); pg.wait_for_timeout(700)
            pruef(pg.evaluate("window.__marker") == 1 and pg.evaluate("!!document.querySelector('#rueckblick')"), "F5 lädt nicht neu")
            thema0 = pg.evaluate("document.documentElement.dataset.theme || ''")
            pg.keyboard.press("t")
            pruef(pg.evaluate("document.documentElement.dataset.theme") in ("dark", "light") and pg.evaluate("document.documentElement.dataset.theme") != thema0
                  and pg.evaluate("localStorage.getItem('sj.thema')") == pg.evaluate("document.documentElement.dataset.theme"), "T: hell oder dunkel, gemerkt")
            pg.keyboard.press("t")
            pg.mouse.move(400, 400)
            pg.wait_for_timeout(200)
            pruef(pg.evaluate("!document.querySelector('#rb-leiste').classList.contains('weg')"), "Mausbewegung zeigt die Steuerleiste")
            pg.click("#rb-leiste [data-k=zurueck]"); pg.click("#rb-leiste [data-k=weiter]")
            pruef(pg.evaluate("RB.zustand().phase") == "show", "Steuerleiste bedienbar")

        if an(7):
            print("Gruppe 7: Schutz vor dem Neuzeichnen")
            pg.evaluate("RB.zeige('weg2', 6000)")
            pg.evaluate("document.querySelector('#rueckblick').__m = 1; window.__appAlt = document.querySelector('#app').innerHTML")
            vorher_z = pg.evaluate("RB.zustand()")
            pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            pg.evaluate("window.dispatchEvent(new HashChangeEvent('hashchange'))")
            pg.mouse.click(300, 300)
            pg.click("#rb-buehne", position={"x": 100, "y": 100})
            pg.evaluate("window.dispatchEvent(new Event('focus')); window.dispatchEvent(new Event('resize'))")
            pg.wait_for_timeout(500)
            nachher = pg.evaluate("RB.zustand()")
            pruef(nachher["id"] == "weg2" and nachher["lokal"] == vorher_z["lokal"], f"Kapitel und Zeit nach visibilitychange, hashchange und Klick unverändert ({nachher['id']}, {nachher['lokal']:.0f})")
            pruef(pg.evaluate("document.querySelector('#rueckblick').__m") == 1, "Show-Container ist derselbe geblieben (nicht neu gezeichnet)")
            pg.evaluate("render(); refresh();")
            pg.wait_for_timeout(500)
            pruef(pg.evaluate("document.querySelector('#rueckblick').__m") == 1 and pg.evaluate("RB.zustand().id") == "weg2", "render() und refresh() lassen die Show in Ruhe")
            pruef(pg.evaluate("document.querySelector('#app').innerHTML") == pg.evaluate("window.__appAlt"), "#app wurde nicht angefasst")
            pruef(pg.evaluate("S.view") == "rueckblick", "S.view bleibt rueckblick")
            pruef(pg.evaluate("document.querySelectorAll('#rueckblick [data-act]').length") == 0, "Knöpfe der Show tragen kein data-act")

        if an(8):
            print("Gruppe 8: Läuft ohne Netz")
            res = pg.evaluate("performance.getEntriesByType('resource').map(e => e.name)")
            ext = ["barlow-500-latin-ext", "barlow-600-latin-ext", "barlow-semi-condensed-500-latin-ext", "barlow-semi-condensed-600-latin-ext", "barlow-semi-condensed-700-latin-ext"]
            fehlt = [e for e in ext if not any(e + ".woff2" in r for r in res)]
            pruef(not fehlt, f"alle Schriftschnitte mit latin-ext geholt ({'; '.join(fehlt) or 'alle'})")
            pruef(pg.evaluate("['500 1em \"Barlow Semi Condensed\"','600 1em \"Barlow Semi Condensed\"','700 1em \"Barlow Semi Condensed\"','500 1em Barlow','600 1em Barlow'].every(s => document.fonts.check(s, 'Holešovice Výstaviště Letná Křižík'))"),
                  "document.fonts.check für jeden Schnitt mit dem Mustertext")
            pruef(any("rueckblick-karte.js" in r for r in res) and pg.evaluate("RB.D().hatKarte && RB.D().karteFertig === true"), "Grundkarte geholt und einmal gerastert")
            js = pg.evaluate("[...document.querySelectorAll('script[src],link[href]')].map(e => e.src || e.href).filter(u => /rueckblick/.test(u))")
            pruef(len(js) >= 3 and all(re.search(r"\?v=\d+", u) for u in js), f"rueckblick.js, rueckblick.css und die Karte mit Cache-Bust geladen ({[u.split('/')[-1] for u in js]})")
            pg4 = neu(b, "rueckblick", w=1920, h=1080, abbrechen=("**/rueckblick-karte.js*",))
            pg4.wait_for_selector("#rb-oStart", timeout=60000)
            t4 = text(pg4, "#rueckblick")
            pruef("Grundkarte nicht geladen" in t4 and "Alles geladen" in t4 and not pg4.evaluate("RB.D().hatKarte"), "Karte fehlt: Ausweichlösung, Show bleibt vollständig")
            pg4.click("#rb-oStart"); pg4.wait_for_function("RB.zustand().phase === 'show'")
            pg4.context.close()
            pg5 = neu(b, "rueckblick", w=1920, h=1080, abbrechen=("**/barlow-semi-condensed-700-latin-ext.woff2*",))
            pg5.wait_for_selector("#rb-oStart", timeout=60000)
            t5 = text(pg5, "#rueckblick")
            pruef("Alles geladen" not in t5 and "Schrift nicht geladen" in t5, "Schrift fehlt: kein 'Alles geladen'")
            pg5.context.close()

        if an(9):
            print("Gruppe 9: Auswahl von Fotos, Fehler beim Laden")
            pg.evaluate("RB.vorbereiten()")   # die Gruppen davor haben die Show gestartet
            pg.click("#rb-oDurch")
            pg.wait_for_selector(".d-bild")
            pg.locator(".d-bild").first.click()
            pg.click("#rb-dFertig")
            pg.wait_for_selector("#rb-oStart")
            pruef("(1 aus)" in text(pg, "#rb-oDurch"), "Foto ausgenommen: '(1 aus)'")
            aus = pg.evaluate("sessionStorage.getItem('sj.rb.aus')")
            pruef(bool(re.fullmatch(r'\["[^"]+:\d+"\]', aus or "")), f"nur teamId:position gemerkt ({aus})")
            n_foto = pg.evaluate("RB.kapitel().filter(k => k.art === 'fotos').reduce((n, k) => n + k.fotos, 0)")
            pruef(n_foto == D["fotos"] - 1, f"ausgenommenes Foto fehlt in den Fotokapiteln ({n_foto} von {D['fotos']})")
            pg.context.close()
            pg6 = neu(b, "rueckblick", w=1920, h=1080, init=WAKE)
            pg6.wait_for_selector("#rb-oStart", timeout=60000)
            pg6.click("#rb-oDurch"); pg6.wait_for_selector(".d-bild"); pg6.locator(".d-bild").nth(3).click(); pg6.click("#rb-dFertig")
            pg6.wait_for_selector("#rb-oStart")
            pg6.add_init_script("window.__behalten = true;")   # Neuladen wie auf dem Gerät: Speicher und Adresse bleiben
            pg6.reload()
            pg6.wait_for_selector("#rb-oStart", timeout=60000)
            pruef("(1 aus)" in text(pg6, "#rb-oDurch"), "nach dem Neuladen bleibt das Foto ausgenommen")
            pg6.context.close()
            pg7 = neu(b, "rueckblick", w=1920, h=1080,
                      init="window.__fotoFehler = (a, t) => (t.name === 'Eule' && a.p_position === 2 && a.p_full) || (t.name === 'Tiger' && a.p_position === 1);")
            pg7.wait_for_selector("#rb-oStart", timeout=60000)
            t7 = text(pg7, "#rueckblick")
            pruef("1 Foto nicht geladen" in t7 and pg7.locator("#rb-nochmal").count() == 1, "ein Foto scheitert: 'nicht geladen' mit 'Erneut versuchen'")
            args = pg7.evaluate("window.__FOTO_ARGS.filter(a => a.n === 'Eule' && a.p === 2).map(a => a.full)")
            pruef(args == [True, True, False], f"Eule 2: zweimal voll, dann Vorschau ({args})")
            pg7.evaluate("window.__fotoFehler = null")
            pg7.click("#rb-nochmal")
            pg7.wait_for_function(f"RB.D() && RB.D().fotos.length === {D['fotos']} && !!document.querySelector('#rb-oStart')", timeout=60000)
            pruef("nicht geladen" not in text(pg7, "#rueckblick") and pg7.evaluate("RB.D().fotos.length") == D["fotos"], "Erneut versuchen holt das fehlende Foto")
            pg7.context.close()

        if an(10):
            print("Gruppe 10: Bühne")
            kap = KAP
            dauer = {k["id"]: k["dur"] for k in kap}
            def zeit(i):
                if i.startswith("abspann"):
                    return 6000
                if i.startswith("weg") or i == "ziel":
                    return 9000
                return dauer[i] - 1000
            for w, h, scheme in ((1280, 720, "dark"), (1920, 1080, "light")):
                pgb = show(b, "rueckblick", w=w, h=h, scheme=scheme, init=WAKE)
                gesamt_striche, klein, raus = [], [], []
                SHOT = f"rueckblick-{w}-{scheme}-"
                pgb.screenshot(path=str(SHOTS / (SHOT + "vorbereiten.png")))
                r = pgb.evaluate(SCAN)
                gesamt_striche += r["striche"]; klein += [("vorbereiten", x) for x in r["klein"]]; raus += [("vorbereiten", x) for x in r["raus"]]
                alle_ids = [k["id"] for k in kap]
                knipp = {"vorspann", "weg2", "fotos2", "platz1", "alle", "abspann"}
                pgb.click("#rb-oStart"); pgb.wait_for_function("RB.zustand().phase === 'show'")
                for i in alle_ids:
                    pgb.evaluate(f"RB.zeige('{i}', {zeit(i)})")
                    pgb.wait_for_timeout(120)
                    r = pgb.evaluate(SCAN)
                    gesamt_striche += r["striche"]; klein += [(i, x) for x in r["klein"]]; raus += [(i, x) for x in r["raus"]]
                    if i in knipp:
                        pgb.screenshot(path=str(SHOTS / (SHOT + i + ".png")))
                # Fotos durchsehen und Tastenhilfe sind auch Bühne
                pgb.evaluate("RB.vorbereiten()"); pgb.click("#rb-oDurch"); pgb.wait_for_selector(".d-bild"); pgb.wait_for_timeout(150)
                r = pgb.evaluate(SCAN); gesamt_striche += r["striche"]; klein += [("durchsehen", x) for x in r["klein"]]; raus += [("durchsehen", x) for x in r["raus"]]
                pgb.screenshot(path=str(SHOTS / (SHOT + "durchsehen.png")))
                pgb.click("#rb-dFertig"); pgb.keyboard.press("h"); pgb.wait_for_timeout(150)
                r = pgb.evaluate(SCAN); gesamt_striche += r["striche"]; klein += [("hilfe", x) for x in r["klein"]]; raus += [("hilfe", x) for x in r["raus"]]
                pgb.keyboard.press("Escape")
                pruef(not gesamt_striche, f"{w}x{h} {scheme}: keine Gedankenstriche oder Mittelpunkte im Bild {gesamt_striche[:3]}")
                pruef(not klein, f"{w}x{h} {scheme}: kleinste Schrift mindestens 20 px {klein[:4]}")
                pruef(not raus, f"{w}x{h} {scheme}: nichts ragt aus der Bühne {raus[:4]}")
                pgb.context.close()

    # ------------------------------------------------------------------ 11
    if an(11):
        print("Gruppe 11: Probe")
        pg = neu(b, "rueckblick-probe", w=1920, h=1080)
        pg.wait_for_selector("#rb-oStart", timeout=60000)
        log = pg.evaluate("window.__RPC_LOG")
        pruef(not any(x.startswith("admin_") for x in log), f"Probe fragt keine Admin-Funktion ab ({log})")
        pruef(pg.evaluate("RB.D().teams.length") == 12 and "Rückblick, Probe" in text(pg, "#rueckblick"), "Probe: zwölf Beispielteams, als Probe gekennzeichnet")
        pg.click("#rb-oStart"); pg.wait_for_function("RB.zustand().phase === 'show'")
        pruef(any(k["id"] == "platz1" for k in pg.evaluate("RB.kapitel()")), "Probe: volle Kapitelliste")

    # ------------------------------------------------------------------ 12
    if an(12):
        print("Gruppe 12: Verlassen")
        pg = show(b, "rueckblick", w=1280, h=720)
        pg.evaluate("location.hash = '#/admin'")
        pg.wait_for_function("!document.querySelector('#rueckblick')", timeout=15000)
        pg.wait_for_selector(".tabs", timeout=15000)
        pruef(pg.evaluate("document.querySelector('#app').inert") is False and pg.evaluate("RueckblickShow.offen()") is False, "Verlassen: Show weg, App wieder bedienbar")
        pg.evaluate("location.hash = '#/rueckblick'")
        pg.wait_for_selector("#rb-oStart", timeout=60000)
        pruef(True, "Zurück in die Show: Vorbereiten lädt neu")

    pruef(not err, f"keine Skriptfehler {err[:2]}")
    pruef(not fremd, f"keine Anfrage an fremde Rechner {fremd[:2]}")
    sys.stdout.flush()
    print("FEHLER: " + str(len(fehler)) if fehler else "OK")
    sys.stdout.flush()
    abschluss.ende(fehler, vorher)
