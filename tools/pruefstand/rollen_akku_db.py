#!/usr/bin/env python3
"""
Probelauf für die Migration 20261029120000_rollen_akku.sql (Rollen und Akku, Plan Task 1) gegen die echte Datenbank,
ohne Spuren.

    python tools/pruefstand/rollen_akku_db.py          mit Migration (grün)
    python tools/pruefstand/rollen_akku_db.py --ohne   Stand der Datenbank ohne Migration (rot)

Wie eingaben_db.py: EIN DO-Block spielt die Migration ein, legt erfundene Teams und Personen an, setzt das Spiel im
Block auf running bzw. drawn, prüft und wirft am Ende absichtlich einen Fehler (Marker PROBELAUF_OK oder PROBE FEHLT).
Der Server rollt alles zurück, auch die Migration. Die Migration selbst wird hier nie dauerhaft eingespielt.
Die Prüfungen sammeln ihre Funde und melden alle auf einmal. Während des Laufs (etwa eine Sekunde) ist die Zeile
game_state gesperrt; nicht während eines laufenden Spiels starten.

Weil now() in einer Transaktion stillsteht, setzt der Lauf die Zeitstempel (gesehen_at, akku_at) von Hand auf alt.

Geprüft:
   1  alter Aufruf member_state(token) mit einem Argument, benannt, leerer Token; ichLeite, kein Code im Ergebnis
   2  Akku setzen (Wert, lädt), null überschreibt nichts, lädt ohne Angabe = falsch
   3  ungültige Werte (-1, 101) werden ignoriert, auch gesehen_at/akku_at bleiben
   4  Drosselung: höchstens eine Schreibung je 20 s, außer der Akku ändert sich
   5  team_state.geraete: angemeldet, verbunden (2 min), Akku-Alter (10 min), members unverändert
   6  report_position mit und ohne Akku, alter Aufruf, Akku nur auf die Teamleitung, nichts in drawn
   7  ichLeite nach team_set_leader; Person ohne Team
   8  admin_state: hatHandy, leaderAkku (Alter, keine Leitung)
   9  genau eine member_state, eine report_position; member_state_by_team ist weg (F7)
  10  Rechte, SECURITY DEFINER, search_path; interne Hilfsfunktionen weiter gesperrt; neue Spalten nicht für anon
  11  alle bisherigen Felder von team_state und admin_state noch da
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sql  # noqa: E402
from rechte_db import INTERN  # noqa: E402

MIGRATION = sql.REPO / "supabase" / "migrations" / "20261029120000_rollen_akku.sql"
NEU = ["member_state(text,integer,boolean)",
       "report_position(text,double precision,double precision,double precision,text,integer,boolean)",
       "team_state(text)", "admin_state(text)"]


def chk(bedingung: str, text: str, ist: str = "") -> str:
    """Eine Prüfung: bei Misserfolg wird der Fund gesammelt, der Lauf geht weiter."""
    z = f" || ': ' || coalesce(({ist})::text, 'null')" if ist else ""
    return (f"  if not coalesce(({bedingung}), false) then v_f := v_f || ('{text}'::text{z}); end if; v_n := v_n + 1;")


def pruefungen() -> str:
    c = []
    a = c.append
    st = lambda k: f"(select {k} from participants where id = v_a)"  # noqa: E731
    stb = lambda k: f"(select {k} from participants where id = v_b)"  # noqa: E731

    a("-- 1: alter Aufruf")
    a("  r := member_state(v_ta);")
    a(chk("r->>'name' = v_na and (r->>'ichLeite')::boolean", "1A alter Aufruf: Name oder ichLeite", "r::text"))
    a(chk("r->'team' is not null and json_typeof(r->'team') = 'object' and not ((r::jsonb #> '{team}') ? 'code') "
          "and not ((r::jsonb #> '{team}') ? 'readToken')", "1B Team ohne code und readToken"))
    a(chk("json_typeof(r->'geraete') = 'array'", "1C geraete fehlt in member_state"))
    a("  r := member_state(p_token => v_tb);")
    a(chk("not (r->>'ichLeite')::boolean", "1D benannter Aufruf: ichLeite für Mitglied"))
    a("  begin perform member_state(''); v_f := v_f || '1E leerer Token angenommen'::text; "
      "exception when others then if sqlerrm <> 'Unbekanntes Gerät.' then v_f := v_f || ('1E falscher Text: ' || sqlerrm); end if; end;")
    a("  begin perform member_state('gibt-es-nicht', 50, true); v_f := v_f || '1F unbekannter Token angenommen'::text; "
      "exception when others then if sqlerrm <> 'Unbekanntes Gerät.' then v_f := v_f || ('1F falscher Text: ' || sqlerrm); end if; end;")
    a("  v_n := v_n + 2;")
    a(chk(f"{stb('gesehen_at')} is not null", "1G gesehen_at nach erstem Abruf"))
    a(chk(f"{stb('akku')} is null and {stb('akku_at')} is null", "1H ohne Akku bleibt der Akku leer"))

    a("-- 2: Akku setzen")
    a("  perform member_state(v_tb, 42, true);")
    a(chk(f"{stb('akku')} = 42 and {stb('akku_laedt')} and {stb('akku_at')} = now()", "2A Akku 42 lädt"))
    a("  perform member_state(v_tb, 41, false);")
    a(chk(f"{stb('akku')} = 41 and not {stb('akku_laedt')}", "2B Akku 41 lädt nicht (geändert, trotz Drosselung)"))
    a("  update participants set gesehen_at = now() - interval '1 minute' where id = v_b;")
    a("  perform member_state(v_tb);")
    a(chk(f"{stb('akku')} = 41 and not {stb('akku_laedt')}", "2C null überschreibt den Akku nicht"))
    a(chk(f"{stb('gesehen_at')} = now()", "2D gesehen_at neu nach null-Abruf"))
    a("  update participants set akku_laedt = true, gesehen_at = now() - interval '1 minute' where id = v_b;")
    a("  perform member_state(v_tb, 41, null);")
    a(chk(f"{stb('akku')} = 41 and {stb('akku_laedt')} = false", "2E lädt ohne Angabe ist falsch"))
    a("  perform member_state(v_tb, 0, false);")
    a(chk(f"{stb('akku')} = 0", "2F Grenze 0 gültig"))
    a("  perform member_state(v_tb, 100, true);")
    a(chk(f"{stb('akku')} = 100 and {stb('akku_laedt')}", "2G Grenze 100 gültig"))
    a("  update participants set akku = null, akku_laedt = null, akku_at = null where id = v_b;")

    a("-- 3: ungültige Werte")
    a("  perform member_state(v_tb, 55, true);")
    a("  update participants set gesehen_at = now() - interval '1 minute', akku_at = now() - interval '3 minutes' where id = v_b;")
    a("  perform member_state(v_tb, 101, false);")
    a("  perform member_state(v_tb, -1, false);")
    a(chk(f"{stb('akku')} = 55 and {stb('akku_laedt')}", "3A 101 und -1 ändern den Akku nicht", f"{stb('akku')}"))
    a(chk(f"{stb('akku_at')} = now() - interval '3 minutes'", "3B akku_at bleibt bei ungültigem Wert"))
    a(chk(f"{stb('gesehen_at')} = now()", "3C gesehen_at wird trotzdem gesetzt"))

    a("-- 4: Drosselung")
    a("  update participants set gesehen_at = now() - interval '5 seconds', akku = 50, akku_laedt = false, "
      "akku_at = now() - interval '5 seconds' where id = v_b;")
    a("  perform member_state(v_tb);")
    a(chk(f"{stb('gesehen_at')} = now() - interval '5 seconds'", "4A kein Schreiben ohne Akku nach 5 s"))
    a("  perform member_state(v_tb, 50, false);")
    a(chk(f"{stb('gesehen_at')} = now() - interval '5 seconds' and {stb('akku_at')} = now() - interval '5 seconds'",
          "4B kein Schreiben bei gleichem Akku nach 5 s"))
    a("  perform member_state(v_tb, 49, false);")
    a(chk(f"{stb('akku')} = 49 and {stb('gesehen_at')} = now()", "4C Akku geändert: sofort geschrieben"))
    a("  update participants set gesehen_at = now() - interval '5 seconds' where id = v_b;")
    a("  perform member_state(v_tb, 49, true);")
    a(chk(f"{stb('akku_laedt')} and {stb('gesehen_at')} = now()", "4D Laden geändert: sofort geschrieben"))
    a("  update participants set gesehen_at = now() - interval '30 seconds', akku_at = now() - interval '30 seconds' where id = v_b;")
    a("  perform member_state(v_tb, 49, true);")
    a(chk(f"{stb('gesehen_at')} = now() and {stb('akku_at')} = now()", "4E nach 30 s wieder geschrieben"))

    a("-- 5: geraete")
    a("  update participants set gesehen_at = now() - interval '1 minute', akku = 30, akku_laedt = true, "
      "akku_at = now() - interval '9 minutes' where id = v_b;")
    a("  update participants set gesehen_at = null, akku = null, akku_at = null, akku_laedt = null where id = v_a;")
    a("  r := team_state(v_code);")
    a(chk("json_array_length(r->'geraete') = 3", "5A drei Geräte", "json_array_length(r->'geraete')"))
    a("  select x into r2 from json_array_elements(r->'geraete') x where x->>'name' = v_nb;")
    a(chk("(r2->>'angemeldet')::boolean and (r2->>'verbunden')::boolean and (r2->>'akku')::int = 30 and (r2->>'laedt')::boolean",
          "5B angemeldet, verbunden (1 min), Akku 30 lädt (9 min)", "r2::text"))
    a("  select x into r2 from json_array_elements(r->'geraete') x where x->>'name' = v_nc;")
    a(chk("not (r2->>'angemeldet')::boolean and not (r2->>'verbunden')::boolean and r2->'akku' is not null "
          "and json_typeof(r2->'akku') = 'null'", "5C ohne Gerät: nicht angemeldet, nicht verbunden, kein Akku", "r2::text"))
    a("  select x into r2 from json_array_elements(r->'geraete') x where x->>'name' = v_na;")
    a(chk("(r2->>'angemeldet')::boolean and not (r2->>'verbunden')::boolean and json_typeof(r2->'akku') = 'null'",
          "5D angemeldet, nie gesehen: nicht verbunden", "r2::text"))
    a("  update participants set gesehen_at = now() - interval '3 minutes', akku_at = now() - interval '11 minutes' where id = v_b;")
    a("  select x into r2 from json_array_elements(team_state(v_code)->'geraete') x where x->>'name' = v_nb;")
    a(chk("not (r2->>'verbunden')::boolean and json_typeof(r2->'akku') = 'null' and json_typeof(r2->'laedt') = 'null'",
          "5E 3 min nicht gesehen und Akku 11 min alt: nicht verbunden, Akku und laedt leer", "r2::text"))
    a("  update participants set gesehen_at = now() - interval '119 seconds', akku_at = now() - interval '599 seconds' where id = v_b;")
    a("  select x into r2 from json_array_elements(team_state(v_code)->'geraete') x where x->>'name' = v_nb;")
    a(chk("(r2->>'verbunden')::boolean and (r2->>'akku')::int = 30", "5F knapp unter 2 min und 10 min noch gültig", "r2::text"))
    a(chk("(r->'geraete'->0->>'name') <= (r->'geraete'->1->>'name') and (r->'geraete'->1->>'name') <= (r->'geraete'->2->>'name')",
          "5G Geräte nach Namen sortiert"))
    a(chk("json_array_length(r->'team'->'members') = 3 and json_typeof(r->'team'->'members'->0) = 'string'",
          "5H members bleibt Liste von Namen", "r->'team'->>'members'"))
    a("  r := member_state(v_ta);")
    a(chk("json_array_length(r->'geraete') = 3", "5I geraete auch in member_state"))

    a("-- 6: report_position")
    a("  update game_state set status = 'running', test_mode = false, started_at = coalesce(started_at, now()) where id = 1;")
    a("  update participants set akku = null, akku_laedt = null, akku_at = null, gesehen_at = null where id in (v_a, v_b);")
    a("  v_pl := (select count(*) from position_log where team_id = v_id);")
    a("  perform report_position(v_code, 50.1, 14.4, 5, 'ok', 77, true);")
    a(chk(f"{st('akku')} = 77 and {st('akku_laedt')} and {st('akku_at')} = now() and {st('gesehen_at')} = now()",
          "6A Akku auf die Teamleitung"))
    a(chk(f"{stb('akku')} is null", "6B Mitglied bekommt den Akku der Leitung nicht"))
    a(chk("(select count(*) from position_log where team_id = v_id) = v_pl + 1 and "
          "(select lat from team_positions where team_id = v_id) = 50.1", "6C Position eingetragen"))
    a("  update participants set gesehen_at = now() - interval '1 minute' where id = v_a;")
    a("  perform report_position(v_code, 50.1, 14.4, 5, 'ok');")
    a("  perform report_position(p_code => v_code, p_lat => 50.1, p_lng => 14.4, p_acc => 5);")
    a(chk(f"{st('akku')} = 77 and {st('gesehen_at')} = now() - interval '1 minute'", "6D ohne Akku (alter Aufruf) ändert nichts"))
    a(chk("(select count(*) from position_log where team_id = v_id) = v_pl + 3", "6E alter Aufruf schreibt Position"))
    a("  perform report_position(v_code, 50.1, 14.4, 5, 'ok', 150, false);")
    a("  perform report_position(v_code, 50.1, 14.4, 5, 'ok', -3, false);")
    a(chk(f"{st('akku')} = 77 and {st('akku_laedt')}", "6F ungültiger Akku ignoriert"))
    a("  perform report_position(v_code, 50.1, 14.4, 5, 'ok', 77, true);")
    a("  perform report_position(v_code, 50.1, 14.4, 5, 'ok', 77, true);")
    a(chk(f"{st('gesehen_at')} = now()", "6G gleicher Akku nach 1 min: wieder geschrieben"))
    a("  update participants set gesehen_at = now() - interval '10 seconds' where id = v_a;")
    a("  perform report_position(v_code, 50.1, 14.4, 5, 'ok', 77, true);")
    a(chk(f"{st('gesehen_at')} = now() - interval '10 seconds'", "6H gleicher Akku nach 10 s: nicht geschrieben"))
    a("  perform report_position(v_code, 50.1, 14.4, 5, 'ok', 76, true);")
    a(chk(f"{st('akku')} = 76", "6I geänderter Akku sofort"))
    a("  v_pl := (select count(*) from position_log where team_id = v_id);")
    a("  perform report_position(v_code, null, null, null, null, 60, false);")
    a("  perform report_position(v_code, 0, 0, 5, null, 60, false);")
    a(chk(f"{st('akku')} = 60 and (select count(*) from position_log where team_id = v_id) = v_pl",
          "6J Akku auch ohne brauchbare Position, keine Position geschrieben"))
    a("  update game_state set status = 'drawn' where id = 1;")
    a("  perform report_position(v_code, 50.1, 14.4, 5, 'ok', 12, false);")
    a(chk(f"{st('akku')} = 60 and (select count(*) from position_log where team_id = v_id) = v_pl",
          "6K in drawn wird nichts geschrieben"))
    a("  update game_state set status = 'registration' where id = 1;")
    a("  perform report_position(v_code, 50.1, 14.4, 5, 'ok', 12, false);")
    a(chk(f"{st('akku')} = 60", "6L in registration wird nichts geschrieben"))
    a("  update game_state set status = 'running' where id = 1;")
    a("  insert into teams (name, code, read_token) values ('Probelauf ohne Leitung', v_code2, md5(random()::text)) returning id into v_id2;")
    a("  perform report_position(v_code2, 50.1, 14.4, 5, 'ok', 33, false);")
    a(chk("(select count(*) from position_log where team_id = v_id2) = 1", "6M Team ohne Leitung: Position ja, kein Fehler"))
    a("  begin perform report_position('gibt-es-nicht', 50.1, 14.4, 5, 'ok', 33, false); v_f := v_f || '6N unbekannter Code angenommen'::text; "
      "exception when others then if sqlerrm <> 'Unbekannter Team-Code.' then v_f := v_f || ('6N falscher Text: ' || sqlerrm); end if; end;")
    a("  v_n := v_n + 1;")

    a("-- 7: ichLeite")
    a("  r := member_state(v_ta); r2 := member_state(v_tb);")
    a(chk("(r->>'ichLeite')::boolean and not (r2->>'ichLeite')::boolean", "7A Leitung A", "r->>'ichLeite' || r2->>'ichLeite'"))
    a("  perform team_set_leader(v_code, v_nb);")
    a("  r := member_state(v_ta); r2 := member_state(v_tb);")
    a(chk("not (r->>'ichLeite')::boolean and (r2->>'ichLeite')::boolean", "7B nach team_set_leader wechselt ichLeite", "r->>'ichLeite' || r2->>'ichLeite'"))
    a(chk("r2->'team'->>'leaderName' = v_nb", "7C leaderName passt"))
    a("  perform report_position(v_code, 50.1, 14.4, 5, 'ok', 20, false);")
    a(chk(f"{stb('akku')} = 20 and {st('akku')} <> 20", "7D Akku folgt der neuen Leitung"))
    a("  insert into participants (name, name_key, token) values (v_ne, norm(v_ne), 'probe-' || md5(random()::text)) returning token into v_te;")
    a("  r := member_state(v_te);")
    a(chk("json_typeof(r->'team') = 'null' and not (r->>'ichLeite')::boolean and r->>'name' = v_ne", "7E Person ohne Team", "r::text"))
    a("  perform team_set_leader(v_code, v_na);")

    a("-- 8: admin_state")
    a("  v_pin := (select admin_pin from game_state where id = 1);")
    a("  update participants set akku = 64, akku_laedt = true, akku_at = now() where id = v_a;")
    a("  r := admin_state(v_pin);")
    a("  select x into r2 from json_array_elements(r->'participants') x where x->>'id' = v_a::text;")
    a(chk("(r2->>'hatHandy')::boolean", "8A hatHandy mit Token", "r2::text"))
    a("  select x into r2 from json_array_elements(r->'participants') x where x->>'id' = v_c::text;")
    a(chk("r2->>'hatHandy' = 'false'", "8B hatHandy ohne Token", "r2::text"))
    a("  select x into r2 from json_array_elements(r->'teams') x where x->>'id' = v_id::text;")
    a(chk("(r2->'leaderAkku'->>'akku')::int = 64 and (r2->'leaderAkku'->>'laedt')::boolean and r2->'leaderAkku'->>'at' is not null",
          "8C leaderAkku mit Wert, lädt und at", "r2->>'leaderAkku'"))
    a("  update participants set akku_at = now() - interval '11 minutes' where id = v_a;")
    a("  select x into r2 from json_array_elements(admin_state(v_pin)->'teams') x where x->>'id' = v_id::text;")
    a(chk("r2->>'leaderAkku' is null", "8D leaderAkku nach 11 min leer", "r2->>'leaderAkku'"))
    a("  update participants set akku_at = now() - interval '599 seconds' where id = v_a;")
    a("  select x into r2 from json_array_elements(admin_state(v_pin)->'teams') x where x->>'id' = v_id::text;")
    a(chk("(r2->'leaderAkku'->>'akku')::int = 64", "8E leaderAkku knapp unter 10 min", "r2->>'leaderAkku'"))
    a("  update participants set akku = null, akku_at = null where id = v_a;")
    a("  select x into r2 from json_array_elements(admin_state(v_pin)->'teams') x where x->>'id' = v_id::text;")
    a(chk("r2->>'leaderAkku' is null", "8F Leitung ohne Akku: leer", "r2->>'leaderAkku'"))
    a("  select x into r2 from json_array_elements(admin_state(v_pin)->'teams') x where x->>'id' = v_id2::text;")
    a(chk("r2->>'leaderAkku' is null and r2->>'leaderId' is null", "8G Team ohne Leitung: leer", "r2::text"))

    a("-- 9: Signaturen")
    a(chk("(select count(*) from pg_proc where pronamespace = 'public'::regnamespace and proname = 'member_state') = 1 "
          "and (select pronargs from pg_proc where pronamespace = 'public'::regnamespace and proname = 'member_state') = 3",
          "9A genau eine member_state mit drei Parametern"))
    a(chk("(select count(*) from pg_proc where pronamespace = 'public'::regnamespace and proname = 'report_position') = 1 "
          "and (select pronargs from pg_proc where pronamespace = 'public'::regnamespace and proname = 'report_position') = 7",
          "9B genau eine report_position mit sieben Parametern"))
    a(chk("not exists (select 1 from pg_proc where pronamespace = 'public'::regnamespace and proname = 'member_state_by_team')",
          "9C member_state_by_team gibt es noch"))
    a(chk("(select count(*) from pg_proc where pronamespace = 'public'::regnamespace and proname in ('team_state', 'admin_state')) = 2",
          "9D team_state und admin_state je einmal"))
    a(chk("(select count(*) from information_schema.columns where table_schema = 'public' and table_name = 'participants' "
          "and column_name in ('akku', 'akku_laedt', 'akku_at', 'gesehen_at')) = 4", "9E vier neue Spalten"))
    a(chk("(select data_type from information_schema.columns where table_schema = 'public' and table_name = 'participants' "
          "and column_name = 'akku') = 'smallint'", "9F akku ist smallint"))

    a("-- 10: Rechte")
    a("  foreach f in array array[__NEU__] loop")
    a("    foreach rr in array array['anon', 'authenticated'] loop")
    a("      if not has_function_privilege(rr, f, 'execute') then v_f := v_f || ('10A ' || rr || ' darf ' || f || ' nicht ausführen'); end if; v_n := v_n + 1;")
    a("    end loop;")
    a("    if not (select prosecdef from pg_proc where oid = f::regprocedure) then v_f := v_f || ('10B nicht SECURITY DEFINER: ' || f); end if;")
    a("    if not coalesce((select 'search_path=public' = any (proconfig) from pg_proc where oid = f::regprocedure), false) then "
      "v_f := v_f || ('10C search_path fehlt: ' || f); end if;")
    a("    v_n := v_n + 2;")
    a("  end loop;")
    a("  foreach f in array array[__INTERN__] loop")
    a("    foreach rr in array array['anon', 'authenticated'] loop")
    a("      if has_function_privilege(rr, f, 'execute') then v_f := v_f || ('10D ' || rr || ' darf ' || f || ' ausführen'); end if; v_n := v_n + 1;")
    a("    end loop;")
    a("  end loop;")
    a("  foreach rr in array array['anon', 'authenticated'] loop")
    a("    if has_column_privilege(rr, 'public.participants', 'akku', 'select') or has_column_privilege(rr, 'public.participants', 'gesehen_at', 'select') "
      "or has_table_privilege(rr, 'public.participants', 'select') then v_f := v_f || ('10E ' || rr || ' darf participants lesen'); end if; v_n := v_n + 1;")
    a("  end loop;")

    a("-- 11: bisherige Felder")
    a("  r := team_state(v_code);")
    a("  foreach f in array array['team','background','status','startedAt','durationMin','endsAt','totalStations','solvedCount','digits',"
      "'finalDigit','station','checkedIn','failedAttempts','lockedUntil','pauses','allSolved','caseHint','place','prizeCount',"
      "'prizesLeft','winnerTeamId','isWinner','testMode','selfie','geraete'] loop")
    a("    if not (r::jsonb ? f) then v_f := v_f || ('11A team_state ohne ' || f); end if; v_n := v_n + 1;")
    a("  end loop;")
    a("  foreach f in array array['id','name','code','readToken','leaderName','members'] loop")
    a("    if not ((r->'team')::jsonb ? f) then v_f := v_f || ('11B team_state.team ohne ' || f); end if; v_n := v_n + 1;")
    a("  end loop;")
    a("  foreach f in array array['on','pending','replaceable','deleteOn','photos'] loop")
    a("    if not ((r->'selfie')::jsonb ? f) then v_f := v_f || ('11C team_state.selfie ohne ' || f); end if; v_n := v_n + 1;")
    a("  end loop;")
    a("  r := admin_state(v_pin);")
    a("  foreach f in array array['background','status','startedAt','finishedAt','durationMin','endsAt','caseHint','winnerTeamId',"
      "'prizeCount','testMode','selfieOn','photosDeleteOn','photoCount','participants','stations','testStation','route','start',"
      "'testStart','aktiveStationen','caseCode','teams'] loop")
    a("    if not (r::jsonb ? f) then v_f := v_f || ('11D admin_state ohne ' || f); end if; v_n := v_n + 1;")
    a("  end loop;")
    a("  select x into r2 from json_array_elements(r->'participants') x where x->>'id' = v_a::text;")
    a("  foreach f in array array['id','name','teamId','teamName','hatHandy'] loop")
    a("    if not (r2::jsonb ? f) then v_f := v_f || ('11E participants ohne ' || f); end if; v_n := v_n + 1;")
    a("  end loop;")
    a("  select x into r2 from json_array_elements(r->'teams') x where x->>'id' = v_id::text;")
    a("  foreach f in array array['id','name','code','readToken','leaderId','leaderName','memberCount','members','solved',"
      "'currentPosition','checkedInAt','lastSolvedAt','lastActivity','failedAttempts','lockedUntil','position','place','finishedAt',"
      "'leaderAkku'] loop")
    a("    if not (r2::jsonb ? f) then v_f := v_f || ('11F teams ohne ' || f); end if; v_n := v_n + 1;")
    a("  end loop;")
    return "\n".join(x for x in c if x)


PROBE = r"""
do $probe$
declare v_n int := 0; v_f text[] := '{}'; r json; r2 json; f text; rr text; v_pl int; v_pin text;
        v_code text := 'PROBE-' || substr(md5(random()::text), 1, 8); v_code2 text := 'PROBE-' || substr(md5(random()::text), 1, 8);
        v_id uuid; v_id2 uuid; v_a uuid; v_b uuid; v_c uuid;
        v_na text := 'Probe Anna ' || substr(md5(random()::text), 1, 6); v_nb text := 'Probe Ben ' || substr(md5(random()::text), 1, 6);
        v_nc text := 'Probe Cleo ' || substr(md5(random()::text), 1, 6); v_ne text := 'Probe Emil ' || substr(md5(random()::text), 1, 6);
        v_ta text := 'probe-' || md5(random()::text); v_tb text := 'probe-' || md5(random()::text); v_te text;
