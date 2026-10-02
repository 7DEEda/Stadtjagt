#!/usr/bin/env python3
"""
Kompass-Wächter im Prüfstand, ohne Datenbank.

    python tools/pruefstand/waechter.py

Teil Logik: kompass-waechter.js mit erfundenen Sensorfolgen (virtuelle Zeit, läuft in Millisekunden).
Teile Spiel und Anzeige ergänzen Task 2 und 3. Im Vordergrund mit Timeout aufrufen.
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
from playwright.sync_api import sync_playwright  # noqa: E402

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
      const rate = s.rate + (s.schuetteln ? (i % 10 < 2 ? 40 : -40) : 0);   // Spitzen ohne Netto-Drehung
      w.gyro(rate, t);
      k += (s.kompassFaktor ?? 1) * s.rate * 0.02 + (s.wandern || 0) * 0.02;
      rausch = s.rauschen ? (Math.sin(t / 37) * s.rauschen) : 0;
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
    pruef(r[0] != "unzuverlaessig", f"gutes Handy, beim Gehen geschüttelt: nicht unzuverlässig ({r})")
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
      let t = 100000; for (let i = 0; i < 100; i++) { t += 20; w.gyro(0, t); w.kompass(300, t); }
      lauf(w, [{ ms: 1500, rate: 0 }]); return [w.urteil, w.ergebnisse.join(",")]; }""")
    pruef(r[1].count("schlecht") == 0, f"pause verwirft offene Abschnitte, Sprung danach zählt nicht ({r})")
    r = pg.evaluate("""() => { const z = []; const w = KompassWaechter({ onWechsel: x => z.push(x.urteil + "/" + x.vorbelastet) });
      lauf(w, [].concat(...Array.from({length: 3}, () => drehung(0.4)))); return z; }""")
    pruef("unzuverlaessig/true" in r, f"onWechsel meldet Urteil und Vermerk ({r})")
    pruef(not err, f"keine Skriptfehler {err[:2]}")
    b.close()
print("FEHLER: " + str(len(fehler)) if fehler else "OK")
sys.exit(1 if fehler else 0)
