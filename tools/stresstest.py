#!/usr/bin/env python3
"""
Stresstest der Stadtjagd: 100 Handys spielen das Spiel gegen ein EIGENES Supabase-Projekt.

Nur Python 3.10+ aus der Standardbibliothek, keine Pakete. Läuft auf jedem Rechner mit dem Repo.

    python tools/stresstest.py einrichten   # einmal: Schema, Stationen, Lösungen, PIN ins Testprojekt
    python tools/stresstest.py lauf          # Anmeldung, Auslosen, Start, Spiel, Bericht
    python tools/stresstest.py aufraeumen    # Teilnehmende, Teams, Positionen im Testprojekt löschen

Zugang (Umgebungsvariablen oder gleichnamige Schalter --url, --key, --ref, --token).
URL, Key und Ref des Testprojekts "stadtjagd-stresstest" stehen als Vorgabe im Skript; nötig ist nur der Token:
    STRESS_URL    https://<ref>.supabase.co des Testprojekts
    STRESS_KEY    publishable/anon key des Testprojekts (Settings, API Keys)
    STRESS_REF    Projekt-Ref des Testprojekts (nur für "einrichten")
    SUPABASE_ACCESS_TOKEN  Personal Access Token (nur für "einrichten"), supabase.com/dashboard/account/tokens;
                           ersatzweise in der Datei tools/stresstest.token (in .gitignore)

Das Live-Projekt (Ref aus config.js) wird verweigert: der Test schreibt Anmeldungen, Positionen und
Check-ins. Was gemessen wird: Antwortzeit (p50/p95/p99/max), Fehler und Antwortgröße je Server-Funktion,
dazu alle 10 s eine Zeile mit Anfragen pro Sekunde. Am Ende ein Bericht als JSON neben diesem Skript.

Ablauf "lauf" (Zeitraffer, Standard 15 min Spielzeit):
  1. Anmeldung: --handys Personen melden sich in --anmeldung-s Sekunden an (Spitze wie am Eventtag).
  2. Auslosen in --teams Teams, Start.
  3. Jedes Handy fragt alle --takt Sekunden ab, wie die App: Teamleitung team_state und alle 20 s
     report_position, Mitlesende public_state und member_state, die Spielleitung admin_state und
     admin_tracks. Die Teamleitung läuft im Zeitraffer zur Station, checkt ein, antwortet (manchmal
     erst falsch) und geht weiter; nach der letzten Station der Koffer-Code am Start.
  4. Bericht.
"""
import argparse
import http.client
import json
import math
import os
import pathlib
import random
import re
import statistics
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

for strom in (sys.stdout, sys.stderr):
    try:
        strom.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

REPO = pathlib.Path(__file__).resolve().parent.parent
PIN = "stresstest-2026"   # die Datenbank verlangt mindestens 12 Zeichen
# Das Testprojekt "stadtjagd-stresstest" (13.10.2026). Der Publishable Key ist öffentlich gedacht wie der in config.js.
TEST_URL = "https://brtngzltqgniihjaoskr.supabase.co"
TEST_KEY = "sb_publishable_zxSC2IziBOI8nHmSKmoeuA_j_7-iIcf"
TEST_REF = "brtngzltqgniihjaoskr"
LIVE_REF = (re.search(r"https://([a-z0-9]+)\.supabase\.co", (REPO / "config.js").read_text(encoding="utf-8")) or [None, ""])[1]


