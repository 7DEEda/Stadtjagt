# Teststation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Im Testmodus spielen alle Teams nur eine eigene Teststation (anfangs EDEKA Grenzallee, Berlin); die fünf Prager Stationen bleiben unverändert. Im Testmodus lässt sich außerdem mit nur einer angemeldeten Person (also einem Team) auslosen und starten.

**Architecture:** Die Tabelle `stations` heißt künftig `stations_alle` und bekommt die Spalte `route` (`echt` | `test`). Eine Sicht `stations` zeigt nur die aktive Route (`aktive_route()`: `test`, wenn Testmodus an und eine Teststation da ist). Alle Spielfunktionen lesen weiter `stations` und bekommen so automatisch die richtige Route; angepasst werden nur `admin_save_station` (schreibt in `stations_alle`), `admin_state` (echte Liste, Teststation, aktive Stationen) und vier Zählungen über `progress`, die heute ohne Stationsbezug zählen. Die Spielleitung bearbeitet die Teststation im Reiter „Stationen“ mit demselben Formular und derselben Karte wie die echten Stationen; Schloss und Texte rechnen mit der Stationszahl statt fest mit fünf.

**Tech Stack:** Supabase/Postgres (plpgsql, `security definer`), eine Datei `index.html` (HTML/CSS/JS, kein Build), Python-Werkzeuge (`tools/sql.py`, Prüfstand mit Playwright, Kanal chrome).

**Spec:** `docs/superpowers/specs/2026-10-02-teststation-kompass-waechter-design.md`, Teil 1. Teil 2 (Kompass-Wächter) und Teil 3 (Rollen und Akku) bekommen eigene Pläne.

## Global Constraints

- Die fünf Prager Stationen (heute `stations`, künftig `stations_alle` mit `route = 'echt'`) dürfen sich in keinem Feld ändern; Sicherung: `sicherungen/stationen_2026-10-02_vor_edeka.txt`.
- Teststation: genau eine Zeile, `route = 'test'`, `position = 1` (der Client rechnet mit `digits[position - 1]`).
- Erst-Anlage: Name „EDEKA Grenzallee“, `lat 52.470116`, `lng 13.462131`, `radius_m 50`, Ziffer 1, Entschlüsselung aus (`reveal_start_m`/`reveal_clear_m` null), Ortshinweis/Rätsel „… folgt“, Lösung leer.
- Jede Migration erst als Probelauf (ein DO-Block, `execute $mig$…$mig$`, Prüfungen, am Ende `raise exception 'PROBELAUF_OK'`, alles zurück), dann `python tools/sql.py <datei>`.
- Die Sicht `stations` darf für `anon`/`authenticated` nicht lesbar sein (Supabase vergibt Rechte auf neue Objekte; Sichten haben keine Zeilenrechte).
- Oberflächentexte: echte Umlaute, keine Gedankenstriche (U+2013/U+2014), Kennungen und Zahlen mit Einheit `white-space:nowrap`.
- Git im OneDrive-Ordner: immer `git -c windows.appendAtomically=false commit/push`; Commits enden mit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Prüfstand-Läufe immer im Vordergrund mit Timeout (`timeout 300 python …`).

## Review Focus

- Testmodus an, aber Teams haben schon Prager Stationen gelöst (Probebetrieb heute: Fuchs, Wolf): Teamansicht muss „0 von 1“ zeigen, nicht die Prager Zählung. Test: Probelauf C und Prüfskript-Szenario `teststation`.
- Testmodus aus, Spielleitung bearbeitet die Teststation (oder Testmodus an, sie bearbeitet eine Prager Station): das Speichern muss wirken, obwohl die Zeile in der Sicht gerade nicht sichtbar ist. Test: Probelauf E.
- REST-Zugriff ohne PIN auf die Sicht `stations` (Rätsel und Lösungen): muss verweigert werden. Test: Probelauf F.
- Spalte später an `stations_alle` angefügt: die Sicht (`select *`) zeigt sie nicht von selbst. Doku-Hinweis in Task 4 (SPIEL.md), damit künftige Migrationen die Sicht neu anlegen.
- Koffer im Testmodus: Code ist zwei Ziffern (Ziffer + Schlussziffer); Eingabefeld und Texte dürfen nicht „sechs Ziffern“ verlangen. Test: Prüfskript-Szenario `teststation-koffer`.

---

### Task 1: Migration Teststation und Probelauf

**Files:**
- Create: `tools/migration_teststation.py` (erzeugt die Migration aus den neuesten Funktionsfassungen)
- Create: `supabase/migrations/20261002120000_teststation.sql` (vom Generator geschrieben, eingecheckt)
- Create: `tools/pruefstand/teststation_db.py` (Probelauf gegen die echte Datenbank, nimmt alles zurück)

