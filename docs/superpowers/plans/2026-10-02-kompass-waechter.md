# Kompass-Wächter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Das Spiel erkennt einen schlechten Kompass (Vergleich mit dem Gyroskop), zeigt das dem Team (gestrichelte Nadel, Hinweis, Einmessen, bei der Teamleitung „Leitung abgeben“), weicht auf die Laufrichtung aus und meldet es der Spielleitung. Probeversion: wirkt nur im Testmodus.

**Architecture:** Die Erkennung ist ein eigenständiger Baustein `kompass-waechter.js` (reine Logik, keine DOM-Zugriffe), den `index.html` lädt und mit Sensordaten füttert. `index.html` hört zusätzlich `devicemotion` ab, rechnet die Drehung um die Senkrechte (wie im Geräte-Test erprobt) und setzt bei schlechtem Urteil den bestehenden Zustand `S.gps.kompass = "kalibrieren"`; `richtung()` nimmt dann schon heute die Laufrichtung. Die Spielleitung bekommt das Urteil über `report_position`.

**Tech Stack:** Vanilla JS in `index.html` plus eine Skriptdatei, Supabase/Postgres (plpgsql), Prüfstand mit Playwright (Python, Kanal chrome). Kein Node auf diesem Rechner: Logik-Tests laufen im Browser über Playwright.

**Spec:** `docs/superpowers/specs/2026-10-02-teststation-kompass-waechter-design.md`, Teil 2 (Abschnitte „Messung“, „Prüfabschnitte“, „Urteil“, „Gedächtnis des Handys“, „Anzeige für das Team“ inklusive Nadel Variante A, „Anzeige für die Spielleitung“). Mockups: `mockups/kompass-nadel.html` (Variante A), `mockups/kompass-waechter.html`, `mockups/rollen-akku-kompass.html` (Texte bei erfolglosem Einmessen).

## Global Constraints