# ---------------------------------------------------------------- Messung
class Messung:
    def __init__(self):
        self.lock = threading.Lock()
        self.zeiten = defaultdict(list)      # fn -> [ms]
        self.bytes = defaultdict(list)
        self.fehler = defaultdict(lambda: defaultdict(int))   # fn -> meldung -> anzahl
        self.fenster = []                    # (zeitpunkt, fn, ms, ok)
        self.logik = defaultdict(lambda: defaultdict(int))    # fn -> meldung -> anzahl: HTTP ok, aber {"ok": false}
        self.rand = defaultdict(lambda: [0, 0, []])           # randfall -> [bestanden, gesamt, abweichungen]

    def buche_logik(self, fn, meldung):
        with self.lock:
            self.logik[fn][(meldung or "ok: false")[:120]] += 1

    def randfall(self, name, bestanden, info=""):
        with self.lock:
            r = self.rand[name]
            r[1] += 1
            if bestanden:
                r[0] += 1
            elif len(r[2]) < 3:
                r[2].append(str(info)[:140])

    def buche(self, fn, ms, ok, n_bytes=0, meldung=None):
        with self.lock:
            if ok:
                self.zeiten[fn].append(ms)
                self.bytes[fn].append(n_bytes)
            else:
                self.fehler[fn][(meldung or "Fehler")[:120]] += 1
            self.fenster.append((time.time(), fn, ms, ok))

    def zeile(self, seit):
        with self.lock:
            jetzt = time.time()
            letzte = [x for x in self.fenster if x[0] >= jetzt - 10]
        if not letzte:
            return f"{int(jetzt - seit):>5} s   keine Anfragen"
        ms = sorted(x[2] for x in letzte if x[3])
        err = sum(1 for x in letzte if not x[3])
        p95 = ms[int(len(ms) * .95) - 1] if ms else 0
        return f"{int(jetzt - seit):>5} s   {len(letzte) / 10:5.1f} Anfr./s   p95 {p95:6.0f} ms   Fehler {err}"

    def bericht(self):
        out = {}
        for fn in sorted(set(self.zeiten) | set(self.fehler) | set(self.logik)):
            z = sorted(self.zeiten[fn])
            q = lambda p: round(z[min(len(z) - 1, max(0, int(len(z) * p) - 1))]) if z else None
            out[fn] = {
                "ok": len(z), "fehler": sum(self.fehler[fn].values()),
                "p50_ms": q(.50), "p95_ms": q(.95), "p99_ms": q(.99), "max_ms": round(z[-1]) if z else None,
                "mittel_bytes": round(statistics.mean(self.bytes[fn])) if self.bytes[fn] else None,
                "fehlermeldungen": dict(self.fehler[fn]),
                "logikfehler": dict(self.logik[fn]),
            }
        return out


M = Messung()


# ---------------------------------------------------------------- RPC wie die App
class Verbindung:
    """Eine Keep-Alive-Verbindung je Handy, wie ein Browser sie hält."""

    def __init__(self, url, key):
        u = urllib.parse.urlparse(url)
        self.host, self.key, self.conn = u.netloc, key, None
        # http nur für den Trockenlauf gegen einen lokalen Fake-Server
        self.art = http.client.HTTPConnection if u.scheme == "http" else http.client.HTTPSConnection

    def rpc(self, fn, args=None, buchen=True, streng=True):
        """streng: eine Antwort {"ok": false} zählt als Logikfehler (HTTP ok, aber das Spiel lehnt ab)."""
        body = json.dumps(args or {}).encode("utf-8")
        kopf = {"Content-Type": "application/json", "apikey": self.key, "Authorization": "Bearer " + self.key}
        t0 = time.perf_counter()
        for versuch in (1, 2):
            try:
                if self.conn is None:
                    self.conn = self.art(self.host, timeout=15)
                self.conn.request("POST", "/rest/v1/rpc/" + fn, body, kopf)
                r = self.conn.getresponse()
                daten = r.read()
                break
            except (OSError, http.client.HTTPException) as e:
                self.conn = None
                if versuch == 2:
                    ms = (time.perf_counter() - t0) * 1000
                    if buchen:
                        M.buche(fn, ms, False, meldung="Verbindung: " + type(e).__name__)
                    raise RuntimeError("Verbindung: " + str(e))
        ms = (time.perf_counter() - t0) * 1000
        try:
            data = json.loads(daten) if daten else None
        except ValueError:
            data = None
        if r.status >= 400:
            meldung = f"HTTP {r.status}: " + ((data or {}).get("message") if isinstance(data, dict) else daten[:80].decode("utf-8", "replace"))
            if buchen:
                M.buche(fn, ms, False, meldung=meldung)
            raise RuntimeError(meldung)
        if buchen:
            M.buche(fn, ms, True, len(daten))
            if streng and isinstance(data, dict) and data.get("ok") is False:
                M.buche_logik(fn, data.get("message"))
        return data


# ---------------------------------------------------------------- Geometrie
def meter(a, b):
    kx = math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot((a[0] - b[0]) * 111320, (a[1] - b[1]) * 111320 * kx)