**Interfaces:**
- Produces (Datenbank): Tabelle `stations_alle` (alle Spalten von `stations` plus `route text`), Sicht `stations` (aktive Route), Funktion `aktive_route() returns text`; `admin_state(p_pin)` liefert zusätzlich `testStation` (Objekt wie ein Eintrag von `stations` plus `route`, oder `null`), `route` (`'echt'|'test'`), `aktiveStationen` (Liste `{id, position, name, lat, lng, radiusM}`); jeder Eintrag in `stations` hat zusätzlich `route`.

- [ ] **Step 1: Generator schreiben**

`tools/migration_teststation.py`:

```python
#!/usr/bin/env python3
"""
Erzeugt supabase/migrations/20261002120000_teststation.sql.

    python tools/migration_teststation.py

Kopf: Tabelle umbenennen, Spalte route, Sicht stations, aktive_route(), Teststation EDEKA.
Danach die neuesten Fassungen von team_state, submit_final, public_state, admin_state und
admin_save_station, jeweils mit genau gezählten Ersetzungen (bricht ab, wenn eine fehlt).
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
MIG = REPO / "supabase" / "migrations"
ZIEL = MIG / "20261002120000_teststation.sql"

KOPF = """-- Nachtrag 28: Teststation. Spec: docs/superpowers/specs/2026-10-02-teststation-kompass-waechter-design.md, Teil 1.
-- stations heißt jetzt stations_alle (echte Route und Teststation). Die Sicht stations zeigt nur die aktive
-- Route; alle Spielfunktionen lesen weiter stations. Achtung für spätere Migrationen: die Sicht ist
-- "select *" zum Zeitpunkt des Anlegens. Neue Spalten an stations_alle erst nach drop view/create view sichtbar.

alter table stations rename to stations_alle;
alter table stations_alle add column route text not null default 'echt';
alter table stations_alle add constraint stations_route_pruefen check (route in ('echt', 'test'));
alter table stations_alle drop constraint stations_position_key;
alter table stations_alle add constraint stations_route_position_key unique (route, position);

create or replace function aktive_route() returns text
language sql stable security definer set search_path = public as $$
  select case when coalesce((select test_mode from game_state where id = 1), false)
                   and exists (select 1 from stations_alle where route = 'test')
              then 'test' else 'echt' end
$$;

create view stations as select * from stations_alle where route = aktive_route();
-- Sichten haben keine Zeilenrechte: ohne das hier könnte jede und jeder Rätsel und Lösungen lesen
revoke all on stations from anon, authenticated;
revoke all on function aktive_route() from anon, authenticated;

insert into stations_alle (route, position, name, lat, lng, radius_m, location_hint, riddle, answer, digit, tip)
values ('test', 1, 'EDEKA Grenzallee', 52.470116, 13.462131, 50, 'Ortshinweis folgt', 'Rätsel folgt', '', 1, '');
"""

# (Funktion, Datei mit der neuesten Fassung, [(alt, neu, Anzahl)])
SOLVED_ALT = "select count(*) into v_solved from progress where team_id = t.id and solved_at is not null;"
SOLVED_NEU = ("select count(*) into v_solved from progress pr join stations s on s.id = pr.station_id "
              "where pr.team_id = t.id and pr.solved_at is not null;")
PR_SOLVED_ALT = "(select count(*) from progress pr where pr.team_id = t.id and pr.solved_at is not null)"
PR_SOLVED_NEU = ("(select count(*) from progress pr join stations s on s.id = pr.station_id "
                 "where pr.team_id = t.id and pr.solved_at is not null)")
PR_LAST_ALT = "(select max(pr.solved_at) from progress pr where pr.team_id = t.id)"
PR_LAST_NEU = "(select max(pr.solved_at) from progress pr join stations s on s.id = pr.station_id where pr.team_id = t.id)"

ADMIN_FELDER_ALT = """               s.reveal_start_m as "revealStartM", s.reveal_clear_m as "revealClearM"
        from stations s order by s.position) s2), '[]'::json),"""
ADMIN_FELDER_NEU = """               s.reveal_start_m as "revealStartM", s.reveal_clear_m as "revealClearM", s.route
        from stations_alle s where s.route = 'echt' order by s.position) s2), '[]'::json),
    'testStation', (select to_json(s3) from (
        select s.id, s.position, s.name, s.lat, s.lng, s.radius_m as "radiusM",
               s.location_hint as "locationHint", s.riddle, s.answer, s.digit, s.tip,
               s.reveal_start_m as "revealStartM", s.reveal_clear_m as "revealClearM", s.route
        from stations_alle s where s.route = 'test' order by s.position limit 1) s3),
    'route', aktive_route(),
    'aktiveStationen', coalesce((select json_agg(to_json(s4)) from (
        select s.id, s.position, s.name, s.lat, s.lng, s.radius_m as "radiusM"
        from stations s order by s.position) s4), '[]'::json),"""

AUFGABEN = [
    ("team_state", "20261001120000_zahlenantwort.sql", [(SOLVED_ALT, SOLVED_NEU, 1)]),
    ("submit_final", "20260919030000_wasserdicht.sql", [(SOLVED_ALT, SOLVED_NEU, 1)]),
    ("public_state", "20260930180000_gruppenselfie.sql", [(PR_SOLVED_ALT, PR_SOLVED_NEU, 2), (PR_LAST_ALT, PR_LAST_NEU, 2)]),
    ("admin_state", "20260930200000_name_verschluesselt.sql",
     [(ADMIN_FELDER_ALT, ADMIN_FELDER_NEU, 1), (PR_SOLVED_ALT, PR_SOLVED_NEU, 1), (PR_LAST_ALT, PR_LAST_NEU, 1)]),
    ("admin_save_station", "20260930200000_name_verschluesselt.sql", [("  update stations set", "  update stations_alle set", 1)]),
    # im Testmodus reicht eine Person (ein Team zum Ausprobieren), sonst wie bisher zwei
    ("admin_draw", "20260919100000_bugjagd.sql",
     [("  if v_count < 2 then raise exception 'Es sind noch zu wenige Personen angemeldet.' using errcode='P0001'; end if;",
       "  if v_count < (case when (select test_mode from game_state where id = 1) then 1 else 2 end) then
"
       "    raise exception 'Es sind noch zu wenige Personen angemeldet.' using errcode='P0001';
  end if;", 1)]),
]


def fassung(name: str, datei: str) -> str:
    text = (MIG / datei).read_text(encoding="utf-8")
    # die letzte Definition in der Datei, von "create or replace function name(" bis zum ersten "end $$;" danach
    starts = [m.start() for m in re.finditer(rf"create or replace function {name}\(", text)]
    if not starts:
        sys.exit(f"{name} nicht in {datei}")
    a = starts[-1]
    e = text.index("end $$;", a) + len("end $$;")
    return text[a:e]


def main() -> None:
    teile = [KOPF]
    for name, datei, ersetzungen in AUFGABEN:
        f = fassung(name, datei)
        for alt, neu, n in ersetzungen:
            if f.count(alt) != n:
                sys.exit(f"{name}: '{alt[:50]}' kommt {f.count(alt)}x vor, erwartet {n}x")
            f = f.replace(alt, neu)
        teile.append(f"-- ---------- {name} (aus {datei}, für die Teststation angepasst) ----------\n{f}\n")
    teile.append("notify pgrst, 'reload schema';\n")
    ZIEL.write_text("\n".join(teile), encoding="utf-8", newline="\n")
    print("geschrieben:", ZIEL.relative_to(REPO))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Migration erzeugen und lesen**

Run: `python tools/migration_teststation.py`
Expected: `geschrieben: supabase\migrations\20261002120000_teststation.sql`. Datei öffnen und prüfen: Kopf wie oben, fünf Funktionsblöcke, in `admin_state` stehen `testStation`, `route`, `aktiveStationen`; in `admin_save_station` steht `update stations_alle set`.

- [ ] **Step 3: Probelauf schreiben**

`tools/pruefstand/teststation_db.py` (Aufbau wie `name_db.py`):

```python
#!/usr/bin/env python3
"""
Probelauf für Nachtrag 28 (Teststation) gegen die echte Datenbank, ohne Spuren.

    python tools/pruefstand/teststation_db.py

EIN DO-Block spielt die Migration ein, prüft und wirft am Ende absichtlich einen Fehler.
Postgres nimmt damit alles zurück, auch die Migration.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import sql  # noqa: E402

MIGRATION = sql.REPO / "supabase" / "migrations" / "20261002120000_teststation.sql"

PROBE = r"""
do $probe$
declare
  v_pin text; v_vorher text; v_nachher text; v_code text; t_id uuid; v_test stations_alle; st json; a json; v_n int := 0;
