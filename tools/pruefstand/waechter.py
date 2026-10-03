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
    r = pg.evaluate("""() => { const z = []; const w = KompassWaechter({ vorbelastet: true, onWechsel: x => z.push(x.prueft) }); w.einmessen();
      lauf(w, [].concat(...Array.from({length: 5}, () => drehung(1)))); return [z, w.prueft, w.urteil]; }""")
    pruef(r == [[True, False], False, "ok"], f"onWechsel meldet Beginn und Ende des Prüfens nach dem Einmessen ({r})")
    # Review 2, Befund 5: vorbelastet braucht 5 gute Abschnitte für die Rückkehr, so lange dauert auch das Prüfen
    r = pg.evaluate("""() => { const w = KompassWaechter({ vorbelastet: true }); w.einmessen(); const p = [];
      for (let i = 0; i < 5; i++) { lauf(w, drehung(1)); p.push(w.prueft); } return [p, w.urteil]; }""")
    pruef(r == [[True, True, True, True, False], "ok"], f"vorbelastet, eingemessen: prüft über alle 5 nötigen Abschnitte, dann ok ({r})")
    r = pg.evaluate("""() => { const w = KompassWaechter({ vorbelastet: true }); w.einmessen();
      lauf(w, [].concat(...Array.from({length: 3}, () => drehung(1)))); const p = w.prueft; lauf(w, drehung(0.4)); return [p, w.prueft, w.versuche, w.urteil]; }""")
    pruef(r == [True, False, 1, "unzuverlaessig"], f"vorbelastet, eingemessen: schlecht im vierten Abschnitt zählt einen Versuch ({r})")
    # Review 2, Befund 10: onWechsel nur, wenn sich Urteil, Versuche, Prüfen oder Vermerk ändern
    r = pg.evaluate("""() => { const z = []; const w = KompassWaechter({ onWechsel: x => z.push(x.urteil) });
      lauf(w, [].concat(...Array.from({length: 6}, () => [{ ms: 3200, rate: 0, wandern: 15 }]))); return [z, w.ergebnisse.join(",")]; }""")
    pruef(r == [["ok", "unzuverlaessig"], "schlecht,schlecht,schlecht,schlecht"], f"Stillstand mit lauter schlechten Ergebnissen: onWechsel nur beim Wechsel ({r})")
    r = pg.evaluate("""() => { const z = []; const w = KompassWaechter({ vorbelastet: true, onWechsel: x => z.push(x.prueft) }); w.einmessen(); w.einmessen(); return z; }""")
    pruef(r == [True], f"zweimal Einmessen ohne Wechsel: onWechsel einmal ({r})")

    print("Spiel")
    pg2 = b.new_page(viewport={"width": 390, "height": 844}); pg2.set_default_timeout(15000)
    pg2.on("pageerror", lambda e: err.append(str(e)))
    pg2.goto("http://127.0.0.1:8826/app.html?szenario=waechter-schlecht"); pg2.wait_for_function("typeof S !== 'undefined' && S.gps.on")
    pg2.evaluate("window.__orient('gut'); window.__motion(0)"); pg2.wait_for_timeout(600)
    z = pg2.evaluate("[S.gps.waechter && S.gps.waechter.urteil, S.gps.kompass, S.gps.waechterGrund]")
    pruef(z == ["unzuverlaessig", "kalibrieren", True], f"vorbelastet im Testmodus: Kompass gilt als ungenau ({z})")
    pg2.evaluate("S.team.state.testMode = false; window.__orient('gut')"); pg2.wait_for_timeout(400)
    pruef(pg2.evaluate("S.gps.kompass") == "an", "Testmodus aus: Wächter wirkt nicht")
    ios = lambda acc: "window.__zustellen({ alpha: 63, beta: 35, gamma: 0, absolute: false, webkitCompassHeading: 297, webkitCompassAccuracy: %s })" % acc
    zs = "[S.gps.kompass, S.gps.waechterGrund, S.gps.waechter.urteil]"
    # iPhone meldet schlechte Genauigkeit, Wächter ist vorbelastet: iOS gewinnt, der Wächter hebt nichts auf
    pg2.evaluate("S.team.state.testMode = true; " + ios(42)); pg2.wait_for_timeout(300)
    z = pg2.evaluate(zs)
    pruef(z == ["kalibrieren", False, "unzuverlaessig"], f"iPhone meldet schlechte Genauigkeit: Wächter hebt es nicht auf, Grund bleibt iOS ({z})")
    # Hysterese (20 bis 25 Grad) arbeitet auf dem Rohzustand: Wächter-Grund bleibt über mehrere Ereignisse stabil
    pg2.evaluate(ios(10)); pg2.wait_for_timeout(200)
    z = pg2.evaluate(zs)
    pruef(z == ["kalibrieren", True, "unzuverlaessig"], f"iPhone genau, Wächter ungenau: Grund Wächter ({z})")
    zz = []
    for _ in range(3):
        pg2.evaluate(ios(22)); pg2.wait_for_timeout(200); zz.append(pg2.evaluate(zs))
    pruef(all(x == ["kalibrieren", True, "unzuverlaessig"] for x in zz), f"Wächter-Grund flackert nicht in der Hysterese ({zz})")
    pg2.evaluate("S.team.state.testMode = false; " + ios(22)); pg2.wait_for_timeout(200)
    pruef(pg2.evaluate("[S.gps.kompass, S.gps.waechterGrund]") == ["an", False], "Testmodus aus: Zustand kehrt auf den Rohzustand zurück, nichts hängt")
    pg2.evaluate("S.team.state.testMode = true; " + ios(22)); pg2.wait_for_timeout(200)
    pg2.evaluate("S.gps.waechter = KompassWaechter({}); " + ios(22)); pg2.wait_for_timeout(200)
    pruef(pg2.evaluate("[S.gps.kompass, S.gps.waechterGrund]") == ["an", False], "Wächter-Urteil ok: Zustand kehrt auf den Rohzustand zurück")
    pg2.evaluate("S.gps.waechter.einmessen = (o => function () { window.__eingemessen = true; return o.call(this); })(S.gps.waechter.einmessen); kalStart(); kalEnde(true)")
    pruef(pg2.evaluate("window.__eingemessen === true"), "erfolgreiches Einmessen meldet sich beim Wächter")
    pruef(pg2.evaluate("JSON.parse(localStorage.getItem('sj.kompass') || '{}').vorbelastet") is not None, "Gedächtnis sj.kompass vorhanden")
    # Gesunder Kompass, Handy in verschiedener Neigung: vier Drehungen um die Senkrechte, je 2 s mit 60°/s und 1,5 s Ruhe.
    # Gyroskop und Kompass laufen über die Handler des Spiels (motionH, Orientierung). Android-Art: Schwerkraft zeigt nach
    # oben, oben = (0, y, z) im Handy; Drehung im Uhrzeigersinn = Drehrate -60 um oben. Prüft auch das Vorzeichen (M4).
    KIPP = """(z) => { const w = KompassWaechter({}); S.gps.waechter = w;
      let t = performance.now() + 1000, k = 100;
      for (let d = 0; d < 4; d++) for (let i = 0; i < 175; i++) {
        t += 20; const rate = i < 100 ? 60 : 0; k = (k + rate * 0.02) % 360;
        const zz = z + (i % 2 ? 0.05 : -0.05), y = Math.sqrt(Math.max(0, 1 - zz * zz));   // Hand wackelt ein wenig
        motionH({ accelerationIncludingGravity: { x: 0, y: 9.8 * y, z: 9.8 * zz }, rotationRate: { alpha: 0, beta: -rate * y, gamma: -rate * zz }, timeStamp: t });
        // beta passend zur Lage: oben = (0, sin beta, cos beta) im Handy, über 90° liegt der Bildschirm unten
        window.__zustellen({ alpha: (360 - k) % 360, beta: Math.atan2(y, zz) * 180 / Math.PI, gamma: 0, absolute: true, timeStamp: t });
      }
      return [w.urteil, w.ergebnisse.join(",")]; }"""
    for z, grad in ((0.8, 37), (0.5, 60)):
        r = pg2.evaluate(KIPP, z)
        pruef(r == ["ok", "gut,gut,gut,gut"], f"gesund, {grad}° gekippt: Urteil ok, vier gute Drehungen ({r})")
    for z, grad in ((-0.1, 84), (-0.3, 73)):
        r = pg2.evaluate(KIPP, z)
        pruef(r[0] != "unzuverlaessig" and "schlecht" not in r[1], f"gesund, über die Senkrechte gekippt (oben z {z}, {grad}°): kein schlecht ({r})")
    # Review 2, Befund 6: Bildschirm nach unten (beta 143°), gesund gedreht: das Wenden auf z > 0 rät "oben" falsch, also ruhen
    r = pg2.evaluate(KIPP, -0.8)
    pruef(r[0] != "unzuverlaessig" and "schlecht" not in r[1], f"gesund, Bildschirm nach unten (oben z -0.8, 143°): kein schlecht ({r})")
    # Review 2, Befund 4: hält das System selbst den Kompass für ungenau, misst der Wächter nicht (kein Urteil, kein Vermerk).
    # Kompass folgt nur zu 40 %; Gegenprobe mit genauem Kompass zeigt, dass die Folge sonst "unzuverlässig" ergäbe.
    SYSTEM = """([art, acc, np]) => { localStorage.removeItem('sj.kompass'); const w = waechterNeu(); S.gps.waechter = w; S.gps.nachPause = np;
      let t = performance.now() + 1000, k = 100;
      for (let d = 0; d < 4; d++) for (let i = 0; i < 175; i++) {
        t += 20; const rate = i < 100 ? 60 : 0; k = (k + 0.4 * rate * 0.02) % 360;
        motionH({ accelerationIncludingGravity: { x: 0, y: 0, z: 9.8 }, rotationRate: { alpha: 0, beta: 0, gamma: -rate }, timeStamp: t });
        window.__zustellen(art === "ios" ? { alpha: 0, beta: 0, gamma: 0, absolute: false, webkitCompassHeading: k, webkitCompassAccuracy: acc, timeStamp: t }
          : { alpha: (360 - k) % 360, beta: 0, gamma: 0, absolute: true, timeStamp: t });
      }
      S.gps.nachPause = false; S.gps.nachPauseOffen = false;
      return [w.urteil, w.ergebnisse.join(","), !!JSON.parse(localStorage.getItem('sj.kompass') || '{}').vorbelastet]; }"""
    r = pg2.evaluate(SYSTEM, ["ios", 60, False])
    pruef(r[0] != "unzuverlaessig" and "schlecht" not in r[1] and r[2] is False, f"iPhone meldet ±60°, schlechte Drehungen: kein Urteil, kein Vermerk ({r})")
    r = pg2.evaluate(SYSTEM, ["ios", 10, False])
    pruef(r[0] == "unzuverlaessig" and r[2] is True, f"Gegenprobe iPhone ±10°, schlechte Drehungen: unzuverlässig mit Vermerk ({r})")
    r = pg2.evaluate(SYSTEM, ["android", None, True])
    pruef(r[0] != "unzuverlaessig" and "schlecht" not in r[1] and r[2] is False, f"Android nach Pause, schlechte Drehungen: kein Urteil, kein Vermerk ({r})")
    r = pg2.evaluate(SYSTEM, ["android", None, False])
    pruef(r[0] == "unzuverlaessig" and r[2] is True, f"Gegenprobe Android ohne Pause: unzuverlässig mit Vermerk ({r})")
    # Review 2, Befund 9: Vermerk mit lokalem Datum; gestern verfallen, heute gültig; wiederholtes schlecht schreibt das Datum nicht neu
    r = pg2.evaluate("""() => { const tag = ms => new Date(ms).toDateString(), r = [];
      for (const d of [tag(Date.now() - 86400000), tag(Date.now())]) {
        localStorage.setItem('sj.kompass', JSON.stringify({ vorbelastet: true, versuche: 1, datum: d })); const w = waechterNeu(); r.push([w.vorbelastet, w.versuche]); }
      return r; }""")
    pruef(r == [[False, 0], [True, 1]], f"Vermerk von gestern verfallen, von heute gültig ({r})")
    pg2.add_script_tag(content=FOLGEN)
    r = pg2.evaluate("""() => { localStorage.removeItem('sj.kompass'); const w = waechterNeu(); S.gps.waechter = w;
      lauf(w, [].concat(...Array.from({length: 3}, () => drehung(0.4)))); const m1 = JSON.parse(localStorage.getItem('sj.kompass') || '{}');
      localStorage.setItem('sj.kompass', JSON.stringify(Object.assign({}, m1, { datum: 'Marke' })));
      lauf(w, [].concat(...Array.from({length: 3}, () => drehung(0.4)))); lauf(w, [].concat(...Array.from({length: 3}, () => [{ ms: 3200, rate: 0, wandern: 15 }])));
      const m2 = JSON.parse(localStorage.getItem('sj.kompass') || '{}');
      w.einmessen(); lauf(w, drehung(0.4)); const m3 = JSON.parse(localStorage.getItem('sj.kompass') || '{}');
      return [w.urteil, m1.vorbelastet, m1.datum === new Date().toDateString(), m2.datum, m3.versuche, m3.datum === new Date().toDateString()]; }""")
    pruef(r == ["unzuverlaessig", True, True, "Marke", 1, True], f"Datum entsteht mit dem Vermerk, bleibt bei weiterem schlecht, neu bei neuem Versuch ({r})")
    pg2.wait_for_timeout(200)
    # Chrome mit DeviceOrientationEvent.requestPermission, aber ohne DeviceMotionEvent.requestPermission: Gyroskop trotzdem an
    pg4 = b.new_page(viewport={"width": 390, "height": 844}); pg4.set_default_timeout(15000)
    pg4.on("pageerror", lambda e: err.append(str(e)))
    pg4.add_init_script("try { Object.defineProperty(DeviceMotionEvent, 'requestPermission', { value: undefined, configurable: true }); } catch (e) { }")
    pg4.goto("http://127.0.0.1:8826/app.html?szenario=waechter-schlecht"); pg4.wait_for_function("typeof S !== 'undefined' && S.gps.on")
    pg4.wait_for_timeout(400)
    z = pg4.evaluate("[typeof DeviceOrientationEvent.requestPermission, typeof DeviceMotionEvent.requestPermission, motionH !== null]")
    pruef(z == ["function", "undefined", True], f"Fingertipp ohne Bewegungs-Freigabe: Gyroskop hört trotzdem zu ({z})")
    pg4.close()
    # Review 2, Befund 3: iOS-Freigaben gespielt. Erst der Kompass, gleich danach (vor jedem await) die Bewegung;
    # lehnt die Bewegung ab oder wirft sie, bleibt der Kompass an.
    for art in ("granted", "abgelehnt", "wirft"):
        pg6 = b.new_page(viewport={"width": 390, "height": 844}); pg6.set_default_timeout(15000)
        pg6.on("pageerror", lambda e: err.append(str(e)))
        pg6.add_init_script("""window.__perm = []; const art = %r;
          Object.defineProperty(DeviceOrientationEvent, 'requestPermission', { configurable: true, value: () => { window.__perm.push('orient'); return Promise.resolve('granted'); } });
          Object.defineProperty(DeviceMotionEvent, 'requestPermission', { configurable: true, value: () => { window.__perm.push('motion');
            if (art === 'wirft') throw new Error('nein'); return art === 'abgelehnt' ? Promise.resolve('denied') : Promise.resolve('granted'); } });""" % art)
        pg6.goto("http://127.0.0.1:8826/app.html?szenario=waechter-schlecht"); pg6.wait_for_function("window.__fertig === true")
        z = pg6.evaluate("[window.__perm, S.gps.kompass, S.gps.heading != null, motionH !== null]")
        pruef(z[0] == ["orient", "motion"] and z[1] not in ("abgelehnt", "tippen", "fehlt") and z[2] and z[3] == (art == "granted"),
              f"iOS-Freigaben, Bewegung {art}: erst Kompass, dann Bewegung, Kompass an ({z})")
        pg6.close()
    print("Anzeige")
    pg2.goto("http://127.0.0.1:8826/app.html?szenario=waechter-schlecht"); pg2.wait_for_function("typeof S !== 'undefined' && S.gps.on")
    pg2.evaluate("window.__orient('gut'); window.__motion(0)"); pg2.wait_for_timeout(800)
    OHNE = "Geht ein paar Schritte, dann zeigt der Pfeil eure Laufrichtung. Die Entfernung stimmt immer."
    MIT = "Der Pfeil richtet sich nach eurer Laufrichtung."
    ANZ = """() => { const c = document.querySelector('.compass.gross'), kc = document.querySelector('#kchip');
      return [c.className, getComputedStyle(c.querySelector('#needle')).display, getComputedStyle(c.querySelector('.nq')).display,
        kc && !kc.hidden ? kc.textContent.trim() : null, richtung(), S.gps.gpsHeading]; }"""
    # Vorbelastet, noch keine Laufrichtung: der Kompass ist bekannt falsch, also keine Nadel, sondern das Fragezeichen
    z = pg2.evaluate(ANZ)
    pruef("unsicher" in z[0] and "lauf" not in z[0] and z[1] == "none" and z[2] != "none", f"ohne Laufrichtung: Ring gestrichelt mit Fragezeichen, keine Nadel ({z})")
    pruef(z[3] == "erst ein paar Schritte", f"ohne Laufrichtung: Plakette erst ein paar Schritte ({z[3]})")
    pruef(z[4] is None and z[5] is None, f"ohne Laufrichtung: richtung() liefert keinen Kompasswert ({z[4]})")
    t = pg2.inner_text("#app")
    pruef("Der Kompass dieses Handys zeigt gerade falsch" in t, "Hinweis des Wächters")
    pruef(OHNE in t and MIT not in t, "Hinweis ohne Laufrichtung: erst ein paar Schritte gehen")
    pruef(pg2.locator("[data-act=t-kal]").count() >= 1, "Knopf Kompass einmessen")
    pruef(pg2.locator(".msg [data-act=t-abgeben-frage]").count() == 1, "Teamleitung: Leitung abgeben im Hinweis")
    pg2.screenshot(path=str(HIER / "shots" / "waechter-ohne-richtung.png"), full_page=True)
    # Plakette: liveUpdate ersetzt sie nur, wenn sich etwas ändert; nach Standort aus und wieder an ist sie wieder da
    z = pg2.evaluate("""() => { const a = document.querySelector('#kchip'); liveUpdate(); liveUpdate(); const gleich = a === document.querySelector('#kchip');
      S.gps.on = false; liveUpdate(); const k = document.querySelector('#kchip'), aus = !k || k.hidden;
      S.gps.on = true; liveUpdate(); const k2 = document.querySelector('#kchip'); return [gleich, aus, k2 && !k2.hidden ? k2.textContent.trim() : null]; }""")
    pruef(z[0], f"Plakette bleibt stehen, solange sich nichts ändert ({z})")
    pruef(z[1] and z[2] == "erst ein paar Schritte", f"Plakette verschwindet ohne Standort und kommt wieder ({z})")
    # Ein paar Schritte (GPS über 6 m): Laufrichtung da. Der Hinweis entsteht nur in render(), er muss trotzdem nachziehen.
    pg2.evaluate("window.__gps(50.10520, 14.42290, 8)"); pg2.wait_for_timeout(400)
    z = pg2.evaluate(ANZ)
    pruef("lauf" in z[0] and "unsicher" not in z[0] and z[1] != "none" and z[3] == "nach Laufrichtung" and z[5] is not None and z[4] == z[5],
          f"mit Laufrichtung: Nadel gestrichelt nach Laufrichtung, Plakette nach Laufrichtung ({z})")
    t = pg2.inner_text("#app")
    pruef(MIT in t and OHNE not in t, "Hinweis mit Laufrichtung, ohne eigenes Neuzeichnen")
    # alle drei Hinweise richten sich nach der Lage
    r = pg2.evaluate("""() => { const g = S.gps, alt = [g.waechter, g.gpsHeading], r = [];
      for (const v of [0, 1, 2]) for (const gh of [null, 40]) {
        g.waechter = KompassWaechter({ vorbelastet: true, versuche: v }); g.gpsHeading = gh; g.gpsHeadingAt = Date.now(); const h = waechterHinweisHTML(S.team.state, false);
        r.push([v, gh, h.includes(%r), /Der Pfeil (richtet sich nach eurer|folgt solange eurer|bleibt bei der) Laufrichtung/.test(h)]); }
      [g.waechter, g.gpsHeading] = alt; return r; }""" % OHNE)
    pruef(all(x[2] == (x[1] is None) and x[3] == (x[1] is not None) for x in r), f"Hinweis nach Versuchen 0, 1, 2: Satz je nach Laufrichtung ({r})")
    pg2.screenshot(path=str(HIER / "shots" / "waechter-schlecht.png"), full_page=True)
    pg2.click(".msg [data-act=t-abgeben-frage]"); pg2.wait_for_timeout(900)
    pruef(pg2.locator("#tneu").is_visible() and pg2.locator("#tneu").evaluate("e => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight }"), "Leitung abgeben im Hinweis: Fenster offen und im Blick")
    # Auswahl treffen, dann meldet der Wächter "schlecht" (Kompass wandert im Stillstand): Auswahl und Knopf bleiben
    name = pg2.evaluate("[...document.querySelectorAll('#tneu option')].map(o => o.textContent)[1]")
    pg2.select_option("#tneu", name); pg2.wait_for_timeout(100)
    r = pg2.evaluate("""() => { window.__tneu = document.querySelector('#tneu'); let t = performance.now() + 1000, a = 63;
      for (let i = 0; i < 200; i++) { t += 20; a = (a + 0.3) % 360;
        motionH({ accelerationIncludingGravity: { x: 0, y: 0, z: 9.8 }, rotationRate: { alpha: 0, beta: 0, gamma: 0 }, timeStamp: t });
        window.__zustellen({ alpha: a, beta: 35, gamma: 0, absolute: true, timeStamp: t }); }
      return S.gps.waechter.ergebnisse; }""")
    pg2.wait_for_timeout(300)
    z = pg2.evaluate("[document.querySelector('#tneu').value, document.querySelector('#tabgeben').disabled, document.querySelector('#tneu') === window.__tneu]")
    pruef("schlecht" in r and z == [name, False, True], f"Wächter meldet schlecht: kein Neuzeichnen, Auswahl bleibt, Übergeben bleibt aktiv ({r}, {z})")
    pg2.evaluate("render()"); pg2.wait_for_timeout(100)
    z = pg2.evaluate("[document.querySelector('#tneu').value, document.querySelector('#tabgeben').disabled]")
    pruef(z == [name, False], f"Neuzeichnen behält die Auswahl ({z})")
    pg2.evaluate("S.team.abgeben = false; S.team.state.team.members = [S.team.state.team.leaderName]; render()"); pg2.wait_for_timeout(200)
    pruef(pg2.locator(".msg [data-act=t-abgeben-frage]").count() == 0 and "Oder gebt die Leitung" not in pg2.inner_text("#app"), "allein im Team: kein Knopf, kein Satz")
    pg2.goto("http://127.0.0.1:8826/app.html?szenario=waechter-versuche-2"); pg2.wait_for_function("typeof S !== 'undefined' && S.gps.on")
    pg2.evaluate("window.__orient('gut'); window.__motion(0)"); pg2.wait_for_timeout(800)
    t = pg2.inner_text("#app")
    pruef("Einmessen hilft bei diesem Handy nicht" in t, "nach zwei Versuchen: hilft nicht")
    pruef(pg2.locator(".msg .btn[data-act=t-kal]").count() == 0 and pg2.locator(".msg .link[data-act=t-kal]").count() == 1, "kein großer Knopf, nur Link")
    pg2.evaluate("S.team.state.testMode = false; window.__orient('gut')"); pg2.wait_for_timeout(400)
    pruef("lauf" not in (pg2.locator(".compass.gross").get_attribute("class") or "") and pg2.inner_text("#kchip").strip() == "Kompass", "Testmodus aus: volle Nadel, Plakette Kompass")
    # Übungskompass vor dem Start: dieselbe Regel. iPhone ungenau, noch keine Laufrichtung: Fragezeichen statt Nadel
    pg2.goto("http://127.0.0.1:8826/app.html?szenario=leitung-startklar-kompass"); pg2.wait_for_function("typeof S !== 'undefined' && S.gps.on")
    pg2.wait_for_timeout(1500)   # die Schritte des Szenarios (Kompass gut) erst durchlaufen lassen
    pg2.evaluate("window.__orient('ungenau')"); pg2.wait_for_timeout(400)
    UEB = "() => { const c = document.querySelector('#needle').closest('.compass'); return [c.className, richtung()]; }"
    z = pg2.evaluate(UEB)
    pruef("unsicher" in z[0] and "lauf" not in z[0] and z[1] is None, f"Übungskompass, Kompass ungenau ohne Laufrichtung: Fragezeichen ({z})")
    z = pg2.evaluate("() => { S.gps.gpsHeading = 40; S.gps.gpsHeadingAt = Date.now(); render(); return (" + UEB + ")(); }")
    pruef("lauf" in z[0] and "unsicher" not in z[0] and z[1] == 40, f"Übungskompass mit Laufrichtung: schon render() zeichnet gestrichelt ({z})")
    # Review 2, Befunde 1 und 2: Laufrichtung vom Ankerpunkt, immer mitgerechnet, nach 30 s verfallen. Eigene Seite mit
    # Playwright-Uhr, damit die 30 s nicht echt gewartet werden müssen.
    ctx5 = b.new_context(viewport={"width": 390, "height": 844}); pg5 = ctx5.new_page(); pg5.set_default_timeout(15000)
    pg5.on("pageerror", lambda e: err.append(str(e)))
    pg5.clock.install()
    pg5.goto("http://127.0.0.1:8826/app.html?szenario=waechter-schlecht"); pg5.wait_for_function("window.__fertig === true")
    M = 1 / 111320   # Grad Breite je Meter
    SPUR = """([punkte, acc]) => { for (const [lat, lng] of punkte) window.__gps(lat, lng, acc); return [S.gps.gpsHeading, richtung()]; }"""
    LAT, LNG = 50.10495, 14.42290
    z = pg5.evaluate(SPUR, [[[LAT + (3 if i % 2 else -3) * M, LNG] for i in range(12)], 5])
    pruef(z == [None, None], f"Zittern ±3 m um einen Punkt: keine Laufrichtung ({z})")
    z = pg5.evaluate(SPUR, [[[LAT + 10 * M, LNG]], 20])
    pruef(z == [None, None], f"10 m Sprung bei ±20 m Genauigkeit: keine Laufrichtung ({z})")
    z = pg5.evaluate(SPUR, [[[LAT + 1.4 * i * M, LNG] for i in range(1, 6)], 5])
    pruef(z == [None, None], f"1,4 m je Fix, 7 m vom Anker: noch keine Laufrichtung ({z})")
    z = pg5.evaluate(SPUR, [[[LAT + 1.4 * i * M, LNG] for i in range(6, 8)], 5])
    pruef(z[0] is not None and min(z[0], 360 - z[0]) < 2 and z[1] == z[0], f"1,4 m je Fix nach Norden, über 8 m: Laufrichtung Norden ({z})")
    pg5.wait_for_timeout(300)
    pruef("lauf" in (pg5.locator(".compass.gross").get_attribute("class") or ""), "Laufrichtung da: Nadel gestrichelt")
    # Kompass gilt als gut (Testmodus aus, Wächter wirkt nicht): die Laufrichtung läuft trotzdem mit. Der Anker liegt bei 8,4 m.
    z = pg5.evaluate("""() => { S.team.state.testMode = false; window.__orient('gut'); const k = S.gps.kompass, lat = 50.10495 + 8.4 / 111320, m = 1 / (111320 * Math.cos(lat * Math.PI / 180));
      for (let i = 1; i <= 7; i++) window.__gps(lat, 14.42290 + 1.4 * i * m, 5);
      const r = [k, S.gps.gpsHeading]; S.team.state.testMode = true; window.__orient('gut'); return r; }""")
    pruef(z[0] == "an" and z[1] is not None and abs(z[1] - 90) < 2, f"Kompass an: Laufrichtung wird trotzdem mitgerechnet, jetzt Osten ({z})")
    pg5.wait_for_timeout(300)
    # 31 s ohne neue Laufrichtung: sie verfällt, der Kompass zeigt wieder das Fragezeichen, der Hinweis sagt "erst ein paar Schritte".
    # Im Funkloch, damit nicht die Abfrage alle 10 s das Neuzeichnen übernimmt: das muss die Laufrichtung selbst auslösen.
    pg5.evaluate("window.__funkloch = true"); pg5.clock.fast_forward(31000); pg5.wait_for_timeout(400)
    z = pg5.evaluate(ANZ)
    pruef("unsicher" in z[0] and "lauf" not in z[0] and z[1] == "none" and z[3] == "erst ein paar Schritte" and z[4] is None,
          f"Laufrichtung älter als 30 s: Fragezeichen, Plakette erst ein paar Schritte ({z})")
    t = pg5.inner_text("#app")
    pruef(OHNE in t and MIT not in t and "Erst ein paar Schritte gehen" in t, "Laufrichtung verfallen: Hinweis und Text neu gezeichnet")
    ctx5.close()
    print("Spielleitung")
    pg2.goto("http://127.0.0.1:8826/app.html?szenario=waechter-schlecht"); pg2.wait_for_function("typeof S !== 'undefined' && S.gps.on")
    pg2.evaluate("window.__orient('gut'); window.__motion(0)"); pg2.wait_for_timeout(600)
    pg2.evaluate("window.__gps(52.4701, 13.4621, 8)"); pg2.wait_for_timeout(800)
    z = pg2.evaluate("[window.__KOMPASS, S.gps.waechter.urteil]")
    pruef(z[0] == "unzuverlaessig" and z[1] == "unzuverlaessig", f"Handy meldet das Urteil mit der Position ({z})")
    pg2.evaluate("S.team.state.testMode = false; window.__KOMPASS = 'nichts'; window.__gps(52.4712, 13.4632, 8)"); pg2.wait_for_timeout(800)
    pruef(pg2.evaluate("window.__KOMPASS") == "unzuverlaessig", "Urteil geht auch außerhalb des Testmodus mit")
    # Datenbank noch ohne Nachtrag 30: report_position kennt p_kompass nicht. Die Position muss trotzdem ankommen.
    pg2.evaluate("window.__ALTE_DB = true; window.__POSITION = null; window.__gps(52.4730, 13.4660, 8)"); pg2.wait_for_timeout(800)
    z = pg2.evaluate("window.__POSITION")
    pruef(z == [52.473, 13.466], f"alte Datenbank lehnt p_kompass ab: Position kommt ohne an ({z})")
    pg2.evaluate("window.__ALTE_DB = false")
    # Review 2, Befund 7: Netzfehler ist kein Grund für einen Aufruf ohne p_kompass; das Urteil geht beim nächsten Melden mit
    pg2.evaluate("""() => { window.__RV = []; const f = window.fetch; window.fetch = function (u, i) {
      if (String(u).includes('/rpc/report_position')) window.__RV.push(JSON.parse(i.body)); return f.apply(this, arguments); }; }""")
    pg2.evaluate("window.__funkloch = true; S.gps.waechter = KompassWaechter({}); window.__gps(52.4760, 13.4700, 8)"); pg2.wait_for_timeout(800)
    z = pg2.evaluate("window.__RV.map(a => 'p_kompass' in a)")
    pruef(z == [True], f"Netzfehler: kein zweiter Aufruf ohne p_kompass ({z})")
    pg2.evaluate("window.__funkloch = false; window.__RV = []; window.__KOMPASS = 'nichts'; window.__gps(52.47605, 13.4700, 8)"); pg2.wait_for_timeout(800)
    z = pg2.evaluate("[window.__RV.length, window.__KOMPASS]")
    pruef(z == [1, None], f"nach dem Netzfehler: nächstes Melden schickt das neue Urteil ({z})")
    pg3 = b.new_page(viewport={"width": 1180, "height": 820}); pg3.set_default_timeout(15000)
    pg3.on("pageerror", lambda e: err.append(str(e)))
    pg3.goto("http://127.0.0.1:8826/app.html?szenario=admin-teststation"); pg3.wait_for_selector(".tabs")
    pg3.click("[data-act=a-tab][data-tab=teams]"); pg3.wait_for_timeout(500)
    zeile = pg3.locator("text=Kompass falsch, Pfeil nach Laufrichtung")
    pruef(zeile.count() == 1, f"Reiter Teams: genau ein Team mit Hinweis ({zeile.count()})")
    pruef(pg3.locator(".card, tr, li", has=pg3.locator("text=Fuchs")).filter(has=zeile).count() >= 1, "der Hinweis steht bei Fuchs")
    # Testmodus aus: der Pfeil des Teams folgt weiter dem Kompass, also nur der Vermerk, ohne "Pfeil nach Laufrichtung"
    VERMERK = "[...document.querySelectorAll('.chip')].map(c => c.textContent.trim()).filter(x => x.startsWith('Kompass falsch'))"
    z = pg3.evaluate("() => { S.admin.state.testMode = false; render(); return " + VERMERK + "; }")
    pruef(z == ["Kompass falsch"], f"Testmodus aus: Vermerk nur Kompass falsch ({z})")
    z = pg3.evaluate("() => { S.admin.state.testMode = true; render(); return " + VERMERK + "; }")
    pruef(z == ["Kompass falsch, Pfeil nach Laufrichtung"], f"Testmodus an: Kompass falsch, Pfeil nach Laufrichtung ({z})")
    # Review 2, Befund 8: der Vermerk gilt nur zu einer Position, die jünger als 3 min ist
    ALT = """(min) => { const t = S.admin.state.teams.find(x => x.name === 'Fuchs'); t.position.updatedAt = new Date(Date.now() - min * 60000).toISOString();
      render(); return %s; }""" % VERMERK
    z = [pg3.evaluate(ALT, 2), pg3.evaluate(ALT, 4)]
    pruef(z == [["Kompass falsch, Pfeil nach Laufrichtung"], []], f"Position 2 min alt: Vermerk, 4 min alt: kein Vermerk ({z})")
    pruef(not err, f"keine Skriptfehler {err[:2]}")
    b.close()
print("FEHLER: " + str(len(fehler)) if fehler else "OK")
sys.exit(1 if fehler else 0)