def zwischen(a, b, f):
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


# ---------------------------------------------------------------- Handys
class Lauf:
    def __init__(self, a):
        self.a = a
        self.ende = False
        self.start_t = None
        self.lock = threading.Lock()
        self.fertig = 0
        self.n_teams = 0
        self.alle = threading.Event()

    def warte(self, s):
        """Schlafen, aber beim Ende sofort aufhören."""
        bis = time.time() + s
        while not self.ende and time.time() < bis:
            time.sleep(min(.5, bis - time.time()))
        return not self.ende

    def mitlesen(self, token):
        v = Verbindung(self.a.url, self.a.key)
        self.warte(random.uniform(0, self.a.takt))         # nicht alle im selben Takt
        while self.warte(0):
            for fn, args in (("public_state", {}), ("member_state", {"p_token": token})):
                try:
                    v.rpc(fn, args)
                except RuntimeError:
                    pass
            self.warte(self.a.takt)

    def spielleitung(self):
        v = Verbindung(self.a.url, self.a.key)
        seit = None
        while self.warte(0):
            try:
                v.rpc("admin_state", {"p_pin": PIN})
                r = v.rpc("admin_tracks", {"p_pin": PIN, "p_since": seit} if seit else {"p_pin": PIN})
                seit = (r or {}).get("now", seit)
            except RuntimeError:
                pass
            self.warte(self.a.takt)

    def teamleitung(self, code, stationen, start):
        v = Verbindung(self.a.url, self.a.key)
        pos = (start[0] + random.uniform(-.0003, .0003), start[1] + random.uniform(-.0003, .0003))
        tempo = random.uniform(1.0, 1.6) * self.a.zeitraffer          # m/s im Zeitraffer
        letzte_meldung = 0

        def abfragen():
            nonlocal letzte_meldung
            st = v.rpc("team_state", {"p_code": code})
            if time.time() - letzte_meldung >= 20:
                v.rpc("report_position", {"p_code": code, "p_lat": pos[0], "p_lng": pos[1], "p_acc": 8, "p_kompass": "ok"})
                letzte_meldung = time.time()
            return st

        def rand(name, fn, args, erwartet):
            """Randfall: erwartet 'ok' (ok: true), 'nein' (ok: false) oder 'fehler' (HTTP-Fehler). Ungebucht."""
            try:
                r = v.rpc(fn, args, buchen=False, streng=False)
            except RuntimeError as e:
                M.randfall(name, erwartet == "fehler", f"unerwartet: {e}")
                return None
            msg = r.get("message") if isinstance(r, dict) else r
            if erwartet == "fehler":
                M.randfall(name, False, f"kein Fehler: {msg}")
            else:
                M.randfall(name, (isinstance(r, dict) and r.get("ok") is True) == (erwartet == "ok"), msg)
            return r

        def falsch():
            try:
                v.rpc("submit_answer", {"p_code": code, "p_answer": "falsch"}, streng=False)
            except RuntimeError:
                pass

        self.warte(random.uniform(0, self.a.takt))
        # Randfälle am Start, vor der ersten Station
        if random.random() < .5:
            rand("Antwort ohne Check-in", "submit_answer", {"p_code": code, "p_answer": stationen[0]["answer"]}, "nein")
        if random.random() < .5:
            rand("Check-in zu weit weg (am Start)", "check_in", {"p_code": code, "p_lat": pos[0], "p_lng": pos[1], "p_acc": 8}, "nein")
        if random.random() < .2:
            rand("Unbekannter Teamcode", "team_state", {"p_code": "XXXXXXXX"}, "fehler")

        for i, ziel in enumerate(stationen):
            nach = (ziel["lat"], ziel["lng"])
            von, weg = pos, meter(pos, nach)
            dauer = max(1.0, weg / tempo)
            t0 = time.time()
            while self.warte(0):            # unterwegs: im Takt abfragen und Position melden
                f = min(1.0, (time.time() - t0) / dauer)
                pos = zwischen(von, nach, f)
                try:
                    abfragen()
                except RuntimeError:
                    pass
                if f >= 1.0:
                    break
                self.warte(min(self.a.takt, dauer * (1 - f)))
            if self.ende:
                return
            try:
                v.rpc("check_in", {"p_code": code, "p_lat": nach[0], "p_lng": nach[1], "p_acc": 8})
            except RuntimeError:
                pass
            if random.random() < .25:
                rand("Doppelter Check-in (Doppeltipp)", "check_in", {"p_code": code, "p_lat": nach[0], "p_lng": nach[1], "p_acc": 8}, "ok")
            self.warte(random.uniform(20, 90) / self.a.zeitraffer * 10)      # Rätsel lesen und lösen
            if i == 1 and random.random() < .3:      # dreimal falsch: Denkpause, die Pause läuft in Echtzeit
                for _ in range(3):
                    falsch()
                    self.warte(random.uniform(1, 3))
                rand("Richtig, aber in der Denkpause", "submit_answer", {"p_code": code, "p_answer": ziel["answer"]}, "nein")
                self.warte(125)
            elif random.random() < .3:
                falsch()
                self.warte(random.uniform(5, 15))
            try:
                v.rpc("submit_answer", {"p_code": code, "p_answer": ziel["answer"]})
            except RuntimeError:
                pass
            if random.random() < .25:           # zweimal getippt: darf die nächste Station nicht mitlösen
                rand("Doppelte richtige Antwort (Doppeltipp)", "submit_answer", {"p_code": code, "p_answer": ziel["answer"]}, "nein")

        # Alle Stationen gelöst: der Koffer steht an der letzten Station. Alle Teams geben ihn ungefähr gleichzeitig ein
        # (Platzvergabe unter Sperre), höchstens 4 min Wartezeit auf die langsamsten.
        with self.lock:
            self.fertig += 1
            if self.fertig >= self.n_teams:
                self.alle.set()
        t0 = time.time()
        while not self.alle.is_set() and time.time() - t0 < 240 and self.warte(0):
            try:
                abfragen()
            except RuntimeError:
                pass
            self.alle.wait(self.a.takt)
        if self.ende:
            return
        koffer = self.a.koffer
        if random.random() < .5:
            rand("Koffer zu weit weg (am Start)", "submit_final", {"p_code": code, "p_value": koffer, "p_lat": start[0], "p_lng": start[1], "p_acc": 8}, "nein")
        if random.random() < .2:
            rand("Koffer ohne GPS", "submit_final", {"p_code": code, "p_value": koffer}, "nein")
        if random.random() < .3:
            rand("Falscher Koffer-Code", "submit_final", {"p_code": code, "p_value": koffer[:-1] + str((int(koffer[-1]) + 1) % 10), "p_lat": pos[0], "p_lng": pos[1], "p_acc": 8}, "nein")
        wert = "-".join(koffer) if random.random() < .25 else koffer       # Eingabe mit Strichen zählt auch
        r1 = None
        try:
            r1 = v.rpc("submit_final", {"p_code": code, "p_value": wert, "p_lat": pos[0], "p_lng": pos[1], "p_acc": 8})
        except RuntimeError:
            pass
        if r1 and r1.get("ok") and random.random() < .3:
            r2 = None
            try:
                r2 = v.rpc("submit_final", {"p_code": code, "p_value": koffer, "p_lat": pos[0], "p_lng": pos[1], "p_acc": 8}, buchen=False, streng=False)
            except RuntimeError:
                pass
            M.randfall("Koffer doppelt abgeschickt, gleicher Platz", bool(r2 and r2.get("ok") and r2.get("place") == r1.get("place")), r2)
        while self.warte(self.a.takt):      # im Ziel: weiter abfragen wie die App
            try:
                abfragen()
            except RuntimeError:
                pass