- Schwellen (aus der Spec, wörtlich): Drehabschnitt beginnt über 8°/s, endet nach 1 s unter 3°/s oder nach 10 s; gewertet ab 90° laut Gyroskop; gut höchstens 20° Unterschied, schlecht mehr als 45°. Stillstand 3 s unter 3°/s; schlecht, wenn der Kompass mehr als 30° wandert. Urteil `unzuverlaessig` bei 3 schlechten unter den letzten 4; zurück auf `ok` nach 3 guten in Folge, vorbelastet nach 5.
- Ohne Gyroskop-Daten: kein Urteil (`null`), alles wie heute.
- Wirkung (Zustand, Nadel, Hinweis) nur bei `testMode`; gemessen und gemeldet wird immer.
- Gedächtnis lokal unter `localStorage` `sj.kompass` (JSON `{ "vorbelastet": bool, "versuche": int, "datum": "YYYY-MM-DD" }`), ohne Namen.
- Nadel Variante A: Umriss gestrichelt, Ring gestrichelt, Plakette „nach Laufrichtung“ statt „Kompass“; ohne Richtung gestrichelter Ring mit Fragezeichen, Plakette „erst ein paar Schritte“.
- Texte: echte Umlaute, keine Gedankenstriche (U+2013/U+2014); Zahl mit Einheit `white-space:nowrap`.
- Migrationen erst als Probelauf (DO-Block, `PROBELAUF_OK`, alles zurück), dann `python tools/sql.py`. Die Sicht `stations` nicht anfassen.
- Git: `git -c windows.appendAtomically=false commit`, Commit-Ende `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Nicht pushen (macht der Koordinator am Ende).
- Prüfstand-Läufe im Vordergrund mit Timeout (`timeout 300 python …`), nie im Hintergrund.

## Review Focus

- Gutes Handy, das beim Gehen geschüttelt wird (Gyroskop-Spitzen ohne echte Drehung, Kompass rauscht ±10°): darf nie `unzuverlaessig` werden. Test in Task 1 (Szenario „gesund mit Rauschen und Schütteln“).
- Kompass, der im Stillstand einfriert und nur beim Drehen versagt (Lauf VRB5): Stillstand darf kein „gut“ liefern, sonst schaltet der Wächter fälschlich zurück. Test in Task 1 (Szenario „eingefroren“).
- Seite war im Hintergrund oder Einmessen läuft: offene Abschnitte verwerfen, keine Fehlurteile aus dem Sprung danach. Test in Task 1 (`pause()`).
- Testmodus aus: Wächter misst, aber Nadel und Pfeil bleiben wie heute. Test in Task 3.
- iPhone, das selbst schlechte Genauigkeit meldet: bleibt `kalibrieren`, der Wächter darf nie auf `an` zurückstellen. Test in Task 2.

---

### Task 1: Baustein `kompass-waechter.js` mit Logik-Tests

**Files:**
- Create: `kompass-waechter.js`
- Create: `tools/pruefstand/waechter.py` (Teil „Logik“; Task 2 und 3 ergänzen weitere Teile)

**Interfaces:**
- Produces: `window.KompassWaechter(opt) → w` mit
  - `opt = { vorbelastet?: boolean, versuche?: number, onWechsel?: (zustand) => void }`; `zustand = { urteil, vorbelastet, versuche }`
  - `w.gyro(rateGradProS: number, tMs: number)`: Drehrate um die Senkrechte, im Uhrzeigersinn positiv
  - `w.kompass(richtungGrad: number, tMs: number)`: Kompassrichtung 0..360, im Uhrzeigersinn steigend
  - `w.pause()`: offene Abschnitte verwerfen (Seite verborgen, Einmessen läuft)
  - `w.einmessen()`: nach erfolgreichem Einmessen aufrufen
  - Getter `w.urteil` (`null | "ok" | "unzuverlaessig"`), `w.versuche` (int), `w.prueft` (bool: nach Einmessen, noch keine 3 Ergebnisse), `w.vorbelastet` (bool), `w.ergebnisse` (Array der letzten Ergebnisse `"gut"|"schlecht"`, zum Prüfen)

Ruling vorab (in die Ledger übernehmen): Stillstand-Abschnitte zählen nur als „schlecht“ (Wandern über 30°), nie als „gut“. Grund: ein eingefrorener Kompass (Lauf VRB5, 02.10.) wandert im Stillstand nicht und hätte den Wächter sonst nach 9 s Stillstand zurück auf `ok` gesetzt. Gute Ergebnisse kommen nur aus Drehungen.

- [ ] **Step 1: Prüfskript (Logik) schreiben**

`tools/pruefstand/waechter.py`:

```python
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
window.lauf = (w, schritte) => { let t = 0, k = 100, rausch = 0;
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
  return t; };
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
```

- [ ] **Step 2: Rot laufen lassen**

Run: `timeout 120 python tools/pruefstand/waechter.py`
Expected: Abbruch beim Laden (`kompass-waechter.js` fehlt) bzw. alle `FEHLT`.

- [ ] **Step 3: `kompass-waechter.js` schreiben**

```js
// Kompass-Wächter (Nachtrag 30): vergleicht Kompass und Gyroskop und urteilt, ob dem Kompass zu trauen ist.
// Reine Logik ohne DOM, damit sie im Prüfstand mit erfundenen Sensorfolgen geprüft werden kann.
// Schwellen aus docs/superpowers/specs/2026-10-02-teststation-kompass-waechter-design.md, Teil 2.
(function () {
  const DREH_START = 8, RUHE = 3, RUHE_MS = 1000, DREH_MAX_MS = 10000, DREH_MIN = 90;
  const GUT = 20, SCHLECHT = 45, STILL_MS = 3000, WANDERN = 30;
  const kurz = d => ((d % 360) + 540) % 360 - 180;

  window.KompassWaechter = function (opt) {
    opt = opt || {};
    let urteil = opt.vorbelastet ? "unzuverlaessig" : null, vorbelastet = !!opt.vorbelastet, versuche = opt.versuche || 0;
    let ergebnisse = [], gutInFolge = 0, nachEinmessen = -1;   // -1: nicht nach Einmessen, sonst Zahl der Ergebnisse seither
    let gyroWinkel = 0, gyroT = null, gyroDa = false, rate = 0, letzteBewegung = 0;
    let kompassAlt = null, kompassWeg = 0, kompassPfad = 0;
    let dreh = null, still = null;

    const melden = () => { if (opt.onWechsel) opt.onWechsel({ urteil, vorbelastet, versuche }); };
    function ergebnis(e) {
      ergebnisse.push(e); if (ergebnisse.length > 4) ergebnisse.shift();
      const vorher = urteil;
      if (nachEinmessen >= 0) {
        nachEinmessen++;
        if (e === "schlecht" && urteil === "unzuverlaessig") { versuche++; nachEinmessen = -1; }
        else if (nachEinmessen >= 3) nachEinmessen = -1;
      }
      if (e === "gut") {
        gutInFolge++;
        if (urteil !== "unzuverlaessig") urteil = "ok";
        else if (gutInFolge >= (vorbelastet ? 5 : 3)) { urteil = "ok"; vorbelastet = false; versuche = 0; ergebnisse = []; }
      } else {
        gutInFolge = 0;
        if (ergebnisse.filter(x => x === "schlecht").length >= 3 && urteil !== "unzuverlaessig") { urteil = "unzuverlaessig"; vorbelastet = true; }
        else if (urteil == null) urteil = "ok";
      }
      if (urteil !== vorher || e === "schlecht") melden();
    }
    function schritt(t) {
      if (!gyroDa) return;
      const a = Math.abs(rate);
      if (a > RUHE) letzteBewegung = t;
      if (!dreh && a > DREH_START) { dreh = { t0: t, g0: gyroWinkel, k0: kompassWeg }; still = null; }
      if (dreh && (t - letzteBewegung > RUHE_MS || t - dreh.t0 > DREH_MAX_MS)) {
        const gw = gyroWinkel - dreh.g0, kw = kompassWeg - dreh.k0;
        dreh = null;
        if (Math.abs(gw) >= DREH_MIN) {
          const d = Math.abs(kw - gw);
          if (d <= GUT) ergebnis("gut"); else if (d > SCHLECHT) ergebnis("schlecht");
        }
      }
      if (!dreh) {
        if (a >= RUHE) still = null;
        else if (!still) still = { t0: t, p0: kompassPfad };
        else if (t - still.t0 >= STILL_MS) {
          // Stillstand zählt nur als schlecht (Wandern), nie als gut: ein eingefrorener Kompass wandert nicht
          if (kompassPfad - still.p0 > WANDERN) ergebnis("schlecht");
          still = { t0: t, p0: kompassPfad };
        }
      }
    }
    return {
      gyro(r, t) {
        if (gyroT != null) gyroWinkel += r * Math.min(0.1, Math.max(0, (t - gyroT) / 1000));
        gyroT = t; rate = r; gyroDa = true; schritt(t);
      },
      kompass(g, t) {
        if (kompassAlt != null) { const d = kurz(g - kompassAlt); kompassWeg += d; kompassPfad += Math.abs(d); }
        kompassAlt = g; schritt(t);
      },
      pause() { dreh = null; still = null; kompassAlt = null; gyroT = null; },
      einmessen() { ergebnisse = []; gutInFolge = 0; nachEinmessen = 0; dreh = null; still = null; melden(); },
      get urteil() { return urteil; },
      get versuche() { return versuche; },
      get prueft() { return nachEinmessen >= 0; },
      get vorbelastet() { return vorbelastet; },
      get ergebnisse() { return ergebnisse.slice(); }
    };
  };
})();
```

- [ ] **Step 4: Grün laufen lassen**

Run: `timeout 120 python tools/pruefstand/waechter.py`
Expected: alle `ok`, `OK`. Schlägt ein Szenario fehl: zuerst prüfen, ob die Folge im Test das beschreibt, was die Spec meint (nicht die Schwellen anpassen); Abweichungen als Ruling.

- [ ] **Step 5: Commit**

```bash
git add kompass-waechter.js tools/pruefstand/waechter.py
git -c windows.appendAtomically=false commit -m "Kompass-Wächter: Logik als eigener Baustein, Prüfungen mit erfundenen Sensorfolgen

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Anbindung im Spiel (Sensoren, Wirkung, Gedächtnis)

