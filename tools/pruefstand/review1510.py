#!/usr/bin/env python3
"""
Befunde des Code-Reviews vom 15.10.2026 im Prüfstand, ohne Datenbank.

    python tools/pruefstand/review1510.py          alle
    python tools/pruefstand/review1510.py 1 5      nur diese Befunde

Spiel (app.html mit mock.js, Port 8862). Der 10-s-Abruf läuft über die Playwright-Uhr (clock.fast_forward).
Die Datenbank-Seite von Befund 3 prüft namenssuche_grenze_db.py. Im Vordergrund mit Timeout aufrufen.
Am Ende steht OK oder FEHLT.
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


PORT = 8862
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
APP = f"http://127.0.0.1:{PORT}/app.html?szenario="
NUR = {int(x) for x in sys.argv[1:] if x.isdigit()}
an = lambda n: not NUR or n in NUR
fehler, err = [], []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def neu(b, szenario, breit=False, uhr=False):
    pg = b.new_page(viewport={"width": 1440, "height": 900} if breit else {"width": 390, "height": 844})
    pg.set_default_timeout(15000)
    pg.on("pageerror", lambda e: err.append(f"{szenario}: {e}"))
    if uhr:
        pg.clock.install()
    pg.goto(APP + szenario)
    pg.wait_for_function("window.__fertig === true", timeout=30000)
    return pg


def takt(pg):
    """Ein 10-s-Abruf: Uhr vorstellen, Antworten abwarten."""
    pg.clock.fast_forward(10000)
    pg.wait_for_timeout(700)


with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)

    if an(1):
        print("Befund 1: Teamliste und Zähler im 10-s-Abruf")
        pg = neu(b, "admin-probleme", breit=True, uhr=True)
        pg.wait_for_selector("#map .leaflet-marker-icon", timeout=25000)
        pruef("3 Teams brauchen dich" in pg.inner_text("[data-act=a-probleme]"), "vorher: 3 Teams brauchen dich")
        pg.click("#teamfeld .row:has-text('Otter') .row-main"); pg.wait_for_selector("#teamfeld .row.sel .detail")
        pg.locator("#teamfeld").evaluate("e => e.scrollTop = 120")
        # Delfin meldet ab jetzt einen frischen Standort
        pg.evaluate("""() => { const alt = rpc; window.__frisch = ['Delfin']; window.rpc = async (fn, a) => { const r = await alt(fn, a);
          if (fn === 'admin_state') (r.teams || []).forEach(t => { if (window.__frisch.includes(t.name))
            t.position = { lat: 50.1024, lng: 14.4316, accuracy: 9, updatedAt: new Date().toISOString() }; });
          return r; }; }""")
        takt(pg)
        pruef("2 Teams brauchen dich" in pg.inner_text("[data-act=a-probleme]"), f"Zähler nachgezogen ({pg.inner_text('[data-act=a-probleme]')})")
        grp = pg.locator("#teamfeld .grp").all_inner_texts()
        pruef(grp and grp[0].startswith("Braucht dich · 2"), f"Teamliste nachgezogen ({grp})")
        pruef("Delfin" not in "".join(pg.locator("#teamfeld .row.p-fehler, #teamfeld .row.p-warn").all_inner_texts()), "Delfin nicht mehr unter Braucht dich")
        sel = pg.locator("#teamfeld .row.sel")
        pruef(sel.count() == 1 and "Otter" in sel.inner_text() and sel.locator(".detail").count() == 1, "Auswahl und aufgeklappte Zeile bleiben")
        pruef(pg.locator("#teamfeld").evaluate("e => e.scrollTop") == 120, f"Scrollstand bleibt ({pg.locator('#teamfeld').evaluate('e => e.scrollTop')})")
        # Auswahlfeld Teamleitung offen (Fokus): die Liste bleibt unangetastet
        pg.evaluate("() => { const s = document.querySelector('#teamfeld .row.sel select'); s.__mark = 1; s.focus(); window.__frisch.push('Igel'); }")
        takt(pg)
        pruef(pg.evaluate("document.activeElement && document.activeElement.__mark === 1"), "offenes Auswahlfeld bleibt stehen und behält den Fokus")
        pg.evaluate("document.activeElement.blur()")
        takt(pg)
        pruef("1 Team braucht dich" in pg.inner_text("[data-act=a-probleme]"), f"nach dem Auswahlfeld wieder nachgezogen ({pg.inner_text('[data-act=a-probleme]')})")
        # Dialog offen: nicht anfassen
        pg.click("#teamfeld .row:has-text('Otter') .btn[data-key=solve]"); pg.wait_for_selector("#dlgok")
        pg.evaluate("() => { document.querySelector('#teamfeld').__mark = 1; document.querySelector('#teamfeld .tliste').__mark = 1; window.__frisch.length = 0; }")
        takt(pg)
        pruef(pg.evaluate("document.querySelector('#teamfeld .tliste').__mark === 1") and pg.locator(".overlay").count() == 1, "offener Dialog: Liste unangetastet")
        pg.click("[data-act=a-dlg-cancel]")
        pg.close()

    if an(2):
        print("Befund 2: Denkpause gehört zu Braucht dich")
        pg = neu(b, "admin-probleme", breit=True)
        pg.wait_for_selector("#teamfeld .row")
        pg.evaluate("""() => { const t = S.admin.state.teams.find(x => x.name === 'Fuchs');
          t.failedAttempts = 0; t.checkedInAt = new Date().toISOString(); t.lockedUntil = new Date(Date.now() + 90000).toISOString(); S.admin.sel = t.id; render(); }""")
        z = pg.locator("#teamfeld .row:has-text('Fuchs')")
        pruef("p-warn" in (z.get_attribute("class") or ""), "Fuchs in der Denkpause: Warnung")
        bis = pg.evaluate("uhrzeit(S.admin.state.teams.find(x => x.name === 'Fuchs').lockedUntil)")
        pruef(f"Denkpause bis {bis}" in z.inner_text(), f"Kurztext 'Denkpause bis {bis}' ({z.inner_text()[:80]!r})")
        pruef("werten" in z.locator(".detail").inner_text(), "Text nennt das Werten des Rätsels")
        pruef(pg.locator("#teamfeld .grp").first.inner_text().startswith("Braucht dich · 4"), "Fuchs zählt unter Braucht dich")
        pruef("4 Teams brauchen dich" in pg.inner_text("[data-act=a-probleme]"), "Zähler im Kopf zählt Fuchs mit")
        pg.evaluate("S.admin.state.teams.find(x => x.name === 'Fuchs').lockedUntil = new Date(Date.now() - 1000).toISOString(); render()")
        pruef("p-warn" not in (pg.locator("#teamfeld .row:has-text('Fuchs')").get_attribute("class") or ""), "abgelaufene Denkpause: wieder normal")
        pg.close()

    if an(4):
        print("Befund 4: Zeitachse wirkt nicht auf die Live-Karte")
        pg = neu(b, "admin-karte", breit=True)
        pg.click("[data-act=a-tab][data-tab=zeit]"); pg.wait_for_selector("#tlslider")
        pg.wait_for_function("S.admin.window && S.admin.window.start")
        pg.click("#tlplay"); pg.wait_for_timeout(300)
        pruef(pg.evaluate("S.admin.playing") is True, "Abspielen läuft")
        pg.click("[data-act=a-tab][data-tab=live]"); pg.wait_for_timeout(300)
        pruef(pg.evaluate("S.admin.playing") is False and pg.evaluate("S.admin.cursor") is None, "Reiter live: Abspielen gestoppt, Cursor auf jetzt")
        pg.click("[data-act=a-tab][data-tab=zeit]"); pg.wait_for_selector("#tlslider")
        pg.evaluate("() => { const s = document.querySelector('#tlslider'); s.value = 300; s.dispatchEvent(new Event('input', { bubbles: true })); }")
        pruef(pg.evaluate("S.admin.cursor") is not None, "Schieber setzt einen Zeitpunkt")
        pg.click("[data-act=a-tab][data-tab=people]"); pg.click("[data-act=a-tab][data-tab=live]")
        pruef(pg.evaluate("S.admin.cursor") is None, "über einen anderen Reiter zurück: Cursor auf jetzt")
        pg.click("[data-act=a-tab][data-tab=zeit]"); pg.wait_for_selector("#tlslider"); pg.click("#tlplay"); pg.wait_for_timeout(200)
        pg.click("[data-act=a-probleme]"); pg.wait_for_timeout(300)
        pruef(pg.evaluate("S.admin.tab") == "live" and pg.evaluate("S.admin.playing") is False and pg.evaluate("S.admin.cursor") is None,
              "Zähler im Kopf aus der Zeitachse: Abspielen gestoppt, Cursor auf jetzt")
        pg.close()

    if an(5):
        print("Befund 5: Hochhalten und Hilfe-Blatt flackern nicht")
        pg = neu(b, "leitung-unterwegs", uhr=True)
        pg.evaluate("""() => { const alt = rpc; window.rpc = async (fn, a) => { const r = await alt(fn, a);
          if (fn === 'team_state' && window.__dazu) r.team.members = r.team.members.concat(['Neue Person']); return r; }; }""")
        pg.click(".ftabs [data-tab=team]"); pg.click("#inhalt [data-act=pub-hoch]")
        pg.evaluate("document.querySelector('.hochhalten').__mark = 1; window.__dazu = true; window.__RPC_LOG.length = 0")
        takt(pg)
        pruef("team_state" in pg.evaluate("window.__RPC_LOG"), "Teamleitung: der Abruf läuft trotzdem")
        pruef(pg.evaluate("!!document.querySelector('.hochhalten') && document.querySelector('.hochhalten').__mark === 1"), "Teamleitung: Hochhalten bleibt stehen")
        pg.click(".hochhalten")
        pruef(pg.inner_text(".ftabs [data-tab=team] .badge") == "9", "beim Schließen neu gezeichnet, mit den neuen Daten")
        pg.click(".kopf [data-act=t-hilfe]")
        pg.evaluate("document.querySelector('.blatt').__mark = 1")
        takt(pg)
        pruef(pg.evaluate("!!document.querySelector('.blatt') && document.querySelector('.blatt').__mark === 1"), "Teamleitung: Hilfe-Blatt bleibt stehen")
        pg.keyboard.press("Escape")
        pruef(pg.locator(".blatt").count() == 0, "Escape schließt das Blatt")
        pg.close()
        pg = neu(b, "mitglied-unterwegs", uhr=True)
        pg.click(".kopf [data-act=t-hilfe]")
        pg.evaluate("document.querySelector('.blatt').__mark = 1")
        takt(pg)
        pruef(pg.evaluate("!!document.querySelector('.blatt') && document.querySelector('.blatt').__mark === 1"), "Mitlesende: Hilfe-Blatt bleibt stehen")
        pg.keyboard.press("Escape")
        pg.click(".ftabs [data-tab=team]"); pg.click("#inhalt [data-act=pub-hoch]")
        pg.evaluate("document.querySelector('.hochhalten').__mark = 1")
        takt(pg)
        pruef(pg.evaluate("!!document.querySelector('.hochhalten') && document.querySelector('.hochhalten').__mark === 1"), "Mitlesende: Hochhalten bleibt stehen")
        pg.close()

    if an(6):
        print("Befund 6: Hochhalten hängt nach Spielende nicht fest")
        pg = neu(b, "leitung-unterwegs")
        pg.click(".ftabs [data-tab=team]"); pg.click("#inhalt [data-act=pub-hoch]")
        pruef(pg.evaluate("document.body.classList.contains('fest')"), "Hochhalten offen: Seite fest")
        pg.evaluate("S.team.state = Object.assign({}, S.team.state, { status: 'finished' }); render()")
        pruef(pg.locator(".ph").count() == 0, "Spielende: keine Hülle mehr")
        pruef(not pg.evaluate("document.body.classList.contains('fest')") and pg.evaluate("S.hoch") is False, "Seite wieder frei, Hochhalten zurückgesetzt")
        pg.close()

    if an(7):
        print("Befund 7: Teamliste im Reiter Auslosen mit Stil")
        pg = neu(b, "admin-bereit", breit=True)
        pg.wait_for_selector(".tliste .row")
        stil = pg.evaluate("""() => { const l = document.querySelector('.tliste'), r = l.querySelector('.row'), t = l.querySelector('.tier');
          return [getComputedStyle(l).listStyleType, getComputedStyle(r).borderBottomWidth, getComputedStyle(t).width, getComputedStyle(l.closest('.panel')).paddingTop]; }""")
        pruef(stil == ["none", "1px", "40px", "0px"], f"Liste wie im Reiter live gestaltet ({stil})")
        pg.close()

    if an(8):
        print("Befund 8: Erfolgsmeldungen der Leiste auf jedem Tab")
        pg = neu(b, "leitung-testmodus")
        pg.click(".ftabs [data-tab=team]")
        pg.click("#leiste [data-act=t-check]"); pg.wait_for_selector("#leiste #tans")
        pruef("eingecheckt" in pg.inner_text("#leiste"), f"Einchecken: Meldung in der Leiste ({pg.inner_text('#leiste')[:80]!r})")
        pg.fill("#tans", "x"); pg.click("#leiste [data-act=t-answer]"); pg.wait_for_selector("#leiste #tcheck")
        pruef("Richtig" in pg.inner_text("#leiste"), f"Antwort: Meldung in der Leiste ({pg.inner_text('#leiste')[:80]!r})")
        pg.click(".ftabs [data-tab=weg]")
        pruef(pg.inner_text("#app").count("Richtig") == 1, "Meldung steht genau einmal da")
        pg.close()
        # Koffer ohne Standort: Testmodus nur auf dem Handy, der Prüfstand prüft am Koffer keine Entfernung
        pg = neu(b, "leitung-koffer")
        pg.evaluate("S.team.state.testMode = true; render()")
        pg.click(".ftabs [data-tab=team]")
        pg.fill("#tfin", "371955"); pg.click("#leiste [data-act=t-final]"); pg.wait_for_timeout(600)
        pruef(pg.locator(".ph").count() == 0 and "Koffer offen" in pg.inner_text("#app"), "Koffer offen: Meldung steht im Platz-Bildschirm (ohne Hülle)")
        pg.close()

    if an(9):
        print("Befund 9: alte Karte wird abgebaut")
        pg = neu(b, "admin-probleme", breit=True)
        pg.wait_for_selector("#map .leaflet-marker-icon", timeout=25000)
        pg.evaluate("window.__alteKarte = map; render()")
        pg.wait_for_function("map !== window.__alteKarte && document.querySelector('#map .leaflet-marker-icon')", timeout=25000)
        pruef(pg.evaluate("Object.keys(window.__alteKarte._layers).length === 0 && window.__alteKarte._containerId === undefined"), "render(): alte Karte mit remove() abgebaut")
        # Abbau mitten in einer Zoom-Animation: deren Ende darf nicht über die abgebaute Karte fallen
        n = len(err)
        pg.evaluate("map.setZoom(map.getZoom() + 1)"); pg.wait_for_function("map._animatingZoom === true", timeout=3000)
        pg.evaluate("render()"); pg.wait_for_timeout(900)
        pruef(len(err) == n, f"Abbau während Zoom-Animation ohne Seitenfehler {err[n:n + 1]}")
        pg.evaluate("window.__karte = map")
        pg.click("#teamfeld .row:has-text('Otter') .row-main"); pg.wait_for_timeout(800)
        pruef(pg.evaluate("map === window.__karte") and pg.locator("#teamfeld .row.sel").count() == 1 and pg.locator(".mapbadge.team.sel").count() == 1,
              "Auswahl in der Liste: Karte bleibt, Zeile und Marker hervorgehoben")
        pg.click(".ohnepos [data-act=a-sel]"); pg.wait_for_timeout(800)
        pruef(pg.evaluate("map === window.__karte") and "Delfin" in pg.locator("#teamfeld .row.sel").inner_text(), "kein Standort: wählt ohne Neubau")
        pg.evaluate("layers.teams[S.admin.state.teams.find(x => x.name === 'Igel').id].fire('click')"); pg.wait_for_timeout(800)
        pruef(pg.evaluate("map === window.__karte") and "Igel" in pg.locator("#teamfeld .row.sel").inner_text() and pg.locator(".leaflet-popup").count() == 1,
              "Marker-Klick: wählt ohne Neubau, Popup offen")
        pg.evaluate("window.__alteKarte = map; render()")
        pg.wait_for_function("map !== window.__alteKarte && document.querySelector('#map .leaflet-marker-icon')", timeout=25000); pg.wait_for_timeout(500)
        pruef(pg.locator(".leaflet-popup").count() == 1 and pg.evaluate("S.admin.popupAuf") is not None, "Neubau nach Marker-Klick: Popup wieder offen")
        pg.click("[data-act=a-probleme]"); pg.wait_for_timeout(800)
        pruef("Delfin" in pg.locator("#teamfeld .row.sel").inner_text(), "Zähler im Kopf wählt das erste Problem")
        pg.close()
        pg = neu(b, "admin-station-karte", breit=True)
        pg.wait_for_selector("#emap .leaflet-marker-icon", timeout=25000)
        pg.evaluate("window.__alteKarte = ekarte.map; render()")
        pg.wait_for_function("ekarte && ekarte.map !== window.__alteKarte", timeout=25000)
        pruef(pg.evaluate("Object.keys(window.__alteKarte._layers).length === 0"), "Station bearbeiten: alte Karte mit remove() abgebaut")
        n = len(err)
        pg.evaluate("render(); setTimeout(render, 20)"); pg.wait_for_timeout(700)
        pruef(len(err) == n, f"Station bearbeiten: zweimal schnell neu gezeichnet ohne Seitenfehler {err[n:n + 1]}")
        pg.close()

    if an(10):
        print("Befund 10: toter Zweig, Reitername, Hinweis Neu auslosen")
        pg = neu(b, "admin-karte", breit=True)
        pruef("if (laeuft)" not in pg.evaluate("viewAdmin.toString()"), "kein toter Zweig im Reiter Auslosen")
        pg.click("[data-act=a-tab][data-tab=danger]")
        t = pg.inner_text(".inhalt900")
        pruef("Reiter Teams" not in t and "Fortschritt zurücksetzen" in t and "Neu auslosen geht erst wieder" in t, f"laufendes Spiel: Hinweis aufs Zurücksetzen ({t[-160:]!r})")
        pg.close()
        pg = neu(b, "admin-auslosen", breit=True)
        pg.click("[data-act=a-tab][data-tab=danger]")
        t = pg.inner_text(".inhalt900")
        pruef("Reiter Auslosen" in t and "Reiter Teams" not in t, f"vor dem Start: Reiter Auslosen ({t[-120:]!r})")
        pg.close()
        pg = neu(b, "leitung-login")
        pg.click("[data-act=t-codefeld]")
        pruef("Reiter Teams" not in pg.inner_text("#app") and "Reiter Karte und Teams" in pg.inner_text("#app"), "Code-Feld nennt den heutigen Reiter")
        pg.close()
        pg = neu(b, "admin-start-dialog", breit=True)
        pg.click("#dlgok"); pg.wait_for_timeout(600)
        pruef(pg.evaluate("S.admin.tab") == "live" and pg.locator("#map").count() == 1, f"nach Spiel starten steht der Reiter Karte und Teams ({pg.evaluate('S.admin.tab')})")
        pg.close()

    pruef(not err, f"keine Seitenfehler {err[:3]}")
    # Ergebnis vor dem Schließen: Chrome 155 hängt hier beim Schließen nach Seiten mit Leaflet-Karte (15.10.2026)
    print("\nOK" if not fehler else "\nFEHLT: " + "; ".join(fehler), flush=True)
    import os
    os._exit(1 if fehler else 0)
