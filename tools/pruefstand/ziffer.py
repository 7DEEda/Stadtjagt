#!/usr/bin/env python3
"""
Rückfrage beim Ändern einer Ziffer im laufenden Spiel im Prüfstand prüfen, ohne Datenbank.

    python tools/pruefstand/ziffer.py

Station 1 haben im Szenario admin-stationen elf Teams gelöst: neue Ziffer fragt nach,
"Abbrechen" lässt das Getippte stehen, "Ziffer ändern" speichert, gleiche Ziffer fragt nicht.
Station 5 hat nur ein Team gelöst: Text in der Einzahl. Im Vordergrund mit Timeout aufrufen.
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


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8814), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
fehler = []


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1180, "height": 820}); pg.set_default_timeout(15000); err = []
    pg.on("pageerror", lambda e: err.append(str(e)))
    pg.goto("http://127.0.0.1:8814/app.html?szenario=admin-stationen"); pg.wait_for_selector("[data-act=a-edit]")
    st = pg.evaluate("S.admin.state.stations.map(s => ({ id: s.id, pos: s.position, digit: s.digit }))")
    erste, letzte = st[0], st[-1]
    geloest = pg.evaluate(f"S.admin.state.teams.filter(t => (t.solved || 0) >= {erste['pos']}).map(t => t.name)")
    print(f"Station 1 gelöst von {len(geloest)} Teams")

    print("Station 1, neue Ziffer")
    pg.click(f"[data-act=a-edit][data-id='{erste['id']}']"); pg.wait_for_selector("#e-digit")
    neu = str((erste["digit"] + 5) % 10)
    pg.fill("#e-digit", neu); pg.fill("#e-hint", "Geänderter Hinweis")
    pg.evaluate("window.__GESPEICHERT = null")
    pg.click("[data-act=a-save]"); pg.wait_for_selector(".dialog")
    t = pg.inner_text(".dialog")
    pruef("Ziffer von Station 1 ändern" in t and f"verlangt der Koffer die {neu}" in t, "Rückfrage mit alter und neuer Ziffer")
    pruef(pg.evaluate("window.__GESPEICHERT") is None, "noch nichts gespeichert")
    pg.screenshot(path=str(HIER / "shots" / "ziffer-rueckfrage.png"))
    pg.click("[data-act=a-dlg-cancel]"); pg.wait_for_selector(".dialog", state="detached")
    pruef(pg.input_value("#e-digit") == neu and pg.input_value("#e-hint") == "Geänderter Hinweis", "Abbrechen: Getipptes steht noch")
    pg.click("[data-act=a-save]"); pg.wait_for_selector(".dialog"); pg.click("#dlgok")
    pg.wait_for_function("window.__GESPEICHERT")
    g = pg.evaluate("window.__GESPEICHERT")
    pruef(g["p_digit"] == int(neu) and g["p_hint"] == "Geänderter Hinweis", f"Ziffer ändern: gespeichert ({g['p_digit']}, {g['p_hint']!r})")
    pruef("Die neue Ziffer ist " + neu in pg.inner_text("#app"), "Meldung nennt die neue Ziffer")

    print("Station 1, gleiche Ziffer")
    pg.click(f"[data-act=a-edit][data-id='{erste['id']}']"); pg.wait_for_selector("#e-digit")
    pg.evaluate("window.__GESPEICHERT = null"); pg.fill("#e-hint", "Nur Text")
    pg.click("[data-act=a-save]"); pg.wait_for_function("window.__GESPEICHERT")
    pruef(pg.locator(".dialog").count() == 0, "keine Rückfrage, wenn die Ziffer bleibt")

    print("Station 5, nur ein Team im Ziel")
    wer = pg.evaluate(f"S.admin.state.teams.filter(t => (t.solved || 0) >= {letzte['pos']}).map(t => t.name)")
    pg.click(f"[data-act=a-edit][data-id='{letzte['id']}']"); pg.wait_for_selector("#e-digit")
    pg.fill("#e-digit", str((letzte["digit"] + 1) % 10)); pg.click("[data-act=a-save]"); pg.wait_for_selector(".dialog")
    t = pg.inner_text(".dialog")
    pruef(len(wer) == 1 and f"Team {wer[0]} hat Station {letzte['pos']}" in t and "dem Team" in t, f"Einzahl: {wer}")
    pg.click("[data-act=a-dlg-cancel]")
    pruef(not err, f"keine Skriptfehler {err[:2]}")
    b.close()
srv.shutdown()
print("FEHLER: " + str(len(fehler)) if fehler else "OK")
sys.exit(1 if fehler else 0)