# ---------------------------------------------------------------- Befehle
def zugang(a, mit_admin=False):
    for n in ("url", "key") + (("ref", "token") if mit_admin else ()):
        if not getattr(a, n):
            sys.exit(f"--{n} fehlt (oder Umgebungsvariable {'SUPABASE_ACCESS_TOKEN' if n == 'token' else 'STRESS_' + n.upper()}).")
    ref = a.ref or (re.search(r"https://([a-z0-9]+)\.supabase\.co", a.url) or [None, ""])[1]
    if LIVE_REF and (ref == LIVE_REF or LIVE_REF in a.url):
        sys.exit(f"Das ist das Live-Projekt ({LIVE_REF}). Der Stresstest läuft nur gegen ein eigenes Testprojekt.")


def sql(a, text):
    req = urllib.request.Request(f"https://api.supabase.com/v1/projects/{a.ref}/database/query",
                                 data=json.dumps({"query": text}).encode("utf-8"),
                                 headers={"Authorization": "Bearer " + a.token, "Content-Type": "application/json", "User-Agent": "stadtjagd-stresstest/1.0"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:600]}")


def einrichten(a):
    zugang(a, mit_admin=True)
    dateien = sorted((REPO / "supabase" / "migrations").glob("*.sql"))
    # Wiederholbar: steht das Schema schon (admin_state gibt es), nur Stationen, Lösungen und PIN setzen.
    # Die erste Migration beginnt mit "drop table ... cascade" und scheitert auf einem fertigen Schema.
    da = sql(a, "select to_regprocedure('public.admin_state(text)') is not null as da")
    if da and da[0].get("da"):
        print("Schema steht schon, Migrationen übersprungen.")
        dateien = []
    else:
        print(f"Spiele {len(dateien)} Migrationen in Projekt {a.ref} ein ...")
    for d in dateien:
        try:
            sql(a, d.read_text(encoding="utf-8"))
            print("  ok   ", d.name)
        except RuntimeError as e:
            sys.exit(f"  FEHLER in {d.name}:\n{e}")
    print("Stationen, Lösungen, PIN ...")
    sql(a, (REPO / "supabase" / "seed-stationen-prag.sql").read_text(encoding="utf-8"))
    # Der Seed lässt die Lösungen leer (zählt nie als richtig): für den Test eindeutige Lösungen setzen
    sql(a, f"update stations set answer = 'loesung' || position; update game_state set admin_pin = '{PIN}', test_mode = false where id = 1;")
    st = sql(a, "select position, name, lat, lng, digit, answer from stations order by position")
    print(json.dumps(st, ensure_ascii=False, indent=1))
    print("Fertig. Jetzt: python tools/stresstest.py lauf")


