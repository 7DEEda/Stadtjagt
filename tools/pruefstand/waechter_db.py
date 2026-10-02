#!/usr/bin/env python3
"""
Probelauf für Nachtrag 30 (Kompass-Wächter) gegen die echte Datenbank, ohne Spuren.

    python tools/pruefstand/waechter_db.py

EIN DO-Block spielt die Migration ein, prüft und wirft am Ende absichtlich einen Fehler. Auch wenn eine
Prüfung scheitert, endet der Block mit einer Ausnahme: der Server rollt die ganze Anweisung zurück.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import sql  # noqa: E402

MIGRATION = sql.REPO / "supabase" / "migrations" / "20261002160000_kompass_waechter.sql"

PROBE = r"""
do $probe$
declare v_pin text; v_status text; v_code text := 'PROBE-' || substr(md5(random()::text), 1, 8);
        v_id uuid; a json; k text; v_n int := 0;
begin
  execute $mig$__MIGRATION__$mig$;
  select admin_pin, status into v_pin, v_status from game_state where id = 1;

  -- A: Spalte da, genau eine report_position
  if not exists (select 1 from information_schema.columns where table_name = 'team_positions' and column_name = 'kompass') then
    raise exception 'PROBE FEHLT A1: Spalte kompass fehlt'; end if;
  if (select count(*) from pg_proc where proname = 'report_position' and pronamespace = 'public'::regnamespace) <> 1 then
    raise exception 'PROBE FEHLT A2: report_position nicht genau einmal'; end if;
  v_n := v_n + 2;

  -- Probe-Team, Spiel kurz auf running
  update game_state set status = 'running' where id = 1;
  insert into teams (name, code, read_token) values ('Probelauf', v_code, md5(random()::text)) returning id into v_id;

  -- B: Urteil kommt bei der Spielleitung an
  perform report_position(v_code, 52.47, 13.46, 8, 'unzuverlaessig');
  select x->'position'->>'kompass' into k from json_array_elements(admin_state(v_pin)->'teams') x where (x->>'id')::uuid = v_id;
  if k is distinct from 'unzuverlaessig' then raise exception 'PROBE FEHLT B1: kompass = %', k; end if;
  perform report_position(v_code, 52.47, 13.46, 8, 'ok');
  select x->'position'->>'kompass' into k from json_array_elements(admin_state(v_pin)->'teams') x where (x->>'id')::uuid = v_id;
  if k is distinct from 'ok' then raise exception 'PROBE FEHLT B2: kompass = %', k; end if;
  v_n := v_n + 2;

  -- C: Aufruf mit 4 Parametern (so ruft die heutige App) geht weiter und setzt null
  perform report_position(p_code => v_code, p_lat => 52.48, p_lng => 13.47, p_acc => 9);
  select x->'position'->>'kompass' into k from json_array_elements(admin_state(v_pin)->'teams') x where (x->>'id')::uuid = v_id;
  if k is not null then raise exception 'PROBE FEHLT C1: 4 Parameter setzen kompass nicht auf null: %', k; end if;
  if (select lat from team_positions where team_id = v_id) <> 52.48 then raise exception 'PROBE FEHLT C2: Position nicht übernommen'; end if;
  v_n := v_n + 2;

  -- D: unbekannter Wert wird zu null
  perform report_position(v_code, 52.47, 13.46, 8, 'unzuverlaessig');
  perform report_position(v_code, 52.47, 13.46, 8, 'kaputt');
  if (select kompass from team_positions where team_id = v_id) is not null then raise exception 'PROBE FEHLT D1: kaputt nicht verworfen'; end if;
  v_n := v_n + 1;

  -- E: admin_state hat seine übrigen Felder behalten
  a := admin_state(v_pin);
  if a->'start' is null or a->'testStart' is null or a->'aktiveStationen' is null then raise exception 'PROBE FEHLT E1: Felder aus Nachtrag 28/29 verloren'; end if;
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