begin
  select md5(string_agg(row(s.*)::text, '|' order by s.position)) into v_vorher from stations s;
  execute $mig$__MIGRATION__$mig$;
  select admin_pin into v_pin from game_state where id = 1;

  -- A: die Prager Stationen sind unverändert (ohne die neue Spalte route verglichen)
  select md5(string_agg(row(s.id, s.position, s.name, s.lat, s.lng, s.radius_m, s.location_hint, s.riddle, s.answer, s.digit, s.tip, s.reveal_start_m, s.reveal_clear_m)::text, '|' order by s.position))
    into v_nachher from stations_alle s where s.route = 'echt';
  if v_nachher is distinct from v_vorher then raise exception 'PROBE FEHLT A1: Prager Stationen verändert'; end if;
  if (select count(*) from stations_alle where route = 'echt') <> 5 then raise exception 'PROBE FEHLT A2: nicht fünf echte Stationen'; end if;
  select * into v_test from stations_alle where route = 'test';
  if v_test.id is null or v_test.position <> 1 or v_test.name <> 'EDEKA Grenzallee' then raise exception 'PROBE FEHLT A3: Teststation fehlt oder falsch'; end if;
  v_n := v_n + 3;

  -- B: Testmodus schaltet die Route
  update game_state set test_mode = false where id = 1;
  if aktive_route() <> 'echt' or (select count(*) from stations) <> 5 then raise exception 'PROBE FEHLT B1: Testmodus aus, aber nicht die echte Route'; end if;
  update game_state set test_mode = true where id = 1;
  if aktive_route() <> 'test' or (select count(*) from stations) <> 1 then raise exception 'PROBE FEHLT B2: Testmodus an, aber nicht die Teststation'; end if;
  v_n := v_n + 2;

  -- C: ein Team mit gelösten Prager Stationen steht im Testmodus bei 0 von 1 an der Teststation
  select code, id into v_code, t_id from teams order by name limit 1;
  if v_code is not null then
    update game_state set test_mode = false where id = 1;
    insert into progress (team_id, station_id, checked_in_at, solved_at)
      select t_id, s.id, now(), now() from stations_alle s where s.route = 'echt' and s.position = 1
      on conflict (team_id, station_id) do update set solved_at = now();
    update game_state set test_mode = true, status = 'running', started_at = coalesce(started_at, now()) where id = 1;
    st := team_state(v_code);
    if (st->>'totalStations')::int <> 1 then raise exception 'PROBE FEHLT C1: totalStations = %', st->>'totalStations'; end if;
    if (st->>'solvedCount')::int <> 0 then raise exception 'PROBE FEHLT C2: Prager Fortschritt zählt mit: %', st->>'solvedCount'; end if;
    if st->'station'->>'name' <> 'EDEKA Grenzallee' then raise exception 'PROBE FEHLT C3: Station = %', st->'station'->>'name'; end if;
    if json_array_length(st->'digits') <> 1 then raise exception 'PROBE FEHLT C4: digits = %', st->'digits'; end if;
    v_n := v_n + 4;
  end if;

  -- D: admin_state liefert echte Liste, Teststation und aktive Stationen
  a := admin_state(v_pin);
  if json_array_length(a->'stations') <> 5 then raise exception 'PROBE FEHLT D1: stations hat % Einträge', json_array_length(a->'stations'); end if;
  if a->'testStation'->>'name' <> 'EDEKA Grenzallee' then raise exception 'PROBE FEHLT D2: testStation fehlt'; end if;
  if a->>'route' <> 'test' or json_array_length(a->'aktiveStationen') <> 1 then raise exception 'PROBE FEHLT D3: route/aktiveStationen falsch'; end if;
  if length(a->>'caseCode') <> 2 then raise exception 'PROBE FEHLT D4: caseCode = %', a->>'caseCode'; end if;
  v_n := v_n + 4;

  -- E: Speichern wirkt auch auf Zeilen, die in der Sicht gerade nicht sichtbar sind
  update game_state set test_mode = false where id = 1;
  perform admin_save_station(v_pin, v_test.id, 'EDEKA Probe', v_test.lat, v_test.lng, 40, v_test.location_hint, v_test.riddle, v_test.answer, 2, v_test.tip, 300, 120);
  if (select name from stations_alle where id = v_test.id) <> 'EDEKA Probe' or (select reveal_start_m from stations_alle where id = v_test.id) <> 300
    then raise exception 'PROBE FEHLT E1: Teststation bei Testmodus aus nicht gespeichert'; end if;
  v_n := v_n + 1;

  -- G: im Testmodus reicht eine Person zum Auslosen (die Prüfung steht im Quelltext, Auslosen selbst würde echte Teams verwerfen)
  if position('case when (select test_mode from game_state where id = 1) then 1 else 2 end' in pg_get_functiondef('admin_draw'::regproc)) = 0
    then raise exception 'PROBE FEHLT G1: admin_draw verlangt im Testmodus weiter zwei Personen'; end if;
  v_n := v_n + 1;

  -- F: die Sicht ist ohne PIN nicht lesbar
  if has_table_privilege('anon', 'stations', 'select') or has_table_privilege('authenticated', 'stations', 'select')
    then raise exception 'PROBE FEHLT F1: anon darf die Sicht stations lesen'; end if;
  v_n := v_n + 1;

  raise exception 'PROBELAUF_OK: % Prüfungen bestanden, alles zurückgenommen', v_n;
