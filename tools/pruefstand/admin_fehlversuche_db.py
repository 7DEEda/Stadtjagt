#!/usr/bin/env python3
"""
Probelauf für admin_state mit failedAttempts/lockedUntil (06.10.2026) gegen die echte Datenbank, ohne Spuren.

    python tools/pruefstand/admin_fehlversuche_db.py

Wie namenssuche_db.py: EIN DO-Block spielt die Migration ein, prüft und wirft am Ende absichtlich einen
Fehler. Postgres nimmt damit alles zurück, auch die Migration und die Testdaten.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import sql  # noqa: E402

MIGRATION = sql.REPO / "supabase" / "migrations" / "20261006090000_admin_fehlversuche.sql"

PROBE = r"""
do $probe$
declare v_pin text; r json; t_id uuid; s_id uuid; v_n int := 0;
begin
  execute $mig$__MIGRATION__$mig$;
  select admin_pin into v_pin from game_state where id = 1;
  r := admin_state(v_pin);
  if json_array_length(r->'teams') = 0 then
    insert into teams(name, code) values ('Probe', 'PROBE-' || upper(substr(md5(random()::text), 1, 6))) returning id into t_id;
    r := admin_state(v_pin);
  end if;
  if (r->'teams'->0)::jsonb ? 'failedAttempts' is false then raise exception 'PROBE FEHLT A1: kein failedAttempts'; end if;
  if (r->'teams'->0->>'failedAttempts') is null then raise exception 'PROBE FEHLT A2: failedAttempts null statt 0'; end if;
  v_n := v_n + 2;
  -- B: Fehlversuche an der ersten ungelösten Station kommen an
  -- frisches Team ohne Fortschritt, damit es sicher eine ungelöste Station gibt
  insert into teams(name, code) values ('Probe2', 'PROBE-' || upper(substr(md5(random()::text), 1, 6))) returning id into t_id;
  select s.id into s_id from stations s left join progress pr on pr.station_id = s.id and pr.team_id = t_id
    where pr.solved_at is null order by s.position limit 1;
  insert into progress(team_id, station_id, failed_attempts) values (t_id, s_id, 2)
    on conflict (team_id, station_id) do update set failed_attempts = 2;
  r := admin_state(v_pin);
  if not exists (select 1 from json_array_elements(r->'teams') e where (e->>'id')::uuid = t_id and (e->>'failedAttempts')::int = 2)
    then raise exception 'PROBE FEHLT B1: Fehlversuche kommen nicht an'; end if;
  v_n := v_n + 1;
  if not has_function_privilege('anon', 'admin_state(text)', 'execute') then raise exception 'PROBE FEHLT C1: anon darf admin_state nicht'; end if;
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
        m = re.search(r'PROBELAUF_OK[^"\\]*', text)
        if m:
            print(m.group(0))
            return
        m = re.search(r'PROBE FEHLT[^"\\]*', text)
        sys.exit(m.group(0) if m else "Der Probelauf ist abgebrochen:\n" + text)
    sys.exit("Der Probelauf lief ohne den erwarteten Abbruch durch. Bitte prüfen, ob etwas stehen geblieben ist.")


if __name__ == "__main__":
    main()
