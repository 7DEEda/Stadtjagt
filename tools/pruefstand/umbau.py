#!/usr/bin/env python3
"""
Umbau Weiterentwicklung im Prüfstand, ohne Datenbank.

    python tools/pruefstand/umbau.py

Handy-Hülle (390x844): Kopf, Inhalt, drei Tabs unten. Im Vordergrund mit Timeout starten.
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


PORT = 8840
BASIS = f"http://127.0.0.1:{PORT}"
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
fehler = []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 390, "height": 844}); pg.set_default_timeout(15000); err = []
    pg.on("pageerror", lambda e: err.append(str(e)))

    print("Handy, Teamleitung unterwegs")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-unterwegs"); pg.wait_for_selector(".ph")
    pruef(pg.locator(".ph > .kopf").count() == 1 and pg.locator(".ph > .inhalt").count() == 1, "Hülle mit Kopf und Inhalt")
    tabs = pg.locator(".ftabs [role=tab]")
    pruef(tabs.count() == 3 and [tabs.nth(i).inner_text().split("\n")[0] for i in range(3)] == ["Weg", "Ziffern", "Team"], "drei Tabs Weg, Ziffern, Team")
    pruef(pg.locator("#needle").count() == 1 and pg.locator("#dist").count() == 1, "Kompass und Entfernung im Tab Weg")
    pg.click(".ftabs [data-tab=team]")
    pruef(pg.locator("#needle").count() == 0, "Tab Team ohne Kompass")
    pg.evaluate("render()")                      # die 10-s-Abfrage zeichnet neu
    pruef(pg.get_attribute(".ftabs [data-tab=team]", "aria-selected") == "true", "Tab bleibt nach render() gewählt")
    box = pg.locator(".ftabs").bounding_box()
    pruef(abs(box["y"] + box["height"] - 844) < 2, "Tabs kleben unten")
    pruef(pg.evaluate("document.documentElement.scrollWidth") <= 390, "kein seitliches Scrollen")
    print("Handy, Teamleitung Rätsel")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-raetsel"); pg.wait_for_selector(".ph")
    pruef(pg.inner_text(".ftabs [data-tab=weg]").startswith("Rätsel"), "erster Tab heißt im Rätsel 'Rätsel'")

    print("Scrollstand im Inhalt")
    pg.set_viewport_size({"width": 390, "height": 420})
    pg.goto(f"{BASIS}/app.html?szenario=leitung-raetsel"); pg.wait_for_selector(".ph")
    pg.evaluate("document.querySelector('#inhalt').scrollTop = 60")
    h0 = pg.evaluate("document.querySelector('#inhalt').scrollTop")
    pruef(h0 > 0, f"Inhalt lässt sich scrollen ({h0})")
    pg.evaluate("render()")
    pruef(pg.evaluate("document.querySelector('#inhalt').scrollTop") == h0, "Scrollstand bleibt nach render()")
    pg.set_viewport_size({"width": 390, "height": 260})
    pg.evaluate("render()")
    pg.evaluate("document.querySelector('#inhalt').scrollTop = 60")
    pg.click(".ftabs [data-tab=ziffern]")
    sz = pg.evaluate("(() => { const i = document.querySelector('#inhalt'); return [i.scrollHeight, i.clientHeight]; })()")
    pruef(sz[0] > sz[1], f"Tab Ziffern ist scrollbar {sz}")
    pruef(pg.evaluate("document.querySelector('#inhalt').scrollTop") == 0, "nach Tabwechsel beginnt der neue Inhalt oben")
    pg.evaluate("document.querySelector('#inhalt').scrollTop = 30"); pg.evaluate("render()")
    pruef(pg.evaluate("document.querySelector('#inhalt').scrollTop") == 30, "im neuen Tab bleibt der Stand nach render()")
    pg.click(".ftabs [data-tab=weg]")
    pruef(pg.evaluate("document.querySelector('#inhalt').scrollTop") == 0, "zurück im Tab Weg oben")

    print("Aktionsleiste")
    pg.set_viewport_size({"width": 390, "height": 844})
    pg.goto(f"{BASIS}/app.html?szenario=leitung-unterwegs"); pg.wait_for_selector(".ph")
    pruef(pg.locator("#leiste [data-act=t-gps]").count() == 1 and pg.locator("#inhalt [data-act=t-gps]").count() == 0, "ohne Standort: Freigabe steht in der Leiste")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-unterwegs-standort"); pg.wait_for_selector("#leiste #tcheck")
    pruef(pg.locator("#leiste #tcheck").count() == 1 and pg.locator("#inhalt #tcheck").count() == 0, "Einchecken steht in der Leiste")
    pg.click(".ftabs [data-tab=team]")
    pruef(pg.locator("#leiste #tcheck").count() == 1, "Leiste bleibt in jedem Tab")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-raetsel"); pg.wait_for_selector("#leiste #tans")
    pg.click("#tans"); pg.keyboard.type("527")
    r = pg.locator("#tans").bounding_box()
    pruef(r["y"] + r["height"] <= 844 and pg.evaluate("document.documentElement.scrollWidth") <= 390, "Antwortfeld sichtbar, nichts seitlich verschoben")
    pg.evaluate("render()")
    pruef(pg.input_value("#tans") == "527", "Getipptes übersteht render()")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-raetsel"); pg.wait_for_selector("#leiste #tans")
    pg.evaluate("() => { window.rpc = async () => { throw new Error('Keine Verbindung zum Test'); }; }")
    pg.click(".ftabs [data-tab=team]")
    pg.click("#tans"); pg.keyboard.type("1")
    pg.click("#leiste [data-act=t-answer]")
    pg.wait_for_timeout(600)
    pruef("Keine Verbindung zum Test" in pg.inner_text("#leiste") and "Keine Verbindung zum Test" not in pg.inner_text("#inhalt"), "Fehler beim Prüfen erscheint in der Leiste, auch im Tab Team")
    pg.goto(f"{BASIS}/app.html?szenario=mitglied-raetsel"); pg.wait_for_selector(".ph")
    pruef(pg.locator("#leiste input").count() == 0 and "gibt" in pg.inner_text("#leiste"), "Mitlesende: keine Eingabe, Leiste sagt wer eingibt")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-koffer"); pg.wait_for_selector("#leiste #tfin")
    pruef(pg.locator("#inhalt #tfin").count() == 0 and pg.locator("#leiste [data-act=t-final]").count() == 1, "Koffer-Code steht in der Leiste")
    for sz in ["leitung-startklar", "leitung-koffer", "leitung-platz2", "leitung-beendet", "selfie-offen"]:
        pg.goto(f"{BASIS}/app.html?szenario={sz}"); pg.wait_for_selector("#app > *")
        leer = pg.evaluate("(() => { const l = document.querySelector('#leiste'); return !!l && l.innerText.trim() === '' && getComputedStyle(l).display !== 'none'; })()")
        pruef(not leer and not err, f"{sz}: keine leere Leiste, keine Fehler")

    print("Kopf")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-unterwegs"); pg.wait_for_selector(".kopf")
    k = pg.inner_text(".kopf")
    pruef("Team Fuchs" in k and "Noch" in k, "Kopf: Teamname und Restzeit")
    pruef(pg.locator(".kopf .minilock").count() == 1, "Kopf: Ziffern klein")
    pruef(pg.locator(".kopf #stand").count() == 1 and pg.locator(".kopf .uhr").count() >= 1, "Kopf: Uhr und Stand-Chip vorhanden")
    pruef(pg.locator("#inhalt .hilfe, #inhalt h1").count() == 0, "Hülle: kein alter Kopf, kein Hilfe-Knopf im Inhalt")
    hoehen = pg.evaluate("[...document.querySelectorAll('.kopf .minilock, .kopf .hilfe-btn, .ftabs button')].map(e => e.getBoundingClientRect().height)")
    pruef(len(hoehen) >= 5 and min(hoehen) >= 44, f"Kopf und Tabs mindestens 44 px hoch {hoehen}")
    pg.click(".kopf .minilock")
    pruef(pg.get_attribute(".ftabs [data-tab=ziffern]", "aria-selected") == "true", "Ziffern im Kopf öffnen den Tab Ziffern")
    pg.click(".kopf [data-act=t-hilfe]")
    pruef(pg.locator(".blatt a[href^='https://wa.me'], .blatt a[href^='tel:']").count() >= 1, "Hilfe öffnet ein Blatt mit WhatsApp oder Anrufen")
    pg.keyboard.press("Escape")
    pruef(pg.locator(".blatt").count() == 0, "Escape schließt das Blatt")
    pg.click(".kopf [data-act=t-hilfe]")
    zu = pg.evaluate("document.querySelector('.blatt button[data-act=t-hilfe-zu]').getBoundingClientRect().height")
    pruef(zu >= 44, f"Schließen im Hilfe-Blatt mindestens 44 px hoch ({zu})")
    pg.click(".blatt [data-act=t-hilfe-zu]")
    pruef(pg.locator(".blatt").count() == 0, "Schließen-Link schließt das Blatt")
    pg.click(".kopf [data-act=t-hilfe]"); pg.click(".ueber", position={"x": 5, "y": 5})
    pruef(pg.locator(".blatt").count() == 0, "Klick auf den Hintergrund schließt das Blatt")
    pg.click(".kopf [data-act=t-hilfe]"); pg.click(".blatt h2")
    pruef(pg.locator(".blatt").count() == 1, "Klick ins Blatt lässt es offen")
    pg.keyboard.press("Escape")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-startklar"); pg.wait_for_selector(".ph, #app > *")
    pruef(pg.locator(".kopf").count() == 0 and pg.locator("[data-act=t-hilfe]").count() == 0 and pg.locator("a.help").count() >= 1, "Phase ohne Hülle behält ihren Hilfe-Knopf")

    print("Tab Team")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-unterwegs"); pg.wait_for_selector(".ph"); pg.click(".ftabs [data-tab=team]")
    t = pg.inner_text("#inhalt")
    pruef("Mitlesen fürs Team" in t and "Anna Berger" in t and "Abmelden" in t, "Teamleitung: Mitlese-Link, Mitglieder, Abmelden")
    pg.goto(f"{BASIS}/app.html?szenario=mitglied-unterwegs"); pg.wait_for_selector(".ph"); pg.click(".ftabs [data-tab=team]")
    t = pg.inner_text("#inhalt")
    pruef("Mitlesen fürs Team" not in t and "Abmelden" not in t and "Anna Berger" in t, "Mitlesende: nur Mitglieder")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-unterwegs"); pg.wait_for_selector(".ph")
    pruef("Abmelden" not in pg.inner_text("#inhalt") and "Mitlesen fürs Team" not in pg.inner_text("#inhalt"), "Weg-Tab ohne Abmelden und Mitlese-Link")

    print("Spielleitung, Karte und Teams")
    pg.set_viewport_size({"width": 1440, "height": 900})
    pg.goto(f"{BASIS}/app.html?szenario=admin-karte"); pg.wait_for_selector("#map .leaflet-marker-icon", timeout=25000)
    reiter = [x.strip() for x in pg.locator(".tabs [role=tab]").all_inner_texts()]
    pruef(reiter[:2] == ["Karte und Teams", "Zeitachse"], f"Reiter: {reiter}")
    pruef("Auslosen" not in reiter and "Teams" not in reiter, "im Spiel kein Reiter Auslosen")
    m, l = pg.locator("#map").bounding_box(), pg.locator("#teamfeld").bounding_box()
    pruef(l["x"] > m["x"] + m["width"] - 2 and abs(l["y"] - m["y"]) < 40, "Teamliste rechts neben der Karte")
    pruef(pg.locator("#app").bounding_box()["width"] > 1300, "volle Breite")
    pruef(pg.locator("#tlrows").count() == 0, "Zeitachse nicht mehr unter der Karte")
    pg.click("[data-act=a-tab][data-tab=zeit]"); pg.wait_for_selector("#tlrows")
    pruef(pg.locator("#tlslider").count() == 1, "Zeitachse mit Schieber im eigenen Reiter")
    pg.click("[data-act=a-tab][data-tab=live]"); pg.wait_for_selector("#map .leaflet-marker-icon", timeout=25000)
    pg.click(".kartefuss [data-act=a-full]"); pg.wait_for_timeout(300)
    vb = pg.locator("#map").bounding_box()
    pruef(vb["width"] >= 1430 and vb["height"] >= 890, f"Vollbild füllt das Fenster ({vb})")
    pg.click(".kartezu"); pg.wait_for_timeout(200)
    pg.set_viewport_size({"width": 820, "height": 1180})
    pg.goto(f"{BASIS}/app.html?szenario=admin-karte"); pg.wait_for_selector("#teamfeld")
    m, l = pg.locator("#map").bounding_box(), pg.locator("#teamfeld").bounding_box()
    pruef(l["y"] >= m["y"] + m["height"] - 2, "Tablet hoch: Liste unter der Karte")
    pg.set_viewport_size({"width": 1440, "height": 900}); pg.goto(f"{BASIS}/app.html?szenario=admin-karte"); pg.wait_for_selector(".tabs")
    pg.click("[data-act=a-tab][data-tab=people]"); pg.wait_for_selector("#aadd")
    pw, tw = pg.locator(".inhalt900 .panel").first.bounding_box()["width"], pg.locator(".tabs").bounding_box()["width"]
    pruef(pw <= 900 and tw > 1300, f"Teilnehmende: Inhalt {pw:.0f} px, Reiterleiste {tw:.0f} px")
    pg.goto(f"{BASIS}/app.html?szenario=admin-auslosen"); pg.wait_for_selector(".tabs")
    reiter = [x.strip() for x in pg.locator(".tabs [role=tab]").all_inner_texts()]
    pruef("Auslosen" in reiter, f"vor dem Spiel gibt es den Reiter Auslosen ({reiter})")
    pg.set_viewport_size({"width": 1440, "height": 900})

    print("Teamliste")
    pg.set_viewport_size({"width": 1440, "height": 900})
    pg.goto(f"{BASIS}/app.html?szenario=admin-probleme"); pg.wait_for_selector("#teamfeld .row")
    gruppen = pg.locator("#teamfeld .grp").all_inner_texts()
    pruef(gruppen and gruppen[0].startswith("Braucht dich"), f"erster Block 'Braucht dich': {gruppen}")
    erste = pg.locator("#teamfeld .row").first.inner_text()
    pruef("kein GPS" in erste, f"kein Standort steht ganz oben: {erste[:60]!r}")
    pruef("3 Teams brauchen dich" in pg.inner_text("[data-act=a-probleme]"), "Zähler im Kopf")
    pg.wait_for_selector("#map .leaflet-marker-icon", timeout=25000)
    pg.click("#teamfeld .row:nth-child(3) .row-main")
    sel = pg.evaluate("S.admin.sel")
    pruef(sel and pg.locator("#teamfeld .row.sel").count() == 1, "Zeile aufgeklappt")
    pg.wait_for_selector(".mapbadge.team.sel", timeout=10000)
    pruef(pg.locator(".mapbadge.team.sel").count() == 1, "Team auf der Karte markiert")
    pruef(pg.locator("#teamfeld select[data-chg=a-leader]").count() == 1 and pg.locator("#teamfeld [data-act=a-mit]").count() == 1, "aufgeklappt: Leitung und Mitlese-Link")
    pg.locator("#teamfeld").evaluate("e => e.scrollTop = 200"); pg.evaluate("render()")
    pruef(pg.evaluate("S.admin.sel") == sel and pg.locator("#teamfeld").evaluate("e => e.scrollTop") > 150, "Auswahl und Scrollen überstehen render()")
    pg.click("[data-act=a-probleme]")
    pruef(pg.locator("#teamfeld .row.sel").inner_text().find("kein GPS") >= 0, "Zähler springt zum ersten Problem")
    pruef(pg.locator(".ohnepos [data-act=a-sel]").count() == 1 and "kein Standort" in pg.inner_text(".ohnepos"), "Knopf kein Standort unter der Karte")
    # Fix 1: wechselt die Leitung, während die Zeile offen ist, öffnet das nächste Neuzeichnen keinen Dialog
    pg.goto(f"{BASIS}/app.html?szenario=admin-probleme"); pg.wait_for_selector("#teamfeld .row"); pg.wait_for_selector("#map .leaflet-marker-icon", timeout=25000)
    pg.click("#teamfeld .row:has-text('Igel') .row-main"); pg.wait_for_selector("#teamfeld .row.sel select[data-chg=a-leader]")
    pg.evaluate("""() => { const st = S.admin.state, t = st.teams.find(x => x.name === 'Igel'), p = st.participants.find(x => x.teamId === t.id && x.id !== t.leaderId);
      t.leaderId = p.id; t.leaderName = p.name; render(); }""")
    pg.wait_for_timeout(300)
    pruef(pg.evaluate("S.admin.confirm") is None and pg.locator(".overlay").count() == 0, "Leitungswechsel bei offener Zeile öffnet keinen Dialog")
    # Fix 2: Auswahl lässt Zoom und Ausschnitt der Karte stehen
    pg.evaluate("map.setView(map.getCenter(), map.getZoom() + 2, { animate: false })"); pg.wait_for_timeout(300)
    z0, c0 = pg.evaluate("[map.getZoom(), map.getCenter().lat]")
    pg.click("#teamfeld .row:has-text('Otter') .row-main"); pg.wait_for_timeout(1500)
    z1, c1 = pg.evaluate("[map.getZoom(), map.getCenter().lat]")
    pruef(z1 == z0 and abs(c1 - c0) < 1e-6, f"Auswahl in der Liste lässt Zoom und Mitte stehen ({z0}/{z1})")
    pg.evaluate("layers.teams[S.admin.state.teams.find(x => x.name === 'Igel').id].fire('click')"); pg.wait_for_timeout(1500)
    pruef(pg.evaluate("map.getZoom()") == z0 and pg.locator(".leaflet-popup").count() == 1, "Marker-Klick: Zoom bleibt, Popup bleibt offen")
    # Fix 3: Rückmeldung zu Freischalten erscheint auch an der zugeklappten Zeile
    pg.click("#teamfeld .row:has-text('Delfin') .btn[data-key=unlock]"); pg.wait_for_selector("#dlgok")
    pg.click("#dlgok"); pg.wait_for_timeout(800)
    zeile = pg.locator("#teamfeld .row:has-text('Delfin')")
    pruef("eingecheckt" in zeile.inner_text() and zeile.locator(".detail").count() == 0, "Freischalten an zugeklappter Zeile: Meldung steht in der Zeile")
    pg.goto(f"{BASIS}/app.html?szenario=admin-karte"); pg.wait_for_selector("#teamfeld .row")
    pruef(pg.locator("#teamfeld .row .btn[data-key=solve], #teamfeld .row .btn[data-key=unlock]").count() >= 3, "Freischalten und Rätsel werten als Zeilenknopf")

    print("Zuletzt")
    pg.goto(f"{BASIS}/app.html?szenario=admin-probleme"); pg.wait_for_selector("#zuletzt li", timeout=20000)
    li = pg.locator("#zuletzt li").all_inner_texts()
    pruef(1 <= len(li) <= 8, f"zwischen 1 und 8 Ereignisse: {len(li)}")
    pruef(any("eingecheckt" in x or "Ziffer" in x for x in li), "Check-in oder Ziffer als Ereignis")
    pruef(all(__import__("re").match(r"\d\d:\d\d$", x.split(chr(10))[0].strip()) for x in li), f"Uhrzeit HH:MM vorn: {[x[:8] for x in li]}")
    pg.locator("#zuletzt li button").first.click()
    pruef(pg.evaluate("S.admin.sel") is not None, "Antippen wählt das Team")
    pg.locator("#zuletzt li button").first.click()
    pruef(pg.evaluate("S.admin.sel") is not None and pg.locator("#teamfeld .row.sel").count() == 1, "zweites Antippen derselben Zeile wählt wieder, kein Abwählen")
    # Karte: andere Route (Teststation) passt neu ein, der gemerkte Ausschnitt gilt nur für dieselbe Route
    pg.goto(f"{BASIS}/app.html?szenario=admin-probleme"); pg.wait_for_selector("#map .leaflet-marker-icon", timeout=25000)
    lat0 = pg.evaluate("map.getCenter().lat")
    pg.evaluate("S.admin.state.route = 'test'; render()"); pg.wait_for_timeout(2500)
    lat1 = pg.evaluate("map.getCenter().lat")
    pruef(abs(lat1 - lat0) > 0.5, f"Routenwechsel echt zu test passt die Karte neu ein ({lat0:.2f} zu {lat1:.2f})")

    print("Schlussprüfung: Mitlese-Hülle, Randfälle")
    pg.set_viewport_size({"width": 390, "height": 844})
    pg.goto(f"{BASIS}/app.html?szenario=mitglied-unterwegs"); pg.wait_for_selector(".ph")
    pg.evaluate("window.scrollTo(0, 400)"); pg.evaluate("render()")
    pruef(pg.evaluate("window.scrollY") == 0, "Mitlesen: Fensterscroll wird beim Neuzeichnen zurückgesetzt")
    kt = pg.locator(".kopf").bounding_box()["y"]; tb = pg.locator(".ftabs").bounding_box()
    pruef(kt >= 0 and tb["y"] + tb["height"] <= 844 + 1, f"Mitlesen: Kopf und Tabs im Bild ({kt}, {tb['y'] + tb['height']})")
    fremd = pg.evaluate("[...document.querySelector('#app').children].filter(e => !e.classList.contains('ph') && !e.classList.contains('overlay') && !e.classList.contains('hochhalten')).map(e => e.className || e.tagName)")
    pruef(fremd == [], f"Mitlesen: nach der Hülle steht nichts im #app ({fremd})")
    pg.click(".ftabs [data-tab=team]")
    pruef(pg.locator("#inhalt [data-act=pub-hoch]").count() == 1, "Tab Team (Mitglied): Team-Zeichen zum Hochhalten")
    pg.click("#inhalt [data-act=pub-hoch]")
    pruef(pg.locator(".hochhalten").count() == 1 and pg.locator(".hochhalten b").inner_text().startswith("Team "), "Hochhalten öffnet das Teamfenster in der Hülle")
    pg.click(".hochhalten")
    pruef(pg.locator(".hochhalten").count() == 0, "Hochhalten schließt per Tipp")
    pg.evaluate("S.pub.ranking = [{ teamName: 'Adler', place: 1, finishedAt: new Date().toISOString(), solved: 5 }]; render()")
    pruef("Zieleinlauf" in pg.inner_text("#inhalt") and pg.locator("#app > .panel").count() == 0, "Zieleinlauf steht unten im Tab Team, nicht hinter der Hülle")
    pg.goto(f"{BASIS}/app.html?szenario=leitung-unterwegs"); pg.wait_for_selector(".ph"); pg.click(".ftabs [data-tab=team]")
    pruef(pg.locator("#inhalt [data-act=pub-hoch]").count() == 1, "Tab Team (Leitung): Team-Zeichen zum Hochhalten")
    pg.click("#inhalt [data-act=pub-hoch]")
    pruef(pg.locator(".hochhalten").count() == 1, "Leitung: Hochhalten-Fenster")
    pg.click(".hochhalten")
    # R1: Abmelden setzt den Tab zurück
    pg.click("[data-act=t-logout-frage]"); pg.click("[data-act=t-logout]")
    pruef(pg.evaluate("S.team.tab") == "weg", "Abmelden setzt den Tab auf Weg zurück")
    # R2: ohne Hülle ist kein Hilfe-Blatt offen
    pg.goto(f"{BASIS}/app.html?szenario=leitung-unterwegs"); pg.wait_for_selector(".ph")
    pg.evaluate("S.team.hilfe = true; S.team.state.status = 'drawn'; render()")
    pruef(pg.evaluate("S.team.hilfe") is False, "Hilfe-Blatt-Zustand fällt ohne Hülle zurück")
    # M1: Testmodus-Hinweis auch ohne Hülle
    pg.goto(f"{BASIS}/app.html?szenario=leitung-startklar"); pg.wait_for_selector("#app > *")
    pg.evaluate("S.team.state.testMode = true; render()")
    pruef("Testmodus" in pg.inner_text("#app"), "Phase ohne Hülle zeigt den Testmodus-Hinweis")
    # M2: Fehlversuchszeile bricht um statt zu überlaufen
    pg.set_viewport_size({"width": 320, "height": 700})
    pg.goto(f"{BASIS}/app.html?szenario=leitung-raetsel"); pg.wait_for_selector("#leiste #tans")
    sw = pg.evaluate("(() => { const l = document.querySelector('#leiste'); return [l.scrollWidth, l.clientWidth]; })()")
    pruef(sw[0] <= sw[1], f"320 px: Leiste läuft nicht über {sw}")
    pg.set_viewport_size({"width": 390, "height": 844})
    # M3: eine Schwelle für Marker und Problemliste
    pruef(pg.evaluate("drawMap.toString().includes('GPS_ALT_MS') && !drawMap.toString().includes('180000')"), "Karte nutzt GPS_ALT_MS")
    # I1 und I3
    pg.set_viewport_size({"width": 820, "height": 1180})
    pg.goto(f"{BASIS}/app.html?szenario=admin-probleme"); pg.wait_for_selector(".ohnepos [data-act=a-sel]"); pg.wait_for_selector("#map .leaflet-marker-icon", timeout=25000)
    pg.click(".ohnepos [data-act=a-sel]"); sel = pg.evaluate("S.admin.sel")
    pg.click(".ohnepos [data-act=a-sel]"); pg.wait_for_timeout(1200)
    r = pg.locator("#teamfeld .row.sel").bounding_box(); vh = pg.evaluate("innerHeight")
    pruef(pg.evaluate("S.admin.sel") == sel and r and 0 <= r["y"] and r["y"] + r["height"] <= vh + 1, f"kein Standort: zweites Tippen wählt wieder, Zeile im Bild ({r and r['y']:.0f})")
    ev = pg.evaluate("ereignisse(S.admin.state).map(e => e.text)")
    pruef(ev and all(not __import__("re").search(r"(Station|Platz) \d", x) for x in ev) and any(" " in x for x in ev), f"Zuletzt: Nummern bleiben beim Wort {ev[:3]}")
    pg.set_viewport_size({"width": 390, "height": 844})

    pruef(not err, f"keine Seitenfehler {err[:2]}")
    b.close()

print("\nOK" if not fehler else "\nFEHLT: " + "; ".join(fehler))
sys.exit(1 if fehler else 0)