end $probe$;
"""


def main() -> None:
    migration = MIGRATION.read_text(encoding="utf-8")
    assert "$mig$" not in migration and "$probe$" not in migration
    probe = PROBE.replace("__MIGRATION__", migration)
    print(f"Sende den Probelauf ({len(probe)} Zeichen) an Projekt {sql.project_ref()} ...", file=sys.stderr)
    try:
        sql.ausfuehren(probe, read_only=False)
    except SystemExit as e:
        text = str(e)
        m = re.search(r"PROBELAUF_OK[^\"\\]*", text)
        if m:
            print(m.group(0))
            return
        m = re.search(r"PROBE FEHLT[^\"\\]*", text)
        sys.exit(m.group(0) if m else "Der Probelauf ist abgebrochen:\n" + text)
    sys.exit("Der Probelauf lief ohne den erwarteten Abbruch durch. Bitte prüfen, ob etwas stehen geblieben ist.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Probelauf ausführen**

Run: `timeout 120 python tools/pruefstand/teststation_db.py`
Expected: `PROBELAUF_OK: 16 Prüfungen bestanden, alles zurückgenommen` (12, falls es kein Team gibt). Bei `PROBE FEHLT …`: Generator oder Migration korrigieren, Step 2 und 4 wiederholen.

- [ ] **Step 5: Danach die echte Datenbank prüfen (nichts verändert)**

Run: `python tools/sql.py --read-only -c "select to_regclass('stations_alle') is null as unberuehrt"`
Expected: `"unberuehrt": true`

- [ ] **Step 6: Commit**

```bash
git add tools/migration_teststation.py supabase/migrations/20261002120000_teststation.sql tools/pruefstand/teststation_db.py
git -c windows.appendAtomically=false commit -m "Nachtrag 28 vorbereitet: Teststation (stations_alle, Sicht stations, aktive_route), Probelauf

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Spielleitung, Reiter „Stationen“: Teststation bearbeiten

**Files:**
- Modify: `index.html` (Reiter Stationen ab `out += \`<div class="panel ${st.testMode ? "danger" : ""}"><h3>Testmodus</h3>` bis zum Koffer-Code; `"a-edit"(d)`; `ekVorgaenger()`; Fortschrittsbalken im Reiter Teams; Karte der Spielleitung `(st.stations || []).forEach(s => {` und `anker`)
- Modify: `tools/pruefstand/mock.js` (Szenario-Schalter `teststation`, `adminState()` mit `testStation`, `route`, `aktiveStationen`)
- Create: `tools/pruefstand/teststation.py` (Prüfskript ohne Datenbank)

**Interfaces:**
- Consumes: `admin_state` mit `testStation`, `route`, `aktiveStationen`, `stations[].route` (Task 1).
- Produces (index.html): `alleStationen(st)` → `[testStation?, ...stations]`; `stationZeile(s, st)` → HTML einer Station (Bearbeiten-Formular oder Zusammenfassung); `aktiv(st)` → `st.aktiveStationen || st.stations || []`.

- [ ] **Step 1: Mock erweitern**

In `tools/pruefstand/mock.js` direkt nach `const STATIONEN = [ … ];` die Teststation ergänzen:

```js
  const TESTSTATION = { id: "st", position: 1, name: "EDEKA Grenzallee", lat: 52.470116, lng: 13.462131, radiusM: 50, digit: 1,
    locationHint: "Ortshinweis folgt", riddle: "Rätsel folgt", answer: "", tip: "", revealStartM: null, revealClearM: null, route: "test" };
```

In `adminState()` nach `revealStartM: s.revealStartM, revealClearM: s.revealClearM })),` einfügen (der Eintrag `stations` bekommt dabei `route: "echt"`):

```js
      testStation: TESTSTATION, route: WELT.testMode && C.teststation ? "test" : "echt",
      aktiveStationen: (WELT.testMode && C.teststation ? [TESTSTATION] : STATIONEN).map(s => ({ id: s.id, position: s.position, name: s.name, lat: s.lat, lng: s.lng, radiusM: s.radiusM })),
```

und in der Abbildung von `STATIONEN` für `stations` `route: "echt"` ergänzen. Neues Szenario in `SZ`:

```js
    "admin-teststation": { welt: "running", view: "admin", testMode: true, teststation: true, ss: { "sj.pin": "4711" } },
```

- [ ] **Step 2: Prüfskript schreiben (zunächst rot)**

`tools/pruefstand/teststation.py` (Aufbau wie `ziffer.py`, Port 8822):

```python
#!/usr/bin/env python3
"""
Teststation im Prüfstand, ohne Datenbank.

    python tools/pruefstand/teststation.py