**Files:**
- Modify: `index.html` (Skript laden nach `<script src="config.js"></script>`; `addOrient`, `startGps`, `kalEnde`, `S.gps`; neue Funktionen `addMotion`, `waechterSchlecht`)
- Modify: `tools/pruefstand/mock.js` (Haken `window.__motion(rateGradProS)`, zustellen an `devicemotion`-Zuhörer; Szenario `waechter-schlecht` mit `testMode: true, teststation: true` und `ls: { "sj.kompass": '{"vorbelastet":true,"versuche":0,"datum":"2026-10-02"}', … IM_TEAM }`, `gps: GPS_UNTERWEGS`, `steps: kompassAn`)
- Modify: `tools/pruefstand/shoot.py` nur falls `kompass-waechter.js` neben `app.html` liegen muss (shoot kopiert `vendor/`; die neue Datei ebenso mitkopieren)
- Modify: `tools/pruefstand/waechter.py` (Teil „Spiel“)

**Interfaces:**
- Consumes: `KompassWaechter` aus Task 1.
- Produces: `S.gps.waechter` (Instanz), `S.gps.waechterGrund` (bool: Zustand `kalibrieren` kommt vom Wächter), `waechterSchlecht() → boolean` (Testmodus an und Urteil `unzuverlaessig`), `addMotion(neu)`.

