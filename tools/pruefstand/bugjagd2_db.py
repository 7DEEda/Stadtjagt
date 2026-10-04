#!/usr/bin/env python3
"""
Probelauf für Nachtrag 32 (Bugjagd 03.10.2026, Funde 9, 12, 14, 16) gegen die echte Datenbank, ohne Spuren.

    python tools/pruefstand/bugjagd2_db.py           mit Migration (grün)
    python tools/pruefstand/bugjagd2_db.py --ohne    ohne Migration (zeigt, was fehlt: rot)

EIN DO-Block spielt die Migration ein, prüft und wirft am Ende absichtlich einen Fehler. Auch wenn eine
Prüfung scheitert, endet der Block mit einer Ausnahme: der Server rollt die ganze Anweisung zurück.
Geprüft werden auch die Rechte wie in rechte_db.py: interne Hilfsfunktionen für anon und authenticated
gesperrt, die geänderten Spielfunktionen offen.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sql  # noqa: E402
from rechte_db import INTERN  # noqa: E402

MIGRATION = sql.REPO / "supabase" / "migrations" / "20261004100000_bugjagd2.sql"
SPIEL = ["register_participant(text,text)", "submit_answer(text,text)", "admin_set_test_mode(text,boolean)",
         "device_test_save(text,jsonb)"]

PROBE = r"""
do $probe$
declare v_pin text; v_n int := 0; r json; v_err text; f text; rr text;
        v_tok text := md5(random()::text) || md5(random()::text);
        v_name text := 'Probe ' || translate(substr(md5(random()::text), 1, 10), '0123456789', 'ghijklmnop');
        v_code text := 'PROBE-' || substr(md5(random()::text), 1, 8); v_id uuid; v_st uuid;
