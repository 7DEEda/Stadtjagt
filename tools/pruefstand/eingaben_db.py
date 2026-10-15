#!/usr/bin/env python3
"""
Probelauf für die Migration 20261016090000_eingaben_wiederholen.sql (Ausfallsicherheit, Abschnitt 3.3) gegen die
echte Datenbank, ohne Spuren.

    python tools/pruefstand/eingaben_db.py          mit Migration (grün)
    python tools/pruefstand/eingaben_db.py --ohne   Stand der Datenbank ohne Migration (rot)

Wie bugjagd2_db.py: EIN DO-Block spielt die Migration ein, legt ein erfundenes Team an, setzt das Spiel im Block auf
running, gibt den ersten beiden Stationen der echten Route Probewerte, prüft und wirft am Ende absichtlich einen
Fehler. Auch wenn eine Prüfung scheitert, endet der Block mit einer Ausnahme: Postgres nimmt alles zurück, auch
die Migration. Die Sperren auf game_state und den beiden Stationen halten nur so lange wie der Block.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sql  # noqa: E402
from rechte_db import INTERN  # noqa: E402

MIGRATION = sql.REPO / "supabase" / "migrations" / "20261016090000_eingaben_wiederholen.sql"
SPIEL = ["submit_answer(text,text,integer)", "check_in(text,double precision,double precision,double precision)",
         "submit_final(text,text,double precision,double precision,double precision)"]

PROBE = r"""
do $probe$
declare v_n int := 0; r json; r2 json; f text; rr text; v_s1 uuid; v_s2 uuid; v_st uuid; v_id uuid; p progress;
        v_code text := 'PROBE-' || substr(md5(random()::text), 1, 8); v_ziffer int;
