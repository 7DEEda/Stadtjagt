#!/usr/bin/env python3
"""
Probelauf für Nachtrag 26 (Stationsname verschlüsselt) gegen die echte Datenbank, ohne Spuren.

    python tools/pruefstand/name_db.py

Wie selfie_db.py: EIN DO-Block spielt die Migration ein, prüft und wirft am Ende
absichtlich einen Fehler. Postgres nimmt damit alles zurück, auch die Migration.
Geprüft wird an einer vorhandenen Station; ihre Werte stehen danach wieder wie vorher.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import sql  # noqa: E402

MIGRATION = sql.REPO / "supabase" / "migrations" / "20260930200000_name_verschluesselt.sql"

PROBE = r"""
do $probe$
declare
  v_pin text; v_code text := 'PROBE-' || upper(substr(md5(random()::text), 1, 6)); t_id uuid;
  s stations; r json; st json; v_n int := 0;
begin
  execute $mig$__MIGRATION__$mig$;

  select admin_pin into v_pin from game_state where id = 1;
  select * into s from stations order by position limit 1;
  if s.id is null then raise exception 'PROBE FEHLT 0: keine Station vorhanden'; end if;

  -- A: nach der Migration ist nichts verschlüsselt
  if exists (select 1 from stations where reveal_start_m is not null or reveal_clear_m is not null) then raise exception 'PROBE FEHLT A1: Stationen haben schon Werte'; end if;
  v_n := v_n + 1;

  -- B: speichern mit den beiden Entfernungen, die übrigen Felder bleiben
  r := admin_save_station(v_pin, s.id, s.name, s.lat, s.lng, s.radius_m, s.location_hint, s.riddle, s.answer, s.digit, s.tip, 340, 170);
  if (select reveal_start_m from stations where id = s.id) <> 340 or (select reveal_clear_m from stations where id = s.id) <> 170 then raise exception 'PROBE FEHLT B1: Werte nicht gespeichert'; end if;
  if (select name from stations where id = s.id) <> s.name or (select answer from stations where id = s.id) <> s.answer then raise exception 'PROBE FEHLT B2: andere Felder verändert'; end if;
  if not exists (select 1 from json_array_elements(r->'stations') e where e->>'id' = s.id::text and (e->>'revealStartM')::int = 340 and (e->>'revealClearM')::int = 170) then raise exception 'PROBE FEHLT B3: admin_state ohne die Felder'; end if;
  v_n := v_n + 3;

  -- C: der alte Aufruf mit elf Angaben geht weiter und schaltet das Verschlüsseln aus
  perform admin_save_station(v_pin, s.id, s.name, s.lat, s.lng, s.radius_m, s.location_hint, s.riddle, s.answer, s.digit, s.tip);
  if (select reveal_start_m from stations where id = s.id) is not null then raise exception 'PROBE FEHLT C1: alter Aufruf lässt Werte stehen'; end if;
  if (select count(*) from pg_proc where proname = 'admin_save_station') <> 1 then raise exception 'PROBE FEHLT C2: admin_save_station gibt es mehrfach'; end if;
  v_n := v_n + 2;

  -- D: unsinnige Werte werden abgelehnt
  begin
    perform admin_save_station(v_pin, s.id, s.name, s.lat, s.lng, s.radius_m, s.location_hint, s.riddle, s.answer, s.digit, s.tip, 100, 200);
    raise exception 'PROBE FEHLT D1: beginnt innen, lesbar außen angenommen';
  exception when sqlstate 'P0001' then if sqlerrm like 'PROBE FEHLT%' then raise; end if; end;
  begin
    perform admin_save_station(v_pin, s.id, s.name, s.lat, s.lng, s.radius_m, s.location_hint, s.riddle, s.answer, s.digit, s.tip, 300, null);
    raise exception 'PROBE FEHLT D2: nur eine der beiden Entfernungen angenommen';
  exception when sqlstate 'P0001' then if sqlerrm like 'PROBE FEHLT%' then raise; end if; end;
  begin
    perform admin_save_station('falsch', s.id, s.name, s.lat, s.lng, s.radius_m, s.location_hint, s.riddle, s.answer, s.digit, s.tip, 300, 100);
    raise exception 'PROBE FEHLT D3: ohne PIN gespeichert';
  exception when sqlstate 'P0001' then if sqlerrm like 'PROBE FEHLT%' then raise; end if; end;
  v_n := v_n + 3;

  -- E: das Team bekommt die Werte mit der Station
  perform admin_save_station(v_pin, s.id, s.name, s.lat, s.lng, s.radius_m, s.location_hint, s.riddle, s.answer, s.digit, s.tip, 340, 170);
  insert into teams (name, code, read_token) values ('Probelauf', v_code, md5(random()::text)) returning id into t_id;
  update game_state set status = 'running', started_at = now() where id = 1;
  st := team_state(v_code);
  if (st->'station'->>'position')::int is distinct from s.position then raise exception 'PROBE FEHLT E1: Station = %', st->'station'->>'position'; end if;
  if (st->'station'->>'revealStartM')::int is distinct from 340 or (st->'station'->>'revealClearM')::int is distinct from 170 then raise exception 'PROBE FEHLT E2: team_state ohne die Werte: %', st->'station'; end if;
  if (st->'station'->>'name') <> s.name then raise exception 'PROBE FEHLT E3: Name fehlt'; end if;
  if (st->'selfie') is null then raise exception 'PROBE FEHLT E4: Selfie-Feld aus Nachtrag 25 ist verloren gegangen'; end if;
  v_n := v_n + 4;

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