begin
  __MIGRATION__
  select admin_pin into v_pin from game_state where id = 1;

  -- ---------- Fund 9: register_participant mit p_token wiederholbar ----------
  if not exists (select 1 from pg_proc where proname = 'register_participant' and pronamespace = 'public'::regnamespace and pronargs = 2) then
    raise exception 'PROBE FEHLT 9: register_participant kennt p_token nicht'; end if;
  if (select count(*) from pg_proc where proname = 'register_participant' and pronamespace = 'public'::regnamespace) <> 1 then
    raise exception 'PROBE FEHLT 9: register_participant nicht genau einmal'; end if;
  update game_state set status = 'registration' where id = 1;
  r := register_participant(v_name, v_tok);
  if r->>'token' is distinct from v_tok or r->>'name' is distinct from v_name then raise exception 'PROBE FEHLT 9A: erste Anmeldung %', r; end if;
  r := register_participant(v_name, v_tok);
  if r->>'token' is distinct from v_tok or r->>'name' is distinct from v_name then raise exception 'PROBE FEHLT 9B: Wiederholung %', r; end if;
  if (select count(*) from participants where name_key = norm(v_name)) <> 1 then raise exception 'PROBE FEHLT 9C: doppelt angelegt'; end if;
  begin perform register_participant(v_name, md5('fremd') || md5('handy')); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is null or v_err not like '%schon angemeldet%' then raise exception 'PROBE FEHLT 9D: anderer Schlüssel: %', coalesce(v_err, 'angenommen'); end if;
  if (select token from participants where name_key = norm(v_name)) <> v_tok then raise exception 'PROBE FEHLT 9E: Schlüssel überschrieben'; end if;
  -- alter Aufruf ohne p_token: vorhandener Name abgelehnt, neuer Name bekommt einen Schlüssel vom Server
  begin perform register_participant(v_name); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is null or v_err not like '%schon angemeldet%' then raise exception 'PROBE FEHLT 9F: alter Aufruf, vorhandener Name: %', coalesce(v_err, 'angenommen'); end if;
  r := register_participant(p_name => v_name || 'zwei');
  if coalesce(r->>'token', '') !~ '^[0-9a-f]{64}$' then raise exception 'PROBE FEHLT 9G: alter Aufruf ohne Schlüssel: %', r; end if;
  begin perform register_participant(v_name || 'drei', 'kurz'); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is null or v_err not like 'Ungültiger Geräte-Schlüssel%' then raise exception 'PROBE FEHLT 9H: Schlüssel ohne Format: %', coalesce(v_err, 'angenommen'); end if;
  -- nach dem Auslosen: die Wiederholung bleibt ein Erfolg, Neues ist geschlossen
  update game_state set status = 'drawn' where id = 1;
  r := register_participant(v_name, v_tok);
  if r->>'token' is distinct from v_tok then raise exception 'PROBE FEHLT 9I: Wiederholung nach dem Auslosen %', r; end if;
  begin perform register_participant(v_name || 'vier', md5('a') || md5('b')); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is null or v_err not like 'Die Anmeldung ist geschlossen%' then raise exception 'PROBE FEHLT 9J: nach dem Auslosen neu: %', coalesce(v_err, 'angenommen'); end if;
  -- Spielleitung berichtigt den Namen zwischen zwei Versuchen: die Wiederholung bekommt den Erfolg der Person
  -- (mit dem neuen Namen), statt an der Eindeutigkeit des Schlüssels zu scheitern
  update game_state set status = 'registration' where id = 1;
  update participants set name = v_name || ' Neu', name_key = norm(v_name || ' Neu') where token = v_tok;
  begin r := register_participant(v_name, v_tok); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is not null then raise exception 'PROBE FEHLT 9K: nach Umbenennen: %', v_err; end if;
  if r->>'token' is distinct from v_tok or r->>'name' is distinct from v_name || ' Neu' then raise exception 'PROBE FEHLT 9L: nach Umbenennen %', r; end if;
  if (select count(*) from participants where token = v_tok) <> 1 or exists (select 1 from participants where name_key = norm(v_name))
    then raise exception 'PROBE FEHLT 9M: nach Umbenennen doppelt angelegt'; end if;
  v_n := v_n + 15;

  -- ---------- Fund 12: device_test_save prüft die Form ----------
  perform device_test_save('PROBEAAAAAA1', '{"suite": 21, "label": "Probe", "tests": {"umgebung": {"art": "ok"}}, "bilanz": {"ok": 1}}'::jsonb);
  if not exists (select 1 from device_test_runs where run_key = 'PROBEAAAAAA1') then raise exception 'PROBE FEHLT 12A: gültiger Lauf abgelehnt'; end if;
  foreach f in array array['{"suite": 21, "tests": "x", "bilanz": {}}', '{"suite": 21, "tests": {}, "bilanz": "x"}',
                           '{"suite": "21", "tests": {}, "bilanz": {}}', '{"tests": {}, "bilanz": {}}',
                           '{"suite": 21, "tests": {"umgebung": "x"}, "bilanz": {}}'] loop
    begin perform device_test_save('PROBEAAAAAA2', f::jsonb); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is null then raise exception 'PROBE FEHLT 12B: angenommen: %', f; end if;
    v_n := v_n + 1;
  end loop;
  v_n := v_n + 1;

  -- ---------- Fund 14: Testmodus umschalten mit Plätzen ----------
  update game_state set status = 'running', test_mode = true, started_at = coalesce(started_at, now()) where id = 1;
  insert into teams (name, code, read_token) values ('Probelauf', v_code, md5(random()::text)) returning id into v_id;
  delete from finishes where true;
  perform admin_set_test_mode(v_pin, false);
  if (select test_mode from game_state where id = 1) then raise exception 'PROBE FEHLT 14A: ohne Plätze nicht ausgeschaltet'; end if;
  perform admin_set_test_mode(v_pin, true);
  if not (select test_mode from game_state where id = 1) then raise exception 'PROBE FEHLT 14B: Einschalten im laufenden Spiel'; end if;
  insert into finishes (team_id, place) values (v_id, 1);
  begin perform admin_set_test_mode(v_pin, false); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is distinct from 'Im Testlauf gibt es schon Plätze. Erst im Reiter Daten löschen „Fortschritt zurücksetzen“, dann den Testmodus ausschalten.'
    then raise exception 'PROBE FEHLT 14C: Ausschalten mit Plätzen: %', coalesce(v_err, 'erlaubt'); end if;
  if not (select test_mode from game_state where id = 1) then raise exception 'PROBE FEHLT 14D: Testmodus trotzdem aus'; end if;
  perform admin_set_test_mode(v_pin, true);   -- an bleibt an: kein Umschalten, kein Fehler
  update game_state set status = 'finished' where id = 1;
  perform admin_set_test_mode(v_pin, false);
  if (select test_mode from game_state where id = 1) then raise exception 'PROBE FEHLT 14E: nach dem Ende nicht ausgeschaltet'; end if;
  -- Entscheidung 04.10.2026: im laufenden Spiel mit Plätzen auch nicht einschalten
  update game_state set status = 'running' where id = 1;
  begin perform admin_set_test_mode(v_pin, true); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is distinct from 'Im laufenden Spiel gibt es schon Plätze. Den Testmodus jetzt einzuschalten würde die Rangliste durcheinanderbringen.'
    then raise exception 'PROBE FEHLT 14F: Einschalten mit Plätzen: %', coalesce(v_err, 'erlaubt'); end if;
  if (select test_mode from game_state where id = 1) then raise exception 'PROBE FEHLT 14G: Testmodus trotzdem an'; end if;
  perform admin_set_test_mode(v_pin, false);   -- aus bleibt aus: kein Fehler
  delete from finishes where true;
  perform admin_set_test_mode(v_pin, true);
  if not (select test_mode from game_state where id = 1) then raise exception 'PROBE FEHLT 14H: Einschalten ohne Platz'; end if;
  v_n := v_n + 8;

  -- ---------- Fund 16: leere Antwort ----------
  update game_state set status = 'running', test_mode = false where id = 1;
  delete from finishes where true;
  select id into v_st from stations_alle where route = 'echt' order by position limit 1;
  update stations_alle set answer = 'probe' where id = v_st;
  insert into progress (team_id, station_id, checked_in_at) values (v_id, v_st, now());
  r := submit_answer(v_code, '');
  if (r->>'ok')::boolean or r->>'message' is distinct from 'Bitte gebt eine Antwort ein.' then raise exception 'PROBE FEHLT 16A: leer: %', r->>'message'; end if;
  r := submit_answer(v_code, ' ?! ');
  if (r->>'ok')::boolean or r->>'message' is distinct from 'Bitte gebt eine Antwort ein.' then raise exception 'PROBE FEHLT 16B: Satzzeichen: %', r->>'message'; end if;
  if (select failed_attempts from progress where team_id = v_id and station_id = v_st) <> 0 then raise exception 'PROBE FEHLT 16C: leer als Fehlversuch gezählt'; end if;
  r := submit_answer(v_code, 'falsch');
  if (select failed_attempts from progress where team_id = v_id and station_id = v_st) <> 1 then raise exception 'PROBE FEHLT 16D: falsch nicht gezählt'; end if;
  r := submit_answer(v_code, 'Probe!');
  if not (r->>'ok')::boolean then raise exception 'PROBE FEHLT 16E: richtige Antwort: %', r->>'message'; end if;
  update game_state set test_mode = true where id = 1;
  select id into v_st from stations_alle where route = 'test' order by position limit 1;
  insert into progress (team_id, station_id, checked_in_at) values (v_id, v_st, now());
  r := submit_answer(v_code, '');
  if not coalesce((r->>'ok')::boolean, false) then raise exception 'PROBE FEHLT 16F: Testmodus, leer: %', r->>'message'; end if;
  v_n := v_n + 6;

  -- ---------- Rechte ----------
  foreach f in array array[__INTERN__] loop
    foreach rr in array array['anon', 'authenticated'] loop
      if has_function_privilege(rr, f, 'execute') then raise exception 'PROBE FEHLT R1: % darf % ausführen', rr, f; end if;
      v_n := v_n + 1;
    end loop;
  end loop;
  foreach f in array array[__SPIEL__] loop
    foreach rr in array array['anon', 'authenticated'] loop
      if not has_function_privilege(rr, f, 'execute') then raise exception 'PROBE FEHLT R2: % darf % nicht ausführen', rr, f; end if;
      v_n := v_n + 1;
    end loop;
  end loop;

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