def aufraeumen(a):
    zugang(a)
    v = Verbindung(a.url, a.key)
    for fn in ("admin_reset", "admin_clear_positions", "admin_clear_participants"):
        try:
            v.rpc(fn, {"p_pin": PIN}, buchen=False)
            print("  ok   ", fn)
        except RuntimeError as e:
            print("  ", fn, e)


def lauf(a):
    zugang(a)
    v = Verbindung(a.url, a.key)
    st = v.rpc("admin_state", {"p_pin": PIN}, buchen=False)
    if st.get("status") != "registration" or st.get("participants"):
        print(f"Das Testprojekt steht auf '{st.get('status')}' mit {len(st.get('participants') or [])} Personen: räume erst auf ...")
        aufraeumen(a)
        st = v.rpc("admin_state", {"p_pin": PIN}, buchen=False)
    # "stations" ist die echte Route mit Lösungen ("aktiveStationen" hat keine); der Test läuft ohne Testmodus
    stationen = [s for s in (st.get("stations") or []) if s.get("lat") is not None]
    stationen.sort(key=lambda s: s["position"])
    if not stationen or any(not s.get("answer") for s in stationen):
        sys.exit("Keine Stationen mit Koordinaten und Lösung. Erst: python tools/stresstest.py einrichten")
    start = (st["start"]["lat"], st["start"]["lng"]) if (st.get("start") or {}).get("lat") is not None else (stationen[0]["lat"], stationen[0]["lng"])
    if st.get("testMode") or st.get("route") == "test":
        sys.exit("Das Testprojekt steht im Testmodus. Der Stresstest prüft Entfernungen und Antworten echt: Testmodus aus.")
    a.koffer = st.get("caseCode") or "".join(str(s.get("digit", 0)) for s in stationen)
    v.rpc("admin_set_settings", {"p_pin": PIN, "p_duration_min": int(math.ceil(a.dauer)) + 10, "p_case_hint": "Stresstest"}, buchen=False)

    print(f"1. Anmeldung: {a.handys} Handys in {a.anmeldung_s} s")
    tokens, tlock = [], threading.Lock()

    def anmelden(i):
        time.sleep(random.uniform(0, a.anmeldung_s))
        r = Verbindung(a.url, a.key).rpc("register_participant", {"p_name": f"Stress Person {i:03d}"})
        with tlock:
            tokens.append(r["token"])
    th = [threading.Thread(target=lambda i=i: _still(anmelden, i)) for i in range(a.handys)]
    [t.start() for t in th]
    [t.join() for t in th]
    print(f"   {len(tokens)} angemeldet")
    vr = Verbindung(a.url, a.key)

    def rand(name, fn, args, erwartet_fehler=True):
        try:
            r = vr.rpc(fn, args, buchen=False, streng=False)
            M.randfall(name, not erwartet_fehler, f"kein Fehler: {r}" if erwartet_fehler else "")
        except RuntimeError as e:
            M.randfall(name, erwartet_fehler, f"unerwartet: {e}")
    if tokens:
        rand("Anmeldung: Name doppelt", "register_participant", {"p_name": "Stress Person 000"})
        rand("Anmeldung: Name doppelt (Groß/Klein, Leerzeichen)", "register_participant", {"p_name": "  stress   PERSON 000 "})
        rand("Anmeldung: Name zu kurz", "register_participant", {"p_name": "A"})
        rand("Anmeldung: Name nur Sonderzeichen", "register_participant", {"p_name": "!!!???"})
        rand("Anmeldung: Name zu lang", "register_participant", {"p_name": "X" * 61})
        rand("Anmeldung: ungültiger Geräte-Schlüssel", "register_participant", {"p_name": "Stress Rand 001", "p_token": "abc"})
        try:    # Wiederholung mit demselben Schlüssel (Antwort ging verloren): gleiche Person, kein Fehler
            r = vr.rpc("register_participant", {"p_name": "Stress Person 000", "p_token": tokens[0]}, buchen=False, streng=False)
            M.randfall("Anmeldung: Wiederholung mit eigenem Schlüssel", r.get("token") == tokens[0], r)
        except RuntimeError as e:
            M.randfall("Anmeldung: Wiederholung mit eigenem Schlüssel", False, f"unerwartet: {e}")

    print(f"2. Auslosen in {a.teams} Teams und Start")
    v.rpc("admin_draw", {"p_pin": PIN, "p_teams": a.teams, "p_size": None})
    leitungen = []
    for tok in tokens:
        try:
            leitungen.append((tok, Verbindung(a.url, a.key).rpc("leader_code", {"p_token": tok}, buchen=False)["code"]))
        except RuntimeError:
            pass
    v.rpc("admin_start", {"p_pin": PIN})
    print(f"   {len(leitungen)} Teamleitungen, Spiel läuft")
    for i in range(3):      # nach dem Start: die Anmeldung ist zu, die Spielleitung trägt nach
        rand("Nachmelden nach Start wird abgelehnt", "register_participant", {"p_name": f"Stress Spät {i}"})

    L = Lauf(a)
    L.n_teams = len(leitungen)
    leit_tok = {t for t, _ in leitungen}
    threads = [threading.Thread(target=L.teamleitung, args=(code, stationen, start), daemon=True) for _, code in leitungen]
    threads += [threading.Thread(target=L.mitlesen, args=(tok,), daemon=True) for tok in tokens if tok not in leit_tok]
    threads += [threading.Thread(target=L.spielleitung, daemon=True) for _ in range(a.spielleitungen)]
    print(f"3. Spiel: {len(threads)} Handys/Tablets, {a.dauer} min, Takt {a.takt} s, Zeitraffer {a.zeitraffer}x")
    seit = time.time()
    [t.start() for t in threads]
    try:
        while time.time() - seit < a.dauer * 60:
            time.sleep(10)
            print("  ", M.zeile(seit))
    except KeyboardInterrupt:
        print("   abgebrochen")
    L.ende = True
    [t.join(timeout=20) for t in threads]

    try:
        ende = v.rpc("admin_state", {"p_pin": PIN}, buchen=False)
        im_ziel = sum(1 for t in ende.get("teams") or [] if t.get("place"))
        geloest = sum(t.get("solved") or 0 for t in ende.get("teams") or [])
    except RuntimeError:
        im_ziel = geloest = None
        ende = {}
    plaetze = sorted(t.get("place") for t in (ende.get("teams") or []) if t.get("place"))
    plaetze_ok = plaetze == list(range(1, len(plaetze) + 1))
    soll_geloest = len(stationen) * len(ende.get("teams") or [])
    b = {"zeit": time.strftime("%Y-%m-%d %H:%M"), "parameter": {k: getattr(a, k) for k in ("handys", "teams", "dauer", "takt", "zeitraffer", "spielleitungen", "anmeldung_s")},
         "ergebnis": {"teams_im_ziel": im_ziel, "teams": len(ende.get("teams") or []), "stationen_geloest": geloest, "stationen_soll": soll_geloest, "plaetze_lueckenlos": plaetze_ok},
         "randfaelle": {k: {"bestanden": r[0], "gesamt": r[1], "abweichungen": r[2]} for k, r in sorted(M.rand.items())}, "funktionen": M.bericht()}
    datei = REPO / "tools" / f"stresstest-bericht-{time.strftime('%Y%m%d-%H%M')}.json"
    datei.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n4. Bericht ({datei.name}): Teams im Ziel {im_ziel} von {len(ende.get('teams') or [])}, "
          f"Stationen gelöst {geloest} von {soll_geloest}, Plätze {'lückenlos und eindeutig' if plaetze_ok else 'FEHLERHAFT: ' + str(plaetze)}\n")
    print(f"{'Funktion':<22}{'ok':>7}{'Fehler':>8}{'p50':>7}{'p95':>7}{'p99':>7}{'max':>7}{'KB':>7}")
    for fn, r in b["funktionen"].items():
        kb = f"{r['mittel_bytes'] / 1024:.1f}" if r["mittel_bytes"] is not None else "-"
        print(f"{fn:<22}{r['ok']:>7}{r['fehler']:>8}{r['p50_ms'] or '-':>7}{r['p95_ms'] or '-':>7}{r['p99_ms'] or '-':>7}{r['max_ms'] or '-':>7}{kb:>7}")
        for m, n in r["fehlermeldungen"].items():
            print(f"{'':<22}  {n} x {m}")
        for m, n in r["logikfehler"].items():
            print(f"{'':<22}  {n} x Logik: {m}")
    print("\nRandfälle (erwartetes Verhalten des Servers):")
    for k, r in b["randfaelle"].items():
        print(f"  {'ok  ' if r['bestanden'] == r['gesamt'] else 'ABW '} {k}: {r['bestanden']}/{r['gesamt']}")
        for x in r["abweichungen"]:
            print(f"        {x}")


