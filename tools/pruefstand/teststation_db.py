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
  v_pin text; v_vorher text; v_nachher text; v_code text; t_id uuid; v_test record; st json; a json; v_n int := 0;
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

  -- H: eine spätere Spalte an stations_alle darf current_station nicht zerbrechen (Review I-1):
  -- current_station liefert den Typ der Sicht, und nach "create or replace view" läuft alles weiter
  if (select prorettype from pg_proc where proname = 'current_station') <> 'stations'::regtype
    then raise exception 'PROBE FEHLT H1: current_station liefert % statt der Sicht stations', (select prorettype::regtype from pg_proc where proname = 'current_station'); end if;
  alter table stations_alle add column probe_spalte int;
  create or replace view stations as select * from stations_alle where route = aktive_route();
  if v_code is not null then st := team_state(v_code); end if;
  alter table stations_alle drop column probe_spalte cascade;
  create or replace view stations as select * from stations_alle where route = aktive_route();
  revoke all on stations from anon, authenticated;   -- neu angelegt: Supabase vergibt Rechte von selbst
  v_n := v_n + 1;

  -- I: die Spielleitung sieht Fotos beider Routen, unabhängig vom Testmodus (Review M-3, Friedrich 02.10.)
  if position('stations_alle' in pg_get_functiondef('admin_photos'::regproc)) = 0
     or position('p_route' in pg_get_functiondef('admin_photo'::regproc)) = 0
     or (select count(*) from pg_proc where proname = 'admin_photo') <> 1
    then raise exception 'PROBE FEHLT I1: admin_photos/admin_photo nicht über beide Routen'; end if;
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
