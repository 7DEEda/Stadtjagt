"""Spielleitung-Durchsicht (02.11.2026): Teamliste vor der Karte, Knöpfe in der Teamliste, Reiter in zwei Reihen,
Gewicht der Löschknöpfe, Teilnehmende einspaltig, Zeitachse ohne Nummern, Schalter im Kopf, „Spiel starten“ nur
einmal. Port 8876, bei 390, 768 und 1280 px Breite.

Im Wegwerf-Container aufrufen (Regel vom 31.10.2026). Am Ende steht OK oder FEHLT.
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


PORT = 8876
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
APP = f"http://127.0.0.1:{PORT}/app.html?szenario="
fehler, err = [], []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def neu(b, szenario, breite=390, hoehe=844):
    pg = b.new_page(viewport={"width": breite, "height": hoehe})
    pg.set_default_timeout(15000)
    pg.route("**/vendor/leaflet-1.9.4/**", lambda r: r.abort())
    pg.on("pageerror", lambda e: err.append(f"{szenario}: {e}"))
    pg.goto(APP + szenario)
    pg.wait_for_function("window.__fertig === true", timeout=30000)
    return pg


def reiter(pg, k):
    pg.click(f"[data-act=a-tab][data-tab={k}]")
    pg.wait_for_timeout(300)


OBEN = "s => Math.round(document.querySelector(s).getBoundingClientRect().top)"
REIHEN = "() => new Set([...document.querySelectorAll('.tabs button')].map(b => Math.round(b.getBoundingClientRect().top))).size"

with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)

    print("1 Teamliste vor der Karte, 2 Knöpfe, 4 Reiter, 8 Kopf (390 px)")
    pg = neu(b, "admin-teams")
    pruef(pg.evaluate("document.querySelector('.lv').firstElementChild.id") == "teamfeld", "Teamliste steht im Quelltext zuerst")
    pruef(pg.evaluate(OBEN, "#teamfeld") < pg.evaluate(OBEN, "#map"), "Handy: Liste über der Karte")
    z = pg.evaluate("""() => [...document.querySelectorAll('#teamfeld .row')].filter(r => r.querySelector('[data-act=a-danger]')).map(r => {
      const k = r.querySelector('[data-act=a-danger]'), cs = getComputedStyle(k);
      return [/p-(fehler|warn)/.test(r.className), k.classList.contains('leise'), k.classList.contains('alt'), cs.backgroundColor, Math.round(k.getBoundingClientRect().height)]; })""")
    prob = [x for x in z if x[0]]
    ruhig = [x for x in z if not x[0]]
    pruef(prob and all(not x[1] and not x[2] and x[3] not in ("rgba(0, 0, 0, 0)", "transparent") for x in prob), f"Braucht dich: gefüllte Knöpfe ({prob})")
    pruef(ruhig and all(x[1] and x[3] in ("rgba(0, 0, 0, 0)", "transparent") for x in ruhig), f"Alle anderen: Textknöpfe ({ruhig[:3]})")
    pruef(all(x[4] >= 44 for x in z), f"alle Knöpfe mindestens 44 px hoch ({[x[4] for x in z]})")
    pruef(pg.evaluate(REIHEN) == 2, f"Reiter in zwei Reihen ({pg.evaluate(REIHEN)})")
    pruef(pg.evaluate("document.documentElement.scrollWidth") <= 390, "nichts ragt seitlich heraus")
    z = pg.evaluate("""() => { const t = document.querySelector('.akopf .thema').getBoundingClientRect(), h = document.querySelector('.akopf h1').getBoundingClientRect(),
      k = document.querySelector('.akopf [data-act=a-finish]').getBoundingClientRect(); return [t.top < h.bottom, t.left > h.right, k.top > t.bottom]; }""")
    pruef(all(z), f"Schalter neben dem Titel, Knöpfe darunter ({z})")

    print("7 Zeitachse ohne Nummern (390 px)")
    reiter(pg, "zeit")
    z = pg.evaluate("[...document.querySelectorAll('.tl-bar .st')].map(e => [getComputedStyle(e).fontSize, Math.round(e.getBoundingClientRect().width)])")
    pruef(z and all(x == ["0px", 10] for x in z), f"Marken als Punkte ohne Ziffer ({z[:3]})")

    print("6 Teilnehmende einspaltig (390 px)")
    reiter(pg, "people")
    z = pg.evaluate("""() => { const ul = document.querySelector('ul.names'), r = ul.getBoundingClientRect();
      return [getComputedStyle(ul).columnCount, [...ul.querySelectorAll('li')].slice(0, 5).map(l => Math.round(r.right - l.querySelector('.del').getBoundingClientRect().right))]; }""")
    pruef(z[0] == "1" and all(x <= 1 for x in z[1]), f"eine Spalte, × am rechten Rand ({z})")

    print("5 Daten löschen")
    reiter(pg, "danger")
    z = pg.evaluate("Object.fromEntries([...document.querySelectorAll('.panel.danger [data-act=a-danger]')].map(k => [k.dataset.key, k.className]))")
    pruef(z.get("people") == "btn warn" and all(v == "btn warnrand" for k, v in z.items() if k != "people") and len(z) >= 2,
          f"nur „Alle Teilnehmenden löschen“ gefüllt ({z})")
    pg.click(".panel.danger [data-key=reset]")
    pruef(pg.locator("#dlgok").count() == 1, "Randknopf öffnet weiter die Rückfrage")
    pg.close()

    print("9 Spiel starten nur im Kopf")
    pg = neu(b, "admin-bereit")
    t = pg.inner_text("#app").replace(" ", " ")
    pruef(pg.locator("[data-act=a-start]").count() == 1 and pg.locator(".akopf [data-act=a-start]").count() == 1, "ein Startknopf, oben im Kopf")
    pruef("Bereit zum Start" in t and "Gestartet wird oben" in t, "Bereit zum Start erklärt den Weg")
    pruef(pg.evaluate(REIHEN) == 2, "acht Reiter in zwei Reihen")
    reiter(pg, "settings")
    z = pg.evaluate("[...document.querySelectorAll('.panel h3')].map(h => h.textContent)")
    pruef(z[:3] == ["Spieldauer und Koffer-Hinweis", "Hintergrund", "Testmodus"] and pg.locator("#a-dauer").count() == 1, f"Reiter Einstellungen: Spieldauer, Hintergrund, Testmodus ({z})")
    reiter(pg, "stations")
    pruef(pg.locator("#a-dauer").count() == 0 and pg.locator("[data-act=a-test]").count() == 0, "Reiter Stationen ohne Einstellungen")
    pg.click(".akopf [data-act=a-start]")
    pruef(pg.locator("#dlgok").count() == 1, "Startknopf fragt nach")
    pg.close()

    print("Tablet 768 px und Laptop 1280 px")
    pg = neu(b, "admin-teams", 768, 1024)
    pruef(pg.evaluate(OBEN, "#teamfeld") < pg.evaluate(OBEN, "#map"), "Tablet: Liste über der Karte")
    pruef(pg.evaluate(REIHEN) == 1, "Tablet: Reiter in einer Reihe")
    pg.close()
    pg = neu(b, "admin-teams", 1280, 800)
    z = pg.evaluate("""() => { const t = document.querySelector('#teamfeld').getBoundingClientRect(), m = document.querySelector('#map').getBoundingClientRect();
      return [m.left < t.left, Math.abs(m.top - t.top) < 2, getComputedStyle(document.querySelector('#teamfeld')).position]; }""")
    pruef(z == [True, True, "sticky"], f"Laptop: Karte links, Liste rechts daneben, mitlaufend ({z})")
    reiter(pg, "zeit")
    z = pg.evaluate("[...document.querySelectorAll('.tl-bar .st')].slice(0, 3).map(e => e.textContent && getComputedStyle(e).fontSize !== '0px')")
    pruef(z and all(z), "Laptop: Zeitachse mit Nummern")
    pg.close()
    b.close()

pruef(not err, f"keine Seitenfehler {err}")
srv.shutdown()
print("FEHLT: " + "; ".join(fehler) if fehler else "OK")
sys.exit(1 if fehler else 0)