- [ ] **Step 1: Prüfstand-Haken und Prüfungen (rot)**

In `mock.js` neben den Orientierungs-Zuhörern auch `devicemotion` abfangen (wie `orientHandler`) und `window.__motion = r => motionHandler.forEach(h => h.fn({ rotationRate: { alpha: 0, beta: 0, gamma: -r }, accelerationIncludingGravity: { x: 0, y: 0, z: 9.8 }, timeStamp: performance.now() }))` bereitstellen (gamma = Drehung um z, gegen den Uhrzeigersinn positiv; flach liegend ist „oben“ z). In `waechter.py` einen Teil „Spiel“ anhängen (Port 8826, Aufbau wie `teststation.py`, `shoot.bauen()` vorher):

```python
    print("Spiel")
    pg2 = b.new_page(viewport={"width": 390, "height": 844}); pg2.set_default_timeout(15000)
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
```

Run: `timeout 300 python tools/pruefstand/waechter.py`
Expected: Teil Logik `ok`, Teil Spiel `FEHLT`.

- [ ] **Step 2: Anbindung schreiben**

In `index.html`:
1. `<script src="kompass-waechter.js"></script>` direkt nach `<script src="config.js"></script>`.
2. Nach dem Anlegen von `S` (wo `S.gps` definiert ist) den Wächter mit Gedächtnis anlegen:

```js
// Kompass-Wächter (Nachtrag 30): Gedächtnis je Handy, ohne Namen; Datum, damit ein alter Vermerk nach einem Tag verfällt
function waechterNeu() {
  let m = {}; try { m = JSON.parse(LS.getItem("sj.kompass") || "{}"); } catch { /* defekt: neu anfangen */ }
  const frisch = m.datum && (Date.now() - Date.parse(m.datum)) < 86400000;
  return window.KompassWaechter ? KompassWaechter({ vorbelastet: frisch && !!m.vorbelastet, versuche: frisch ? m.versuche || 0 : 0,
    onWechsel: z => { try { LS.setItem("sj.kompass", JSON.stringify({ vorbelastet: z.vorbelastet, versuche: z.versuche, datum: new Date().toISOString().slice(0, 10) })); } catch { /* egal */ }
      kompassNeu = true; } }) : null;
}
S.gps.waechter = waechterNeu();
const waechterSchlecht = () => { const st = aktiverStand(); return !!(st && st.testMode && S.gps.waechter && S.gps.waechter.urteil === "unzuverlaessig"); };
```

(`waechterNeu` muss nach `LS` und vor dem ersten `addOrient` laufen; `kompassNeu` ist weiter unten mit `let` deklariert: die Zuweisung passiert erst später zur Laufzeit, das ist in Ordnung.)

3. `addMotion` neben `addOrient`, Rechnung wie in `geraete-test.html` (`sensor.bewegt`):

```js
// Gyroskop für den Kompass-Wächter: Drehung um die Senkrechte (Drehrate auf "oben" projiziert, oben aus der Schwerkraft,
// auf z > 0 gewendet; alpha um x, beta um y, gamma um z, so auf Android-Chrome und iOS-Safari gemessen)
let motionH = null, motionOben = null;
function addMotion(neu) {
  if (!window.DeviceMotionEvent || (motionH && !neu)) return;
  if (motionH) window.removeEventListener("devicemotion", motionH);
  motionH = e => {
    const g = e.accelerationIncludingGravity, r = e.rotationRate, w = S.gps.waechter;
    if (g && typeof g.z === "number") {
      const b = Math.hypot(g.x || 0, g.y || 0, g.z);
      if (b > 1) { let o = [(g.x || 0) / b, (g.y || 0) / b, g.z / b]; if (o[2] < 0) o = o.map(v => -v);
        motionOben = motionOben ? motionOben.map((v, i) => v + (o[i] - v) * 0.6) : o; }
    }
    if (!w || !r || typeof r.alpha !== "number" || !motionOben || document.hidden) return;
    if (S.gps.kal) { w.pause(); return; }
    const v = r.alpha * motionOben[0] + r.beta * motionOben[1] + r.gamma * motionOben[2];
    w.gyro(-v, e.timeStamp || performance.now());   // Drehraten gegen den Uhrzeigersinn positiv, Kompass im Uhrzeigersinn
  };
  window.addEventListener("devicemotion", motionH, { passive: true });
}
```

4. In `addOrient`, direkt nach der Zuweisung von `g.heading`:

