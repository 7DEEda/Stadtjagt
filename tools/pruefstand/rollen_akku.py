#!/usr/bin/env python3
"""
Rollen und Akku (29.10.2026): Rolle vom Server, Übergabe-Fenster, Akku lesen und melden, Akku-Hinweis und
Akku-Fenster, Spielleitung. Ohne Datenbank, gegen mock.js (Port 8873).

    python tools/pruefstand/rollen_akku.py          alle
    python tools/pruefstand/rollen_akku.py 2 6      nur diese Teile

Teile: 1 Mitglied wird Leitung und zurück (stilles Umschalten, ab Auslosen), 2 Leitung abgeben (Fenster mit Personen),
3 Spielleitung nimmt die Leitung weg, veraltete Antwort, 4 Notweg-Tablet (sj.hand), 5 Abmelden und sj.abgemeldet (F1),
6 Akku-Fenster bei 20 % und 10 %, 7 Akku-Hinweis, 8 Spielleitung (Vermerk, Braucht dich), 9 Meldungen mit Akku,
10 alte Datenbank (PGRST202), 11 iPhone ohne Akku, 12 Texte und Tippziele.
Haken in mock.js: window.__akku(level, laedt), __AKKUS, __MEMBER_ARGS, __REPORT_ARGS, __AKKU, __ALTE_DB, __leitung(name).
Der Mitlese-Link (F7) ist gestrichen und kommt hier nicht mehr vor.
Im Vordergrund mit Timeout aufrufen, etwa `timeout 590 python tools/pruefstand/rollen_akku.py`. Am Ende steht OK oder FEHLT.
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
import abschluss  # noqa: E402

shoot.bauen()
from playwright.sync_api import sync_playwright  # noqa: E402


class Leise(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


PORT = 8873
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Leise, directory=str(HIER)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
APP = f"http://127.0.0.1:{PORT}/app.html?szenario="
NUR = {int(x) for x in sys.argv[1:] if x.isdigit()}
an = lambda n: not NUR or n in NUR  # noqa: E731
fehler, err = [], []
QUELLE = (REPO / "index.html").read_text(encoding="utf-8")
DASH = "–—"


def pruef(ok, text):
    print(("  ok    " if ok else "  FEHLT ") + text)
    if not ok:
        fehler.append(text)


def neu(b, szenario, vorab=None, uhr=True, leaflet=False):
    pg = b.new_page(viewport={"width": 390, "height": 844})
    pg.set_default_timeout(15000)
    if not leaflet:
        pg.route("**/vendor/leaflet-1.9.4/**", lambda r: r.abort())
    pg.on("pageerror", lambda e: err.append(f"{szenario}: {e}"))
    pg.add_init_script("window.__h0 = history.length;")
    if vorab:
        pg.add_init_script(vorab)
    if uhr:
        pg.clock.install()
    pg.goto(APP + szenario)
    pg.wait_for_function("window.__fertig === true", timeout=30000)
    return pg


def takt(pg, ms=10000):
    pg.clock.fast_forward(ms)
    pg.wait_for_timeout(700)


def warte(pg, js, ms=8000):
    try:
        pg.wait_for_function(js, timeout=ms)
        return True
    except Exception:
        return False


def text(pg, sel="#app"):
    return pg.inner_text(sel).replace(" ", " ")


def ls(pg, k):
    return pg.evaluate(f"localStorage.getItem({k!r})")


def nachladen(pg, extra=""):
    """Neuladen wie auf dem Handy: Speicher und Adresse bleiben (window.__behalten)."""
    pg.add_init_script("window.__behalten = true;" + extra)
    pg.reload()
    pg.wait_for_function("window.__fertig === true", timeout=30000)


vorher = abschluss.merken()
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome", headless=True)

    if an(1):
        print("1 Mitglied wird Leitung und zurück")
        pg = neu(b, "rolle-leitung")
        pruef(warte(pg, "S.view === 'team' && S.team.state && S.team.code"), "Anna (Leitung) öffnet #/public und landet von selbst in der Teamleitung")
        pruef(pg.evaluate("location.hash") == "#/team", "Adresse still auf #/team ersetzt")
        pruef(pg.evaluate("history.length") == pg.evaluate("window.__h0"), "kein neuer Verlaufseintrag (Zurück-Taste führt nicht dorthin)")
        pruef(ls(pg, "sj.code") == "FUCHS-4821", "Code vom Server gemerkt (sj.code)")
        pruef(pg.locator("#kurz").count() == 1 and text(pg, "#kurz") == "Du leitest jetzt Team Fuchs", f"Einblendung: {text(pg, '#kurz') if pg.locator('#kurz').count() else ''!r}")
        pruef(pg.locator(".ph").count() == 1 and pg.locator("#leiste").count() == 1, "Ansicht der Teamleitung steht (Hülle mit Leiste)")
        pruef(pg.evaluate("S.mit") is None, "Mitlese-Stand verworfen")
        # kein Hin und Her: absichtlich auf die öffentliche Seite gehen, Leitung bleibt Leitung
        pg.evaluate("location.hash = '#/public'")
        pg.wait_for_timeout(800)
        takt(pg)
        takt(pg)
        pruef(pg.evaluate("S.view") == "public", "wer absichtlich auf #/public geht, wird nicht sofort zurückgeholt")
        pg.close()

        pg = neu(b, "rolle-leitung-vorstart")
        pruef(warte(pg, "S.view === 'team' && S.team.state"), "schon nach dem Auslosen (drawn) schaltet es um (F4)")
        pruef(pg.evaluate("S.team.state.status") == "drawn", "Stand ist drawn")
        pg.close()

        pg = neu(b, "rolle-mitglied")
        pruef(pg.evaluate("S.view") == "public" and warte(pg, "S.mit && S.mit.team"), "Jonas (Mitglied) bleibt beim Mitlesen")
        pruef(pg.evaluate("S.mit.ichLeite") is False, "member_state sagt ichLeite = false")
        pg.evaluate("window.__leitung('Jonas Keller')")
        takt(pg)
        pruef(warte(pg, "S.view === 'team' && S.team.state"), "die Spielleitung macht Jonas zur Leitung: sein Handy schaltet nach dem Abruf um")
        pruef(text(pg, "#kurz") == "Du leitest jetzt Team Fuchs", "Einblendung: Du leitest jetzt Team Fuchs")
        pruef(pg.evaluate("S.team.code") == "FUCHS-4821" and pg.evaluate("location.hash") == "#/team", "Code und Adresse stimmen")
        pg.evaluate("window.__leitung('Anna Berger')")
        takt(pg)
        pruef(warte(pg, "S.view === 'public' && S.mit && S.mit.team"), "Anna übernimmt wieder: Jonas liest wieder mit")
        pruef(text(pg, "#kurz") == "Anna leitet jetzt das Team", f"Einblendung: {text(pg, '#kurz') if pg.locator('#kurz').count() else ''!r}")
        pruef(pg.evaluate("S.team.code") is None and ls(pg, "sj.code") is None and ls(pg, "sj.letzter.team") is None, "Code und gemerkter Leitungsstand sind weg")
        pg.close()

    if an(2):
        print("2 Leitung abgeben: Fenster mit Personen")
        pg = neu(b, "akku-leitung")
        pg.click(".ftabs [data-tab=team]")
        pg.click("[data-act=t-abgeben-frage]")
        pruef(pg.locator(".ueber .blatt[role=dialog]").count() == 1, "Fenster steht")
        pruef(pg.locator("select").count() == 0, "keine Auswahlliste mehr")
        namen = pg.locator(".wahl button").all_inner_texts()
        namen = [n.replace(" ", " ").replace("\n", " | ") for n in namen]
        pruef(len(namen) == 6 and not any("Tobias" in n for n in namen), f"6 Personen, Tobias (ohne eigenes Handy) fehlt ({len(namen)})")
        pruef(namen[-1].startswith("Lea Hoffmann") and "Handy nicht verbunden" in namen[-1], f"nicht verbundenes Handy steht zuletzt: {namen[-1]!r}")
        pruef(any(n.startswith("Emre Demir") and "Akku 70 %, lädt" in n for n in namen), "Akku und 'lädt' stehen dran")
        pruef(any(n.startswith("Jonas Keller") and "Akku 81 %" in n for n in namen), "Jonas mit Akku 81 %")
        pruef(pg.locator("#tabgeben").is_disabled(), "'Übergeben' gesperrt ohne Wahl")
        hoehen = pg.evaluate("[...document.querySelectorAll('.blatt button')].map(e => e.getBoundingClientRect().height)")
        pruef(min(hoehen) >= 42, f"alle Knöpfe im Fenster mindestens 42 px hoch ({min(hoehen):.0f})")
        pg.click(".wahl button:has-text('Jonas')")
        pruef(pg.locator(".wahl button[aria-pressed=true]").count() == 1 and not pg.locator("#tabgeben").is_disabled(), "Wahl markiert, 'Übergeben' frei")
        pg.keyboard.press("Escape")
        pruef(pg.locator(".ueber").count() == 0 and pg.evaluate("S.team.wahl") is None, "Escape schließt, Wahl vergessen")
        pg.click("[data-act=t-abgeben-frage]")
        pg.click(".blatt h2")
        pruef(pg.locator(".ueber").count() == 1, "Tipp ins Fenster lässt es offen")
        pg.mouse.click(195, 30)
        pruef(pg.locator(".ueber").count() == 0, "Tipp daneben schließt")
        # Funkloch: Meldung im Fenster, Fenster bleibt
        pg.click("[data-act=t-abgeben-frage]")
        pg.click(".wahl button:has-text('Julia')")
        pg.evaluate("window.__weg = ['team_set_leader']")
        pg.click("#tabgeben")
        pg.wait_for_timeout(800)
        pruef(pg.locator(".ueber .blatt .msg.err").count() == 1 and pg.evaluate("S.view") == "team", "Funkloch: Meldung im Fenster, Rolle bleibt")
        pg.evaluate("window.__weg = null")
        gps_vorher = pg.evaluate("S.gps.on")
        pg.click("#tabgeben")
        pruef(warte(pg, "S.view === 'public'"), "Übergabe klappt: dieses Handy liest mit")
        pruef(pg.evaluate("location.hash") == "#/public" and pg.evaluate("history.length") == pg.evaluate("window.__h0"), "Adresse still ersetzt")
        pruef(text(pg, "#kurz") == "Julia leitet jetzt das Team", f"Einblendung {text(pg, '#kurz')!r}")
        pruef(ls(pg, "sj.code") is None and ls(pg, "sj.letzter.team") is None, "sj.code und sj.letzter.team gelöscht")
        pruef(gps_vorher is True and pg.evaluate("S.gps.on") is True, "GPS läuft weiter")
        pruef(warte(pg, "S.mit && S.mit.team && S.mit.team.leaderName === 'Julia Krüger' && S.mit.ichLeite === false"), "Mitlesen zeigt Julia als Leitung")
        t = text(pg)
        pruef("Anmeldeseite" not in t and "tippt" not in t, "keine alte Meldung ('Anmeldeseite', 'tippt')")
        pg.close()

        pg = neu(b, "akku-leitung")
        pg.click(".ftabs [data-tab=team]")
        pg.click("[data-act=t-abgeben-frage]")
        pg.click(".wahl button:has-text('Lea')")
        pg.click("#tabgeben")
        pruef(warte(pg, "S.view === 'public'"), "Übergabe an ein nicht verbundenes Handy klappt")
        pruef(text(pg, "#kurz") == "Lea leitet jetzt das Team, sobald das Handy wieder verbunden ist.", f"Wortlaut F6: {text(pg, '#kurz')!r}")
        pg.close()

    if an(3):
        print("3 Spielleitung nimmt die Leitung weg, veraltete Antwort")
        pg = neu(b, "akku-leitung")
        pruef(pg.evaluate("S.view") == "team" and pg.evaluate("S.team.code") == "FUCHS-4821", "Anna leitet")
        pg.evaluate("window.__leitung('Jonas Keller')")
        takt(pg)
        pruef(warte(pg, "S.view === 'public'"), "nach dem Wechsel liest Anna mit")
        pruef(text(pg, "#kurz") == "Jonas leitet jetzt das Team", f"Einblendung {text(pg, '#kurz')!r}")
        pruef(pg.evaluate("S.team.code") is None and ls(pg, "sj.code") is None and ls(pg, "sj.letzter.team") is None, "kein Code, kein gemerkter Stand mehr (höchstens ein Handy mit Code)")
        pruef(pg.evaluate("S.gps.on") is True, "GPS läuft weiter")
        pruef(warte(pg, "S.mit && S.mit.team && S.mit.ichLeite === false"), "Mitlesen läuft")
        pg.close()

        pg = neu(b, "akku-leitung")
        pg.evaluate("window.__halten = ['team_state']")
        takt(pg)
        pg.evaluate("window.__leitung('Jonas Keller')")
        pg.evaluate("rolleWechseln('mitglied', S.team.state.team, 'Test')")
        pg.wait_for_timeout(300)
        pg.evaluate("window.__halten = null; window.__freigeben()")
        pg.wait_for_timeout(700)
        pruef(pg.evaluate("S.team.state") is None and pg.evaluate("S.view") == "public", "laufende Antwort der anderen Ansicht verfällt (Takt-Zähler)")
        pg.close()

    if an(4):
        print("4 Notweg-Tablet (sj.hand)")
        pg = neu(b, "rolle-notweg")
        pg.click("[data-act=t-codefeld]")
        pg.fill("#tcode", "FUCHS-4821")
        pg.click("[data-act=t-login]")
        pruef(warte(pg, "S.team.code === 'FUCHS-4821' && S.team.state"), "Code von Hand")
        pruef(ls(pg, "sj.hand") == "1", "Merker sj.hand gesetzt")
        pg.click("[data-act=t-gps]")
        pg.wait_for_timeout(700)
        pg.evaluate("window.__gps(50.1056, 14.4240, 8)")
        pg.wait_for_timeout(500)
        ra = pg.evaluate("window.__REPORT_ARGS")
        pruef(len(ra) >= 1 and all("p_akku" not in a for a in ra), f"Tablet meldet keinen Akku ({len(ra)} Meldungen)")
        pg.click(".ftabs [data-tab=team]")
        pruef(pg.locator("[data-act=t-logout-frage]").count() == 1, "Abmelden gibt es am Notweg-Tablet")
        pg.evaluate("window.__akku(15)")
        pg.wait_for_timeout(300)
        pruef(pg.locator(".ueber").count() == 0, "kein Akku-Fenster am Notweg-Tablet")
        takt(pg)
        takt(pg)
        pruef(pg.evaluate("S.view") == "team" and pg.evaluate("S.team.code") == "FUCHS-4821", "Tablet bleibt Teamleitung, keine Rollenwechsel")
        pg.close()

        pg = neu(b, "rolle-mitglied")
        pg.evaluate("localStorage.setItem('sj.hand', '1')")
        pg.evaluate("window.__leitung('Jonas Keller')")
        takt(pg)
        takt(pg)
        pruef(pg.evaluate("S.view") == "public", "mit sj.hand schaltet das Handy nicht von selbst um")
        pg.close()

    if an(5):
        print("5 Abmelden und sj.abgemeldet (F1)")
        pg = neu(b, "akku-leitung")
        pg.evaluate("localStorage.setItem('sj.abgemeldet', '1')")
        nachladen(pg)
        pruef(ls(pg, "sj.abgemeldet") is None, "alter Merker sj.abgemeldet beim Start gelöscht")
        pruef(warte(pg, "S.team.code === 'FUCHS-4821' && S.team.state"), "Handy mit Token ist wieder Teamleitung")
        pg.click(".ftabs [data-tab=team]")
        pruef(pg.locator("[data-act=t-logout-frage]").count() == 0 and "Abmelden" not in text(pg), "Teamleitung hat kein Abmelden mehr")
        pg.close()
        pg = neu(b, "rolle-leitung-vorstart")
        warte(pg, "S.view === 'team' && S.team.state")
        pruef("Abmelden" not in text(pg), "auch vor dem Start kein Abmelden")
        pg.close()
        pruef("sj.abgemeldet\", \"1\"" not in QUELLE and "Du hast dich abgemeldet" not in QUELLE, "Quelltext setzt sj.abgemeldet nicht mehr")

    if an(6):
        print("6 Akku-Fenster bei 20 % und 10 %")
        pg = neu(b, "akku-leitung")
        pruef(pg.locator(".ueber").count() == 0, "kein Fenster beim Laden (Akku 60 %)")
        pg.evaluate("window.__akku(25)")
        pg.wait_for_timeout(300)
        pruef(pg.locator(".ueber").count() == 0, "bei 25 % noch nichts")
        pg.evaluate("window.__akku(20)")
        pruef(warte(pg, "S.team.uebergabe === 'akku20'"), "bei 20 % öffnet das Fenster")
        t = text(pg, ".blatt")
        pruef("Akku wird knapp" in t and "20 %" in t and "Gebt die Leitung jetzt an jemanden mit vollerem Akku ab." in t, "Wortlaut der 20-%-Stufe")
        pruef("Damit euer Team nicht hängen bleibt" not in t and "tippt" not in t, "alter Füllsatz und 'tippt dann' sind weg")
        pruef(pg.locator(".blatt .akkuzeile svg").count() == 1, "Akku-Symbol im Fenster")
        pruef(text(pg, ".blatt .row2").startswith("Später"), "Knopf heißt 'Später'")
        pg.click(".blatt .row2 .btn.alt")
        pg.evaluate("window.__akku(19)")
        pg.wait_for_timeout(300)
        pruef(pg.locator(".ueber").count() == 0, "20 % nur einmal")
        pg.evaluate("window.__akku(10)")
        pruef(warte(pg, "S.team.uebergabe === 'akku10'"), "bei 10 % noch einmal")
        t = text(pg, ".blatt")
        pruef("Akku fast leer" in t and "Bald geht dieses Handy aus. Jetzt abgeben, dann spielt euer Team ohne Pause weiter." in t, "Wortlaut der 10-%-Stufe")
        pg.click(".blatt .row2 .btn.alt")
        pg.evaluate("window.__akku(8)")
        pg.wait_for_timeout(300)
        pruef(pg.locator(".ueber").count() == 0, "10 % nur einmal")
        nachladen(pg, "window.__akkuStart = { level: 9, laedt: false };")
        warte(pg, "S.team.state")
        takt(pg)
        pruef(pg.evaluate("AKKU.level") == 9 and pg.locator(".ueber").count() == 0, "auch nach Neuladen bei 9 % nicht wieder (sj.akku)")
        # wieder scharf nach Laden über 25 % (F3)
        pg.evaluate("window.__akku(30, true)")
        pg.evaluate("window.__akku(40, false)")
        pg.evaluate("window.__akku(20)")
        pruef(warte(pg, "S.team.uebergabe === 'akku20'"), "nach Laden über 25 % wieder scharf: 20-%-Fenster kommt wieder")
        pg.keyboard.press("Escape")
        pg.close()

        pg = neu(b, "akku-leitung-15")
        pruef(warte(pg, "S.team.uebergabe === 'akku20'"), "Start mit 15 %: Fenster kommt einmal")
        pg.click(".blatt .row2 .btn.alt")
        nachladen(pg)
        warte(pg, "S.team.state")
        takt(pg)
        pruef(pg.evaluate("AKKU.level") == 15 and pg.locator(".ueber").count() == 0, "nach Neuladen mit 15 % kein zweites Fenster")
        pg.close()

        pg = neu(b, "akku-laedt")
        pg.evaluate("window.__akku(9, true)")
        pg.wait_for_timeout(500)
        pruef(pg.locator(".ueber").count() == 0 and pg.locator("#akkuhinweis").count() == 0, "ladend: kein Fenster, kein Hinweis")
        pg.close()

        pg = neu(b, "akku-leitung")
        pg.click(".kopf [data-act=t-hilfe]")
        pg.evaluate("window.__akku(18)")
        pg.wait_for_timeout(400)
        pruef(pg.locator(".ueber .blatt #tabgeben").count() == 0 and pg.evaluate("S.team.uebergabe") is None, "Hilfe-Blatt offen: kein Akku-Fenster")
        pg.keyboard.press("Escape")
        takt(pg)
        pruef(pg.evaluate("S.team.uebergabe") == "akku20", "nach dem Schließen kommt das Fenster beim nächsten Abruf")
        pg.close()

        pg = neu(b, "akku-leitung")
        pg.click(".ftabs [data-tab=team]")
        pg.click("#inhalt [data-act=pub-hoch]")
        pg.evaluate("window.__akku(18)")
        pg.wait_for_timeout(400)
        pruef(pg.locator(".hochhalten").count() == 1 and pg.evaluate("S.team.uebergabe") is None, "Hochhalten offen: kein Akku-Fenster")
        pg.click(".hochhalten")
        takt(pg)
        pruef(pg.evaluate("S.team.uebergabe") == "akku20", "nach Hochhalten kommt es")
        pg.close()

        pg = neu(b, "akku-leitung")
        pg.evaluate("S.gps.kal = { bewegt: 0, letzt: null }; render()")
        pg.evaluate("window.__akku(18)")
        pg.wait_for_timeout(400)
        pruef(pg.evaluate("S.team.uebergabe") is None, "Einmessen läuft: kein Akku-Fenster")
        pg.evaluate("S.gps.kal = null; render()")
        takt(pg)
        pruef(pg.evaluate("S.team.uebergabe") == "akku20", "nach dem Einmessen kommt es")
        pg.close()

        pg = neu(b, "akku-leitung")
        pg.evaluate("S.selfie = { pos: 2, status: 'vorschau' }")
        pg.evaluate("window.__akku(18)")
        pg.wait_for_timeout(400)
        pruef(pg.evaluate("S.team.uebergabe") is None, "Selfie-Kamera offen: kein Akku-Fenster")
        pg.evaluate("S.selfie = null")
        takt(pg)
        pruef(pg.evaluate("S.team.uebergabe") == "akku20", "nach dem Selfie kommt es")
        pg.close()

        pg = neu(b, "akku-leitung")
        pg.evaluate("document.body.insertAdjacentHTML('beforeend', '<input id=\"probe\">'); document.getElementById('probe').focus()")
        pg.evaluate("window.__akku(18)")
        pg.wait_for_timeout(400)
        pruef(pg.evaluate("S.team.uebergabe") is None, "beim Tippen: kein Akku-Fenster")
        pg.close()

        pg = neu(b, "rolle-leitung-vorstart")
        warte(pg, "S.view === 'team' && S.team.state")
        pg.evaluate("window.__akku(15)")
        pg.wait_for_timeout(400)
        pruef(pg.evaluate("S.team.uebergabe") is None, "vor dem Start (drawn): kein Akku-Fenster, erst ab running (F4)")
        pg.close()

        pg = neu(b, "akku-mitglied-knapp")
        pg.wait_for_timeout(500)
        pruef(pg.locator(".ueber").count() == 0, "Mitglied mit 18 %: kein Fenster (das ist Sache der Teamleitung)")
        pg.close()

        pg = neu(b, "akku-leitung")
        pg.click(".ftabs [data-tab=team]")
        pg.evaluate("S.team.state.geraete = S.team.state.geraete.map(g => g.name === 'Anna Berger' ? g : Object.assign({}, g, { angemeldet: false })); window.__geraeteLeer = true")
        pg.evaluate("window.__akku(18)")
        pg.wait_for_timeout(400)
        pruef(pg.evaluate("S.team.uebergabe") is None, "niemand zum Übergeben: kein Fenster")
        pg.close()

    if an(7):
        print("7 Akku-Hinweis")
        pg = neu(b, "akku-mitglied-knapp")
        pruef(warte(pg, "S.mit && S.mit.team"), "Jonas liest mit")
        pg.wait_for_selector("#akkuhinweis")
        t = text(pg, "#akkuhinweis")
        pruef(t.startswith("Akku knapp: dein Handy 18 %, Julia 15 %") and "Ladet das Handy, wenn ihr könnt." in t, f"Hinweis bei knappem Mitglied: {t!r}")
        pruef(pg.evaluate("document.querySelector('#akkuhinweis').closest('#inhalt') !== null"), "Hinweis steht oben im Reiter Weg")
        pg.click(".ftabs [data-tab=ziffern]")
        pruef(pg.locator("#akkuhinweis").count() == 0, "nicht im Reiter Ziffern")
        pg.click(".ftabs [data-tab=weg], .ftabs [data-tab=raetsel]")
        pg.evaluate("window.__akku(18, true)")
        pg.wait_for_timeout(400)
        pruef("dein Handy" not in text(pg, "#akkuhinweis") and "Julia" in text(pg, "#akkuhinweis"), "Laden nimmt das eigene Handy aus dem Hinweis")
        pg.evaluate("window.__AKKUS['Julia Krüger'] = { akku: 15, laedt: true, at: Date.now() + 1e7 }")
        takt(pg)
        pruef(pg.locator("#akkuhinweis").count() == 0, "alle laden: kein Hinweis")
        pg.close()

        pg = neu(b, "akku-leitung-knapp-mitglied")
        pg.wait_for_selector("#akkuhinweis")
        t = text(pg, "#akkuhinweis")
        pruef(t.startswith("Akku knapp: Anna 14 %") and "Das Handy der Teamleitung geht bald aus. Anna sollte die Leitung rechtzeitig abgeben." in t, f"Leitung knapp, Mitglied liest: {t!r}")
        pruef(pg.locator("#akkuhinweis [data-act]").count() == 0, "Mitglied hat keinen Abgeben-Knopf")
        pg.evaluate("window.__AKKUS['Anna Berger'].at = Date.now() - 11 * 60000")
        takt(pg)
        pruef(pg.locator("#akkuhinweis").count() == 0, "Stand älter als 10 Minuten: kein Hinweis")
        pg.close()

        pg = neu(b, "akku-leitung")
        pg.evaluate("window.__AKKUS['Julia Krüger'] = { akku: 15, laedt: false, at: Date.now() }; window.__AKKUS['Lea Hoffmann'] = { akku: 5, laedt: false, at: Date.now() }")
        takt(pg)
        t = text(pg, "#akkuhinweis")
        pruef(t.startswith("Akku knapp: Julia 15 %") and "Lea" not in t and "Ladet das Handy, wenn ihr könnt." in t, f"Leitung sieht Julia, nicht das nicht verbundene Handy von Lea: {t!r}")
        pg.evaluate("window.__akku(18)")
        pruef(warte(pg, "S.team.uebergabe === 'akku20'"), "eigenes Handy bei 18 %: Fenster")
        pg.click(".blatt .row2 .btn.alt")
        t = text(pg, "#akkuhinweis")
        pruef(t.startswith("Akku knapp: dein Handy 18 %, Julia 15 %") and "Gib die Leitung rechtzeitig an jemanden mit vollerem Akku ab." in t, f"Hinweis der Leitung: {t!r}")
        pg.click("#akkuhinweis [data-act=t-abgeben-frage]")
        pruef(pg.evaluate("S.team.uebergabe") == "abgeben", "Knopf im Hinweis öffnet das Übergabe-Fenster")
        pg.close()

    if an(8):
        print("8 Spielleitung")
        pg = b.new_page(viewport={"width": 1180, "height": 820})
        pg.set_default_timeout(15000)
        pg.route("**/vendor/leaflet-1.9.4/**", lambda r: r.abort())
        pg.on("pageerror", lambda e: err.append(f"admin-akku: {e}"))
        pg.clock.install()
        pg.goto(APP + "admin-akku")
        pg.wait_for_function("window.__fertig === true", timeout=30000)
        pg.wait_for_selector("#teamfeld .row")
        zeile = lambda n: pg.locator(f"#teamfeld .row:has(b:text-is('{n}'))")  # noqa: E731
        pruef("Akku 18 %" in zeile("Fuchs").inner_text().replace(" ", " "), "Fuchs: Vermerk 'Akku 18 %' ab 20 %")
        pruef("Akku" not in zeile("Tiger").inner_text(), "Tiger (12 %, lädt): kein Vermerk")
        pruef("Akku" not in zeile("Panda").inner_text(), "Panda (64 %): kein Vermerk")
        eule = zeile("Eule")
        pruef(eule.count() == 1 and eule.inner_text().replace(" ", " ").count("Akku 8 %") == 1, "Eule (8 %): genau ein Chip 'Akku 8 %'")
        grp = pg.evaluate("[...document.querySelectorAll('#teamfeld .tliste > li')].map(l => l.classList.contains('grp') ? 'G:' + l.innerText.replace(/\\s+/g, ' ') : l.querySelector('b') ? l.querySelector('b').innerText : '?')")
        i_braucht = next(i for i, x in enumerate(grp) if x.startswith("G:Braucht dich"))
        i_andere = next(i for i, x in enumerate(grp) if x.startswith("G:Alle anderen"))
        pruef("Eule" in grp[i_braucht:i_andere] and "Fuchs" not in grp[i_braucht:i_andere], f"Eule unter 'Braucht dich', Fuchs (18 %) nicht ({grp[i_braucht:i_andere]})")
        zeile("Fuchs").locator(".row-main").click()
        pg.wait_for_timeout(300)
        d = pg.locator("#teamfeld .row.sel .detail").inner_text().replace(" ", " ")
        pruef("Akku der Teamleitung: 18 %" in d, f"Detail: Akku der Teamleitung ({d[:80]!r})")
        opts = pg.locator("#teamfeld .row.sel select option").all_inner_texts()
        pruef("Emre Demir (kein eigenes Handy)" in opts and "Anna Berger" in opts, f"Auswahl: Emre mit '(kein eigenes Handy)' ({opts})")
        pg.evaluate("S.admin.confirm = { key: 'leader', id: S.admin.state.teams[0].id, value: 'x', name: 'Jonas Keller', team: 'Fuchs', alt: 'Anna Berger' }; render()")
        dl = text(pg, ".dialog, #dlg, .overlay")
        pruef("tippt" not in dl and "Beide Handys schalten nach dem nächsten Abruf von selbst um" in dl, f"Dialog 'Teamleitung wechseln' ohne 'tippt' ({dl[:160]!r})")
        pruef(not any(c in pg.inner_text("body") for c in DASH), "keine Gedankenstriche in der Spielleitung")
        pg.evaluate("S.admin.confirm = null")
        # Ergebnis steht vor dem Schließen (Chrome 155 hängt sonst, siehe abschluss.py)

    if an(9):
        print("9 Meldungen mit Akku")
        pg = neu(b, "akku-leitung")
        pg.evaluate("window.__gps(50.10496, 14.4231, 8)")
        pg.wait_for_timeout(500)
        ra = pg.evaluate("window.__REPORT_ARGS")
        pruef(len(ra) >= 1 and ra[0].get("p_akku") == 60 and ra[0].get("p_laedt") is False, f"report_position meldet Akku 60 und laedt = false ({ra[:1]})")
        pruef(pg.evaluate("window.__AKKU") == {"akku": 60, "laedt": False}, "Server hat den Akku der Leitung")
        n = len(pg.evaluate("window.__REPORT_ARGS"))
        pg.evaluate("window.__akku(55)")
        pg.evaluate("window.__gps(50.10496, 14.4231, 8)")
        pg.wait_for_timeout(400)
        pruef(len(pg.evaluate("window.__REPORT_ARGS")) == n, "55 % statt 60 %: keine zusätzliche Meldung (Drosselung bleibt)")
        pg.evaluate("window.__akku(20)")
        pg.evaluate("window.__gps(50.10496, 14.4231, 8)")
        pg.wait_for_timeout(500)
        ra = pg.evaluate("window.__REPORT_ARGS")
        pruef(len(ra) == n + 1 and ra[-1]["p_akku"] == 20, f"Schwelle 20 % löst sofort eine Meldung aus ({len(ra) - n})")
        pg.evaluate("window.__akku(20, true)")
        pg.evaluate("window.__gps(50.10496, 14.4231, 8)")
        pg.wait_for_timeout(500)
        ra = pg.evaluate("window.__REPORT_ARGS")
        pruef(ra[-1]["p_akku"] == 20 and ra[-1]["p_laedt"] is True, "Laden-Wechsel geht sofort mit")
        pg.close()

        pg = neu(b, "akku-mitglied-knapp")
        pg.wait_for_selector("#akkuhinweis")
        ma = pg.evaluate("window.__MEMBER_ARGS")
        pruef(any(a.get("p_akku") == 18 and a.get("p_laedt") is False for a in ma), f"member_state meldet Akku 18 ({ma[-1:]})")
        pg.close()

    if an(10):
        print("10 Alte Datenbank (PGRST202)")
        pg = neu(b, "akku-leitung", vorab="window.__ALTE_DB = true;")
        pg.evaluate("window.__gps(50.10496, 14.4231, 8)")
        pg.wait_for_timeout(600)
        pruef(pg.evaluate("window.__POSITION") is not None and pg.evaluate("DB_OHNE_AKKU") is True, "Meldung geht über den Rückfall durch, DB_OHNE_AKKU gemerkt")
        pg.evaluate("window.__REPORT_ARGS.length = 0; window.__gps(50.1051, 14.4235, 8)")
        pg.wait_for_timeout(500)
        ra = pg.evaluate("window.__REPORT_ARGS")
        pruef(ra == [] or all("p_akku" not in a for a in ra), "danach kein p_akku mehr")
        pg.click(".ftabs [data-tab=team]")
        pg.click("[data-act=t-abgeben-frage]")
        namen = pg.locator(".wahl button").all_inner_texts()
        pruef(len(namen) == 7 and any("Tobias" in n for n in namen), f"ohne geraete: alle anderen aus members ({len(namen)})")
        pg.click(".wahl button:has-text('Jonas')")
        pg.click("#tabgeben")
        pruef(warte(pg, "S.view === 'public'"), "Übergabe geht auch mit alter Datenbank")
        pg.close()

        pg = neu(b, "rolle-mitglied", vorab="window.__ALTE_DB = true;")
        pruef(warte(pg, "S.mit && S.mit.team"), "Mitlesen klappt mit alter Datenbank (member_state ohne p_akku)")
        pruef(pg.evaluate("DB_OHNE_AKKU") is True, "DB_OHNE_AKKU gemerkt")
        pg.evaluate("window.__MEMBER_ARGS.length = 0")
        takt(pg)
        pruef(all("p_akku" not in a for a in pg.evaluate("window.__MEMBER_ARGS")), "danach ruft es ohne p_akku")
        pg.evaluate("window.__leitung('Jonas Keller')")
        takt(pg)
        pruef(warte(pg, "S.view === 'team'"), "Rolle ohne ichLeite (alte Datenbank): Umschalten über den Namen")
        pg.close()

    if an(11):
        print("11 iPhone ohne Akku")
        pg = neu(b, "akku-iphone")
        pruef(pg.evaluate("typeof navigator.getBattery") == "undefined" and pg.evaluate("AKKU.level") is None, "kein getBattery, Akku unbekannt")
        pg.evaluate("window.__gps(50.10496, 14.4231, 8)")
        pg.wait_for_timeout(500)
        ra = pg.evaluate("window.__REPORT_ARGS")
        pruef(len(ra) >= 1 and all("p_akku" not in a and "p_laedt" not in a for a in ra), "report_position ohne Akku")
        pruef(pg.locator(".ueber").count() == 0 and pg.locator("#akkuhinweis").count() == 0, "keine Warnung")
        pg.click(".ftabs [data-tab=team]")
        pg.click("[data-act=t-abgeben-frage]")
        pruef(pg.locator(".wahl button").count() == 6, "Übergabe geht trotzdem")
        pg.close()
        pg = neu(b, "mitglied-unterwegs")
        pg.wait_for_timeout(300)
        pruef(all("p_akku" not in a for a in pg.evaluate("window.__MEMBER_ARGS")), "Mitglied ohne Akku: member_state nur mit p_token")
        pg.close()

    if an(12):
        print("12 Texte und Tippziele")
        pg = neu(b, "akku-leitung")
        pg.evaluate("window.__AKKUS['Julia Krüger'] = { akku: 15, laedt: false, at: Date.now() }")
        pg.evaluate("window.__akku(18)")
        pg.wait_for_selector(".ueber .blatt")
        alle = [pg.inner_text("body")]
        umbr = pg.evaluate("[...document.querySelectorAll('.nw')].filter(e => /%/.test(e.textContent)).map(e => e.getClientRects().length)")
        pruef(umbr and all(n == 1 for n in umbr), f"Prozentwerte brechen nicht um ({umbr})")
        pg.click(".blatt .row2 .btn.alt")
        alle.append(pg.inner_text("body"))
        pg.click(".ftabs [data-tab=team]")
        pg.click("[data-act=t-abgeben-frage]")
        alle.append(pg.inner_text("body"))
        pg.click(".wahl button:has-text('Lea')")
        pg.click("#tabgeben")
        pg.wait_for_selector("#kurz")
        alle.append(pg.inner_text("body"))
        pruef(not any(c in "".join(alle) for c in DASH), "keine Gedankenstriche in Fenster, Hinweis, Einblendung")
        pg.close()
        neu_text = [l for l in QUELLE.splitlines() if "Rollen und Akku" in l or "akkuHinweisHTML" in l]
        pruef(neu_text != [], "Quelltext trägt die Kommentare zu Rollen und Akku")

    pruef(not err, "keine Fehler auf der Seite" + (f": {err[:3]}" if err else ""))
    print("FEHLT:\n  " + "\n  ".join(fehler) if fehler else "OK")
    abschluss.ende(fehler, vorher)
