#!/usr/bin/env python3
"""
Geräte-Test am Laptop durchlaufen lassen, mit gespielten Sensoren.

    python tools/pruefstand/geraetetest.py

Startet einen Server auf Port 8792 im Repo, öffnet geraete-test.html mit
Playwright (Kanal chrome), spielt Standort und Ausrichtung ein und fängt
device_test_save und device_test_echo ab, damit nichts in der Datenbank
landet. Alles andere (public_state, unpkg, OSM, Realtime) geht ins echte Netz.

Prüft: jeder selbstlaufende Baustein liefert ein Ergebnis, der gespeicherte
Lauf hat die erwartete Form, ein Hand-Schritt ergänzt denselben Lauf.
Im Vordergrund mit Timeout aufrufen. Am Ende steht OK oder FEHLER.
"""
import datetime
import functools
import http.server
import json
import pathlib
import sys
import threading

from playwright.sync_api import sync_playwright

for strom in (sys.stdout, sys.stderr):
    try:
        strom.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
PORT = 8792
SELBST = ["umgebung", "speicher", "server", "uhr", "standort", "kompass", "neigung",
          "wachhalten", "karte", "schrift", "teilen", "live", "offline"]

# Dreht das gespielte Handy stetig im Kreis, wie ein Android-Gerät es melden würde
SENSOR = """
let a = 0;
setInterval(() => {
  a = (a + 7) % 360;
  window.dispatchEvent(new DeviceOrientationEvent("deviceorientationabsolute", { alpha: a, beta: 40 + a % 5, gamma: 3, absolute: true }));
  window.dispatchEvent(new DeviceOrientationEvent("deviceorientation", { alpha: a, beta: 40 + a % 5, gamma: 3, absolute: false }));
}, 40);
"""


class Leise(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main() -> int:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(REPO)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    gespeichert, fehler = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            ctx = browser.new_context(viewport={"width": 390, "height": 844}, geolocation={"latitude": 50.0875, "longitude": 14.4213, "accuracy": 12},
                                      permissions=["geolocation"], locale="de-DE")
            page = ctx.new_page()
            page.set_default_timeout(90000)
            page.on("pageerror", lambda e: fehler.append(f"Skriptfehler: {e}"))

            def speichern(route):
                gespeichert.append(json.loads(route.request.post_data))
                route.fulfill(json={"ok": True, "serverTime": "2026-09-30T12:00:00Z"})

            def echo(route):
                zeit = datetime.datetime.now(datetime.timezone.utc).isoformat()
                route.fulfill(json={"bytes": 0, "serverTime": zeit})

            page.route("**/rest/v1/rpc/device_test_save", speichern)
            page.route("**/rest/v1/rpc/device_test_echo", echo)
            page.add_init_script(SENSOR)
            page.goto(f"http://127.0.0.1:{PORT}/geraete-test.html")
            page.click("#start")
            page.wait_for_selector("#speicher.ok")

            if not gespeichert:
                fehler.append("device_test_save wurde nie aufgerufen")
            else:
                lauf = gespeichert[-1]
                pl = lauf["p_payload"]
                if len(lauf["p_key"]) != 12:
                    fehler.append(f"Schlüssel hat {len(lauf['p_key'])} Zeichen")
                for feld in ("suite", "label", "begonnen", "beendet", "ua", "bilanz", "tests"):
                    if feld not in pl:
                        fehler.append(f"Im Lauf fehlt {feld}")
                for i in SELBST:
                    t = pl.get("tests", {}).get(i)
                    if not t:
                        fehler.append(f"{i}: kein Ergebnis")
                    elif t["art"] not in ("ok", "warn", "err"):
                        fehler.append(f"{i}: unbekannte Art {t['art']}")
                    else:
                        print(f"  {i:12} {t['art']:5} {t['wert']}")
                    if t and "Fehler im Test" in t.get("mess", {}):
                        fehler.append(f"{i}: abgestürzt mit {t['mess']['Fehler im Test']}")
                if len(json.dumps(pl)) > 60000:
                    fehler.append("Der Lauf ist größer als 60 KB")

            # Ein Hand-Schritt: Kompass drehen, der gespielte Sensor dreht ohnehin
            vorher = len(gespeichert)
            page.click("#hand li:nth-child(1) [data-was=los]")
            page.wait_for_function("document.querySelector('#hand li').className !== 'laeuft'")
            page.wait_for_timeout(500)
            if len(gespeichert) <= vorher:
                fehler.append("Nach dem Hand-Schritt wurde nicht erneut gespeichert")
            else:
                t = gespeichert[-1]["p_payload"]["tests"].get("kompass-drehen")
                print(f"  {'kompass-drehen':12} {t['art'] if t else '-':5} {t['wert'] if t else ''}")
                if not t or t["art"] != "ok":
                    fehler.append("kompass-drehen ist mit gespieltem Sensor nicht ok")
                if gespeichert[-1]["p_key"] != gespeichert[0]["p_key"]:
                    fehler.append("Der Hand-Schritt hat einen anderen Schlüssel benutzt")
            page.click("#neu li:nth-child(2) [data-was=weg]")   # Vibration überspringen

            shots = pathlib.Path(__file__).resolve().parent / "shots"
            shots.mkdir(exist_ok=True)
            page.screenshot(path=str(shots / "geraetetest.png"), full_page=True)
            browser.close()
    finally:
        server.shutdown()

    if fehler:
        print("FEHLER")
        for f in fehler:
            print("  -", f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