Spielleitung: Abschnitt Teststation sichtbar und bearbeitbar (Formular, Karte mit Kreisen),
Speichern schickt die id der Teststation, die Prager Liste bleibt. Im Vordergrund mit Timeout.
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


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8822), functools.partial(Leise, directory=str(HIER)))
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

    print("Spielleitung, Reiter Stationen")
    pg.goto("http://127.0.0.1:8822/app.html?szenario=admin-teststation"); pg.wait_for_selector("[data-act=a-edit]")
    pg.evaluate("S.admin.tab = 'stationen'; render()"); pg.wait_for_selector("#teststation")
    t = pg.inner_text("#teststation")
    pruef("EDEKA Grenzallee" in t and "Testmodus an: alle Teams spielen nur die Teststation" in t, f"Abschnitt Teststation: {t[:80]!r}")
    pruef(pg.locator("[data-act=a-edit]").count() == 6, "sechs Bearbeiten-Knöpfe (Teststation und fünf Stationen)")
    pg.click("#teststation [data-act=a-edit]"); pg.wait_for_selector("#emap .leaflet-container", timeout=20000)
    pruef(pg.input_value("#e-name") == "EDEKA Grenzallee", "Formular zeigt die Teststation")
    pruef("Start" in pg.inner_text("#e-etappe"), "Etappe beginnt am Start, nicht bei einer Prager Station")
    pg.fill("#e-radius", "40"); pg.evaluate("window.__GESPEICHERT = null")
    pg.click("[data-act=a-save]"); pg.wait_for_function("window.__GESPEICHERT")
    g = pg.evaluate("window.__GESPEICHERT")
    pruef(g["p_id"] == "st" and g["p_radius"] == 40, f"Speichern mit id der Teststation ({g['p_id']}, {g['p_radius']})")
    pruef(len(pg.evaluate("S.admin.state.stations")) == 5, "Prager Liste unverändert fünf Stationen")
    pruef(not err, f"keine Skriptfehler {err[:2]}")
    b.close()