```js
    // Wächter füttern (nicht beim Einmessen, nicht im Hintergrund) und seine Wirkung anwenden
    const w = g.waechter;
    if (w) {
      if (g.kal || document.hidden) w.pause();
      else if (hd != null) w.kompass(hd, e.timeStamp || performance.now());
      g.waechterGrund = false;
      if (waechterSchlecht() && g.kompass === "an") { g.kompass = "kalibrieren"; g.waechterGrund = true; }
    }
```

5. In `startGps`: im Zweig mit Fingertipp (`else if (typeof DOE.requestPermission === "function") {`) vor `const r = await DOE.requestPermission();` die Bewegungs-Freigabe im selben Tipp anstoßen:

```js
      const DME = window.DeviceMotionEvent;
      const mot = DME && typeof DME.requestPermission === "function" ? DME.requestPermission().catch(() => "denied") : null;
```

und nach `if (r === "granted") { … }` ergänzen: `if (mot) mot.then(x => { if (x === "granted") addMotion(true); });`. In den übrigen Zweigen, wo `addOrient()` aufgerufen wird, zusätzlich `addMotion();`.

6. In `kalEnde(fertig)`: `if (fertig && g.waechter) g.waechter.einmessen();`. In `kompassNachPause`: `if (g.waechter) g.waechter.pause();` am Anfang.

- [ ] **Step 3: Grün**

Run: `timeout 300 python tools/pruefstand/waechter.py`
Expected: `OK`.

- [ ] **Step 4: Bestehende Prüfungen**

Run: `timeout 300 python tools/pruefstand/kritik.py; timeout 300 python tools/pruefstand/name.py; timeout 300 python tools/pruefstand/teststation.py`
Expected: je `OK`.

- [ ] **Step 5: Commit**

```bash
git add index.html tools/pruefstand/mock.js tools/pruefstand/shoot.py tools/pruefstand/waechter.py
git -c windows.appendAtomically=false commit -m "Kompass-Wächter im Spiel: Gyroskop, Wirkung im Testmodus, Gedächtnis je Handy

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Anzeige für das Team (Nadel A, Hinweis, Leitung abgeben)

**Files:**
- Modify: `index.html` (CSS `.compass.lauf`, `.compass.unsicher`; Kompass-Block der Team-Ansicht im Zweig `if (!st.checkedIn)`; `kompassText()`; `liveUpdate()`; neue Funktionen `kompassFolgt`, `kompassChip`, `waechterHinweisHTML`)
- Modify: `tools/pruefstand/waechter.py` (Teil „Anzeige“), `tools/pruefstand/mock.js` (Szenarien `waechter-versuche-2` mit `sj.kompass` `versuche: 2`)

**Interfaces:**
- Consumes: `S.gps.waechter`, `S.gps.waechterGrund`, `waechterSchlecht()` (Task 2).
- Produces: `kompassFolgt() → boolean` (`g.heading != null && g.kompass === "an"`), `kompassChip() → string` (HTML der Plakette), `waechterHinweisHTML(st, lesen) → string`.

- [ ] **Step 1: Prüfungen (rot)**

In `waechter.py` Teil „Anzeige“ (Szenario `waechter-schlecht`, nach `window.__orient('gut'); window.__motion(0)` und kurzem Warten):

```python
    print("Anzeige")
    pg2.goto("http://127.0.0.1:8826/app.html?szenario=waechter-schlecht"); pg2.wait_for_function("typeof S !== 'undefined' && S.gps.on")
    pg2.evaluate("window.__orient('gut'); window.__motion(0)"); pg2.wait_for_timeout(800)
    k = pg2.locator(".compass.gross")
    pruef("lauf" in k.get_attribute("class") or "unsicher" in k.get_attribute("class"), f"Kompass gestrichelt ({k.get_attribute('class')})")
    pruef(pg2.inner_text("#kchip").strip() in ("nach Laufrichtung", "erst ein paar Schritte"), f"Plakette ({pg2.inner_text('#kchip')})")
    t = pg2.inner_text("#app")
    pruef("Der Kompass dieses Handys zeigt gerade falsch" in t, "Hinweis des Wächters")
    pruef(pg2.locator("[data-act=t-kal]").count() >= 1, "Knopf Kompass einmessen")
    pruef(pg2.locator(".msg [data-act=t-abgeben-frage]").count() == 1, "Teamleitung: Leitung abgeben im Hinweis")
    pg2.evaluate("S.gps.gpsHeading = 40; liveUpdate()"); pg2.wait_for_timeout(200)
    pruef("lauf" in pg2.locator(".compass.gross").get_attribute("class") and pg2.inner_text("#kchip").strip() == "nach Laufrichtung", "mit Laufrichtung: Nadel gestrichelt, Plakette nach Laufrichtung")
    pg2.screenshot(path=str(HIER / "shots" / "waechter-schlecht.png"), full_page=True)
    pg2.goto("http://127.0.0.1:8826/app.html?szenario=waechter-versuche-2"); pg2.wait_for_function("typeof S !== 'undefined' && S.gps.on")
    pg2.evaluate("window.__orient('gut'); window.__motion(0)"); pg2.wait_for_timeout(800)
    t = pg2.inner_text("#app")
    pruef("Einmessen hilft bei diesem Handy nicht" in t, "nach zwei Versuchen: hilft nicht")
    pruef(pg2.locator(".msg .btn[data-act=t-kal]").count() == 0 and pg2.locator(".msg .link[data-act=t-kal]").count() == 1, "kein großer Knopf, nur Link")
    pg2.evaluate("S.team.state.testMode = false; window.__orient('gut')"); pg2.wait_for_timeout(400)
    pruef("lauf" not in (pg2.locator(".compass.gross").get_attribute("class") or "") and pg2.inner_text("#kchip").strip() == "Kompass", "Testmodus aus: volle Nadel, Plakette Kompass")
