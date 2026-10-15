#!/usr/bin/env python3
"""
Ausfallsicherheit, Abschnitt 5: Notfallmappe der Spielleitung.

    python tools/pruefstand/mappe.py

Spiel (app.html mit mock.js, Port 8866). Die Leaflet-Karte im Reiter Karte und Teams wird gar nicht erst geladen
(Anfrage abgebrochen): ohne Leaflet-Seite hängt Chrome beim Schließen nicht. Im Vordergrund mit Timeout aufrufen.
Am Ende steht OK oder FEHLT.
"""
import functools
import http.server
import io
import pathlib
import re
import sys
import threading

sys.stdout.reconfigure(encoding="utf-8")
HIER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import shoot  # noqa: E402
import abschluss  # noqa: E402

shoot.bauen()
from playwright.sync_api import sync_playwright  # noqa: E402


class Leise(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


PORT = 8866
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
APP = f"http://127.0.0.1:{PORT}/app.html?szenario="
fehler, err = [], []

# aus mock.js: Stationen, Ziffern, Lösungen
STATIONEN = [("Planetarium Prag", 3, "1960"), ("Rudolfstollen", 7, "1098"), ("Wasserturm Letná", 1, "7 oder sieben"),
             ("Aussicht Letná, ehemalige Bergstation", 9, "5 oder fünf"), ("Metronom", 5, "1991")]
CODE = "371955"


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def neu(b, szenario, breit=True, schema="light"):
    pg = b.new_page(viewport={"width": 1180, "height": 820} if breit else {"width": 390, "height": 844}, color_scheme=schema)
    pg.set_default_timeout(15000)
    pg.route("**/vendor/leaflet-1.9.4/**", lambda r: r.abort())
    pg.on("pageerror", lambda e: err.append(f"{szenario}: {e}"))
    pg.goto(APP + szenario)
    pg.wait_for_function("window.__fertig === true", timeout=30000)
    return pg


def mappe_auf(pg):
    pg.click("[data-act=a-tab][data-tab=stations]")
    knopf = pg.locator("[data-act=a-mappe]")
    if not knopf.count():
        return False
    knopf.click()
    pg.wait_for_selector(".papier", timeout=5000)
    return True


def seiten(pdf):
    return len(re.findall(rb"/Type\s*/Page(?!s)", pdf))


vorher = abschluss.merken()
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)

    print("Knopf und Ansicht")
    pg = neu(b, "admin-stationen")
    pg.click("[data-act=a-tab][data-tab=stations]")
    k = pg.locator("[data-act=a-mappe]")
    pruef(k.count() == 1 and k.inner_text() == "Notfallmappe", "Knopf 'Notfallmappe' im Reiter Stationen")
    pruef(k.count() == 1 and "alt" in (k.get_attribute("class") or "") and "sm" in (k.get_attribute("class") or ""), "Knopf ist .btn.sm.alt")
    pruef(k.count() == 1 and k.evaluate("e => !!e.closest('.panel') && e.closest('.panel').textContent.includes('Koffer-Code')"), "Knopf steht im Panel mit dem Koffer-Code")
    ok = mappe_auf(pg)
    pruef(ok, "Mappe öffnet sich")
    if ok:
        leiste = pg.locator(".mappe-leiste")
        pruef(leiste.locator("[data-act=a-mappe-zu]").inner_text() == "Zurück", "Leiste: Zurück")
        pruef(leiste.locator("[data-act=a-drucken]").inner_text() == "Drucken", "Leiste: Drucken")
        pruef(pg.locator(".tabs").count() == 0, "statt der Reiter")
        blatt = pg.locator(".papier")
        t = blatt.inner_text()
        pruef(t.startswith("Stadtjagd Notfallmappe"), "Kopf: Stadtjagd Notfallmappe")
        pruef(re.search(r"Daten vom \d\d\.\d\d\.\d{4}, \d\d:\d\d", t) is not None, "Daten vom TT.MM.JJJJ, hh:mm")
        pruef("12 Teams, 96 Personen" in t, "Zahl der Teams und Personen")
        pruef("Testmodus aus" in t, "Testmodus aus")
        pruef(pg.locator(".papier .code b").inner_text() == CODE, f"Koffer-Code {CODE}")
        pruef("gilt für alle 3 Koffer" in t, "gilt für alle 3 Koffer")
        pruef("Mama Shelter Prague" in t and "50.10246, 14.43168" in t, "Start mit Koordinaten")
        pruef("Innenhof hinter der Bar" in t, "Koffer-Hinweis")
        pruef(pg.locator(".papier ol li").count() == 5, "fünf Schritte für den Ausfall")
        st = pg.locator(".papier .station")
        pruef(st.count() == 5, f"5 Stationen ({st.count()})")
        for i, (name, ziffer, loesung) in enumerate(STATIONEN):
            if i < st.count():
                s = st.nth(i).inner_text()
                pruef(f"{i + 1} {name}" in s and f"Ziffer {ziffer}" in s and loesung in s, f"Station {i + 1}: Name, Ziffer {ziffer}, Lösung {loesung}")
        pruef("Radius 50 m" in st.first.inner_text() and "50.10529, 14.42741" in st.first.inner_text(), "Ort mit 5 Nachkommastellen und Radius")
        pruef("Tretet ein paar Schritte zurück" in st.first.inner_text(), "Tipp")
        zeilen = pg.locator(".papier table tbody tr")
        pruef(zeilen.count() == 12, f"12 Teams im Laufzettel ({zeilen.count()})")
        fuchs = pg.locator(".papier table tbody tr:has-text('Fuchs')")
        ft = fuchs.inner_text() if fuchs.count() else ""
        pruef("FUCHS-4821" in ft and "Anna Berger" in ft, "Fuchs mit Code und Leitung")
        pruef("Emre" in ft and "Emre Demir" not in ft, "Mitglieder mit Vornamen")
        pruef(fuchs.locator(".box").count() == 5 and fuchs.locator(".box.an").count() == 1, "Fuchs: 5 Kästchen, 1 abgehakt")
        adler = pg.locator(".papier table tbody tr:has-text('Adler')")
        pruef(adler.count() == 1 and "Platz 1" in adler.inner_text(), "Adler: Platz 1")
        pruef("Platz ____" in ft, "Fuchs: Platz ____")
        pruef(t.rstrip().endswith("Enthält alle Lösungen. Nach dem Spiel vernichten."), "Fuß")
        pruef(pg.locator(".papier .version, .papier .nav").count() == 0, "keine Navigation im Blatt")
        nw = pg.evaluate("""() => [...document.querySelectorAll('.papier .code b, .papier td.k, .papier .station .nw')]
          .every(e => getComputedStyle(e).whiteSpace === 'nowrap')""")
        pruef(nw, "Codes und Koordinaten brechen nicht um")
        # "Daten vom" ist die Zeit des letzten admin_state, nicht die irgendeines Aufrufs
        pg.evaluate("S.admin.stateAt = new Date(2026, 9, 18, 9, 12).getTime(); render()")
        pruef("Daten vom 18.10.2026, 09:12" in pg.locator(".papier").inner_text(), "Daten vom: Zeit des letzten admin_state")
        pg.evaluate("rpc('public_state', {}).then(() => render())"); pg.wait_for_timeout(400)
        pruef("Daten vom 18.10.2026, 09:12" in pg.locator(".papier").inner_text(), "ein anderer Aufruf ändert 'Daten vom' nicht")
        # der 10-s-Abruf zeichnet die Mappe nicht weg
        pg.evaluate("refresh()"); pg.wait_for_timeout(500)
        pruef(pg.locator(".papier").count() == 1, "Mappe bleibt nach einem Abruf")
        pg.click("[data-act=a-mappe-zu]")
        pruef(pg.locator(".papier").count() == 0 and pg.locator(".tabs").count() == 1, "Zurück: wieder die Reiter")
        pruef(pg.evaluate("S.admin.tab") == "stations", "Zurück landet im Reiter Stationen")
    pg.close()

    print("Testmodus: Koffer-Code aus der echten Route, Laufzettel ohne Haken")
    pg = neu(b, "admin-stationen")
    pg.evaluate("""() => { const alt = rpc; window.rpc = async (fn, a) => { const r = await alt(fn, a);
      if (r && fn === 'admin_state') { r.testMode = true; r.route = 'test'; r.caseCode = '12'; } return r; }; }""")
    pg.evaluate("refresh()"); pg.wait_for_timeout(500)
    if mappe_auf(pg):
        t = pg.locator(".papier").inner_text()
        pruef(pg.locator(".papier .code b").inner_text() == CODE, f"Koffer-Code aus den Stationen ({pg.locator('.papier .code b').inner_text()})")
        pruef("Testmodus an" in t, "Warnung Testmodus an")
        pruef(pg.locator(".papier .warnung").count() == 1, "Testmodus an als Warnung hervorgehoben")
        pruef(pg.locator(".papier .station").count() == 5, "echte Route mit 5 Stationen")
        pruef(pg.locator(".papier .box.an").count() == 0, "keine Haken im Testmodus")
    else:
        pruef(False, "Mappe öffnet sich im Testmodus")
    pg.close()

    print("Fehlende Angaben")
    pg = neu(b, "admin-stationen")
    pg.evaluate("""() => { const alt = rpc; window.rpc = async (fn, a) => { const r = await alt(fn, a);
      if (r && fn === 'admin_state') { r.stations[1].lat = null; r.stations[1].lng = null; r.stations[2].riddle = 'Rätsel folgt'; r.stations[3].digit = null; } return r; }; }""")
    pg.evaluate("refresh()"); pg.wait_for_timeout(500)
    if mappe_auf(pg):
        st = pg.locator(".papier .station")
        pruef(st.nth(1).locator(".fehlt").count() >= 1 and "fehlt" in st.nth(1).inner_text(), "Station 2 ohne Koordinaten: fehlt")
        pruef(st.nth(2).locator(".fehlt").count() >= 1, "Station 3 mit Platzhalter-Rätsel: fehlt")
        farbe = pg.evaluate("(() => { const e = document.querySelector('.papier .fehlt'); return e && getComputedStyle(e).color; })()")
        pruef(farbe == "rgb(179, 38, 30)", f"fehlt in --err ({farbe})")
        pruef(pg.locator(".papier .code .fehlt").count() == 1, "Koffer-Code ohne Ziffer 4: fehlt")
    else:
        pruef(False, "Mappe öffnet sich mit fehlenden Angaben")
    pg.close()

    print("Vor dem Auslosen")
    pg = neu(b, "admin-auslosen")
    if mappe_auf(pg):
        t = pg.locator(".papier").inner_text()
        pruef("Noch nicht ausgelost." in t and pg.locator(".papier table").count() == 0, "statt der Tabelle: Noch nicht ausgelost.")
    else:
        pruef(False, "Mappe öffnet sich vor dem Auslosen")
    pg.close()

    print("Dunkles Design, Druck, Handy")
    pg = neu(b, "admin-stationen", schema="dark")
    if mappe_auf(pg):
        bg = pg.evaluate("getComputedStyle(document.querySelector('.papier')).backgroundColor")
        fg = pg.evaluate("getComputedStyle(document.querySelector('.papier')).color")
        pruef(bg == "rgb(255, 255, 255)", f"Blatt im dunklen Design hell ({bg})")
        pruef(fg == "rgb(23, 48, 42)", f"Schrift im Blatt dunkel ({fg})")
        pruef(pg.evaluate("getComputedStyle(document.body).backgroundColor") != "rgb(241, 245, 238)", "der Rest bleibt dunkel")
        pg.emulate_media(media="print")
        sichtbar = pg.evaluate("""() => { const zeig = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
            return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
          return { leiste: zeig(document.querySelector('.mappe-leiste')), topo: !!document.querySelector('.topo') && zeig(document.querySelector('.topo')),
            blatt: zeig(document.querySelector('.papier')), body: getComputedStyle(document.body).backgroundColor }; }""")
        pruef(sichtbar["blatt"] and not sichtbar["leiste"] and not sichtbar["topo"], f"Druck: nur das Blatt ({sichtbar})")
        pruef(sichtbar["body"] in ("rgb(255, 255, 255)", "rgba(0, 0, 0, 0)"), f"Druck: Seitengrund weiß ({sichtbar['body']})")
        pruef(pg.evaluate("getComputedStyle(document.querySelector('.papier .station')).breakInside") == "avoid", "Stationsblöcke brechen nicht")
        pruef(pg.evaluate("getComputedStyle(document.querySelector('.papier .teams')).breakBefore") == "page", "Teams ab neuer Seite")
        pdf = pg.pdf(format="A4")
        n = seiten(pdf)
        pruef(1 <= n <= 5, f"PDF hat höchstens 5 Seiten ({n})")
        pg.emulate_media(media="screen")
    else:
        pruef(False, "Mappe öffnet sich im dunklen Design")
    pg.close()

    pg = neu(b, "admin-stationen", breit=False)
    if mappe_auf(pg):
        pruef(pg.evaluate("document.documentElement.scrollWidth") <= 390, f"kein seitliches Scrollen bei 390 px ({pg.evaluate('document.documentElement.scrollWidth')})")
        nw = pg.evaluate("""() => [...document.querySelectorAll('.papier .code b, .papier td.k, .papier .station .nw')]
          .every(e => e.getClientRects().length === 1)""")
        pruef(nw, "Codes und Koordinaten einzeilig bei 390 px")
    else:
        pruef(False, "Mappe öffnet sich am Handy")
    pg.close()

    pruef(not err, "keine Fehler auf der Seite" + (f": {err[:3]}" if err else ""))
    print("FEHLT:\n  " + "\n  ".join(fehler) if fehler else "OK")
    abschluss.ende(fehler, vorher)
