#!/usr/bin/env python3
"""
Kompass-Wächter im Prüfstand, ohne Datenbank.

    python tools/pruefstand/waechter.py

Teil Logik: kompass-waechter.js mit erfundenen Sensorfolgen (virtuelle Zeit, läuft in Millisekunden).
Teil Spiel: Anbindung in index.html (Szenario waechter-schlecht, Port 8826). Teil Anzeige ergänzt Task 3. Im Vordergrund mit Timeout aufrufen.
"""
import functools
import http.server
import pathlib
import sys
import threading

sys.stdout.reconfigure(encoding="utf-8")
HIER = pathlib.Path(__file__).resolve().parent
REPO = HIER.parent.parent
sys.path.insert(0, str(HIER))
import shoot  # noqa: E402

shoot.bauen()
from playwright.sync_api import sync_playwright  # noqa: E402


class Leise(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8826), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
fehler = []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


# Sensorfolgen in virtueller Zeit: alle 20 ms ein Gyro- und ein Kompasswert
FOLGEN = r"""
window.lauf = (w, schritte) => { let t = w._t || 0, k = w._k ?? 100, rausch = 0;   // Zeit und Kompass laufen über mehrere Aufrufe weiter
  for (const s of schritte) {
    const n = Math.round(s.ms / 20);
    for (let i = 0; i < n; i++) {
      t += 20;
      const rate = s.rate + (s.schuetteln ? (i % 10 < 2 ? 160 : -40) : 0);   // Spitzen ohne Netto-Drehung: 2 x 160 + 8 x -40 = 0
      w.gyro(rate, t);
      k += (s.kompassFaktor ?? 1) * s.rate * 0.02 + (s.wandern || 0) * 0.02;
      rausch = s.rauschen ? (Math.sin(t / 37) * s.rauschen) : 0;
      if (s.zittern) rausch += (i % 2 ? s.zittern : -s.zittern);   // Zittern ohne Netto-Wandern
      if (!s.eingefroren) w.kompass(((k + rausch) % 360 + 360) % 360, t);
      else if (i === 0) w.kompass(((k + rausch) % 360 + 360) % 360, t);
    }
  }
  w._t = t; w._k = k; return t; };
// eine Drehung: 2 s mit 60°/s (120°), dann 1,5 s Ruhe
window.drehung = (faktor, extra) => [Object.assign({ ms: 2000, rate: 60, kompassFaktor: faktor }, extra || {}), { ms: 1500, rate: 0 }];
"""