begin
  __MIGRATION__
  update game_state set status = 'running', test_mode = false, started_at = coalesce(started_at, now()) where id = 1;
  insert into teams (name, code, read_token) values ('Probelauf', v_code, md5(random()::text)) returning id into v_id;
  select id into v_s1 from stations_alle where route = 'echt' and position = 1;
  select id into v_s2 from stations_alle where route = 'echt' and position = 2;
  if v_s1 is null or v_s2 is null then raise exception 'PROBE FEHLT 0: echte Route ohne Station 1 und 2'; end if;
  update stations_alle set lat = 50.1, lng = 14.4, radius_m = 50, answer = '7|sieben' where id = v_s1;
  update stations_alle set lat = 50.2, lng = 14.5, radius_m = 50, answer = 'zwei' where id = v_s2;

  -- 1: Check-in im Radius, derselbe Check-in 500 m entfernt: gleiche Antwort, kein distance
  r := check_in(v_code, 50.1, 14.4, 5);
  if not (r->>'ok')::boolean or r->>'message' <> 'Angekommen. Das Rätsel ist frei.' then raise exception 'PROBE FEHLT 1A: erster Check-in %', r->>'message'; end if;
  r2 := check_in(v_code, 50.1045, 14.4, 5);
  if not coalesce((r2->>'ok')::boolean, false) or r2->>'message' is distinct from r->>'message' then
    raise exception 'PROBE FEHLT 1B: Wiederholung 500 m entfernt: %', r2->>'message'; end if;
  if r2->'distance' is not null and json_typeof(r2->'distance') <> 'null' then raise exception 'PROBE FEHLT 1C: Wiederholung mit distance %', r2->'distance'; end if;
  v_n := v_n + 3;

  -- 2: dieselbe falsche Antwort zählt einmal, auch mit anderer Schreibweise
  r := submit_answer(v_code, '12', 1);
  select * into p from progress where team_id = v_id and station_id = v_s1;
  if p.failed_attempts <> 1 or r->>'message' <> 'Leider falsch. Noch 2 Versuche.' then raise exception 'PROBE FEHLT 2A: % / %', p.failed_attempts, r->>'message'; end if;
  r := submit_answer(v_code, '12', 1);
  r2 := submit_answer(v_code, ' 12!', 1);
  select * into p from progress where team_id = v_id and station_id = v_s1;
  if p.failed_attempts <> 1 then raise exception 'PROBE FEHLT 2B: dieselbe falsche Antwort zählte, failed_attempts %', p.failed_attempts; end if;
  if r->>'message' <> 'Leider falsch. Noch 2 Versuche.' or r2->>'message' <> 'Leider falsch. Noch 2 Versuche.' then
    raise exception 'PROBE FEHLT 2C: Text bei Wiederholung % / %', r->>'message', r2->>'message'; end if;
  r := submit_answer(v_code, '13', 1);
  select * into p from progress where team_id = v_id and station_id = v_s1;
  if p.failed_attempts <> 2 or r->>'message' <> 'Leider falsch. Noch 1 Versuch.' then raise exception 'PROBE FEHLT 2D: andere Antwort % / %', p.failed_attempts, r->>'message'; end if;
  v_n := v_n + 4;

  -- 3: richtige Antwort, Wiederholung nach dem Wechsel zu Station 2
  r := submit_answer(v_code, 'sieben', 1);
  if not (r->>'ok')::boolean then raise exception 'PROBE FEHLT 3A: richtige Antwort %', r->>'message'; end if;
  if (select last_wrong from progress where team_id = v_id and station_id = v_s1) is not null then raise exception 'PROBE FEHLT 3B: last_wrong nach Erfolg nicht geleert'; end if;
  r2 := submit_answer(v_code, 'sieben', 1);
  if not coalesce((r2->>'ok')::boolean, false) or r2->>'message' is distinct from r->>'message' then raise exception 'PROBE FEHLT 3C: Wiederholung der richtigen Antwort: %', r2->>'message'; end if;
  if exists (select 1 from progress where team_id = v_id and station_id = v_s2) then raise exception 'PROBE FEHLT 3D: Station 2 angefasst'; end if;
  r := submit_answer(v_code, '12', 1);
  if (r->>'ok')::boolean or r->>'message' <> 'Diese Station ist schon gelöst.' then raise exception 'PROBE FEHLT 3E: falsche Antwort an gelöster Station: %', r->>'message'; end if;
  if exists (select 1 from progress where team_id = v_id and station_id = v_s2) then raise exception 'PROBE FEHLT 3F: Station 2 angefasst'; end if;
  r := submit_answer(v_code, 'zwei', 3);
  if (r->>'ok')::boolean or r->>'message' <> 'Das Rätsel hat gewechselt. Lest es noch mal.' then raise exception 'PROBE FEHLT 3G: Station passt nicht: %', r->>'message'; end if;
  r := submit_answer(v_code, 'zwei', 2);
  if (r->>'ok')::boolean or r->>'message' <> 'Erst am Ort einchecken, dann gibt es das Rätsel.' then raise exception 'PROBE FEHLT 3H: richtige Station ohne Check-in: %', r->>'message'; end if;
  v_n := v_n + 7;

  -- 4 und 5: alte App (zwei benannte Argumente), Denkpause
  perform check_in(v_code, 50.2, 14.5, 5);
  r := submit_answer(p_code => v_code, p_answer => 'x');
  r := submit_answer(p_code => v_code, p_answer => 'x');
  select * into p from progress where team_id = v_id and station_id = v_s2;
  if p.failed_attempts <> 1 or r->>'message' <> 'Leider falsch. Noch 2 Versuche.' then raise exception 'PROBE FEHLT 4A: alte App % / %', p.failed_attempts, r->>'message'; end if;
  r := submit_answer(p_code => v_code, p_answer => 'y');
  r := submit_answer(p_code => v_code, p_answer => 'z');
  select * into p from progress where team_id = v_id and station_id = v_s2;
  if p.locked_until is null or p.pauses <> 1 or r->>'message' not like 'Dreimal falsch.%' then raise exception 'PROBE FEHLT 5A: Denkpause % / % / %', p.locked_until, p.pauses, r->>'message'; end if;
  r := submit_answer(v_code, 'z', 2);
  select * into p from progress where team_id = v_id and station_id = v_s2;
  if r->>'message' not like 'Denkpause: noch %' or p.pauses <> 1 then raise exception 'PROBE FEHLT 5B: Wiederholung in der Denkpause % / %', r->>'message', p.pauses; end if;
  update progress set locked_until = now() - interval '1 second' where team_id = v_id and station_id = v_s2;
  r := submit_answer(v_code, 'z', 2);
  select * into p from progress where team_id = v_id and station_id = v_s2;
  if r->>'message' <> 'Leider falsch. Noch 3 Versuche.' or p.pauses <> 1 or p.failed_attempts <> 0 then
    raise exception 'PROBE FEHLT 5C: dieselbe Antwort nach der Pause % / % / %', r->>'message', p.pauses, p.failed_attempts; end if;
  r := submit_answer(p_code => v_code, p_answer => 'zwei');
  if not (r->>'ok')::boolean then raise exception 'PROBE FEHLT 4B: alte App, richtige Antwort %', r->>'message'; end if;
  v_n := v_n + 5;

  -- 6: submit_final zweimal, gleicher Platz (Testmodus: eine Station, keine Ortsprüfung)
  update game_state set test_mode = true where id = 1;
  select id, digit into v_st, v_ziffer from stations_alle where route = 'test' order by position limit 1;
  insert into progress (team_id, station_id, checked_in_at, solved_at) values (v_id, v_st, now(), now());
  r := submit_final(v_code, v_ziffer::text || (v_ziffer % 10)::text);
  r2 := submit_final(v_code, v_ziffer::text || (v_ziffer % 10)::text);
  if not (r->>'ok')::boolean or r->>'place' is null or r2->>'place' is distinct from r->>'place' then raise exception 'PROBE FEHLT 6: Plätze % / %', r->>'place', r2->>'place'; end if;
  v_n := v_n + 1;

  -- 7: Rechte
  if exists (select 1 from pg_proc where proname = 'submit_answer' and pronamespace = 'public'::regnamespace and pronargs = 2) then
    raise exception 'PROBE FEHLT 7A: submit_answer(text, text) gibt es noch'; end if;
  foreach f in array array[__INTERN__] loop
    foreach rr in array array['anon', 'authenticated'] loop
      if has_function_privilege(rr, f, 'execute') then raise exception 'PROBE FEHLT 7B: % darf % ausführen', rr, f; end if;
      v_n := v_n + 1;
    end loop;
  end loop;
  foreach f in array array[__SPIEL__] loop
    foreach rr in array array['anon', 'authenticated'] loop
      if not has_function_privilege(rr, f, 'execute') then raise exception 'PROBE FEHLT 7C: % darf % nicht ausführen', rr, f; end if;
      v_n := v_n + 1;
    end loop;
  end loop;
  v_n := v_n + 1;

  raise exception 'PROBELAUF_OK: % Prüfungen bestanden, alles zurückgenommen', v_n;
end $probe$;
"""


def main() -> None:
    migration = "" if "--ohne" in sys.argv else MIGRATION.read_text(encoding="utf-8")
    assert "$mig$" not in migration and "$probe$" not in migration
    liste = lambda xs: ", ".join("'" + x + "'" for x in xs)  # noqa: E731
    probe = (PROBE.replace("__INTERN__", liste(INTERN)).replace("__SPIEL__", liste(SPIEL))
             .replace("__MIGRATION__", f"execute $mig${migration}$mig$;" if migration.strip() else ""))
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
