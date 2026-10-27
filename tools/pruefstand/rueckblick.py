#!/usr/bin/env python3
"""
Rückblick-Show, Fassung v2 (Ablauf nach dem Nachtrag 17.10.2026 der Spezifikation 2026-10-15-rueckblick-show-design.md,
Vorlage mockups/rueckblick-v2/index.html, SPIEL.md §16) im Prüfstand, ohne Datenbank.

    python tools/pruefstand/rueckblick.py          alle
    python tools/pruefstand/rueckblick.py 3 5      nur diese Gruppen

Gruppen: 1 Texte der App (Datenschutz, Löschdatum, Knopf), 2 Sperren und PIN, 3 Laden und Vorbereiten (S21, S22, S23,
K4, K5, K14), 4 Kapitel (Ablauf, S17), 5 Aufbereiten (M6, M7, S14, S15, S16, S17, K11, K12, Startgruppen), 6 Tasten und
Schutz (M1, M2, M3, M8, S9, S11, Rand), 7 Schutz vor dem Neuzeichnen, 8 Läuft ohne Netz (Karte, Schriften, Version),
9 Auswahl von Fotos und Fehler beim Laden, 10 Bühne (Schrift, Rand, Striche, Bildschirmfotos 1920x1080 und 1280x720,
hell und dunkel), 11 Probe, 12 Verlassen (M5), 13 Bildrate (auch mit echter GPS-Dichte), 14 Awards gegen eine
unabhängige Rechnung in Python.
Spiel (app.html mit mock.js, Port 8864). Das Ergebnis steht VOR dem Schließen (Chrome 155 hängt sonst, siehe
abschluss.py). Im Vordergrund mit Timeout aufrufen, etwa `timeout 590 python tools/pruefstand/rueckblick.py`.
Bildschirmfotos nach tools/pruefstand/shots oder in den Ordner aus der Umgebungsvariablen RB_SHOTS.
"""
import bisect
import functools
import http.server
import json
import math
import os
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
SHOTS = pathlib.Path(os.environ.get("RB_SHOTS") or (HIER / "shots"))
SHOTS.mkdir(parents=True, exist_ok=True)
NUR = {int(x) for x in sys.argv[1:] if x.isdigit()}
an = lambda n: not NUR or n in NUR
fehler, err, fremd = [], [], []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text, flush=True)
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


def neu(b, szenario, w=390, h=844, scheme="light", init=None, abbrechen=(), tz=None):
    opt = {"viewport": {"width": w, "height": h}, "color_scheme": scheme}
    if tz:
        opt["timezone_id"] = tz
    c = b.new_context(**opt)
    pg = c.new_page()
    pg.set_default_timeout(30000)
    pg.on("pageerror", lambda e: err.append(f"{szenario}: {e}"))
    pg.on("dialog", lambda d: d.accept())   # beforeunload (M5): beim Neuladen in den Prüfungen bestätigen
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