```

Run: `timeout 300 python tools/pruefstand/waechter.py`
Expected: Teil Anzeige `FEHLT`.

- [ ] **Step 2: CSS**

Bei den Kompass-Regeln (`.compass.unsicher .nq{…}`) ergänzen:

```css
/* Nadel Variante A (Entscheidung 02.10.2026): folgt der Pfeil der Laufrichtung, nur Umriss und Ring gestrichelt */
.compass.lauf .needle{fill:none;stroke:var(--flag);stroke-width:2.5;stroke-dasharray:4 3;stroke-linejoin:round}
.compass.lauf .ring,.compass.unsicher .ring{stroke-dasharray:5 5}
.kchip{display:inline-flex;margin-top:6px;white-space:nowrap}
.kchip.ok{background:var(--ok-bg);color:var(--ok);border-color:transparent}
.kchip.warn{background:var(--warn-bg);color:var(--warn);border-color:transparent}
```

- [ ] **Step 3: Funktionen und Einbau**

Vor `function kompassText()`:

```js
// Folgt der Pfeil dem Kompass? Sonst Laufrichtung (gestrichelte Nadel) oder noch keine Richtung (Fragezeichen)
const kompassFolgt = () => S.gps.heading != null && S.gps.kompass === "an";
function kompassChip() {
  const g = S.gps;
  if (!g.on) return "";
  if (kompassFolgt()) return `<span class="chip kchip ok" id="kchip">Kompass</span>`;
  return `<span class="chip kchip warn" id="kchip">${g.gpsHeading != null ? "nach Laufrichtung" : "erst ein paar Schritte"}</span>`;
}
// Hinweis des Wächters; nach erfolglosem Einmessen ehrlicher (Mockup rollen-akku-kompass.html)
function waechterHinweisHTML(st, lesen) {
  const g = S.gps, w = g.waechter;
  if (!g.waechterGrund || !w) return "";
  const leitung = !lesen;
  const tipp = `Tipp: Schaut auf ein anderes Handy aus eurem Team. Wer mitliest und den Standort freigibt, sieht dort den Pfeil mit dem eigenen Kompass.${leitung ? " Oder gebt die Leitung an jemanden ab, dessen Handy richtig zeigt." : ""}`;
  const abgeben = leitung ? `<button class="btn alt" data-act="t-abgeben-frage">Leitung abgeben</button>` : "";
  if (w.prueft) return `<div class="msg info"><b>Kompass wird geprüft …</b> Dreht euch einmal um, dann sieht das Handy, ob der Kompass jetzt mitgeht.</div>`;
  if (w.versuche === 0) return `<div class="msg warn"><b>Der Kompass dieses Handys zeigt gerade falsch</b><br>Der Pfeil richtet sich nach eurer Laufrichtung. ${tipp}
    <button class="btn alt" data-act="t-kal">Kompass einmessen</button>${abgeben}</div>`;
  if (w.versuche === 1) return `<div class="msg warn"><b>Einmessen hat nicht geholfen</b><br>Probiert es noch einmal, mit etwas Abstand zu Metall, Magneten und Handyhüllen. Der Pfeil folgt solange eurer Laufrichtung. ${tipp}
    <button class="btn alt" data-act="t-kal">Noch einmal einmessen</button>${abgeben}</div>`;
  return `<div class="msg warn"><b>Einmessen hilft bei diesem Handy nicht</b><br>Der Pfeil bleibt bei der Laufrichtung, die Entfernung stimmt immer. ${tipp}
    ${abgeben}<button class="link" data-act="t-kal">Trotzdem noch einmal einmessen</button></div>`;
}
```

In `kompassText()` als erste Zeile nach `const g = …`: `if (g.waechterGrund) return lauf ? "Pfeil nach Laufrichtung" : "Erst ein paar Schritte gehen, dann zeigt der Pfeil eure Laufrichtung";`

Im Kompass-Block der Team-Ansicht (`<div class="compass gross ${richtungBekannt() ? "" : "unsicher"}">`) die Klasse erweitern zu `${!richtungBekannt() ? "unsicher" : kompassFolgt() ? "" : "lauf"}` und unter `<div class="muted small" id="gnote">…</div>` `${kompassChip()}` einfügen. Den bestehenden Hinweis `${g.on && g.kompass === "kalibrieren" && !kalOk && !g.kal ? … "Der Kompass ist ungenau." …}` nur zeigen, wenn `!g.waechterGrund`, und davor `${!g.kal ? waechterHinweisHTML(st, lesen) : ""}` einsetzen. In `liveUpdate()` die Zeile mit `classList.toggle("unsicher", …)` ersetzen durch:

```js
  const n = $("#needle"); if (n) { const c = n.closest(".compass"); c.classList.toggle("unsicher", !richtungBekannt()); c.classList.toggle("lauf", richtungBekannt() && !kompassFolgt()); }
  const kc = $("#kchip"); if (kc) kc.outerHTML = kompassChip();