srv.shutdown()
print("FEHLER: " + str(len(fehler)) if fehler else "OK")
sys.exit(1 if fehler else 0)
```

Run: `timeout 200 python tools/pruefstand/teststation.py`
Expected: FEHLT (es gibt noch kein `#teststation`).

- [ ] **Step 3: Helfer in index.html**

Direkt vor `function ekMitte() {` einfügen:

```js
// Teststation (Nachtrag 28): echte Stationen und Teststation zum Bearbeiten; gespielt wird die aktive Route
const alleStationen = st => [...(st.testStation ? [st.testStation] : []), ...(st.stations || [])];
const aktiv = st => st.aktiveStationen || st.stations || [];
```

In `"a-edit"(d)` die Suche ersetzen:

```js
    const s = alleStationen(S.admin.state).find(x => x.id === d.id);
```

In `ekVorgaenger()` die erste Zeile ersetzen, damit die Teststation am Start beginnt:

```js
  const st = S.admin.state, s = alleStationen(st).find(x => x.id === S.admin.edit);
  if (s && s.route === "test") return { name: START.name, nr: null, lat: START.lat, lng: START.lng };
```

In `"a-save"` die Suche `const st = S.admin.state, alt = (st.stations || []).find(s => String(s.id) === String(d.id));` ersetzen durch:

```js
    const st = S.admin.state, alt = alleStationen(st).find(s => String(s.id) === String(d.id));
```

- [ ] **Step 4: Stationszeile als Funktion, Abschnitt Teststation**

Den Ausdruck `${(st.stations || []).map(s => S.admin.edit === s.id ? \`…\` : \`…\`).join("")}` im Reiter Stationen herauslösen: das komplette Template (Formular- und Zusammenfassungszweig, unverändert) wandert in

```js
function stationZeile(s, st) {
  return S.admin.edit === s.id ? `…Formular wie bisher, Überschrift ${s.route === "test" ? "Teststation" : "Station " + s.position}…` : `…Zusammenfassung wie bisher…`;
}
```

(die Überschrift `<h3>Station ${s.position}</h3>` wird `<h3>${s.route === "test" ? "Teststation" : "Station " + s.position}</h3>`, in der Zusammenfassung die Nummer `${s.position}` bei der Teststation `T`). Der Aufruf im Reiter wird `${(st.stations || []).map(s => stationZeile(s, st)).join("")}`. Direkt vor dem Panel mit der Stationsliste kommt der neue Abschnitt:

```js
    if (st.testStation) out += `<div class="panel" id="teststation"><h3>Teststation</h3>
      <p class="small ${st.route === "test" ? "" : "muted"}">${st.route === "test"
        ? "Testmodus an: alle Teams spielen nur die Teststation."
        : "Testmodus aus: es gilt die echte Route (5 Stationen). Mit dem Testmodus spielen alle Teams nur die Teststation."}</p>
      ${stationZeile(st.testStation, st)}</div>`;
```

Über der Prager Liste im Testmodus den Vermerk ergänzen (erste Zeile im Panel der Stationsliste):

```js
${st.route === "test" ? `<p class="small muted">Im Testmodus wird diese Route nicht gespielt.</p>` : ""}
```

- [ ] **Step 5: Teams-Fortschritt und Karte nach der aktiven Route**

Im Reiter Teams `(st.stations || []).length` (zweimal) ersetzen durch `aktiv(st).length`. In der Karte der Spielleitung `(st.stations || []).forEach(s => {` ersetzen durch `aktiv(st).forEach(s => {` und `const anker = (st.stations || []).find(` durch `const anker = aktiv(st).find(`.

- [ ] **Step 5b: Auslosen mit einer Person im Testmodus**

Im Reiter Teams (Panel „Teams auslosen“) die Bedingung `n < 2` an beiden Stellen (Knopf `disabled` und Hinweis) ersetzen durch `n < (st.testMode ? 1 : 2)`; in `drawArgs()` `if (n < 2 || !v || v < 1) return null;` ersetzen durch `if (n < (S.admin.state.testMode ? 1 : 2) || !v || v < 1) return null;`. Der Hinweis wird `` `Es müssen mindestens ${st.testMode ? "eine Person" : "zwei Personen"} angemeldet sein.` ``. Szenario in `mock.js`:

```js
    "admin-auslosen-allein": { welt: "registration", view: "admin", testMode: true, ss: { "sj.pin": "4711" }, nurEine: true },
```