# prüft Schriftgröße (auf dem Bildschirm), Rand und Striche aller sichtbaren Texte der Bühne. Ausgenommen von der
# Mindestgröße: die Fotorolle (läuft durch), die Walzen (Ziffern), die kleinen Karten der Spalten (Grafik) und die
# OSM-Nennung (Pflichthinweis, bewusst klein, Entscheidung Friedrich 16.10.)
SCAN = """() => {
  const st = document.querySelector('#rb-buehne'), r0 = st.getBoundingClientRect(), s = r0.width / 1920;
  const out = { klein: [], raus: [], text: st.innerText, striche: [] };
  const w = document.createTreeWalker(st, NodeFilter.SHOW_TEXT), seen = new Set(); let n;
  while ((n = w.nextNode())) {
    const t = n.nodeValue.trim(); if (!t) continue;
    if (/[\\u2013\\u2014\\u00b7]/.test(t)) out.striche.push(t.slice(0, 40));
    const e = n.parentElement; if (seen.has(e)) continue; seen.add(e);
    if (e.closest('.rolle') || e.closest('.walze') || e.closest('.sp-karte') || e.closest('.osm')) continue;
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

# Rohdaten für Aufbereiten (Gruppe 5): Zeiten in Minuten ab dem Spielstart 12:00 UTC (14:00 in Prag), Punkte als
# [Breite, Länge, Minute(, Genauigkeit)], Stationen in einer Linie nach Norden je 222 m
ROH = """(opt) => {
  const T0 = Date.UTC(2026, 9, 17, 12, 0, 0), M = 60000, iso = t => t == null ? null : new Date(t).toISOString();
  const n = opt.stationen || 3;
  const sts = Array.from({ length: n }, (_, k) => ({ id: 's' + (k + 1), position: k + 1, name: 'S' + (k + 1), lat: 50.1 + (k + 1) * 0.002, lng: 14.4235, radiusM: 50 }));
  const teams = opt.teams.map((t, i) => ({ id: 't' + i, name: t.name, members: t.members || ['A B', 'C D'], place: t.place ?? null,
    finishedAt: t.fertig == null ? null : iso(T0 + t.fertig * M), startedAt: t.start == null ? undefined : iso(T0 + t.start * M), startGroup: t.gruppe }));
  const tracks = opt.teams.map((t, i) => ({ id: 't' + i, name: t.name,
    points: (t.points || []).map(p => [p[0], p[1], Math.round(T0 + p[2] * M)].concat(p.length > 3 ? [p[3]] : [])),
    stations: (t.ein || []).map((e, k) => ({ position: k + 1, checkedInAt: iso(T0 + e * M), solvedAt: t.ok && t.ok[k] != null ? iso(T0 + t.ok[k] * M) : null })) }));
  return { state: { status: 'finished', startedAt: iso(T0), finishedAt: iso(T0 + opt.ende * M), prizeCount: opt.koffer ?? 3,
      start: { name: 'Start', lat: 50.1, lng: 14.4235 }, stations: sts, teams },
    tracks: { finishedAt: iso(T0 + opt.ende * M), teams: tracks }, photos: [], T0 };
}"""


def gehen(lat0, lat1, m0, m1, schritt=0.25, acc=None):
    """Punkte auf der Linie nach Norden von lat0 nach lat1, von Minute m0 bis m1, alle schritt Minuten."""
    n = max(1, round((m1 - m0) / schritt))
    out = []
    for i in range(n + 1):
        f = i / n
        p = [round(lat0 + (lat1 - lat0) * f, 6), 14.4235, m0 + (m1 - m0) * f]
        if acc is not None:
            p.append(acc)
        out.append(p)
    return out


def stehen(lat, m0, m1, schritt=0.25, zittern=0.000015):
    out, i = [], 0
    m = m0
    while m <= m1:
        out.append([round(lat + (zittern if i % 2 else -zittern), 6), 14.4235, m])
        m += schritt
        i += 1
    return out


S = [50.1, 50.102, 50.104, 50.106]   # Start, Station 1 bis 3


def team_voll(name, tempo=1.0, fertig=None, start=0):
    """Ein Team läuft die drei Stationen der ROH-Daten ab (je 10 min gehen mal tempo, 5 min rätseln)."""
    pts, ein, ok, m = [], [], [], start
    for k in range(3):
        g = 10 * tempo
        pts += gehen(S[k], S[k + 1], m, m + g)
        m += g
        ein.append(m)
        pts += stehen(S[k + 1], m, m + 5)
        m += 5
        ok.append(m)
    t = {"name": name, "points": pts, "ein": ein, "ok": ok, "fertig": fertig if fertig is not None else m + 3}
    if start:
        t["start"] = start
    return t


# ------------------------------------------------------------------ unabhängige Rechnung der Awards (Gruppe 14)
def kennzahlen(t, d):
    z = {}
    r = [x["ok"] - x["ein"] for x in t["sts"] if x["ein"] and x["ok"] and x["ok"] > x["ein"]]
    if r:
        z["raetsel"] = sum(r) / len(r)
    reihe = []
    for s in d["stationen"]:
        if not s["xy"]:
            break
        x = next((y for y in t["sts"] if y["position"] == s["position"]), None)
        if not x or not x["ein"] or not x["ok"]:
            break
        reihe.append((s, x))
    if not reihe or t["ohneGps"]:
        return z
    pts = t["pts"]
    ts = [p["t"] for p in pts]
    d2 = lambda p, xy: math.hypot(p["x"] - xy[0], p["y"] - xy[1])
    kurz = gelaufen = tm = tz = 0.0
    vor_xy, vor_t = d["start"], d["t0"]
    for s, x in reihe:
        i0 = bisect.bisect_left(ts, vor_t)
        i1 = bisect.bisect_right(ts, x["ein"]) - 1
        ps = [] if i0 >= len(pts) else pts[i0:i1 + 1]
        nach = pts[i1 + 1] if i1 + 1 < len(pts) else None
        if len(ps) < 3 or any(p["g"] for p in ps[1:]) or (nach and nach["g"]) or d2(ps[0], vor_xy) >= 100 or d2(ps[-1], s["xy"]) >= 100:
            return z
        j1 = next((j for j, p in enumerate(ps) if d2(p, s["xy"]) < 60), -1)
        j0 = -1
        if j1 >= 0:
            for j in range(j1, -1, -1):
                if d2(ps[j], vor_xy) < 60:
                    j0 = j
                    break
        if j0 < 0 or j1 - j0 < 2:
            return z
        geh = ps[j0:j1 + 1]
        a = geh[0]
        m = math.hypot(vor_xy[0] - a["x"], vor_xy[1] - a["y"])
        for q in geh:
            dd = math.hypot(a["x"] - q["x"], a["y"] - q["y"])
            if dd > 15:
                m += dd
                a = q
        e = geh[-1]
        innen = m - math.hypot(vor_xy[0] - geh[0]["x"], vor_xy[1] - geh[0]["y"]) + math.hypot(a["x"] - e["x"], a["y"] - e["y"])
        m += math.hypot(a["x"] - e["x"], a["y"] - e["y"]) + d2(e, s["xy"])
        dauer = e["t"] - geh[0]["t"]
        gelaufen += m
        kurz += math.hypot(vor_xy[0] - s["xy"][0], vor_xy[1] - s["xy"][1])
        if dauer >= 60000 and innen >= 100 and all(p["acc"] is None or p["acc"] <= 25 for p in geh):
            tm += innen
            tz += dauer
        vor_xy, vor_t = s["xy"], x["ok"]
    z.update(kurz=kurz, gelaufen=gelaufen, umweg=gelaufen - kurz, faktor=gelaufen / kurz if kurz else math.inf)
    if tz > 0:
        z["tempo"] = tm / 1000 / (tz / 3600000)
    return z


AWARDS_PY = [("navi", "faktor", 1, None), ("sightseeing", "umweg", -1, lambda z: z["umweg"] > 0), ("raetselfuechse", "raetsel", 1, None),
             ("philosophen", "raetsel", -1, None), ("sprinter", "tempo", -1, None), ("flaneure", "tempo", 1, None)]


def awards_py(d):
    alle = [(t, kennzahlen(t, d)) for t in d["teams"]]
    frei = [(t, z) for t, z in alle if not (t["place"] and t["place"] <= d["prizeCount"])]
    vergeben, liste = set(), []
    for aid, feld, richtung, gilt in AWARDS_PY:
        mit = [(t, z) for t, z in frei if feld in z and math.isfinite(z[feld]) and (not gilt or gilt(z))]
        if len(mit) < 3:
            continue
        mit.sort(key=lambda x: x[1][feld] * richtung)
        sieger = next((x for x in mit if x[0]["id"] not in vergeben), None)
        if not sieger:
            continue
        vergeben.add(sieger[0]["id"])
        liste.append({"id": aid, "team": sieger[0]["name"], "wert": sieger[1][feld]})
    return liste


FPS = """(dauer) => new Promise(fertig => { let n = 0, schlimm = 0; const t0 = performance.now(); let letzt = t0;
  const f = t => { n++; schlimm = Math.max(schlimm, t - letzt); letzt = t;
    if (t - t0 < dauer) requestAnimationFrame(f); else fertig({ fps: n / ((t - t0) / 1000), schlimm }); };
  requestAnimationFrame(f); })"""


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
        sw = (REPO / "sw.js").read_text(encoding="utf-8")
        pruef("rueckblick" not in sw, "Rückblick-Dateien bleiben aus dem Service Worker")
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
        pg.context.close()

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
        # Tippen der PIN darf keine Show-Taste auslösen (n, k, f, t, h, b, p, r ...)
        pg = neu(b, "rueckblick-ohne-pin", w=1280, h=720)
        pg.wait_for_selector("#rb-pin", timeout=30000)
        pg.type("#rb-pin", "kfnthbpr")
        pruef(pg.input_value("#rb-pin") == "kfnthbpr" and pg.locator("#rb-hilfeBox").count() == 0, "PIN-Feld nimmt Buchstaben an, Tasten der Show schlafen")
        pg.context.close()

    # ------------------------------------------------------------------ 3 .. 10 am Hauptszenario
    if any(an(n) for n in (3, 4, 5, 6, 7, 8, 9, 10, 14)):
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
            pruef("bis zum Abspann etwa" in vt and "Rückblick starten" in vt, "Vorbereiten: Dauer bis zum Abspann und Startknopf")
            spr = pg.evaluate("[...document.querySelectorAll('#rueckblick [data-sprung]')].map(b => b.textContent.trim())")
            pruef(all(x in spr for x in ("Fun Facts", "Zeitraffer", "Awards", "Rangliste", "Drei Spalten", "Platz 3", "Platz 2", "Platz 1", "Siegerbild", "Abspann"))
                  and "Die Gruppen" not in spr and "Vorspann" not in spr, f"Direktsprünge zu allen Kapiteln ({spr})")
            pruef("Vor und nach jedem Koffer-Platz anhalten" in text(pg, "label:has(#rb-oHalt)"), "Schalter: vor und nach jedem Koffer-Platz anhalten")
            pruef(pg.locator("#rb-oRand").count() == 1 and "Rand für Fernseher" in text(pg, "label:has(#rb-oRand)"), "Schalter: Rand für Fernseher")
            pruef(pg.locator("#rb-oRuhig").count() == 1 and "Bewegung reduzieren" in text(pg, "label:has(#rb-oRuhig)")
                  and not pg.is_checked("#rb-oRuhig"), "Schalter: Bewegung reduzieren, Vorgabe aus")
            pruef(pg.evaluate("window.__wl") >= 1, "Wake Lock beim Öffnen angefordert")
            pg.evaluate("window.__sperren.forEach(s => s.released = true)")
            pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            pg.wait_for_timeout(300)
            pruef(pg.evaluate("window.__wl") >= 2, "Wake Lock nach visibilitychange neu angefordert")
            speicher = pg.evaluate("JSON.stringify([localStorage, sessionStorage].map(s => Object.keys(s).map(k => s.getItem(k))))")
            pruef("/9j/" not in speicher and len(speicher) < 4000, "keine Bilddaten in localStorage oder sessionStorage")
            pruef(pg.evaluate("document.querySelector('#app').inert") is True, "App dahinter ist nicht bedienbar (inert)")
            # K14: Uhrzeiten in Prager Zeit, auch wenn der Laptop anders eingestellt ist
            pgz = show(b, "rueckblick", tz="America/New_York")
            prag = pgz.evaluate("new Date(RB.D().tEndUhr).toLocaleTimeString('de-DE', { timeZone: 'Europe/Prague', hour: '2-digit', minute: '2-digit' })")
            ny = pgz.evaluate("new Date(RB.D().tEndUhr).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })")
            pruef(f"Spiel beendet um {prag} Uhr" in text(pgz, "#rueckblick") and prag != ny, f"Uhrzeit in Prager Zeit ({prag}, Laptop {ny})")
            pgz.context.close()
            # K5: ohne Netz ein Text für die Spielleitung, nicht für die Teams
            pgn = neu(b, "rueckblick", w=1920, h=1080, init="window.__netz = 'weg';")
            pgn.wait_for_selector(".rb-fehler", timeout=40000)
            tn = text(pgn, "#rueckblick")
            pruef("Keine Verbindung zum Server. Prüfe das WLAN und versuche es erneut." in tn and "Wartet kurz" not in tn, f"Verbindungsfehler: eigener Text ({tn.strip()[:90]})")
            pruef(pgn.locator("#rb-nochmal").count() == 1, "Verbindungsfehler: Erneut versuchen")
            pgn.context.close()
            # S21, S23, K4: Fotos hängen; die Ladezeile bricht nicht um, nach der Geduld kommt der Ausweg, danach steht, welche fehlen
            pgh = neu(b, "rueckblick", w=1920, h=1080, init="window.__haengt = ['admin_photo']; window.__rbGeduld = 1500;")
            pgh.wait_for_selector("#rb-ladezeile", timeout=40000)
            pgh.wait_for_function("/Fotos \\d+ von \\d+/.test(document.querySelector('#rb-ladezeile').textContent)", timeout=20000)
            lz = pgh.evaluate("(() => { const z = document.querySelector('#rb-ladezeile'); return { li: !!z.closest('li'), h: z.getBoundingClientRect().height, fs: parseFloat(getComputedStyle(z).fontSize), t: z.textContent }; })()")
            pruef(not lz["li"] and lz["h"] < lz["fs"] * 2, f"Ladezeile in einer Zeile, nicht im Listenraster ({lz})")
            pruef(pgh.locator("#rb-ohne:visible").count() == 0, "Ausweg erst nach der Geduld")
            pgh.wait_for_selector("#rb-ohne:visible", timeout=10000)
            pruef("Ohne die restlichen Fotos weiter" in text(pgh, "#rb-ohne"), "nach der Geduld: 'Ohne die restlichen Fotos weiter'")
            pgh.click("#rb-ohne")
            pgh.wait_for_selector("#rb-oStart", timeout=20000)
            th = text(pgh, "#rueckblick")
            pruef(re.search(r"\d+ Fotos nicht geladen", th) is not None and "Station" in th, f"Vorbereiten nennt die fehlenden Fotos ({th[th.find('nicht geladen') - 6:th.find('nicht geladen') + 80].strip()!r})")
            pgh.context.close()
            # S22: Rastern scheitert, die Spielleitung erfährt es
            pgr = show(b, "rueckblick", init="HTMLCanvasElement.prototype.toBlob = function (cb) { setTimeout(() => cb(null)); };")
            tr = text(pgr, "#rueckblick")
            pruef("Karte nicht vorbereitet" in tr and pgr.locator("#rb-raster").count() == 1, "Karte nicht gerastert: Warnzeile mit Erneut versuchen")
            pgr.context.close()

        if an(4):
            print("Gruppe 4: Kapitel")
            ids = [k["id"] for k in KAP]
            print("      " + " ".join(ids))
            pruef(ids[:4] == ["vorspann", "fakten", "zeitraffer", "rangliste"], "Splash, Fun Facts, Zeitraffer, Rangliste; eine Startgruppe: ohne 'Die Gruppen'")
            aw = [i for i in ids if i.startswith("award")]
            pruef(bool(aw) and ids.index("awards") == 4 and 1 <= len(aw) - 1 <= 6, f"Bonusrunde nach Teil 1 der Rangliste: Auftakt und {len(aw) - 1} Awards")
            hinten = ids[ids.index(aw[-1]) + 1:] if aw else []
            pruef(hinten == ["rangliste2", "spalten", "platz3", "platz2", "platz1", "sieger", "abspann"], f"Rangliste Teil 2, Drei Spalten, Platz 3, 2, 1, Siegerbild, Abspann ({hinten})")
            pruef(not any(k["art"] == "fotos" for k in KAP), "keine Fotokapitel je Station")
            kk = {k["id"]: k for k in KAP}
            pruef(kk["abspann"]["endlos"] and kk["abspann"]["fotos"] == D["fotos"], "Abspann endlos, mit allen Fotos")
            pruef(kk["vorspann"]["halte"] == [3000] and kk["fakten"]["halte"] == [3600], "Splash hält als Startbild, Fun Facts halten auf den Brathähnchen")
            pruef(len(kk["platz3"]["halte"]) == 2 and len(kk["platz1"]["halte"]) == 2 and kk["platz1"]["sperren"], "Platz 3 und 1: Halt davor und danach, Sperre beim Aufdecken")
            pruef(kk["zeitraffer"]["dur"] == 70000, "ein durchgehender Zeitraffer (70 s)")
            pruef(all(not k["endlos"] for k in KAP[:-1]), "nur der Abspann ist endlos, alle anderen halten am Ende")
            gesamt = pg.evaluate("RB.gesamt()") / 1000
            pruef(120 <= gesamt <= 330, f"bis zum Abspann {gesamt:.0f} s (2 bis 5,5 min, ohne Halte)")
            pg2 = show(b, "rueckblick-ohne-fotos")
            k2 = pg2.evaluate("RB.kapitel()")
            pruef(k2[-1]["id"] == "abspann" and k2[-1]["name"] == "Alle Routen" and k2[-1]["fotos"] == 0 and pg2.locator("#rb-oFotos").count() == 0
                  and "Gruppenfoto" not in text(pg2, "#rueckblick"), "ohne Fotos: Abspann mit allen Routen, keine Fotozeile")
            pg2.context.close()
            pg3 = show(b, "rueckblick-niemand")
            k3 = [k["id"] for k in pg3.evaluate("RB.kapitel()")]
            t3 = text(pg3, "#rueckblick")
            pruef(not any(i in k3 for i in ("rangliste", "spalten", "platz1", "sieger")) and k3[-1] == "abspann" and "zeitraffer" in k3,
                  f"niemand im Ziel: ohne Rangliste und Finale ({' '.join(k3)})")
            pruef("Kein Team im Ziel" in t3 and pg3.locator("#rb-oHalt").count() == 0, "niemand im Ziel: Vorwarnung, kein Halt-Schalter")
            pruef("0 von 12 Teams im Ziel" in t3, "niemand im Ziel: 0 von 12")
            pg3.context.close()

        if an(5):
            print("Gruppe 5: Aufbereiten")
            roh = lambda **o: pg.evaluate(f"({ROH})({json.dumps(o)})")
            auf = lambda r, expr: pg.evaluate(f"([roh]) => {{ const d = RB.test.aufbereiten(roh); return ({expr}); }}", [r])
            # S15: Ausreißer aus einem bis drei Punkten fallen weg, eine Tram- oder Taxifahrt bleibt ganz
            r = pg.evaluate("""() => {
              const p = (x, t) => ({ x, y: 0, t: t * 15000 });
              const spitze = [p(0, 0), p(10, 1), p(20, 2), p(3000, 3), p(40, 4), p(50, 5), p(60, 6)];
              const tram = Array.from({ length: 30 }, (_, i) => p(i * 90, i));
              const zwei = [p(0, 0), p(10, 1), p(3000, 2), p(3010, 3), p(20, 4), p(30, 5)];
              const drei = [p(0, 0), p(10, 1), p(3000, 2), p(3010, 3), p(3020, 4), p(20, 5), p(30, 6)];
              const vier = [p(0, 0), p(10, 1), p(3000, 2), p(3010, 3), p(3020, 4), p(3030, 5), p(20, 6), p(30, 7)];
              const f = a => RB.test.ohneAusreisser(a).length;
              return { spitze: f(spitze), tram: f(tram), zwei: f(zwei), drei: f(drei), vier: f(vier) }; }""")
            pruef(r["spitze"] == 6, f"einzelner Sprung verworfen ({r['spitze']} von 7 Punkten)")
            pruef(r["zwei"] == 4 and r["drei"] == 4, f"Ausreißer aus zwei und drei Punkten verworfen ({r['zwei']} von 6, {r['drei']} von 7)")
            pruef(r["vier"] == 8, f"vier Punkte woanders sind kein Ausreißer ({r['vier']} von 8)")
            pruef(r["tram"] == 30, f"Tramfahrt kaskadiert nicht ({r['tram']} von 30 Punkten bleiben)")
            # S14: im Stand fallen die Punkte weg, beim Gehen nur die engen; der Kopf steht trotzdem bis zum Aufbruch
            pts = stehen(50.1, 0, 10, schritt=1 / 60) + gehen(50.1, 50.1027, 10, 14, schritt=1 / 60)
            r = auf(roh(teams=[{"name": "A", "points": pts}], ende=60),
                    "{ n: d.teams[0].pts.length, k9: RB.test.kopf(d.teams[0], roh.T0 + 9.5 * 60000), k12: RB.test.kopf(d.teams[0], roh.T0 + 12 * 60000), start: d.start.xy }")
            pruef(r["n"] < 60, f"Ausdünnen: {len(pts)} Punkte werden {r['n']}")
            pruef(math.hypot(r["k9"][0] - r["start"][0], r["k9"][1] - r["start"][1]) < 6, f"Kopf steht im Stand still bis zum Aufbruch ({r['k9']})")
            pruef(abs((r["start"][1] - r["k12"][1]) - 150) < 15, f"beim Gehen bleibt der Weg in der Zeit (nach 2 von 4 min {r['start'][1] - r['k12'][1]:.0f} von 300 m)")
            # M6: nach dem Koffer-Code (plus 2 min) ist Schluss, auch für die Kilometer
            t6 = team_voll("A", fertig=50)
            t6["points"] += gehen(S[3], S[3] + 0.009, 52.5, 100)
            r = auf(roh(teams=[t6], ende=120), "{ max: Math.max(...d.teams[0].pts.map(p => p.t)), weg: d.teams[0].weg, T0: roh.T0 }")
            pruef(r["max"] <= r["T0"] + 52 * 60000, f"Weg endet 2 min nach dem Koffer-Code ({(r['max'] - r['T0']) / 60000:.1f} min)")
            pruef(600 <= r["weg"] <= 720, f"Kilometer ohne den Heimweg ({r['weg']:.0f} m, Strecke 667 m)")
            # M7: GPS bricht ab; Check-ins kommen dazu, gestrichelt, und Vorbereiten nennt es
            t7 = team_voll("Tiger", fertig=50)
            t7["points"] = [p for p in t7["points"] if p[2] <= 25]
            r = auf(roh(teams=[t7], ende=120), """{ syn: d.teams[0].pts.filter(p => p.syn).map(p => [Math.round((p.t - roh.T0) / 60000), p.g]),
              k: RB.test.kopf(d.teams[0], roh.T0 + 42 * 60000), s3: d.stationen[2].xy, hinweis: d.teams[0].gpsHinweis }""")
            pruef([s[0] for s in r["syn"]] == [30, 40, 45] and all(s[1] for s in r["syn"]), f"Abbruch: Lösung Station 2, Check-in und Lösung Station 3 eingemischt, gestrichelt ({r['syn']})")
            pruef(math.hypot(r["k"][0] - r["s3"][0], r["k"][1] - r["s3"][1]) < 5, "Abbruch: Kopf steht nach dem Check-in an Station 3")
            pruef(r["hinweis"] == "Tiger: GPS nur bis 14:25, danach aus den Check-ins", f"Abbruch: Hinweis für Vorbereiten ({r['hinweis']})")
            t7 = team_voll("Eule", fertig=50)
            t7["points"] = [p for p in t7["points"] if p[2] >= 15]
            r = auf(roh(teams=[t7], ende=120), """{ syn: d.teams[0].pts.filter(p => p.syn).map(p => Math.round((p.t - roh.T0) / 60000)),
              k: RB.test.kopf(d.teams[0], roh.T0 + 60000), start: d.start.xy, hinweis: d.teams[0].gpsHinweis }""")
            pruef(r["syn"] == [0, 10], f"Spätstart: Startpunkt bei 0:00 und Check-in Station 1 eingemischt ({r['syn']})")
            pruef(math.hypot(r["k"][0] - r["start"][0], r["k"][1] - r["start"][1]) < 60, "Spätstart: Kopf beginnt am Start, nicht an Station 1")
            pruef(r["hinweis"] == "Eule: GPS erst ab 14:15, davor aus den Check-ins", f"Spätstart: Hinweis für Vorbereiten ({r['hinweis']})")
            r = auf(roh(teams=[team_voll("A", fertig=50)], ende=120), "{ syn: d.teams[0].pts.filter(p => p.syn).length, hinweis: d.teams[0].gpsHinweis }")
            pruef(r["syn"] == 0 and r["hinweis"] is None, "volles GPS: nichts eingemischt, kein Hinweis")
            # S16 und S17: Spielende vor der letzten Station, niemand im Ziel
            ts = [team_voll("A"), team_voll("B", tempo=1.2)]
            for t in ts:
                t.pop("fertig")
                t["ein"], t["ok"] = t["ein"][:2], t["ok"][:2]
                t["points"] = [p for p in t["points"] if p[2] <= 40]
            r = pg.evaluate(f"""([roh]) => {{ const d = RB.test.aufbereiten(roh), k = RB.test.kapitel(d, {{ fotos: true, anhalten: true, aus: new Set() }});
                return {{ ids: k.map(x => x.id), zr: k.find(x => x.id === 'zeitraffer'), tEnd: d.tEnd, plaetze: d.teams.map(t => t.place) }}; }}""", [roh(teams=ts, ende=40)])
            pruef(r["zr"] and r["zr"]["bis"] == r["tEnd"] and not any(i in r["ids"] for i in ("rangliste", "spalten", "platz1", "sieger")) and r["ids"][-1] == "abspann",
                  f"Spielende vor der letzten Station: Zeitraffer bis zum Spielende, kein Finale ({' '.join(r['ids'])})")
            pruef(r["plaetze"] == [None, None], "niemand im Ziel: kein Platz")
            # Startgruppen: Wertung nach Gesamtzeit ab dem eigenen Start, Zeiten auf 0:00 geschoben, Kapitel 'Die Gruppen'
            ts = [team_voll("A", fertig=50), team_voll("B", start=15, fertig=60), team_voll("C", start=30, fertig=81)]
            r = pg.evaluate(f"""([roh]) => {{ const d = RB.test.aufbereiten(roh), k = RB.test.kapitel(d, {{ fotos: true, anhalten: true, aus: new Set() }});
                return {{ ids: k.map(x => x.id), t: d.teams.map(t => ({{ n: t.name, g: t.gruppe, p: t.place, netto: t.netto / 60000, erst: (t.pts[0].t - roh.T0) / 60000 }})) }}; }}""", [roh(teams=ts, ende=120)])
            tt = {x["n"]: x for x in r["t"]}
            pruef([tt[n]["g"] for n in "ABC"] == [0, 1, 2] and "gruppen" in r["ids"] and r["ids"].index("gruppen") == 2, f"drei Startgruppen: Kapitel 'Die Gruppen' nach den Fun Facts ({r['ids'][:4]})")
            pruef(tt["B"]["p"] == 1 and tt["A"]["p"] == 2 and tt["C"]["p"] == 3 and abs(tt["B"]["netto"] - 45) < .01, f"Wertung nach Gesamtzeit ab dem eigenen Start ({r['t']})")
            pruef(all(abs(tt[n]["erst"]) < .5 for n in "ABC"), "alle Gruppen starten im Zeitraffer bei 0:00")
            # K12: Gleichstand in derselben Sekunde wird benannt
            ts = [team_voll("A", fertig=50 + 0.1 / 60), team_voll("B", fertig=50 + 0.4 / 60), team_voll("C", fertig=55)]
            r = auf(roh(teams=ts, ende=120), "d.teams.map(t => [t.name, t.place, t.gleich || []])")
            g = {x[0]: x for x in r}
            pruef(g["A"][2] == ["0,3 s vor Platz 2"] and g["B"][2] == ["0,3 s hinter Platz 1"] and g["C"][2] == [], f"Gleichstand: '0,3 s vor Platz 2' ({r})")
            # K11: mehr als zwölf Teams
            pruef(pg.evaluate("JSON.stringify([RB.test.ring(12), RB.test.ring(16)])") == json.dumps([{"plaetze": 12, "radius": 116}, {"plaetze": 16, "radius": 150}]).replace(" ", ""),
                  "Ring: zwölf Plätze, ab dem 13. Team sechzehn auf größerem Radius")
            # Team ganz ohne Check-in: steht am Start
            d = pg.evaluate("""() => { const d = RB.D(), t = d.teams.find(x => x.name === 'Delfin'); return { sts: t.sts.length, gps: t.ohneGps, pts: t.pts.length, nah: Math.hypot(t.pts[0].x - d.start.xy[0], t.pts[0].y - d.start.xy[1]) }; }""")
            pruef(d["sts"] == 0 and d["gps"] and d["pts"] == 1 and d["nah"] < 1, f"Delfin ohne Check-in steht am Start ({d})")

        if an(6):
            print("Gruppe 6: Tasten und Schutz")
            z = lambda: pg.evaluate("RB.zustand()")
            pg.evaluate("RB.vorbereiten()")
            pg.click("#rb-oStart")
            pg.wait_for_function("RB.zustand().phase === 'show'")
            pruef(z()["id"] == "vorspann" and z()["spielt"], "Start: Splash läuft")
            pg.wait_for_function("RB.zustand().haelt === true", timeout=8000)
            pruef(z()["id"] == "vorspann" and "wartet auf Weiter" in z()["leiste"], "Splash hält als Startbild")
            pg.keyboard.press("Space")
            pg.wait_for_function("RB.zustand().id === 'fakten'", timeout=5000)
            pruef(True, "Leertaste am Splash: weiter zu den Fun Facts")
            pg.wait_for_timeout(700)
            pg.keyboard.press("Space"); pruef(not z()["spielt"], "Leertaste: Pause")
            pg.wait_for_timeout(300)
            pg.keyboard.press("ArrowRight")
            pruef(z()["id"] == "fakten" and z()["spielt"] and z()["haelt"] and z()["lokal"] == 3600, "M3: Weiter aus der Pause läuft weiter; Fun Facts: springt auf die Brathähnchen (Halt)")
            bier = "+getComputedStyle(document.querySelectorAll('.ff-lagen')[2].children[1]).opacity"
            pruef(pg.evaluate(bier) < .1, "Fun Facts: im Halt stehen die Brathähnchen")
            pg.wait_for_timeout(700)
            pg.keyboard.press("ArrowRight")
            pg.wait_for_timeout(900)
            pruef(pg.evaluate(bier) > .9 and z()["id"] == "fakten", "Fun Facts: Weiter schaltet auf Liter Bier um")
            pg.keyboard.press("ArrowRight")
            pruef(z()["id"] == "zeitraffer" and z()["spielt"], "Fun Facts, Weiter: Zeitraffer")
            pg.keyboard.press("ArrowRight")
            pruef(z()["id"] == "zeitraffer", "M2: Weiter in den ersten 600 ms nach einem Wechsel wirkt nicht")
            pg.wait_for_timeout(700)
            i0 = z()["i"]
            pg.keyboard.down("ArrowRight"); pg.keyboard.down("ArrowRight"); pg.keyboard.down("ArrowRight"); pg.keyboard.up("ArrowRight")
            pruef(z()["i"] == i0 + 1, f"M2: gehaltene Taste rast nicht durch die Kapitel ({i0} nach {z()['i']})")
            pg.wait_for_timeout(700)
            pg.keyboard.press("ArrowLeft"); pruef(z()["i"] == i0, "Pfeil links in den ersten 1,5 s: Kapitel davor")
            pg.keyboard.press("End")
            pruef(z()["id"] == "rangliste", "Ende: Notbremse zur Rangliste")
            pg.wait_for_timeout(700)
            pg.keyboard.press("ArrowRight")
            pruef(z()["id"] == "rangliste" and z()["haelt"] and z()["hNr"] == 0, "Rangliste Schritt 1: Weiter springt auf den ersten Halt (alles rattert, nichts aufgedeckt)")
            auf = pg.evaluate("[...document.querySelectorAll('.rl-zeile .n')].filter(n => +getComputedStyle(n).opacity > .5).length")
            alle_w = "[...document.querySelectorAll('.rl-zeile .band')].map(b => b.style.transform).join()"
            w1 = pg.evaluate(alle_w); pg.wait_for_timeout(500); w2 = pg.evaluate(alle_w)
            pruef(w1 != w2 and auf == 0, "Rangliste, Halt 1: die Walzen drehen weiter, kein Platz ist gesetzt")
            pg.wait_for_timeout(700)
            pg.keyboard.press("ArrowRight")
            pg.wait_for_function("RB.zustand().id === 'rangliste' && RB.zustand().leiste.includes('wartet auf Weiter') && !RB.zustand().haelt", timeout=15000)
            auf2 = pg.evaluate("[...document.querySelectorAll('.rl-zeile .n')].filter(n => +getComputedStyle(n).opacity > .5).length")
            dif = pg.evaluate("[...document.querySelectorAll('.rl-zeile .dif')].map(d => d.textContent.trim())")
            pruef(auf == 0 and auf2 == 9, f"Rangliste Schritt 2: Plätze ab 4 aufgedeckt ({auf} vorher, {auf2} danach), Ende von Teil 1 hält")
            pruef(dif[0] == "" and all(re.fullmatch(r"\+\d+:\d\d(:\d\d)?", x) for x in dif[1:7]), f"Abstand zum Ersten neben der Zeit ({dif[:4]})")
            oben_w = "[...document.querySelectorAll('.rl-zeile')].slice(0, 3).map(r => [...r.querySelectorAll('.band')].map(b => b.style.transform).join())"
            w1 = pg.evaluate(oben_w); pg.wait_for_timeout(500); w2 = pg.evaluate(oben_w)
            pruef(all(x != y for x, y in zip(w1, w2)), "Rangliste, Ende von Teil 1: die Walzen der ersten drei drehen weiter")
            pg.keyboard.press("ArrowRight")
            pruef(z()["id"] == "awards", "nach Teil 1 der Rangliste: die Awards (vor der Siegerehrung)")
            pg.evaluate("RB.starten('rangliste2', 0)")
            pg.wait_for_function("RB.zustand().haelt === true", timeout=5000)
            stand = pg.evaluate("[...document.querySelectorAll('.rl-zeile')].map(r => [+getComputedStyle(r.querySelector('.n')).opacity, +getComputedStyle(r.querySelector('.dif')).opacity])")
            pruef(sum(1 for x in stand if x[0] > .5) == 9 and all(x[1] < .1 for x in stand[:3]), "Rangliste Teil 2: alle Plätze ab 4 stehen, die ersten drei rattern (Halt)")
            w1 = pg.evaluate("[...document.querySelectorAll('.rl-zeile')].slice(0, 3).map(r => [...r.querySelectorAll('.band')].map(b => b.style.transform).join())"); pg.wait_for_timeout(500); w2 = pg.evaluate("[...document.querySelectorAll('.rl-zeile')].slice(0, 3).map(r => [...r.querySelectorAll('.band')].map(b => b.style.transform).join())")
            pruef(all(x != y for x, y in zip(w1, w2)), "Rangliste, Halt 2: die Walzen der ersten drei drehen weiter")
            pg.wait_for_timeout(700)
            pg.keyboard.press("ArrowRight")
            pg.wait_for_function("RB.zustand().id === 'rangliste2' && RB.zustand().leiste.includes('wartet auf Weiter') && !RB.zustand().haelt", timeout=15000)
            pruef(pg.evaluate("[...document.querySelectorAll('.rl-zeile .n')].filter(n => +getComputedStyle(n).opacity > .5).length") == 9,
                  "Rangliste Schritt 3: die Zeiten der ersten drei rasten ein, die Teams bleiben verdeckt, Ende hält")
            pg.keyboard.press("ArrowRight")
            pruef(z()["id"] == "spalten", "Weiter am Ende der Rangliste: Drei Spalten")
            pg.wait_for_timeout(700)
            pg.keyboard.press("ArrowRight")
            pruef(z()["id"] == "platz3", "Drei Spalten, Weiter: Platz 3")
            pg.wait_for_timeout(650)
            pg.keyboard.press("ArrowRight")
            pruef(z()["id"] == "platz3" and z()["haelt"] and z()["hNr"] == 0, "M2: zu frühes Weiter in Platz 3 springt auf den Halt davor, nicht über den Platz")
            pg.wait_for_timeout(700)
            pg.keyboard.press("ArrowRight")
            pruef(not z()["haelt"] and z()["spielt"], "Weiter am Halt deckt auf")
            pg.wait_for_timeout(200)
            l0 = z()
            pg.keyboard.press("ArrowRight"); pg.keyboard.press("ArrowLeft")
            l1 = z()
            pruef(l1["id"] == "platz3" and l1["lokal"] >= l0["lokal"], "M2: während des Aufdeckens wirken Weiter und Zurück nicht")
            pg.wait_for_function("RB.zustand().haelt === true", timeout=10000)
            pruef(z()["id"] == "platz3" and "aufgedeckt, wartet auf Weiter" in z()["leiste"], f"M1: nach dem Aufdecken hält die Show ({z()['leiste']})")
            lok = z()["lokal"]; pg.wait_for_timeout(800)
            pruef(abs(z()["lokal"] - lok) < 5 and z()["id"] == "platz3", "M1: das fertige Bild steht, bis Weiter kommt")
            pg.keyboard.press("ArrowRight")
            pg.wait_for_function("RB.zustand().id === 'platz2'", timeout=3000)
            pruef(z()["id"] == "platz2", "Weiter nach der Übergabe: Platz 2")
            pg.wait_for_timeout(300)
            pg.keyboard.press("b"); pruef(pg.evaluate("document.querySelector('#rb-schwarz').classList.contains('an')") and not z()["spielt"], "B: Bild schwarz und Pause")
            pg.keyboard.press("x"); pruef(not pg.evaluate("document.querySelector('#rb-schwarz').classList.contains('an')") and z()["spielt"], "M3: jede Taste holt das Bild zurück und setzt fort")
            pg.keyboard.press("b"); pg.click("#rb-schwarz")
            pruef(not pg.evaluate("document.querySelector('#rb-schwarz').classList.contains('an')") and z()["spielt"], "Klick aufs Schwarzbild holt es zurück")
            pg.keyboard.press("h"); pruef(pg.locator("#rb-hilfeBox").count() == 1, "H: Tastenhilfe")
            pg.keyboard.press("Escape"); pruef(pg.locator("#rb-hilfeBox").count() == 0, "Esc schließt die Hilfe")
            pg.evaluate("window.__marker = 1")
            pg.keyboard.press("F5"); pg.wait_for_timeout(700)
            pruef(pg.evaluate("window.__marker") == 1 and pg.evaluate("!!document.querySelector('#rueckblick')"), "F5 lädt nicht neu")
            thema0 = pg.evaluate("document.documentElement.dataset.theme || ''")
            pg.keyboard.press("t")
            th = pg.evaluate("document.documentElement.dataset.theme")
            pruef(th in ("dark", "light") and th != thema0 and pg.evaluate("localStorage.getItem('sj.thema')") == th, "T: hell oder dunkel, gemerkt")
            pg.keyboard.press("t")
            s0 = pg.evaluate("document.querySelector('#rb-buehne').getBoundingClientRect().width")
            pg.keyboard.press("r")
            s1 = pg.evaluate("document.querySelector('#rb-buehne').getBoundingClientRect().width")
            pg.keyboard.press("r")
            pruef(abs(s1 / s0 - .94) < .005, f"R: Rand für Fernseher, Bühne auf 94 % ({s1 / s0:.3f})")
            pg.evaluate("RB.zeige('zeitraffer', 5000)")
            pg.keyboard.press("Space")
            pruef(z()["spielt"] and pg.evaluate("document.querySelector('#rb-leiste').classList.contains('weg')"), "Start per Taste: Leiste bleibt weg")
            pg.mouse.move(400, 400)
            pg.wait_for_timeout(200)
            pruef(pg.evaluate("!document.querySelector('#rb-leiste').classList.contains('weg')"), "Mausbewegung zeigt die Steuerleiste")
            pg.keyboard.press("Space")
            pg.wait_for_timeout(2900)
            pruef(not z()["spielt"] and pg.evaluate("!document.querySelector('#rb-leiste').classList.contains('weg')"), "S9: pausiert bleibt die Leiste stehen")
            pg.click("#rb-leiste [data-k=weiter]")
            pruef(z()["phase"] == "show" and z()["spielt"], "Steuerleiste bedienbar")
            # Leiste wie bei einem Video: Klick an eine Stelle, Ziehen, Tooltip mit Kapitel und Zeit
            pg.mouse.move(500, 500)
            box = pg.evaluate("(() => { const s = document.querySelector('#rb-lSpur span[data-i=\"' + RB.kapitel().findIndex(k => k.id === 'platz2') + '\"]').getBoundingClientRect(); return [s.left, s.width, s.top + s.height / 2]; })()")
            dur = next(k["dur"] for k in pg.evaluate("RB.kapitel()") if k["id"] == "platz2")
            pg.mouse.move(box[0] + box[1] * .5, box[2])
            tipp = pg.evaluate("document.querySelector('#rb-lTipp').textContent")
            pg.mouse.click(box[0] + box[1] * .5, box[2])
            zz = z()
            pruef(zz["id"] == "platz2" and abs(zz["lokal"] - dur * .5) < dur * .06 and "Platz 2" in tipp, f"Leiste: Klick springt mitten ins Kapitel ({zz['id']}, {zz['lokal']:.0f} von {dur}, Tooltip {tipp!r})")
            pg.mouse.move(box[0] + box[1] * .2, box[2] + 12); pg.mouse.down(); pg.mouse.move(box[0] + box[1] * .8, box[2] + 12, steps=5)
            zz = z(); pg.mouse.up()
            pruef(zz["id"] == "platz2" and abs(zz["lokal"] - dur * .8) < dur * .06, f"Leiste: Ziehen (auch knapp unter der Leiste) setzt die Zeit ({zz['lokal']:.0f})")
            # Doppelklick nach dem Lösen eines Halts überspringt kein Kapitel (Code-Audit 25.10.): die 600-ms-Sperre gilt auch dort
            for kid, nach in (("rangliste", "Rangliste"), ("fakten", "Fun Facts (Bier)")):
                pg.evaluate(f"RB.starten('{kid}', 0)")
                pg.wait_for_function(f"RB.zustand().id === '{kid}' && RB.zustand().haelt === true", timeout=15000)
                pg.wait_for_timeout(800)
                pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(100); pg.keyboard.press("ArrowRight")
                pg.wait_for_timeout(300)
                pruef(z()["id"] == kid and not z()["haelt"], f"Doppelklick nach dem Lösen des Halts: {nach} bleibt stehen ({z()['id']})")
            # Abstand zum Ersten passt zu den Walzen, die jede Zeit einzeln runden: 3600,6 s und 4200,4 s zeigen 9:59
            pg.evaluate("(() => { const r = RB.D().rang; window.__nettoAlt = [r[0].netto, r[1].netto]; r[0].netto = 3600600; r[1].netto = 4200400; })()")
            pg.evaluate("RB.starten('rangliste', 0)"); pg.wait_for_timeout(300)
            dif1 = pg.evaluate("document.querySelectorAll('.rl-zeile .dif')[1].textContent.trim()")
            pruef(dif1 == "+9:59", f"Abstand zum Ersten stimmt mit den gerundeten Walzen überein ({dif1})")
            pg.evaluate("(() => { const r = RB.D().rang; [r[0].netto, r[1].netto] = window.__nettoAlt; })()")
            pg.evaluate("RB.zeige('abspann', 5000)")
            pg.keyboard.press("Space"); pruef(z()["spielt"], "Abspann: Leertaste setzt fort (endlos)")
            pg.wait_for_timeout(700)
            pg.keyboard.press("ArrowRight"); pruef(z()["id"] == "abspann", "S11: nach dem Abspann tut Weiter nichts")
            # Nichts läuft von selbst durch (17.10.): jedes Kapitel hält an seinem Ende, bis Weiter kommt
            for kid in ("fakten", "zeitraffer", "award1", "spalten"):
                k = next(x for x in pg.evaluate("RB.kapitel()") if x["id"] == kid)
                pg.evaluate(f"RB.starten('{kid}', {max(0, k['dur'] - 400)})")
                pg.wait_for_timeout(1200)
                zz = z()
                pruef(zz["id"] == kid and "wartet auf Weiter" in zz["leiste"], f"{kid}: hält am Ende ({zz['id']}, {zz['leiste']})")
            pg.keyboard.press("Space")
            pruef(z()["id"] == "platz3", "Leertaste im Endhalt: weiter ins nächste Kapitel")
            # Regel (17.10.): kein Halt vor dem Ende des Einblendens, keine Überblendung an der Kapitelzeit. Jedes Kapitel mit
            # Halt wird wie in der Show betreten (Weiter am Ende des Kapitels davor); im ersten Halt steht genau eine Szene,
            # voll eingeblendet, mit ihren Hauptteilen
            HAUPT = {"vorspann": ".titel h1, .titel .fakten", "fakten": ".ff-kopf, .ff-netz > div", "rangliste": ".rl-kopf, .rl-netz",
                     "rangliste2": ".rl-kopf, .rl-netz", "platz3": ".sp-spalte[data-p='3']", "platz2": ".sp-spalte[data-p='2']",
                     "platz1": ".sp-spalte[data-p='1']", "sieger": ".sg-platz, .sg-summe"}
            kap = pg.evaluate("RB.kapitel()")
            for n, k in enumerate(kap):
                if not k["halte"] or k["id"] == "vorspann":
                    continue
                pg.evaluate(f"RB.starten('{kap[n - 1]['id']}', 'ende')")
                pg.wait_for_timeout(700)
                pg.keyboard.press("ArrowRight")
                pg.wait_for_function(f"RB.zustand().id === '{k['id']}' && RB.zustand().haelt === true", timeout=15000)
                pg.wait_for_timeout(200)
                st = pg.evaluate(f"""(() => {{ const sz = [...document.querySelectorAll('#rb-szenen .szene')];
                  const h = sz.length ? [...sz[0].querySelectorAll("{HAUPT.get(k['id'], '*')}")].map(e => +getComputedStyle(e).opacity) : [];
                  return {{ n: sz.length, o: sz.length ? +getComputedStyle(sz[0]).opacity : 0, haupt: h.length ? Math.min(...h) : 1, teile: h.length }}; }})()""")
                pruef(st["n"] == 1 and st["o"] > .99 and st["haupt"] > .99 and st["teile"] > 0,
                      f"{k['id']}: im ersten Halt genau eine Szene, voll eingeblendet ({st})")
            pg.evaluate("RB.vorbereiten()"); pg.click("#rb-oStart")
            pg.wait_for_function("RB.zustand().haelt === true", timeout=8000)
            st = pg.evaluate("(() => { const sz = [...document.querySelectorAll('#rb-szenen .szene')]; return [sz.length, +getComputedStyle(sz[0]).opacity, Math.min(...[...sz[0].querySelectorAll('.titel h1, .titel .fakten')].map(e => +getComputedStyle(e).opacity))]; })()")
            pruef(st[0] == 1 and st[1] > .99 and st[2] > .99, f"vorspann: im Halt voll eingeblendet ({st})")
            # M8: im Durchsehen startet nichts
            pg.evaluate("RB.vorbereiten()")
            pg.click("#rb-oDurch"); pg.wait_for_selector(".d-bild")
            pg.keyboard.press("Space"); pg.keyboard.press("ArrowRight")
            pruef(z()["phase"] == "durchsehen" and pg.locator(".d-bild").count() > 0, "M8: Leertaste und Pfeil starten im Durchsehen nichts")
            pg.click("#rb-dFertig")
            pg.wait_for_selector("#rb-oStart")
            # S10: nach dem Umschalten eines Hakens startet die Leertaste die Show, statt den Haken zu kippen
            pg.click("#rb-oRand"); pg.click("#rb-oRand")
            pg.keyboard.press("Space")
            pruef(z()["phase"] == "show" and not pg.evaluate("RB.opt().rand"), "S10: Leertaste nach einem Haken startet, statt ihn umzuschalten")

        if an(7):
            print("Gruppe 7: Schutz vor dem Neuzeichnen")
            pg.evaluate("RB.zeige('zeitraffer', 20000)")
            pg.evaluate("document.querySelector('#rueckblick').__m = 1; window.__appAlt = document.querySelector('#app').innerHTML")
            vorher_z = pg.evaluate("RB.zustand()")
            pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            pg.evaluate("window.dispatchEvent(new HashChangeEvent('hashchange'))")
            pg.mouse.click(300, 300)
            pg.click("#rb-buehne", position={"x": 100, "y": 100})
            pg.evaluate("window.dispatchEvent(new Event('focus')); window.dispatchEvent(new Event('resize'))")
            pg.wait_for_timeout(500)
            nachher = pg.evaluate("RB.zustand()")
            pruef(nachher["id"] == "zeitraffer" and nachher["lokal"] == vorher_z["lokal"], f"Kapitel und Zeit nach visibilitychange, hashchange und Klick unverändert ({nachher['id']}, {nachher['lokal']:.0f})")
            pruef(pg.evaluate("document.querySelector('#rueckblick').__m") == 1, "Show-Container ist derselbe geblieben (nicht neu gezeichnet)")
            pg.evaluate("render(); refresh();")
            pg.wait_for_timeout(500)
            pruef(pg.evaluate("document.querySelector('#rueckblick').__m") == 1 and pg.evaluate("RB.zustand().id") == "zeitraffer", "render() und refresh() lassen die Show in Ruhe")
            pruef(pg.evaluate("document.querySelector('#app').innerHTML") == pg.evaluate("window.__appAlt"), "#app wurde nicht angefasst")
            pruef(pg.evaluate("S.view") == "rueckblick", "S.view bleibt rueckblick")
            pruef(pg.evaluate("document.querySelectorAll('#rueckblick [data-act]').length") == 0, "Knöpfe der Show tragen kein data-act")
            # zeichneKarte zeichnet nur bei Änderung: steht das Bild, bleibt der Pfad derselbe
            pg.evaluate("RB.zeige('abspann', 4000)")
            pg.wait_for_timeout(200)
            n0 = pg.evaluate("RB.kartenZaehler()")
            pg.wait_for_timeout(600)
            pruef(pg.evaluate("RB.kartenZaehler()") == n0, f"stehendes Bild: die Karte wird nicht neu gezeichnet ({n0})")

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
            # nach dem Laden kein Abruf mehr: Netz weg, ein Durchlauf aller Kapitel
            n_rpc = len(pg.evaluate("window.__RPC_LOG"))
            pg.evaluate("window.__netz = 'weg'")
            for k in KAP:
                pg.evaluate(f"RB.zeige('{k['id']}', 1500)")
            pruef(len(pg.evaluate("window.__RPC_LOG")) == n_rpc, "ohne Netz: alle Kapitel ohne einen Abruf")
            pg.evaluate("window.__netz = null")
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
            pg.evaluate("RB.vorbereiten()")
            pg.click("#rb-oDurch")
            pg.wait_for_selector(".d-bild")
            pg.locator(".d-bild").first.click()
            pg.click("#rb-dFertig")
            pg.wait_for_selector("#rb-oStart")
            pruef("(1 aus)" in text(pg, "#rb-oDurch"), "Foto ausgenommen: '(1 aus)'")
            aus = pg.evaluate("sessionStorage.getItem('sj.rb.aus')")
            pruef(bool(re.fullmatch(r'\["[^"]+:\d+"\]', aus or "")), f"nur teamId:position gemerkt ({aus})")
            pg.click("#rb-oStart")
            pg.wait_for_function("RB.zustand().phase === 'show'")
            n_ab = pg.evaluate("RB.kapitel().find(k => k.id === 'abspann').fotos")
            pruef(n_ab == D["fotos"] - 1, f"M8: ausgenommenes Foto fehlt im Abspann ({n_ab} von {D['fotos']})")
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
            pruef("Tiger Station 1" in t7, "K4: Vorbereiten nennt das fehlende Foto (Tiger Station 1)")
            args = pg7.evaluate("window.__FOTO_ARGS.filter(a => a.n === 'Eule' && a.p === 2).map(a => a.full)")
            pruef(args == [True, True, False], f"Eule 2: zweimal voll, dann Vorschau ({args})")
            pg7.evaluate("window.__fotoFehler = null")
            pg7.click("#rb-nochmal")
            pg7.wait_for_function(f"RB.D() && RB.D().fotos.length === {D['fotos']} && !!document.querySelector('#rb-oStart')", timeout=60000)
            pruef("nicht geladen" not in text(pg7, "#rueckblick") and pg7.evaluate("RB.D().fotos.length") == D["fotos"], "Erneut versuchen holt das fehlende Foto")
            pg7.context.close()

        if an(14):
            print("Gruppe 14: Awards gegen eine unabhängige Rechnung")
            dx = pg.evaluate("RB.test.export()")
            js_aw = pg.evaluate("RB.awards().liste")
            py_aw = awards_py(dx)
            gleich = len(js_aw) == len(py_aw) and all(a["id"] == p["id"] and a["team"] == p["team"] and abs(a["wert"] - p["wert"]) < 1e-6 for a, p in zip(js_aw, py_aw))
            pruef(gleich and len(js_aw) >= 3, f"Awards wie in Python gerechnet ({[(a['id'], a['team']) for a in js_aw]} / {[(a['id'], a['team']) for a in py_aw]})")
            koffer = {t["name"] for t in dx["teams"] if t["place"] and t["place"] <= dx["prizeCount"]}
            pruef(not any(a["team"] in koffer for a in js_aw), "Koffer-Teams bekommen keinen Award")
            pruef(len({a["team"] for a in js_aw}) == len(js_aw), "jedes Team höchstens einen Award")
            # Genauigkeit: ungenaue Punkte zählen nicht fürs Tempo; das Tempo misst Weg und Zeit desselben Stücks
            ts = [team_voll("A"), team_voll("B", tempo=1.3), team_voll("C", tempo=.8)]
            for p in ts[1]["points"]:
                p.append(40)   # B: alles ungenau
            roh14 = pg.evaluate(f"({ROH})({json.dumps({'teams': ts, 'ende': 120, 'koffer': 0})})")
            rr = pg.evaluate("([roh]) => { const d = RB.test.aufbereiten(roh); return d.teams.map(t => RB.test.kennzahlen(t, d)); }", [roh14])
            pruef("tempo" in rr[0] and "tempo" not in rr[1] and "faktor" in rr[1], f"Tempo nur aus Punkten mit höchstens 25 m Genauigkeit ({[sorted(x.keys()) for x in rr]})")
            pruef("tempo" in rr[0] and abs(rr[0]["tempo"] - 1.33) < 0.2, f"Tempo stimmt (A {rr[0].get('tempo', 0):.2f} km/h, gelaufen 222 m je 10 min)")

        # ------------------------------------------------------------------ 10
        if an(10):
            print("Gruppe 10: Bühne")
            def zeit(k):
                h = k["halte"]
                if k["id"].startswith("platz"):
                    return h[-1]
                if k["id"].startswith("rangliste"):
                    return k["dur"]
                if k["id"] == "zeitraffer":
                    return 40000
                if k["id"] == "abspann":
                    return 30000
                return max(0, k["dur"] - 300)
            for w, h, scheme in ((1280, 720, "dark"), (1280, 720, "light"), (1920, 1080, "light"), (1920, 1080, "dark")):
                pgb = show(b, "rueckblick", w=w, h=h, scheme=scheme, init=WAKE)
                gesamt_striche, klein, raus = [], [], []
                SHOT = f"rueckblick-{w}-{scheme}-"
                pgb.wait_for_timeout(300)
                pgb.screenshot(path=str(SHOTS / (SHOT + "00-vorbereiten.png")))
                r = pgb.evaluate(SCAN)
                gesamt_striche += r["striche"]; klein += [("vorbereiten", x) for x in r["klein"]]; raus += [("vorbereiten", x) for x in r["raus"]]
                kap = pgb.evaluate("RB.kapitel()")
                pgb.click("#rb-oStart"); pgb.wait_for_function("RB.zustand().phase === 'show'")
                for n, k in enumerate(kap):
                    pgb.evaluate(f"RB.zeige('{k['id']}', {zeit(k)})")
                    pgb.wait_for_timeout(150)
                    r = pgb.evaluate(SCAN)
                    gesamt_striche += r["striche"]; klein += [(k["id"], x) for x in r["klein"]]; raus += [(k["id"], x) for x in r["raus"]]
                    pgb.screenshot(path=str(SHOTS / (SHOT + f"{n + 1:02d}-{k['id']}.png")))
                # Zwischenbilder, die man sonst nicht sieht: Zeitraffer am Anfang, Platz 1 vor dem Aufdecken, Rangliste halb
                for kid, t_ in (("zeitraffer", 4000), ("zeitraffer", 66000), ("platz1", 1000), ("rangliste", 6000), ("fakten", 2600), ("award1", 1800)):
                    pgb.evaluate(f"RB.zeige('{kid}', {t_})"); pgb.wait_for_timeout(150)
                    r = pgb.evaluate(SCAN); klein += [(kid, x) for x in r["klein"]]; raus += [(kid, x) for x in r["raus"]]
                    pgb.screenshot(path=str(SHOTS / (SHOT + f"zw-{kid}-{t_}.png")))
                # Fotos durchsehen und Tastenhilfe sind auch Bühne
                pgb.evaluate("RB.vorbereiten()"); pgb.click("#rb-oDurch"); pgb.wait_for_selector(".d-bild"); pgb.wait_for_timeout(150)
                r = pgb.evaluate(SCAN); gesamt_striche += r["striche"]; klein += [("durchsehen", x) for x in r["klein"]]; raus += [("durchsehen", x) for x in r["raus"]]
                pgb.screenshot(path=str(SHOTS / (SHOT + "durchsehen.png")))
                pgb.click("#rb-dFertig"); pgb.keyboard.press("h"); pgb.wait_for_timeout(150)
                r = pgb.evaluate(SCAN); gesamt_striche += r["striche"]; klein += [("hilfe", x) for x in r["klein"]]; raus += [("hilfe", x) for x in r["raus"]]
                pgb.screenshot(path=str(SHOTS / (SHOT + "hilfe.png")))
                pgb.keyboard.press("Escape")
                pruef(not gesamt_striche, f"{w}x{h} {scheme}: keine Gedankenstriche oder Mittelpunkte im Bild {gesamt_striche[:3]}")
                pruef(not klein, f"{w}x{h} {scheme}: kleinste Schrift mindestens 20 px {klein[:4]}")
                pruef(not raus, f"{w}x{h} {scheme}: nichts ragt aus der Bühne {raus[:4]}")
                pgb.context.close()
            # mehr als zwölf Teams (K11): Rangliste in zwei Spalten, nichts ragt heraus
            pgk = show(b, "rueckblick-probe")
            pgk.evaluate("RB.test.sechzehn()")
            pgk.click("#rb-oStart"); pgk.wait_for_function("RB.zustand().phase === 'show'")
            k = next(x for x in pgk.evaluate("RB.kapitel()") if x["id"] == "rangliste2")
            pgk.evaluate(f"RB.zeige('rangliste2', {k['dur']})"); pgk.wait_for_timeout(150)
            r = pgk.evaluate(SCAN)
            spalten = pgk.evaluate("new Set([...document.querySelectorAll('.rl-zeile')].map(z => Math.round(z.getBoundingClientRect().left))).size")
            pruef(spalten == 2 and pgk.locator(".rl-zeile").count() == 16 and not r["raus"] and not r["klein"], f"16 Teams: Rangliste in zwei Spalten ({spalten}, {r['raus'][:2]}, {r['klein'][:2]})")
            pgk.screenshot(path=str(SHOTS / "rueckblick-16-teams-rangliste.png"))
            pgk.evaluate("RB.zeige('zeitraffer', 30000)"); pgk.wait_for_timeout(150)
            pgk.screenshot(path=str(SHOTS / "rueckblick-16-teams-zeitraffer.png"))
            pgk.context.close()
        pg.context.close()

    # ------------------------------------------------------------------ 11
    if an(11):
        print("Gruppe 11: Probe")
        pg = neu(b, "rueckblick-probe", w=1920, h=1080)
        pg.wait_for_selector("#rb-oStart", timeout=60000)
        log = pg.evaluate("window.__RPC_LOG")
        pruef(not any(x.startswith("admin_") for x in log), f"Probe fragt keine Admin-Funktion ab ({log})")
        pruef(pg.evaluate("RB.D().teams.length") == 12 and "Rückblick, Probe" in text(pg, "#rueckblick"), "Probe: zwölf Beispielteams, als Probe gekennzeichnet")
        ids = [k["id"] for k in pg.evaluate("RB.kapitel()")]
        pruef(ids[:4] == ["vorspann", "fakten", "gruppen", "zeitraffer"] and "platz1" in ids, f"Probe: drei Startgruppen, volle Kapitelliste ({' '.join(ids)})")
        pg.click("#rb-oStart"); pg.wait_for_function("RB.zustand().phase === 'show'")
        pg.evaluate("RB.zeige('gruppen', 6000)")
        pg.screenshot(path=str(SHOTS / "probe-gruppen-6000.png"))
        gt = text(pg, ".gr-netz")
        pruef(pg.locator(".gr-spalte").count() == 3 and pg.locator(".gr-koepfe .gr-team").count() == 12 and all(n in gt for n in ("Adler", "Wolf", "Igel")) and "?" not in gt,
              "Die Gruppen: drei Spalten, je Gruppe die Teams mit Tier und Namen")
        op = pg.evaluate("[...document.querySelectorAll('.gr-team')].map(e => +getComputedStyle(e).opacity)")
        pruef(min(op) > .99, f"Die Gruppen: nach dem Einsteigen stehen alle Teams ({min(op):.2f})")
        pg.evaluate("RB.zeige('gruppen', 900)")
        op = pg.evaluate("[...document.querySelectorAll('.gr-team')].map(e => +getComputedStyle(e).opacity)")
        pruef(op[0] > op[-1], "Die Gruppen: die Teams steigen nacheinander ein")
        # Ausgang: die Teams drehen sich zu "?" und landen auf den Ringplätzen am Start, genau dort, wo der Zeitraffer beginnt
        pg.evaluate("RB.zeige('gruppen', 7600)"); pg.wait_for_timeout(100); pg.screenshot(path=str(SHOTS / "probe-gruppen-7600.png"))
        pg.evaluate("RB.zeige('gruppen', 9990)"); pg.wait_for_timeout(700); pg.screenshot(path=str(SHOTS / "probe-gruppen-9990.png"))
        fl = pg.evaluate("[...document.querySelectorAll('.gr-flieger')].map(f => { const r = f.getBoundingClientRect(); return [f.textContent, r.left + r.width / 2, r.top + r.height / 2]; })")
        pg.evaluate("RB.zeige('zeitraffer', 0)"); pg.wait_for_timeout(700)
        kp = pg.evaluate("[...document.querySelectorAll('#rb-koepfe .kopf')].map(g => { const r = g.querySelector('circle.k').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })")
        abw = max((min(math.hypot(f[1] - k[0], f[2] - k[1]) for k in kp) for f in fl), default=999)
        pruef(len(fl) == 12 and all(f[0] == "?" for f in fl) and abw < 6, f"Gruppen-Ausgang: zwölf '?' landen auf den Köpfen des Zeitraffers (Abstand höchstens {abw:.1f} px)")
        # 17.10. Friedrich: das Drehen beginnt erst auf Weiter; Hotel (Start) und Laufzeit-Kasten stehen am Ende schon da
        st = pg.evaluate("RB.kapitel().find(k => k.id === 'gruppen')")
        pruef(st.get("halte") == [6500], f"Die Gruppen: Halt vor dem Drehen auf Weiter ({st.get('halte')})")
        pg.evaluate("RB.zeige('gruppen', 6500)"); pg.wait_for_timeout(200)
        pruef(pg.evaluate("RB.zustand().haelt") is True and pg.locator(".gr-flieger").count() == 0
              and pg.evaluate("[...document.querySelectorAll('.gr-team')].every(e => getComputedStyle(e).opacity > .99)"), "Die Gruppen: im Halt stehen die Teams noch, nichts dreht sich")
        pg.evaluate("RB.zeige('gruppen', 9990)"); pg.wait_for_timeout(700)
        hot = pg.evaluate("(() => { const g = document.querySelector('#rb-stationen g'); const r = g.getBoundingClientRect(); const n = [...document.querySelectorAll('#rb-stationen g')].filter(x => getComputedStyle(x).display !== 'none').length; return [getComputedStyle(g).display, r.width, n]; })()")
        pruef(hot[0] != "none" and hot[1] > 20 and hot[2] == 1, f"Gruppen-Ausgang: nur das Hotel Mama Shelter steht auf der Karte ({hot})")
        kz = pg.evaluate("(() => { const k = document.querySelector('.gr-zr'), b = document.querySelector('#rb-buehne').getBoundingClientRect(), r = k.getBoundingClientRect(); return [+getComputedStyle(k).opacity, (r.left + r.width / 2 - b.left) / b.width, (r.top - b.top) / b.height, k.textContent]; })()")
        pruef(kz[0] > .99 and kz[1] > .7 and kz[2] < .1 and "Laufzeit" in kz[3] and "im Ziel" in kz[3], f"Gruppen-Ausgang: Laufzeit und im Ziel stehen oben rechts ({kz})")
        pg.evaluate("RB.zeige('zeitraffer', 0)"); pg.wait_for_timeout(700)
        n_anker = pg.evaluate("[...document.querySelectorAll('#rb-anker line')].filter(l => +getComputedStyle(l).opacity > .5).length")
        pruef(n_anker >= 10, f"Ankerlinien: Köpfe im Ring am Start sind mit dem Start verbunden ({n_anker})")
        lage = pg.evaluate("(() => { const a = document.querySelector('#rb-anker'), s = document.querySelector('#rb-stationen'); return !!(a.compareDocumentPosition(s) & Node.DOCUMENT_POSITION_FOLLOWING); })()")
        pruef(lage, "Ankerlinien liegen unter den Abzeichen")
        kop = lambda: pg.evaluate("(() => { const g = [...document.querySelectorAll('#rb-koepfe .kopf')].find(g => g.style.display !== 'none'); return g ? +getComputedStyle(g).opacity : -1; })()")
        pg.evaluate("RB.zeige('award1', 2500)"); o1 = kop()
        pg.evaluate("RB.zeige('award1', 5500)"); o2 = kop()
        pruef(o1 > .99 and o2 < .01, f"Award: Teamsymbol läuft mit der Route und blendet danach aus ({o1:.2f}, {o2:.2f})")
        pg.evaluate("RB.zeige('zeitraffer', 0)")
        pg.evaluate("RB.zeige('zeitraffer', 30000)")
        zr = pg.evaluate("[...document.querySelectorAll('#rb-koepfe .kopf')].filter(g => g.style.display !== 'none').map(g => getComputedStyle(g.querySelector('.frage')).display)")
        pruef(zr and all(x != "none" for x in zr), "Zeitraffer: alle Köpfe als '?'")
        pruef(pg.evaluate("document.querySelector('.zr-uhr').textContent") not in ("", None) and re.fullmatch(r"\d:\d\d", pg.evaluate("document.querySelector('.zr-uhr').textContent")),
              "Zeitraffer: Laufzeit-Timer")
        # Doppelklick nach dem Lösen des Halts vor dem Drehen überspringt die Zeitraffer-Szene nicht (Code-Audit 25.10.)
        pg.evaluate("RB.starten('gruppen', 0)")
        pg.wait_for_function("RB.zustand().id === 'gruppen' && RB.zustand().haelt === true", timeout=15000)
        pg.wait_for_timeout(800)
        pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(100); pg.keyboard.press("ArrowRight")
        pg.wait_for_timeout(300)
        pruef(pg.evaluate("RB.zustand().id") == "gruppen", f"Die Gruppen: Doppelklick nach dem Lösen des Halts bleibt im Kapitel ({pg.evaluate('RB.zustand().id')})")
        pg.context.close()

    # ------------------------------------------------------------------ 12
    if an(12):
        print("Gruppe 12: Verlassen")
        pg = show(b, "rueckblick", w=1280, h=720)
        z = lambda: pg.evaluate("RB.zustand()")
        pg.click("#rb-oStart"); pg.wait_for_function("RB.zustand().phase === 'show'")
        pg.evaluate("RB.zeige('zeitraffer', 10000)"); pg.keyboard.press("Space")
        pruef(z()["spielt"], "Show läuft")
        pg.evaluate("history.back()")
        pg.wait_for_selector("#rb-frage:not([hidden])", timeout=5000)
        pruef(pg.evaluate("!!document.querySelector('#rueckblick')") and not z()["spielt"] and pg.evaluate("location.hash") == "#/rueckblick",
              "M5: Zurück im Browser fragt, die Show bleibt und hält an")
        pruef("Rückblick verlassen?" in text(pg, "#rb-frage"), "Rückfrage: 'Rückblick verlassen?'")
        pg.click("#rb-bleiben")
        pruef(pg.locator("#rb-frage:not([hidden])").count() == 0 and z()["spielt"] and z()["id"] == "zeitraffer", "Bleiben: Show läuft weiter, wo sie war")
        pg.evaluate("history.back()")
        pg.wait_for_selector("#rb-frage:not([hidden])", timeout=5000)
        pg.keyboard.press("Escape")
        pruef(pg.locator("#rb-frage:not([hidden])").count() == 0 and pg.evaluate("!!document.querySelector('#rueckblick')"), "zweites Zurück fragt wieder, Esc bleibt")
        # Kapitel merken und nach dem Neuladen anbieten (die Rückfrage beim Neuladen bestätigt neu())
        dialoge = []
        pg.on("dialog", lambda d: dialoge.append(d.type))
        pg.evaluate("RB.zeige('platz2', 0)")
        pg.add_init_script("window.__behalten = true;")
        pg.reload()
        pg.wait_for_selector("#rb-oStart", timeout=60000)
        pruef("beforeunload" in dialoge, f"M5: Neuladen fragt nach (beforeunload) ({dialoge})")
        pruef(pg.locator("#rb-oWeiter").count() == 1 and "Weiter bei Platz 2" in text(pg, "#rb-oWeiter"), "nach dem Neuladen: 'Weiter bei Platz 2'")
        pg.click("#rb-oWeiter")
        pruef(z()["id"] == "platz2" and z()["phase"] == "show", "Weiter bei: Show startet bei Platz 2")
        pg.evaluate("RB.vorbereiten()")
        pg.click("#rb-oZurueck")
        pg.wait_for_selector("#rb-frage:not([hidden])", timeout=5000)
        pruef(True, "'Zur Spielleitung' fragt erst")
        pg.click("#rb-verlassen")
        pg.wait_for_function("!document.querySelector('#rueckblick')", timeout=15000)
        pg.wait_for_selector(".tabs", timeout=15000)
        pruef(pg.evaluate("location.hash") == "#/admin" and pg.evaluate("document.querySelector('#app').inert") is False and pg.evaluate("RueckblickShow.offen()") is False,
              "Verlassen: Show weg, Spielleitung wieder bedienbar")
        pg.evaluate("location.hash = '#/rueckblick'")
        pg.wait_for_selector("#rb-oStart", timeout=60000)
        pg.evaluate("location.hash = '#/admin'")
        pg.wait_for_function("!document.querySelector('#rueckblick')", timeout=15000)
        pruef(True, "Adresse direkt geändert: Show schließt")
        pg.context.close()

    # ------------------------------------------------------------------ 13
    if an(13):
        print("Gruppe 13: Bildrate")
        for sz in ("rueckblick", "rueckblick-dicht"):
            pg = show(b, sz)
            info = pg.evaluate("(() => { const d = RB.D(); return { roh: RB.rohPunkte(), pts: d.teams.reduce((n, t) => n + t.pts.length, 0) }; })()")
            print(f"      {sz}: {info['roh']} Punkte geliefert, {info['pts']} nach dem Ausdünnen")
            if sz == "rueckblick-dicht":
                pruef(info["roh"] >= 12 * 4000 * 0.9, f"dichte Probedaten: {info['roh'] / 11:.0f} Punkte je Team mit GPS")
            pg.click("#rb-oStart"); pg.wait_for_function("RB.zustand().phase === 'show'")
            for kid, ab in (("zeitraffer", 3000), ("zeitraffer", 35000), ("zeitraffer", 60000), ("award2", 1000), ("rangliste", 1500), ("spalten", 200), ("platz1", "nach"), ("abspann", 3000)):
                pg.evaluate(f"RB.starten('{kid}', {json.dumps(ab)})")
                pg.wait_for_timeout(400)
                m = pg.evaluate(f"({FPS})(2500)")
                ok = m["fps"] >= 50
                pruef(ok, f"{sz} {kid} ab {ab}: {m['fps']:.0f} Bilder/s (schlimmstes Bild {m['schlimm']:.0f} ms)")
            pg.context.close()

    pruef(not err, f"keine Skriptfehler {err[:2]}")
    pruef(not fremd, f"keine Anfrage an fremde Rechner {fremd[:2]}")
    sys.stdout.flush()
    print("FEHLER: " + str(len(fehler)) if fehler else "OK")
    sys.stdout.flush()
    abschluss.ende(fehler, vorher)