def token_datei():
    """Token aus tools/stresstest.token (steht in .gitignore, kommt nie ins öffentliche Repo)."""
    f = REPO / "tools" / "stresstest.token"
    return f.read_text(encoding="utf-8").strip() if f.exists() else None


def _still(fn, *args):
    try:
        fn(*args)
    except Exception as e:      # ein Handy, das ausfällt, hält den Test nicht an; gebucht ist der Fehler schon
        print("   Handy ausgefallen:", e)


def main():
    p = argparse.ArgumentParser(description="Stresstest der Stadtjagd gegen ein eigenes Supabase-Projekt")
    p.add_argument("befehl", choices=["einrichten", "lauf", "aufraeumen"])
    p.add_argument("--url", default=os.environ.get("STRESS_URL") or TEST_URL)
    p.add_argument("--key", default=os.environ.get("STRESS_KEY") or TEST_KEY)
    p.add_argument("--ref", default=os.environ.get("STRESS_REF") or TEST_REF)
    p.add_argument("--token", default=os.environ.get("SUPABASE_ACCESS_TOKEN") or token_datei())
    p.add_argument("--handys", type=int, default=100)
    p.add_argument("--teams", type=int, default=12)
    p.add_argument("--dauer", type=float, default=15, help="Minuten Spielzeit")
    p.add_argument("--takt", type=float, default=10, help="Sekunden zwischen zwei Abfragen, wie die App")
    p.add_argument("--zeitraffer", type=float, default=8, help="so viel schneller laufen die Teams")
    p.add_argument("--spielleitungen", type=int, default=2, help="Tablets der Spielleitung")
    p.add_argument("--anmeldung-s", dest="anmeldung_s", type=float, default=60, help="Sekunden, in denen sich alle anmelden")
    a = p.parse_args()
    {"einrichten": einrichten, "lauf": lauf, "aufraeumen": aufraeumen}[a.befehl](a)


if __name__ == "__main__":
    main()