```

- [ ] **Step 4: Grün, bestehende Prüfungen, Bildschirmfotos**

Run: `timeout 300 python tools/pruefstand/waechter.py; timeout 300 python tools/pruefstand/kritik.py; timeout 300 python tools/pruefstand/name.py; timeout 600 python tools/pruefstand/shoot.py > /dev/null`
Expected: `OK`, `OK`, `OK`; `shoot.py` ohne `pageerror`. `tools/pruefstand/shots/waechter-schlecht.png` ansehen: gestrichelte Nadel/Ring, Plakette, Hinweis mit beiden Knöpfen.

- [ ] **Step 5: Commit**

```bash
git add index.html tools/pruefstand/waechter.py tools/pruefstand/mock.js
git -c windows.appendAtomically=false commit -m "Kompass-Wächter: gestrichelte Nadel, Plakette, Hinweis mit Einmessen und Leitung abgeben

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Spielleitung sieht den Kompass der Teamleitung

**Files:**
- Create: `tools/migration_waechter.py`, `supabase/migrations/20261002160000_kompass_waechter.sql`, `tools/pruefstand/waechter_db.py`
- Modify: `index.html` (`maybeReport`, `zustandHTML`), `tools/pruefstand/mock.js` (`report_position` merkt `p_kompass`; ein Team mit `position.kompass = "unzuverlaessig"` im Szenario `admin-teststation`), `tools/pruefstand/waechter.py` (Teil „Spielleitung“)

**Interfaces:**
- Produces (DB): `team_positions.kompass text`; `report_position(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_kompass text default null)` (alte 4-Parameter-Fassung gelöscht); `admin_state.teams[].position.kompass`.

- [ ] **Step 1: Generator und Migration**

`tools/migration_waechter.py` nach dem Muster von `tools/migration_startpunkt.py`: Kopf

```sql
-- Nachtrag 30: Kompass-Wächter. Das Handy der Teamleitung meldet sein Urteil mit der Position.
alter table team_positions add column kompass text;
drop function report_position(text, double precision, double precision, double precision);
create function report_position(p_code text, p_lat double precision, p_lng double precision,
                                p_acc double precision, p_kompass text default null)
returns void language plpgsql security definer set search_path = public as $$
declare t teams;
begin
  if (select status from game_state where id = 1) <> 'running' then return; end if;
  if p_lat is null or p_lng is null or abs(p_lat) > 90 or abs(p_lng) > 180
     or (abs(p_lat) < 0.01 and abs(p_lng) < 0.01)
     or p_acc is null or p_acc <= 0 or p_acc > 1000 then
    return;
  end if;
  t := team_by_code(p_code);
  insert into team_positions(team_id, lat, lng, accuracy_m, updated_at, kompass)
  values (t.id, p_lat, p_lng, p_acc, now(), case when p_kompass in ('ok', 'unzuverlaessig') then p_kompass end)
  on conflict (team_id) do update
    set lat = excluded.lat, lng = excluded.lng, accuracy_m = excluded.accuracy_m, updated_at = now(), kompass = excluded.kompass;
  insert into position_log(team_id, lat, lng, accuracy_m) values (t.id, p_lat, p_lng, p_acc);
end $$;
grant execute on function report_position(text, double precision, double precision, double precision, text) to anon, authenticated;
```