with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(); err = []
    pg.on("pageerror", lambda e: err.append(str(e)))
    pg.set_content("<html><body></body></html>")
    pg.add_script_tag(path=str(REPO / "kompass-waechter.js"))
    pg.add_script_tag(content=FOLGEN)

    print("Logik")
    r = pg.evaluate("""() => { const w = KompassWaechter({}); lauf(w, [].concat(...Array.from({length: 10}, () => drehung(1, { rauschen: 10 }))));
      return [w.urteil, w.ergebnisse.join(",")]; }""")
    pruef(r[0] == "ok", f"gesund mit Rauschen ±10°: ok ({r})")
    r = pg.evaluate("""() => { const w = KompassWaechter({}); lauf(w, [].concat(...Array.from({length: 6}, () => [{ ms: 3000, rate: 0, schuetteln: true, rauschen: 10 }])));
      return [w.urteil, w.ergebnisse.join(",")]; }""")
    pruef(r[0] != "unzuverlaessig" and "schlecht" not in r[1], f"gutes Handy, beim Gehen geschüttelt: nicht unzuverlässig, kein schlecht ({r})")
    r = pg.evaluate("""() => { const w = KompassWaechter({}); lauf(w, [].concat(...Array.from({length: 4}, () => [{ ms: 3200, rate: 0, zittern: 1.5 }])));
      return [w.urteil, w.ergebnisse.join(",")]; }""")
    pruef(r[0] != "unzuverlaessig" and "schlecht" not in r[1], f"gesund im Stillstand mit Zittern ±1,5° je Wert: kein schlecht ({r})")
    r = pg.evaluate("""() => { const w = KompassWaechter({}); lauf(w, [].concat(...Array.from({length: 3}, () => drehung(0.4))));
      return [w.urteil, w.ergebnisse.join(",")]; }""")
    pruef(r[0] == "unzuverlaessig", f"folgt zu 40 %: nach 3 Drehungen unzuverlässig ({r})")
    r = pg.evaluate("""() => { const w = KompassWaechter({}); lauf(w, [].concat(...Array.from({length: 4}, () => [{ ms: 3200, rate: 0, wandern: 15 }])));
      return [w.urteil, w.ergebnisse.join(",")]; }""")
    pruef(r[0] == "unzuverlaessig", f"wandert im Stillstand 48° je 3,2 s: unzuverlässig ({r})")
    r = pg.evaluate("""() => { const w = KompassWaechter({}); lauf(w, [].concat(...Array.from({length: 3}, () => drehung(0.4))));
      lauf(w, [].concat(...Array.from({length: 4}, () => [{ ms: 3200, rate: 0, eingefroren: true }]))); return [w.urteil, w.ergebnisse.join(",")]; }""")
    pruef(r[0] == "unzuverlaessig", f"eingefroren im Stillstand: bleibt unzuverlässig ({r})")
    r = pg.evaluate("""() => { const w = KompassWaechter({}); lauf(w, [].concat(...Array.from({length: 3}, () => drehung(0.4))));
      lauf(w, [].concat(...Array.from({length: 3}, () => drehung(1)))); return [w.urteil, w.vorbelastet]; }""")
    pruef(r[0] == "ok" and r[1] is False, f"3 gute Drehungen danach: zurück auf ok, Vermerk weg ({r})")
    r = pg.evaluate("""() => { const w = KompassWaechter({ vorbelastet: true }); const a = w.urteil; lauf(w, [].concat(...Array.from({length: 3}, () => drehung(1)))); const b = w.urteil;
      lauf(w, [].concat(...Array.from({length: 2}, () => drehung(1)))); return [a, b, w.urteil]; }""")
    pruef(r == ["unzuverlaessig", "unzuverlaessig", "ok"], f"vorbelastet: startet unzuverlässig, braucht 5 gute ({r})")
    r = pg.evaluate("""() => { const w = KompassWaechter({}); lauf(w, [].concat(...Array.from({length: 3}, () => drehung(0.4)))); w.einmessen(); const p = w.prueft;
      lauf(w, drehung(0.4)); const v1 = w.versuche; w.einmessen(); lauf(w, drehung(0.4)); return [p, v1, w.versuche, w.urteil]; }""")
    pruef(r == [True, 1, 2, "unzuverlaessig"], f"Einmessen hilft nicht: prueft, dann Versuche 1 und 2 ({r})")
    r = pg.evaluate("""() => { const w = KompassWaechter({}); let t = 0; for (let i = 0; i < 2000; i++) { t += 20; w.kompass((i * 3) % 360, t); } return w.urteil; }""")
    pruef(r is None, f"ohne Gyroskop: kein Urteil ({r})")
    r = pg.evaluate("""() => { const w = KompassWaechter({}); lauf(w, [{ ms: 1000, rate: 60, kompassFaktor: 1 }]); w.pause();
      w._k += 100;   // Kompass springt einmal um 100° (Seite war verborgen)
      lauf(w, [{ ms: 1000, rate: 60, kompassFaktor: 1 }, { ms: 1500, rate: 0 }]); return [w.urteil, w.ergebnisse.join(",")]; }""")
    pruef("schlecht" not in r[1], f"pause mitten in der Drehung verwirft den Abschnitt, Sprung zählt nicht ({r})")
    r = pg.evaluate("""() => { const z = []; const w = KompassWaechter({ onWechsel: x => z.push(x.urteil + "/" + x.vorbelastet) });
      lauf(w, [].concat(...Array.from({length: 3}, () => drehung(0.4)))); return z; }""")
    pruef("unzuverlaessig/true" in r, f"onWechsel meldet Urteil und Vermerk ({r})")

    print("Spiel")
    pg2 = b.new_page(viewport={"width": 390, "height": 844}); pg2.set_default_timeout(15000)
    pg2.on("pageerror", lambda e: err.append(str(e)))
    pg2.goto("http://127.0.0.1:8826/app.html?szenario=waechter-schlecht"); pg2.wait_for_function("typeof S !== 'undefined' && S.gps.on")
    pg2.evaluate("window.__orient('gut'); window.__motion(0)"); pg2.wait_for_timeout(600)
    z = pg2.evaluate("[S.gps.waechter && S.gps.waechter.urteil, S.gps.kompass, S.gps.waechterGrund]")
    pruef(z == ["unzuverlaessig", "kalibrieren", True], f"vorbelastet im Testmodus: Kompass gilt als ungenau ({z})")
    pg2.evaluate("S.team.state.testMode = false; window.__orient('gut')"); pg2.wait_for_timeout(400)
    pruef(pg2.evaluate("S.gps.kompass") == "an", "Testmodus aus: Wächter wirkt nicht")
    pg2.evaluate("S.team.state.testMode = true; window.__zustellen({ alpha: 63, beta: 35, gamma: 0, absolute: false, webkitCompassHeading: 297, webkitCompassAccuracy: 42 })"); pg2.wait_for_timeout(300)
    pg2.evaluate("S.gps.waechter = KompassWaechter({}); window.__zustellen({ alpha: 63, beta: 35, gamma: 0, absolute: false, webkitCompassHeading: 297, webkitCompassAccuracy: 42 })"); pg2.wait_for_timeout(300)
    pruef(pg2.evaluate("S.gps.kompass") == "kalibrieren", "iPhone meldet schlechte Genauigkeit: Wächter stellt nicht auf an")
    pg2.evaluate("S.gps.waechter.einmessen = (o => function () { window.__eingemessen = true; return o.call(this); })(S.gps.waechter.einmessen); kalStart(); kalEnde(true)")
    pruef(pg2.evaluate("window.__eingemessen === true"), "erfolgreiches Einmessen meldet sich beim Wächter")
    pruef(pg2.evaluate("JSON.parse(localStorage.getItem('sj.kompass') || '{}').vorbelastet") is not None, "Gedächtnis sj.kompass vorhanden")
    pruef(not err, f"keine Skriptfehler {err[:2]}")
    b.close()
print("FEHLER: " + str(len(fehler)) if fehler else "OK")
sys.exit(1 if fehler else 0)
