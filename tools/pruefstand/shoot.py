"""Prüfstand Stadtjagd: baut app.html aus der echten index.html (nur ein <script src="mock.js"> davor),
startet einen lokalen Webserver auf Port 8791, fotografiert alle Szenarien und beendet den Server wieder.

    python shoot.py                 alles
    python shoot.py teamsuche ...   nur diese Szenarien (alle Profile, die für sie vorgesehen sind)
    python shoot.py --build         nur app.html neu bauen
"""
import functools, http.server, json, pathlib, sys, threading, time

HIER = pathlib.Path(__file__).resolve().parent
REPO = HIER.parent.parent   # tools/pruefstand liegt im Repo
SHOTS = HIER / "shots"
PORT = 8791


def bauen():
    src = (REPO / "index.html").read_text(encoding="utf-8")
    i = src.index("<script")
    app = src[:i] + '<script src="mock.js"></script>\n' + src[i:]
    (HIER / "app.html").write_text(app, encoding="utf-8")
    # config.js und die Hintergründe neben app.html, damit relative Pfade tragen
    import shutil
    shutil.copy(REPO / "config.js", HIER / "config.js")
    shutil.copytree(REPO / "hintergrund", HIER / "hintergrund", dirs_exist_ok=True)


UA_IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"
UA_ANDROID = "Mozilla/5.0 (Linux; Android 14; SM-A145R) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"
UA_IPAD = "Mozilla/5.0 (iPad; CPU OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"

PROFILE = {
    "hell": dict(w=390, h=844, ua=UA_IPHONE, scheme="light"),
    "dunkel": dict(w=390, h=844, ua=UA_IPHONE, scheme="dark"),
    "klein": dict(w=360, h=740, ua=UA_ANDROID, scheme="light"),
    "quer": dict(w=844, h=390, ua=UA_IPHONE, scheme="light"),
    "tablet-hoch": dict(w=820, h=1180, ua=UA_IPAD, scheme="light"),
    "tablet-quer": dict(w=1180, h=820, ua=UA_IPAD, scheme="light"),
    "tablet-768": dict(w=768, h=1024, ua=UA_IPAD, scheme="light"),
}

HANDY = ["anmeldung-leer", "anmeldung-angemeldet", "teamkarte-mitglied", "teamkarte-leitung", "hochhalten", "teamsuche",
         "leitung-login", "leitung-startklar", "leitung-startklar-kompass", "leitung-unterwegs", "leitung-unterwegs-standort",
         "leitung-kompass-ungenau", "leitung-kompass-einmessen", "leitung-checkin-abgelehnt", "leitung-raetsel",
         "leitung-raetsel-fehlversuch", "leitung-denkpause", "leitung-tipp", "leitung-koffer", "leitung-platz2",
         "leitung-platz5", "leitung-beendet", "leitung-testmodus", "mitglied-unterwegs", "mitglied-raetsel", "mitglied-beendet"]
KLEIN = ["anmeldung-leer", "teamkarte-mitglied", "leitung-unterwegs-standort", "leitung-raetsel-fehlversuch", "leitung-koffer", "leitung-startklar"]
ADMIN = ["admin-login", "admin-karte", "admin-teams", "admin-stationen", "admin-teilnehmende", "admin-loeschen", "admin-auslosen"]
NEU = ["admin-bereit", "admin-start-dialog", "admin-vollbild"]
OHNE_CODE = ["leitung-login", "leitung-ohne-code", "mitglied-auf-teamleitung", "anmeldung-angemeldet", "teamkarte-leitung"]

AUFTRAG = []
for s in HANDY:
    AUFTRAG += [(s, "hell"), (s, "dunkel")]
for s in KLEIN:
    AUFTRAG.append((s, "klein"))
AUFTRAG.append(("leitung-unterwegs-standort", "quer"))
for s in ADMIN:
    AUFTRAG += [(s, "tablet-hoch"), (s, "tablet-quer")]
AUFTRAG += [("admin-teams", "tablet-768"), ("admin-karte", "tablet-768")]
for s in NEU:
    AUFTRAG.append((s, "tablet-hoch"))
for s in ["leitung-ohne-code", "mitglied-auf-teamleitung"]:
    AUFTRAG.append((s, "hell"))


class Leise(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    bauen()
    if "--build" in sys.argv:
        return
    nur = [a for a in sys.argv[1:] if not a.startswith("-")]
    auftrag = [a for a in AUFTRAG if not nur or a[0] in nur]
    SHOTS.mkdir(exist_ok=True)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    bericht = {}
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", headless=True)
            for szenario, profil in auftrag:
                p = PROFILE[profil]
                ctx = browser.new_context(viewport={"width": p["w"], "height": p["h"]}, device_scale_factor=2,
                                          is_mobile=True, has_touch=True, user_agent=p["ua"], color_scheme=p["scheme"],
                                          locale="de-DE", timezone_id="Europe/Prague")
                page = ctx.new_page()
                fehler = []
                page.on("pageerror", lambda e: fehler.append("pageerror: " + str(e)))
                page.on("console", lambda m: fehler.append(m.type + ": " + m.text) if m.type in ("error", "warning") else None)
                t0 = time.time()
                page.goto(f"http://127.0.0.1:{PORT}/app.html?szenario={szenario}", wait_until="load", timeout=30000)
                try:
                    page.wait_for_function("window.__fertig === true", timeout=25000)
                except Exception as e:
                    fehler.append("nicht fertig: " + str(e).splitlines()[0])
                try:
                    page.wait_for_load_state("networkidle", timeout=6000)
                except Exception:
                    pass
                page.evaluate("document.fonts.ready")
                page.wait_for_timeout(300)
                datei = SHOTS / f"{szenario}-{profil}.png"
                # Liegt ein festes Vollbild darüber (Hochhalten, Dialog), zählt nur der Bildschirm: die Seite dahinter scrollt nicht
                fest = page.evaluate("document.body.classList.contains('fest')")
                page.screenshot(path=str(datei), full_page=not fest)
                info = page.evaluate("({rpc: window.__RPC_LOG, h: document.documentElement.scrollHeight, w: document.documentElement.scrollWidth, vw: innerWidth, fonts: [...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family+' '+f.weight)})")
                bericht[datei.name] = {"fehler": fehler, "sek": round(time.time() - t0, 1), **info}
                print(f"{datei.name}: {info['w']}x{info['h']} (vw {info['vw']}), {len(fehler)} Meldungen", flush=True)
                ctx.close()
            browser.close()
    finally:
        srv.shutdown()
        srv.server_close()
    alt = {}
    bp = HIER / "bericht.json"
    if bp.exists() and nur:
        alt = json.loads(bp.read_text(encoding="utf-8"))
    alt.update(bericht)
    bp.write_text(json.dumps(alt, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
