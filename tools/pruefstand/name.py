#!/usr/bin/env python3
"""
Stationsname verschlüsselt (Nachtrag 26) im Prüfstand durchspielen, ohne Datenbank.

    python tools/pruefstand/name.py

Prüft auf dem Handy der Teamleitung: fern ist alles verschlüsselt und der
Ortshinweis fehlt, beim Näherkommen rasten Buchstaben ein, beim Weggehen bleibt
alles stehen (Schloss), nah ist der Name lesbar und der Hinweis da; die Zeile
ändert dabei ihre Höhe nicht. Dazu Mitglied, Station ohne Kreise und das
Bearbeiten der Station mit Karte bei der Spielleitung. Fotos in
shots/name-*.png. Im Vordergrund mit Timeout aufrufen. Am Ende OK oder die
Zahl der Fehler.
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

shoot.bauen()
from playwright.sync_api import sync_playwright  # noqa: E402


class Leise(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8811), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
SHOTS = str(HIER / "shots") + "/name-"
(HIER / "shots").mkdir(exist_ok=True)
fehler = []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


# Station 2 (Rudolfstollen) liegt bei 50.104441, 14.419553; ein Breitengrad-Hundertstel sind 1113 m
STATION = (50.104441, 14.419553)
def ort(m):   # Punkt m Meter nördlich der Station
    return STATION[0] + m / 111320, STATION[1]

Z = """() => { const g = document.querySelector("#geheim");
  return { da: !!g, fest: g ? g.querySelectorAll("i.fest").length : null, offen: g ? g.querySelectorAll("i[data-i]").length : null,
    text: g ? [...g.querySelectorAll("i.fest")].map(i => i.textContent).join("") : null, hoehe: g ? Math.round(g.getBoundingClientRect().height) : null,
    h2: document.querySelector("#app h2")?.textContent, hinweis: !!document.querySelector("#app .hint"), seite: document.querySelector("#app").innerText }; }"""

with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)
    c = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    pg = c.new_page(); pg.set_default_timeout(15000); err = []
    pg.on("pageerror", lambda e: err.append(str(e)))
    url = lambda s: f"http://127.0.0.1:8811/app.html?szenario={s}"
    def gehe(m):
        la, lo = ort(m); pg.evaluate("([a, b]) => window.__gps(a, b, 8)", [la, lo]); pg.wait_for_timeout(350)

    print("Teamleitung, weit weg (Kreise 200 und 100 m, Standort 245 m entfernt)")
    pg.goto(url("name-geheim-fern")); pg.wait_for_function("typeof S !== 'undefined' && S.gps.pos", timeout=15000); pg.wait_for_timeout(600)
    z = pg.evaluate(Z)
    pruef(z["da"] and z["fest"] == 0 and z["offen"] == 13, f"alles verschlüsselt: {z['fest']} fest, {z['offen']} flimmern")
    pruef("Rudolfstollen" not in z["seite"] and not z["hinweis"], "Name und Ortshinweis stehen nirgends auf der Seite")
    a1 = pg.inner_text("#geheim"); pg.wait_for_timeout(400); a2 = pg.inner_text("#geheim")
    pruef(a1 != a2, f"die Zeichen wechseln: {a1!r} -> {a2!r}")
    hoehe0 = z["hoehe"]; pg.screenshot(path=SHOTS + "1-fern.png")

    print("Näherkommen")
    gehe(150); z = pg.evaluate(Z); n150 = z["fest"]
    pruef(0 < n150 < 13 and z["hoehe"] == hoehe0, f"150 m: {n150} von 13 fest, Zeile gleich hoch ({z['hoehe']} px)")
    pg.screenshot(path=SHOTS + "2-halb.png")
    gehe(120); z = pg.evaluate(Z); n120 = z["fest"]
    pruef(n120 > n150, f"120 m: {n120} fest")
    print("Wieder weggehen: Schloss")
    gehe(400); z = pg.evaluate(Z)
    pruef(z["fest"] == n120, f"400 m entfernt: weiter {z['fest']} fest")
    pruef(pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('sj.geheim.')).map(k => localStorage.getItem(k))") == [str(n120)], "der Stand liegt im Handy")
    print("Ganz heran")
    gehe(90); pg.wait_for_timeout(400); z = pg.evaluate(Z)
    pruef(not z["da"] and z["h2"] == "Rudolfstollen" and z["hinweis"], f"90 m: Name lesbar ({z['h2']}), Ortshinweis da")
    pg.screenshot(path=SHOTS + "3-klar.png")
    gehe(400); z = pg.evaluate(Z); pruef(not z["da"] and z["h2"] == "Rudolfstollen", "wieder weg: bleibt lesbar")

    print("Ohne Standort, Mitglied, Station ohne Kreise")
    pg.goto(url("name-geheim-ohne-gps")); pg.wait_for_selector("#geheim")
    pruef("Gebt den Standort frei" in pg.inner_text("#app"), "ohne Standort: Aufforderung zur Freigabe")
    pg.goto(url("name-geheim-mitglied")); pg.wait_for_selector("#geheim")
    pruef("Rudolfstollen" not in pg.inner_text("#app"), "Mitglied: Name verschlüsselt")
    pg.goto(url("leitung-unterwegs-standort")); pg.wait_for_function("S.gps.pos"); pg.wait_for_timeout(300)
    z = pg.evaluate(Z); pruef(not z["da"] and z["h2"] == "Rudolfstollen" and z["hinweis"], "Station ohne Kreise: alles wie bisher")

    print("Testmodus: die Annäherung wird vorgespielt")
    pg.goto(url("name-geheim-test")); pg.wait_for_selector("#geheim"); pg.wait_for_timeout(1200)
    z = pg.evaluate(Z); pruef(z["fest"] == 0 and "Testmodus" in z["seite"] and "Rudolfstollen" not in z["seite"], "zuerst ganz verschlüsselt, mit Erklärung")
    pg.wait_for_timeout(5000); z = pg.evaluate(Z); pruef(z["da"] and 0 < z["fest"] < 13, f"nach 6 s: {z['fest']} von 13 Buchstaben, ohne Standort")
    pg.wait_for_function("!document.querySelector('#geheim')", timeout=12000); z = pg.evaluate(Z)
    pruef(z["h2"] == "Rudolfstollen" and z["hinweis"], "nach rund 10 s: Name lesbar, Ortshinweis da")
    pg.click("[data-act=t-check]"); pg.wait_for_selector("#tans"); pg.fill("#tans", "egal"); pg.click("[data-act=t-answer]")
    pg.wait_for_selector("#geheim"); z = pg.evaluate(Z)
    pruef(z["fest"] == 0 and "Wasserturm" not in z["seite"], "nächste Station nach dem Lösen: wieder ganz verschlüsselt")
    pg.wait_for_function("!document.querySelector('#geheim')", timeout=15000)
    pruef(pg.evaluate(Z)["h2"] == "Wasserturm Letná", "und löst sich wieder von selbst auf")

    print("Spielleitung: Station bearbeiten mit Karte")
    pg.set_viewport_size({"width": 900, "height": 1000})
    pg.goto(url("admin-station-karte")); pg.wait_for_selector("#emap .leaflet-marker-icon", timeout=25000); pg.wait_for_timeout(1200)
    w = pg.evaluate("({b: ekarte.kreise.beginn.getRadius(), k: ekarte.kreise.klar.getRadius(), r: ekarte.kreise.radius.getRadius(), aus: S.admin.karte.aus, etappe: document.querySelector('#e-etappe').textContent, wo: document.querySelector('#e-wo').textContent})")
    pruef((w["b"], w["k"], w["r"]) == (340, 170, 50) and not w["aus"], f"Kreise aus den Werten der Station: {w['b']}, {w['k']}, {w['r']} m")
    pruef("Etappe" in w["etappe"] and "Probe-Team" in w["wo"], w["etappe"][:80])
    pg.fill("#e-beginn", "300"); pg.wait_for_timeout(200)
    pruef(pg.evaluate("ekarte.kreise.beginn.getRadius()") == 300, "getippte Meter ändern den Kreis")
    # am Griff ziehen: von der Station weg
    griff = pg.locator("#emap .egriff").nth(1); box = griff.bounding_box()
    pg.mouse.move(box["x"] + 9, box["y"] + 9); pg.mouse.down(); pg.mouse.move(box["x"] + 40, box["y"] - 30, steps=6); pg.mouse.up(); pg.wait_for_timeout(300)
    k2 = pg.evaluate("parseInt(document.querySelector('#e-klar').value, 10)")
    pruef(k2 != 170 and 55 <= k2 < 300, f"am Griff ziehen schreibt ins Feld: klar {k2} m")
    pg.locator("#emap").scroll_into_view_if_needed(); pg.screenshot(path=SHOTS + "4-station-karte.png", full_page=True)
    pg.fill("#e-riddle", "ungespeichert getippt")
    pg.click("[data-act=a-geheim-aus]"); pg.wait_for_selector("#emap .leaflet-marker-icon"); pg.wait_for_timeout(500)
    pruef(pg.evaluate("S.admin.karte.aus && document.querySelector('#e-beginn').disabled") and "sofort lesbar" in pg.inner_text("#e-etappe"), "Nicht verschlüsseln: Felder gesperrt, Kreise weg")
    pruef(pg.input_value("#e-riddle") == "ungespeichert getippt", "der Schalter lässt ungespeicherte Eingaben stehen")
    pg.click("[data-act=a-save]"); pg.wait_for_function("window.__GESPEICHERT")
    g = pg.evaluate("window.__GESPEICHERT"); pruef(g["p_reveal_start"] is None and g["p_reveal_clear"] is None, "Speichern ohne Verschlüsseln schickt leere Werte")
    pg.click("[data-act=a-edit][data-id=s3]"); pg.wait_for_selector("#emap .leaflet-marker-icon"); pg.wait_for_timeout(500)
    pg.click("[data-act=a-geheim-aus]"); pg.wait_for_selector("#emap .leaflet-marker-icon"); pg.wait_for_timeout(500)
    v = pg.evaluate("[document.querySelector('#e-beginn').value, document.querySelector('#e-klar').value]")
    pruef(int(v[0]) > int(v[1]) > 50, f"Einschalten ohne Werte nimmt den Vorschlag aus der Etappe: {v}")
    pg.evaluate("window.__GESPEICHERT = null"); pg.click("[data-act=a-save]"); pg.wait_for_function("window.__GESPEICHERT")
    g = pg.evaluate("window.__GESPEICHERT"); pruef(g["p_reveal_start"] == int(v[0]) and g["p_reveal_clear"] == int(v[1]), f"Speichern schickt {g['p_reveal_start']} und {g['p_reveal_clear']}")
    pruef("Name verschlüsselt" in pg.inner_text("#app"), "die Stationsliste nennt die Einstellung")
    pruef(not err, f"keine Skriptfehler {err[:2]}")
    b.close()
srv.shutdown()
print("FEHLER: " + str(len(fehler)) if fehler else "OK")
sys.exit(1 if fehler else 0)