danach `admin_state` aus `20261002140000_startpunkt.sql` (letzte Fassung, Ende `$$;` nach dem öffnenden `$$` suchen) mit der Ersetzung `'accuracy', tp.accuracy_m, 'updatedAt', tp.updated_at)` → `'accuracy', tp.accuracy_m, 'updatedAt', tp.updated_at, 'kompass', tp.kompass)` (genau einmal, sonst Abbruch), am Ende `notify pgrst, 'reload schema';`.

- [ ] **Step 2: Probelauf (zuerst ohne Migration rot sehen: `MIGRATION` auf eine leere Datei zeigen lassen, dann zurück)**

`tools/pruefstand/waechter_db.py` nach dem Muster von `startpunkt_db.py`. Prüfungen im DO-Block: Spalte da; Status kurz `running`, ein Probe-Team (`insert into teams (name, code, read_token) values ('Probelauf', v_code, md5(random()::text))`), `report_position(v_code, 52.47, 13.46, 8, 'unzuverlaessig')` → `admin_state(v_pin)->'teams'` enthält für das Team `position.kompass = 'unzuverlaessig'`; Aufruf mit 4 Parametern geht weiter (Default null) und setzt `kompass` auf null; unbekannter Wert `'kaputt'` wird zu null; genau eine Funktion `report_position` in `pg_proc`. Ende `PROBELAUF_OK`.

Run: `timeout 120 python tools/pruefstand/waechter_db.py`
Expected: `PROBELAUF_OK: … Prüfungen bestanden, alles zurückgenommen`.

- [ ] **Step 3: Client**

In `maybeReport`: Urteil mitschicken und bei einem Wechsel nicht auf die Minute warten:

```js
  const urteil = g.waechter ? g.waechter.urteil : null;
  const neuUrteil = urteil !== g.lastSentUrteil;
  if (!moved && !oldEnough && !neuUrteil) return;
  g.lastSentUrteil = urteil;
```

(die bestehende Zeile `if (!moved && !oldEnough) return;` ersetzen) und im Aufruf `p_kompass: urteil` ergänzen. In `zustandHTML` vor `return \`<br><b class="small">${wo}</b><br>${gps}\`;`:

```js
  const kompass = t.position && t.position.kompass === "unzuverlaessig"
    ? ` <span class="chip test" style="margin:0;white-space:nowrap">Kompass falsch, Pfeil nach Laufrichtung</span>` : "";
```

und `${gps}${kompass}` zurückgeben.

- [ ] **Step 4: Prüfstand (rot → grün)**

`mock.js`: `report_position` speichert `a.p_kompass` in `window.__KOMPASS`; im Szenario `admin-teststation` bekommt Team Fuchs `position.kompass = "unzuverlaessig"`. `waechter.py` Teil „Spielleitung“: Reiter Teams zeigt bei Fuchs „Kompass falsch, Pfeil nach Laufrichtung“; im Szenario `waechter-schlecht` nach `window.__gps(…)` (laufendes Spiel) liegt `window.__KOMPASS == "unzuverlaessig"`.

Run: `timeout 300 python tools/pruefstand/waechter.py; timeout 300 python tools/pruefstand/teststation.py`
Expected: `OK`, `OK`.

- [ ] **Step 5: Commit (Migration nicht einspielen, das macht der Koordinator)**

```bash
git add tools/migration_waechter.py supabase/migrations/20261002160000_kompass_waechter.sql tools/pruefstand/waechter_db.py index.html tools/pruefstand/mock.js tools/pruefstand/waechter.py
git -c windows.appendAtomically=false commit -m "Kompass-Wächter: Spielleitung sieht das Urteil der Teamleitung (Nachtrag 30, Migration vorbereitet)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5 (Koordinator): Einspielen, Veröffentlichen, Doku

- [ ] Probelauf `waechter_db.py` noch einmal, dann `python tools/sql.py supabase/migrations/20261002160000_kompass_waechter.sql`.
- [ ] Push, warten bis `https://7deeda.github.io/Stadtjagt/kompass-waechter.js` erreichbar ist.
- [ ] `HANDOFF.md` Abschnitt „Kompass-Wächter (Nachtrag 30)“, `SPIEL.md` Abschnitt 12 ergänzen, `README.md` Prüfskripte `waechter.py`, `waechter_db.py`.