begin
  __MIGRATION__
  update game_state set status = 'running', test_mode = false, started_at = coalesce(started_at, now()) where id = 1;
  insert into teams (name, code, read_token) values ('Probelauf', v_code, md5(random()::text)) returning id into v_id;
  insert into participants (name, name_key, team_id, token) values (v_na, norm(v_na), v_id, v_ta) returning id into v_a;
  insert into participants (name, name_key, team_id, token) values (v_nb, norm(v_nb), v_id, v_tb) returning id into v_b;
  insert into participants (name, name_key, team_id) values (v_nc, norm(v_nc), v_id) returning id into v_c;
  update teams set leader_participant_id = v_a where id = v_id;

__PRUEFUNGEN__

  if array_length(v_f, 1) > 0 then
    raise exception 'PROBE FEHLT (% von % Prüfungen): %', array_length(v_f, 1), v_n, array_to_string(v_f, ' | ');
  end if;
  raise exception 'PROBELAUF_OK: % Prüfungen bestanden, alles zurückgenommen', v_n;
end $probe$;
"""


def main() -> None:
    migration = "" if "--ohne" in sys.argv else MIGRATION.read_text(encoding="utf-8")
    assert "$mig$" not in migration and "$probe$" not in migration
    liste = lambda xs: ", ".join("'" + x + "'" for x in xs)  # noqa: E731
    probe = (PROBE.replace("__PRUEFUNGEN__", pruefungen()).replace("__INTERN__", liste(INTERN))
             .replace("__NEU__", liste(NEU))
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
