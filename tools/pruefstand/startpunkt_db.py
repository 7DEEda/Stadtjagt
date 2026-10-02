#!/usr/bin/env python3
"""
Probelauf für Nachtrag 29 (Startpunkt eintragbar) gegen die echte Datenbank, ohne Spuren.

    python tools/pruefstand/startpunkt_db.py

EIN DO-Block spielt die Migration ein, prüft und wirft am Ende absichtlich einen Fehler.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import sql  # noqa: E402

MIGRATION = sql.REPO / "supabase" / "migrations" / "20261002140000_startpunkt.sql"

PROBE = r"""
do $probe$
declare v_pin text; a json; v_n int := 0;
begin
  execute $mig$__MIGRATION__$mig$;
  select admin_pin into v_pin from game_state where id = 1;

  -- A: die bisherigen Werte stehen drin
  a := admin_state(v_pin);
  if a->'start'->>'name' <> 'Mama Shelter Prague' or (a->'start'->>'lat')::float <> 50.102458 then raise exception 'PROBE FEHLT A1: start = %', a->'start'; end if;
  if a->'testStart'->>'name' <> 'TSE Berlin, Grenzallee 4' then raise exception 'PROBE FEHLT A2: testStart = %', a->'testStart'; end if;
  if a->'testStation' is null or a->'aktiveStationen' is null then raise exception 'PROBE FEHLT A3: Felder aus Nachtrag 28 verloren'; end if;
  v_n := v_n + 3;

  -- B: speichern je Route, die andere bleibt
  a := admin_set_start(v_pin, 'test', 'Haupteingang TSE', 52.47, 13.46);
  if a->'testStart'->>'name' <> 'Haupteingang TSE' or (a->'testStart'->>'lat')::float <> 52.47 then raise exception 'PROBE FEHLT B1: testStart nicht gespeichert'; end if;
  if a->'start'->>'name' <> 'Mama Shelter Prague' then raise exception 'PROBE FEHLT B2: echter Start verändert'; end if;
  a := admin_set_start(v_pin, 'echt', '', 50.1, 14.4);
  if a->'start'->>'name' <> 'Mama Shelter Prague' or (a->'start'->>'lng')::float <> 14.4 then raise exception 'PROBE FEHLT B3: leerer Name überschreibt oder Koordinaten fehlen'; end if;
  v_n := v_n + 3;

  -- C: abgelehnt ohne PIN, ohne Koordinaten, mit unbekannter Route
  begin perform admin_set_start('falsch', 'echt', 'x', 50, 14); raise exception 'PROBE FEHLT C1: ohne PIN gespeichert';
  exception when sqlstate 'P0001' then if sqlerrm like 'PROBE FEHLT%' then raise; end if; end;
  begin perform admin_set_start(v_pin, 'echt', 'x', null, 14); raise exception 'PROBE FEHLT C2: ohne Breite gespeichert';
  exception when sqlstate 'P0001' then if sqlerrm like 'PROBE FEHLT%' then raise; end if; end;
  begin perform admin_set_start(v_pin, 'irgendwas', 'x', 50, 14); raise exception 'PROBE FEHLT C3: unbekannte Route angenommen';
  exception when sqlstate 'P0001' then if sqlerrm like 'PROBE FEHLT%' then raise; end if; end;
  v_n := v_n + 3;

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
