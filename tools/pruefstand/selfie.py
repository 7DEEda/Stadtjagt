#!/usr/bin/env python3
"""
Gruppenselfie (Nachtrag 25) im Prüfstand durchspielen, ohne Datenbank und ohne Kamera.

    python tools/pruefstand/selfie.py

Baut app.html, öffnet die Selfie-Szenarien aus mock.js und spielt den Ablauf:
Aufnahme über die Dateiauswahl (ein gemaltes JPEG), Vorschau, Senden, Ziffer,
Album, Ersetzen, Funkloch mit Nachreichen, Überspringen, dazu Mitglied,
Anmeldung, Schalter aus und die Galerie der Spielleitung mit ZIP.
Fotos der Zustände landen in shots/selfie-*.png. Im Vordergrund mit Timeout
aufrufen. Am Ende steht OK oder die Zahl der Fehler.
"""
import sys, threading, functools, http.server, pathlib, base64, zipfile, io
sys.stdout.reconfigure(encoding="utf-8")
HIER = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HIER))
import shoot; shoot.bauen()
from playwright.sync_api import sync_playwright
class Leise(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8803), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
SHOTS = str(HIER / "shots") + "/selfie-"
(HIER / "shots").mkdir(exist_ok=True)
fehler = []
def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok: fehler.append(text)
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)
    c = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    pg = c.new_page(); pg.set_default_timeout(15000); err = []
    pg.on("pageerror", lambda e: err.append(str(e)))
    url = lambda s: f"http://127.0.0.1:8803/app.html?szenario={s}"
    # ein echtes JPEG für die Dateiauswahl, im Browser gemalt
    pg.goto(url("selfie-offen")); pg.wait_for_selector("[data-act=t-selfie]")
    jpg = base64.b64decode(pg.evaluate("""() => { const c = document.createElement("canvas"); c.width = 2000; c.height = 1500; const g = c.getContext("2d");
      g.fillStyle = "#4a8"; g.fillRect(0, 0, 2000, 1500); g.fillStyle = "#fc9"; for (let i = 0; i < 5; i++) { g.beginPath(); g.arc(300 + i * 350, 700, 150, 0, 7); g.fill(); }
      return c.toDataURL("image/jpeg", .9).split(",")[1]; }"""))
    datei = {"name": "selfie.jpg", "mimeType": "image/jpeg", "buffer": jpg}
    def aufnehmen(sel):
        with pg.expect_file_chooser() as fc: pg.click(sel)
        fc.value.set_files(datei)
    handy = "Object.keys(localStorage).filter(k => k.startsWith(\"sj.foto.\")).length"

    print("Teamleitung, Station 3 gelöst, Foto offen")
    z = pg.evaluate("S.team.state.digits"); pruef(z[2] is None and z[1] is not None, f"Ziffer 3 wird zurückgehalten: {z}")
    pruef("Gruppenselfie" in pg.inner_text("#app"), "Selfie-Schritt steht statt der nächsten Station")
    pruef(pg.locator("[data-act=t-check], [data-act=t-gps]").count() == 0, "kein Einchecken, solange das Foto offen ist")
    pg.screenshot(path=SHOTS + "1.png", full_page=True)
    aufnehmen("[data-act=t-selfie]"); pg.wait_for_selector("img.foto")
    g = pg.evaluate("({l: S.selfie.foto.length, t: S.selfie.thumb.length, w: document.querySelector(\"img.foto\").naturalWidth})")
    pruef(g["w"] == 1280 and g["l"] < 933000 and g["t"] < 80000, f"verkleinert auf {g['w']} px, {g['l'] * 3 // 4 // 1024} KB, Vorschau {g['t'] * 3 // 4 // 1024} KB")
    pg.screenshot(path=SHOTS + "2.png")
    pg.click("[data-act=t-selfie-ok]"); pg.wait_for_selector(".msg.ok")
    z = pg.evaluate("S.team.state.digits"); t = pg.inner_text(".msg.ok")
    pruef(z[2] is not None and "Ziffer" in t, f"nach dem Foto: Ziffer da, Meldung: {t}")
    pruef(pg.locator("[data-act=t-gps], [data-act=t-check]").count() > 0, "danach steht die nächste Station da")
    pg.click(".ftabs [data-tab=team]"); pg.wait_for_function("document.querySelectorAll(\".album button img\").length === 3"); pruef(True, "Album zeigt drei Fotos")
    pg.screenshot(path=SHOTS + "3.png", full_page=True)

    print("Foto groß und ersetzen")
    pg.click(".album button:nth-of-type(3)"); pg.wait_for_selector(".fotogross a[download]")
    pruef(pg.locator("[data-act=t-foto-ersetzen]").count() == 1, "jüngstes Foto: Neu aufnehmen wird angeboten")
    pg.screenshot(path=SHOTS + "4.png")
    aufnehmen("[data-act=t-foto-ersetzen]"); pg.wait_for_selector("img.foto")
    pruef("Foto ersetzen" in pg.inner_text("#app"), "Ersetzen zeigt die Vorschau")
    pg.click("[data-act=t-selfie-ok]"); pg.wait_for_selector(".msg.ok"); pruef("neue Foto" in pg.inner_text(".msg.ok"), "ersetzt: " + pg.inner_text(".msg.ok"))
    pg.click(".ftabs [data-tab=team]"); pg.wait_for_selector(".album button img")
    pg.click(".album button:nth-of-type(1)"); pg.wait_for_selector(".fotogross")
    pruef(pg.locator("[data-act=t-foto-ersetzen]").count() == 0, "älteres Foto: kein Neu aufnehmen")
    pg.keyboard.press("Escape"); pruef(pg.locator(".fotogross").count() == 0, "Escape schließt das große Foto")

    print("Funkloch beim Hochladen")
    pg.goto(url("selfie-offen")); pg.wait_for_selector("[data-act=t-selfie]")
    aufnehmen("[data-act=t-selfie]"); pg.wait_for_selector("img.foto")
    pg.evaluate("window.__funkloch = true")
    pg.click("[data-act=t-selfie-ok]"); pg.wait_for_selector(".msg.err")
    pruef(pg.locator("[data-act=t-selfie-skip]").count() == 1, "Fehler: " + pg.inner_text(".msg.err"))
    pruef(pg.evaluate(handy) == 1, "Foto liegt auf dem Handy")
    pg.screenshot(path=SHOTS + "5.png")
    pg.evaluate("window.__funkloch = \"nur-foto\"")
    pg.click("[data-act=t-selfie-skip]"); pg.wait_for_selector(".msg.ok")
    z = pg.evaluate("S.team.state.digits"); pruef(z[2] is not None, "Ohne Hochladen weiter: Ziffer da. " + pg.inner_text(".msg.ok"))
    pg.evaluate("window.__funkloch = false; fotoNachreichZeit = 0; teamStandSetzen(S.team.state)")
    pg.wait_for_function("S.team.state.selfie.photos.length === 3")
    pruef(pg.evaluate(handy) == 0, "Netz zurück: Foto nachgereicht, Handy-Kopie weg")

    print("Kamera streikt")
    pg.goto(url("selfie-offen")); pg.wait_for_selector("[data-act=t-selfie]")
    pruef(pg.locator("[data-act=t-selfie-skip]").count() == 0, "Überspringen erscheint nicht von Anfang an")
    with pg.expect_file_chooser() as fc: pg.click("[data-act=t-selfie]")
    fc.value.set_files([]); pg.evaluate("render()")
    pruef(pg.locator("[data-act=t-selfie-skip]").count() == 1, "nach einem Versuch: Ohne Foto weiter")

    print("Mitglied, Anmeldung, Schalter aus, Spielleitung")
    pg.goto(url("selfie-mitglied")); pg.wait_for_selector(".album")
    t = pg.inner_text("#app"); pruef("fürs Gruppenselfie" in t and pg.locator("[data-act=t-selfie]").count() == 0, "Mitglied sieht den Hinweis, keinen Knopf")
    pg.wait_for_selector(".album button img"); pg.screenshot(path=SHOTS + "6.png", full_page=True)
    pg.goto(url("selfie-anmeldung")); pg.wait_for_selector("[data-act=pub-reg]")
    pruef("Gruppenfoto" in pg.inner_text("#app"), "Anmeldung nennt die Fotos")
    pg.goto(url("anmeldung-leer")); pg.wait_for_selector("[data-act=pub-reg]")
    pruef("Gruppenfoto" not in pg.inner_text("#app"), "Schalter aus: Anmeldung ohne Hinweis")
    pg.goto(url("leitung-unterwegs")); pg.wait_for_selector("[data-act=t-gps]")
    pruef(pg.locator(".album").count() == 0 and pg.evaluate("S.team.state.digits[0]") is not None, "Schalter aus: kein Album, Ziffer sofort")
    pg.set_viewport_size({"width": 900, "height": 900})
    pg.goto(url("admin-fotos")); pg.wait_for_selector(".galerie img")
    pg.wait_for_timeout(1500); pg.screenshot(path=SHOTS + "7-admin.png", full_page=True)
    n = pg.evaluate("S.admin.fotos.length")
    with pg.expect_download() as dl: pg.click("[data-act=a-fotos-zip]")
    z = zipfile.ZipFile(io.BytesIO(pathlib.Path(dl.value.path()).read_bytes()))
    pruef(z.testzip() is None and len(z.namelist()) == n, f"ZIP mit {len(z.namelist())} Fotos, lesbar, z. B. {z.namelist()[0]}")
    pruef(z.read(z.namelist()[0])[:3] == b"\xff\xd8\xff", "Dateien im ZIP sind JPEGs")
    pg.click("[data-act=a-selfie][data-on=\"0\"]"); pg.wait_for_function("S.admin.state.selfieOn === false && !S.busy")
    pruef("Gruppenselfie ist aus" in pg.inner_text("#app"), "Ausschalten meldet sich und der Schalter steht auf aus")
    pruef(not err, f"keine Skriptfehler {err[:2]}")
    b.close()
srv.shutdown()
print("FEHLER: " + str(len(fehler))) if fehler else print("OK")
sys.exit(1 if fehler else 0)