(mit `nurEine` gibt `adminState()` nur die erste Person in `participants` zurück: `participants: (C.nurEine ? PERSONEN.slice(0, 1) : PERSONEN).map(…)`). In `teststation.py` vor `pruef(not err, …)`:

```python
    print("Auslosen mit einer Person im Testmodus")
    pg.goto("http://127.0.0.1:8822/app.html?szenario=admin-auslosen-allein"); pg.wait_for_selector("[data-act=a-draw]")
    pg.evaluate("S.admin.tab = 'teams'; render()"); pg.wait_for_selector("#dval")
    pruef(not pg.locator(".panel [data-act=a-draw]").last.is_disabled(), "Auslosen-Knopf aktiv bei einer Person im Testmodus")
```

- [ ] **Step 6: Prüfskript grün**

Run: `timeout 200 python tools/pruefstand/teststation.py`
Expected: alle `ok`, `OK`.

- [ ] **Step 7: Bestehende Prüfungen**

Run: `timeout 300 python tools/pruefstand/ziffer.py; timeout 300 python tools/pruefstand/name.py; timeout 300 python tools/pruefstand/kritik.py`
Expected: je `OK`.

- [ ] **Step 8: Commit**

```bash
git add index.html tools/pruefstand/mock.js tools/pruefstand/teststation.py
git -c windows.appendAtomically=false commit -m "Spielleitung: Teststation im Reiter Stationen bearbeiten, Fortschritt und Karte nach aktiver Route

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Schloss und Texte nach Stationszahl

**Files:**
- Modify: `index.html` (`lockHTML`, Texte „Die 6. Ziffer …“, „Tippt die sechs Ziffern …“, `#tfin maxlength`, „Die abgesetzte sechste Ziffer …“)
- Modify: `tools/pruefstand/mock.js` (`teamState`: `totalStations`, `all`, `digits` aus der aktiven Liste)
- Modify: `tools/pruefstand/teststation.py` (Szenarien Team)

**Interfaces:**
- Consumes: `team_state.totalStations`, `digits` (Länge = Stationszahl), `finalDigit`.
- Produces: `ANZ(st)` → `st.totalStations || 5`.

- [ ] **Step 1: Mock: Teamzustand mit aktiver Liste**

In `mock.js` am Anfang von `teamState(t)`:

```js
    const LISTE = WELT.testMode && C.teststation ? [TESTSTATION] : STATIONEN;
```

und darin `f.solved >= 5` → `f.solved >= LISTE.length`, `STATIONEN[f.solved]` → `LISTE[f.solved]`, `STATIONEN.slice(0, f.solved)` → `LISTE.slice(0, f.solved)`, `totalStations: 5` → `totalStations: LISTE.length`, `digits: STATIONEN.map(` → `digits: LISTE.map(`. Szenarien:

```js
    "teststation": { welt: "running", view: "team", ls: IM_TEAM, testMode: true, teststation: true, fuchs: { solved: 0 } },
    "teststation-koffer": { welt: "running", view: "team", ls: IM_TEAM, testMode: true, teststation: true, fuchs: { solved: 1 } },
```

- [ ] **Step 2: Prüfskript um die Team-Ansicht erweitern (rot)**

In `teststation.py` vor `pruef(not err, …)` ergänzen:

```python
    print("Team, eine Station")
    pg.set_viewport_size({"width": 390, "height": 844})
    pg.goto("http://127.0.0.1:8822/app.html?szenario=teststation"); pg.wait_for_selector(".lock")
    pruef(pg.locator(".lock .wheel").count() == 2, f"Schloss mit zwei Rädern ({pg.locator('.lock .wheel').count()})")
    t = pg.inner_text("#app")
    pruef("Station 1 von 1" in t and "EDEKA Grenzallee" in t, "Station 1 von 1, EDEKA")
    pruef("fünf" not in t and "sechs" not in t, "keine Rede von fünf oder sechs Ziffern")
    pg.goto("http://127.0.0.1:8822/app.html?szenario=teststation-koffer"); pg.wait_for_selector("#tfin")
    pruef(pg.get_attribute("#tfin", "maxlength") == "2", f"Koffer-Feld zwei Ziffern ({pg.get_attribute('#tfin', 'maxlength')})")
    t = pg.inner_text("#app")
    pruef("zwei Ziffern" in t and "sechs" not in t, "Koffer-Text nennt zwei Ziffern")
```

Run: `timeout 200 python tools/pruefstand/teststation.py`
Expected: FEHLT bei „Schloss mit zwei Rädern“.

- [ ] **Step 3: index.html anpassen**

Vor `function lockHTML(st, klein) {`:

```js
const ANZ = st => st.totalStations || 5;
// Zahlwort für die Texte rund um das Schloss
const ZAHLWORT = ["null", "eine", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn"];
const zahl = n => ZAHLWORT[n] || String(n);
```

`lockHTML` ersetzen:

```js
function lockHTML(st, klein) {
  const d = st.digits || [], n = ANZ(st);
  let h = '<div class="lock">';
  for (let k = 0; k <= n; k++) {
    const v = k < n ? d[k] : st.finalDigit;
    const neu = S.neueZiffer && S.neueZiffer.i === k && S.neueZiffer.bis > Date.now();
    h += `<div class="wheel ${klein ? "klein" : ""} ${v == null ? "empty" : ""} ${neu ? "neu" : ""} ${k === n ? "schluss" : ""}" ${k === n ? 'title="Schlussziffer"' : ""}>${v == null ? "?" : v}</div>`;
  }
  return h + "</div>";
}
```

Texte ersetzen:
- `"Die 6. Ziffer ist die Einerstelle der Summe eurer fünf Ziffern."` → `` `Die ${ANZ(st) + 1}. Ziffer ist die Einerstelle der Summe eurer ${ANZ(st) === 1 ? "Ziffer" : zahl(ANZ(st)) + " Ziffern"}.` ``
- `Tippt die sechs Ziffern aus dem Schloss oben ab` → `` Tippt die ${zahl(ANZ(st) + 1)} Ziffern aus dem Schloss oben ab ``
- `maxlength="6"` (Feld `#tfin`) → `` maxlength="${ANZ(st) + 1}" ``
- `Die abgesetzte sechste Ziffer ist die Schlussziffer: die Einerstelle der Summe eurer fünf Ziffern.` → `` Die abgesetzte letzte Ziffer ist die Schlussziffer: die Einerstelle der Summe ${ANZ(st) === 1 ? "eurer Ziffer" : "eurer " + zahl(ANZ(st)) + " Ziffern"}. ``

Prüfen, dass `st` an allen vier Stellen im Gültigkeitsbereich ist (`grep -n "ANZ(st)" index.html`), sonst die dort verwendete Variable einsetzen.

- [ ] **Step 4: Prüfskript grün, bestehende Prüfungen**

Run: `timeout 200 python tools/pruefstand/teststation.py; timeout 300 python tools/pruefstand/kritik.py; timeout 300 python tools/pruefstand/selfie.py`
Expected: je `OK` (kritik.py prüft weiter die abgesetzte sechste Ziffer bei fünf Stationen: `.lock .wheel.schluss` = 1).

- [ ] **Step 5: Commit**

```bash
git add index.html tools/pruefstand/mock.js tools/pruefstand/teststation.py
git -c windows.appendAtomically=false commit -m "Schloss, Koffer-Feld und Texte rechnen mit der Stationszahl (Teststation: zwei Ziffern)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Einspielen, Veröffentlichen, Doku

**Files:**
- Modify: `HANDOFF.md`, `SPIEL.md` (Abschnitt 12 ergänzen), `README.md` (Prüfskripte)

- [ ] **Step 1: Probelauf noch einmal (Stand der Datenbank kann sich geändert haben)**

Run: `timeout 120 python tools/pruefstand/teststation_db.py`
Expected: `PROBELAUF_OK: …`

- [ ] **Step 2: Migration einspielen**

Vorher fragen, ob gerade jemand spielt (Testläufe laufen auf derselben Datenbank). Dann:
Run: `python tools/sql.py supabase/migrations/20261002120000_teststation.sql` (meldet die Bremse „drop“ wegen `drop constraint`, dann mit `--force`).
Expected: Erfolg ohne Fehlermeldung.

- [ ] **Step 3: Echte Datenbank prüfen**

Run: `python tools/sql.py --read-only -c "select route, position, name from stations_alle order by route, position"` und `python tools/sql.py --read-only -c "select aktive_route()"`
Expected: fünf Zeilen `echt` (Planetarium Prag …), eine Zeile `test` „EDEKA Grenzallee“; `aktive_route` = `test` (Testmodus ist im Probebetrieb an).

- [ ] **Step 4: Spiel veröffentlichen**

```bash
git push   # mit -c windows.appendAtomically=false
```
Danach warten, bis `https://7deeda.github.io/Stadtjagt/index.html` den neuen Stand liefert (`curl -s … | grep -q "alleStationen"`), und im Browser als Spielleitung den Reiter Stationen öffnen: Abschnitt Teststation sichtbar.

- [ ] **Step 5: Doku**

`HANDOFF.md` (neuer Abschnitt „Teststation (Nachtrag 28, …)“): was die Teststation ist, wo sie bearbeitet wird, dass Testmodus die Route umschaltet, Fortschritt pro Route getrennt, vor dem Event Testmodus aus. `SPIEL.md` Abschnitt 12: `stations_alle`, Sicht `stations`, `aktive_route()`, Hinweis auf `select *` der Sicht bei neuen Spalten, `alleStationen`/`aktiv`/`stationZeile` im Client. `README.md`: Prüfskripte `teststation.py`, `teststation_db.py`.

- [ ] **Step 6: Commit und Push**

```bash
git add HANDOFF.md SPIEL.md README.md
git -c windows.appendAtomically=false commit -m "Doku: Teststation (Nachtrag 28)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git -c windows.appendAtomically=false push
```
