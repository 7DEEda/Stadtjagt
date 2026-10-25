#!/usr/bin/env python3
"""
Probelauf für den Code-Audit vom 25.10.2026 (Migration 20261025090000_audit.sql) gegen die echte Datenbank, ohne Spuren.

    python tools/pruefstand/audit2510_db.py           mit Migration (grün)
    python tools/pruefstand/audit2510_db.py --ohne    ohne Migration (zeigt, was fehlt: rot)

EIN DO-Block spielt die Migration ein, prüft und wirft am Ende absichtlich einen Fehler: der Server rollt die ganze
Anweisung zurück, auch die Migration. Anders als die älteren Probeläufe sammelt dieser die Funde und meldet alle auf
einmal, damit --ohne jeden der sechs Punkte zeigt.

Während des Laufs (etwa eine Sekunde) ist die Zeile game_state gesperrt; Abfragen der App warten so lange. Nicht
während eines laufenden Spiels starten.

Geprüft:
  1  admin_set_selfie: Löschdatum heute und gestern (Prager Zeit) abgelehnt, morgen und leer angenommen; das schon
     gespeicherte Datum geht weiter durch (Ausschalten nach dem Löschtag).
  2  admin_set_test_mode: mit Plätzen in finished, running und drawn in keine Richtung umschaltbar; damit bringt
     „Spiel fortsetzen“ (admin_resume) keine Testplätze ins echte Spiel. Ohne Plätze frei.
  3  Teamleitung: admin_draw, admin_delete_participant, admin_delete_test_participants nehmen zuerst Personen mit
     Geräte-Schlüssel; team_set_leader lehnt ein Ziel ohne Schlüssel ab; admin_set_leader darf jeden (Notweg).
  4  admin_draw: Codes mit sechs Ziffern, team_by_code findet sie; ein alter vierstelliger Code gilt weiter.
  5  register_participant: die 200. Anmeldung geht, die 201. nicht; eine Wiederholung mit bekanntem Schlüssel schon.
  6  register_participant: neue Meldung bei gleichem Namen (beide Stellen).
  7  Rechte und Signaturen unverändert, interne Hilfsfunktionen weiter gesperrt.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sql  # noqa: E402
from rechte_db import INTERN  # noqa: E402

MIGRATION = sql.REPO / "supabase" / "migrations" / "20261025090000_audit.sql"
FUNKTIONEN = ["admin_set_selfie(text,boolean,date)", "admin_set_test_mode(text,boolean)",
              "admin_draw(text,integer,integer)", "admin_delete_participant(text,uuid)",
              "admin_delete_test_participants(text)", "team_set_leader(text,text)", "register_participant(text,text)"]

PROBE = r"""
do $probe$
declare
  v_pin text; v_heute date := (now() at time zone 'Europe/Prague')::date;
  v_sfx text := upper(substr(md5(random()::text), 1, 6));
  v_fehl text[] := '{}'; v_n int := 0; v_err text; r json; f text; rr text; i int; k int;
  t_id uuid; t2_id uuid; a_id uuid; b_id uuid; c_id uuid; v_code text; v_alt text; v_tok text;
  v_rechte_vorher text; v_rechte_nachher text;
  v_neu text := 'Diesen Namen gibt es schon. Bist du das nicht, ergänze etwas, zum Beispiel einen zweiten Vornamen.';
begin
  -- Rechte, Sicherheitsart und search_path der sieben Funktionen vor der Migration (ACL als Menge, die Reihenfolge
  -- der Einträge kann sich durch revoke/grant ändern, ohne dass sich ein Recht ändert)
  select string_agg(p.oid::regprocedure::text || ' ' || coalesce((select array_agg(a::text order by a::text) from unnest(p.proacl) a)::text, '-')
           || ' ' || p.prosecdef::text || ' ' || coalesce(array_to_string(p.proconfig, ','), '-'), ' | ' order by p.oid::regprocedure::text)
    into v_rechte_vorher from pg_proc p where p.oid in (select to_regprocedure(x) from unnest(array[__FUNKTIONEN__]) x);

  __MIGRATION__

  select admin_pin into v_pin from game_state where id = 1;

  -- ---------- 1: Löschdatum ----------
  begin
    update game_state set photos_delete_on = null, selfie_on = false where id = 1;
    begin perform admin_set_selfie(v_pin, true, v_heute); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is distinct from 'Das Löschdatum muss nach heute liegen.' then v_fehl := v_fehl || ('1A Löschdatum heute: ' || coalesce(v_err, 'angenommen')); end if;
    update game_state set photos_delete_on = null where id = 1;
    begin perform admin_set_selfie(v_pin, true, v_heute - 1); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is distinct from 'Das Löschdatum muss nach heute liegen.' then v_fehl := v_fehl || ('1B Löschdatum gestern: ' || coalesce(v_err, 'angenommen')); end if;
    update game_state set photos_delete_on = null where id = 1;
    begin perform admin_set_selfie(v_pin, true, v_heute + 1); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is not null or (select photos_delete_on from game_state where id = 1) is distinct from v_heute + 1 then
      v_fehl := v_fehl || ('1C Löschdatum morgen: ' || coalesce(v_err, 'nicht gespeichert')); end if;
    begin perform admin_set_selfie(v_pin, true, v_heute); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is distinct from 'Das Löschdatum muss nach heute liegen.' then v_fehl := v_fehl || ('1D morgen gespeichert, heute gesendet: ' || coalesce(v_err, 'angenommen')); end if;
    begin perform admin_set_selfie(v_pin, false, null); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is not null then v_fehl := v_fehl || ('1E ohne Löschdatum: ' || v_err); end if;
    -- der Löschtag ist vorbei, die Spielleitung schaltet aus und schickt das gespeicherte Datum mit (wie die App)
    update game_state set photos_delete_on = v_heute - 3, selfie_on = true where id = 1;
    begin perform admin_set_selfie(v_pin, false, v_heute - 3); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is not null or (select selfie_on from game_state where id = 1) then v_fehl := v_fehl || ('1F Ausschalten nach dem Löschtag: ' || coalesce(v_err, 'noch an')); end if;
    update game_state set photos_delete_on = null, selfie_on = false where id = 1;
    v_n := v_n + 6;
  exception when others then v_fehl := v_fehl || ('1 brach ab: ' || sqlerrm);
  end;

  -- ---------- 2: Testmodus mit Plätzen ----------
  begin
    insert into teams (name, code) values ('Probelauf', 'PROBE-' || v_sfx) returning id into t_id;
    insert into finishes (team_id, place) values (t_id, (select coalesce(max(place), 0) + 1 from finishes));
    -- Testlauf beendet, Testmodus aus: abgelehnt
    update game_state set status = 'finished', test_mode = true where id = 1;
    begin perform admin_set_test_mode(v_pin, false); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is null or v_err not like 'Im Testlauf gibt es schon Plätze.%' then v_fehl := v_fehl || ('2A finished, Testmodus aus: ' || coalesce(v_err, 'angenommen')); end if;
    -- danach fortsetzen: das Spiel läuft weiter im Testmodus, die Testplätze landen nicht im echten Spiel
    perform admin_resume(v_pin);
    if (select status || ' ' || test_mode::text from game_state where id = 1) <> 'running true' then
      v_fehl := v_fehl || ('2B nach Fortsetzen: ' || (select status || ' test_mode=' || test_mode::text from game_state where id = 1)); end if;
    -- running: wie bisher
    update game_state set status = 'running', test_mode = true where id = 1;
    begin perform admin_set_test_mode(v_pin, false); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is null then v_fehl := v_fehl || '2C running, Testmodus aus: angenommen'::text; end if;
    -- echtes Spiel beendet: einschalten abgelehnt
    update game_state set status = 'finished', test_mode = false where id = 1;
    begin perform admin_set_test_mode(v_pin, true); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is null or v_err not like 'Es gibt schon Plätze.%' then v_fehl := v_fehl || ('2D finished, Testmodus an: ' || coalesce(v_err, 'angenommen')); end if;
    -- drawn mit Platz (kommt sonst nicht vor): ebenso gesperrt
    update game_state set status = 'drawn', test_mode = true where id = 1;
    begin perform admin_set_test_mode(v_pin, false); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is null then v_fehl := v_fehl || '2E drawn mit Platz, Testmodus aus: angenommen'::text; end if;
    -- gleicher Wert: kein Umschalten, geht durch
    begin perform admin_set_test_mode(v_pin, true); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is not null then v_fehl := v_fehl || ('2F gleicher Wert: ' || v_err); end if;
    -- ohne Plätze frei
    delete from finishes where team_id = t_id;
    update game_state set status = 'finished' where id = 1;
    begin perform admin_set_test_mode(v_pin, false); perform admin_set_test_mode(v_pin, true); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is not null or not (select test_mode from game_state where id = 1) then v_fehl := v_fehl || ('2G ohne Plätze: ' || coalesce(v_err, 'nicht umgeschaltet')); end if;
    delete from teams where id = t_id;
    update game_state set status = 'registration', test_mode = false, started_at = null, finished_at = null where id = 1;
    v_n := v_n + 7;
  exception when others then v_fehl := v_fehl || ('2 brach ab: ' || sqlerrm);
  end;

  -- ---------- 3 und 4: Auslosen, Leitung mit Geräte-Schlüssel, sechsstellige Codes ----------
  begin
    update game_state set status = 'registration', test_mode = false where id = 1;
    for i in 1..20 loop
      insert into participants (name, name_key, token)
        values ('Probe Los ' || i || ' ' || v_sfx, norm('Probe Los ' || i || ' ' || v_sfx),
                case when i <= 4 then md5(random()::text) || md5(random()::text) end);
    end loop;
    k := 0;
    for i in 1..10 loop
      perform admin_draw(v_pin, 4, null);
      if exists (select 1 from teams t
                 where exists (select 1 from participants p where p.team_id = t.id and p.token is not null)
                   and (select p.token from participants p where p.id = t.leader_participant_id) is null) then k := k + 1; end if;
    end loop;
    if k > 0 then v_fehl := v_fehl || ('3A Auslosen: in ' || k || ' von 10 Runden leitet jemand ohne Schlüssel, obwohl es im Team einen mit gibt'); end if;
    if exists (select 1 from teams where code !~ '^[A-Z]+-[0-9]{6}$') then
      v_fehl := v_fehl || ('4A Codes: ' || (select string_agg(code, ', ') from teams)); end if;
    select code into v_code from teams order by random() limit 1;
    if (team_by_code(lower(replace(v_code, '-', ' ')))).code is distinct from v_code then v_fehl := v_fehl || ('4B team_by_code findet ' || v_code || ' nicht'::text); end if;
    -- alter Code aus einem früheren Auslosen: gilt weiter
    v_alt := 'IGEL-' || lpad((floor(random()*9000)+1000)::int::text, 4, '0');
    insert into teams (name, code) values ('Probealt', v_alt) returning id into t2_id;
    if (team_by_code(lower(replace(v_alt, '-', ' ')))).id is distinct from t2_id then v_fehl := v_fehl || ('4C alter Code ' || v_alt || ' nicht gefunden'); end if;
    begin perform team_state(v_alt); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is not null then v_fehl := v_fehl || ('4D team_state mit altem Code: ' || v_err); end if;
    delete from teams where id = t2_id;
    v_n := v_n + 5;
  exception when others then v_fehl := v_fehl || ('3/4 Auslosen brach ab: ' || sqlerrm);
  end;

  begin
    -- ein Team: B mit Schlüssel, fünf ohne
    insert into teams (name, code) values ('Probeleitung', 'PROBEL-' || v_sfx) returning id into t_id;
    v_code := 'PROBEL-' || v_sfx;
    insert into participants (name, name_key, token, team_id) values ('Probe B ' || v_sfx, norm('Probe B ' || v_sfx),
      md5(random()::text) || md5(random()::text), t_id) returning id into b_id;
    for i in 1..5 loop
      insert into participants (name, name_key, team_id) values ('Probe Ohne ' || i || ' ' || v_sfx, norm('Probe Ohne ' || i || ' ' || v_sfx), t_id)
        returning id into c_id;
    end loop;
    -- admin_delete_participant: die Leitung A (mit Schlüssel) wird gelöscht, B muss folgen
    k := 0;
    for i in 1..8 loop
      insert into participants (name, name_key, token, team_id) values ('Probe A ' || i || ' ' || v_sfx, norm('Probe A ' || i || ' ' || v_sfx),
        md5(random()::text) || md5(random()::text), t_id) returning id into a_id;
      update teams set leader_participant_id = a_id where id = t_id;
      perform admin_delete_participant(v_pin, a_id);
      if (select leader_participant_id from teams where id = t_id) is distinct from b_id then k := k + 1; end if;
    end loop;
    if k > 0 then v_fehl := v_fehl || ('3B admin_delete_participant: in ' || k || ' von 8 Runden folgt jemand ohne Schlüssel'); end if;
    -- admin_delete_test_participants: die Leitung X (Test) fällt weg, B muss folgen
    k := 0;
    for i in 1..8 loop
      insert into participants (name, name_key, team_id) values ('Probe X ' || i || ' ' || v_sfx || ' (Test)', norm('Probe X ' || i || ' ' || v_sfx || ' (Test)'), t_id)
        returning id into a_id;
      update teams set leader_participant_id = a_id where id = t_id;
      perform admin_delete_test_participants(v_pin);
      if (select leader_participant_id from teams where id = t_id) is distinct from b_id then k := k + 1; end if;
    end loop;
    if k > 0 then v_fehl := v_fehl || ('3C admin_delete_test_participants: in ' || k || ' von 8 Runden folgt jemand ohne Schlüssel'); end if;
    -- team_set_leader: an jemanden ohne Schlüssel abgelehnt, an B angenommen
    begin perform team_set_leader(v_code, 'Probe Ohne 1 ' || v_sfx); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is distinct from 'Diese Person hat sich nicht selbst angemeldet und kann nicht eingeben.' then
      v_fehl := v_fehl || ('3D team_set_leader ohne Schlüssel: ' || coalesce(v_err, 'angenommen')); end if;
    update teams set leader_participant_id = c_id where id = t_id;
    begin perform team_set_leader(v_code, 'probe b ' || lower(v_sfx)); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is not null or (select leader_participant_id from teams where id = t_id) is distinct from b_id then
      v_fehl := v_fehl || ('3E team_set_leader an B: ' || coalesce(v_err, 'nicht übernommen')); end if;
    begin perform team_set_leader(v_code, 'Niemand ' || v_sfx); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is distinct from 'Diese Person ist nicht in eurem Team.' then v_fehl := v_fehl || ('3F team_set_leader fremd: ' || coalesce(v_err, 'angenommen')); end if;
    -- admin_set_leader: die Spielleitung darf jeden (Notweg)
    begin perform admin_set_leader(v_pin, t_id, c_id); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is not null or (select leader_participant_id from teams where id = t_id) is distinct from c_id then
      v_fehl := v_fehl || ('3G admin_set_leader ohne Schlüssel: ' || coalesce(v_err, 'nicht übernommen')); end if;
    delete from participants where team_id = t_id;
    delete from teams where id = t_id;
    v_n := v_n + 5;
  exception when others then v_fehl := v_fehl || ('3 Leitung brach ab: ' || sqlerrm);
  end;

  -- ---------- 6: gleicher Name ----------
  begin
    update game_state set status = 'registration' where id = 1;
    v_tok := md5(random()::text) || md5(random()::text);
    r := register_participant('Probe Doppelt ' || v_sfx, v_tok);
    begin perform register_participant('probe  doppelt ' || lower(v_sfx), md5(random()::text) || md5(random()::text)); v_err := null;
    exception when others then v_err := sqlerrm; end;
    if v_err is distinct from v_neu then v_fehl := v_fehl || ('6A gleicher Name: ' || coalesce(v_err, 'angenommen')); end if;
    -- die zweite Stelle (gleichzeitige Anmeldung, unique_violation) lässt sich in einer Sitzung nicht auslösen: Quelltext
    f := (select prosrc from pg_proc where oid = to_regprocedure('register_participant(text,text)'));
    if (length(f) - length(replace(f, v_neu, ''))) / length(v_neu) <> 2 or position('Dieser Name ist schon angemeldet' in f) > 0 then
      v_fehl := v_fehl || '6B register_participant: neue Meldung nicht an beiden Stellen'::text; end if;
    v_n := v_n + 2;
  exception when others then v_fehl := v_fehl || ('6 brach ab: ' || sqlerrm);
  end;

  -- ---------- 5: Obergrenze 200 ----------
  begin
    update game_state set status = 'registration' where id = 1;
    k := 199 - (select count(*) from participants);
    if k < 0 then raise exception 'schon % Personen angemeldet, Grenze nicht prüfbar', 199 - k; end if;
    insert into participants (name, name_key)
      select 'Probe Voll ' || g || ' ' || v_sfx, norm('Probe Voll ' || g || ' ' || v_sfx) from generate_series(1, k) g;
    v_tok := md5(random()::text) || md5(random()::text);
    begin r := register_participant('Probe Zweihundert ' || v_sfx, v_tok); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is not null or (select count(*) from participants) <> 200 then v_fehl := v_fehl || ('5A 200. Anmeldung: ' || coalesce(v_err, 'Zahl stimmt nicht')); end if;
    begin perform register_participant('Probe Zweihunderteins ' || v_sfx, md5(random()::text) || md5(random()::text)); v_err := null;
    exception when others then v_err := sqlerrm; end;
    if v_err is distinct from 'Die Anmeldung ist voll. Melde dich bei der Spielleitung.' then
      v_fehl := v_fehl || ('5B 201. Anmeldung: ' || coalesce(v_err, 'angenommen')); end if;
    begin r := register_participant('Probe Zweihundert ' || v_sfx, v_tok); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is not null or r->>'token' is distinct from v_tok then v_fehl := v_fehl || ('5C Wiederholung bei voller Liste: ' || coalesce(v_err, r::text)); end if;
    update game_state set status = 'drawn' where id = 1;
    begin perform register_participant('Probe Spaet ' || v_sfx, null); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is null or v_err not like 'Die Anmeldung ist geschlossen.%' then v_fehl := v_fehl || ('5D nach dem Auslosen: ' || coalesce(v_err, 'angenommen')); end if;
    v_n := v_n + 4;
  exception when others then v_fehl := v_fehl || ('5 brach ab: ' || sqlerrm);
  end;

  -- ---------- 7: Rechte und Signaturen ----------
  select string_agg(p.oid::regprocedure::text || ' ' || coalesce((select array_agg(a::text order by a::text) from unnest(p.proacl) a)::text, '-')
           || ' ' || p.prosecdef::text || ' ' || coalesce(array_to_string(p.proconfig, ','), '-'), ' | ' order by p.oid::regprocedure::text)
    into v_rechte_nachher from pg_proc p where p.oid in (select to_regprocedure(x) from unnest(array[__FUNKTIONEN__]) x);
  if v_rechte_nachher is distinct from v_rechte_vorher then
    v_fehl := v_fehl || ('7A Rechte geändert: vorher ' || coalesce(v_rechte_vorher, '-') || ' nachher ' || coalesce(v_rechte_nachher, '-')); end if;
  v_n := v_n + 1;
  foreach f in array array[__FUNKTIONEN__] loop
    if to_regprocedure(f) is null then v_fehl := v_fehl || ('7B Signatur fehlt: ' || f);
    elsif (select count(*) from pg_proc where pronamespace = 'public'::regnamespace and proname = split_part(f, '(', 1)) <> 1 then
      v_fehl := v_fehl || ('7B mehr als eine Fassung: ' || f);
    end if;
    foreach rr in array array['anon', 'authenticated'] loop
      if to_regprocedure(f) is not null and not has_function_privilege(rr, f, 'execute') then v_fehl := v_fehl || ('7C ' || rr || ' darf ' || f || ' nicht'); end if;
    end loop;
    v_n := v_n + 3;
  end loop;
  foreach f in array array[__INTERN__] loop
    foreach rr in array array['anon', 'authenticated'] loop
      if has_function_privilege(rr, f, 'execute') then v_fehl := v_fehl || ('7D ' || rr || ' darf ' || f); end if;
      v_n := v_n + 1;
    end loop;
  end loop;

  if cardinality(v_fehl) > 0 then
    raise exception 'PROBE FEHLT (% von % Prüfungen): %', cardinality(v_fehl), v_n, array_to_string(v_fehl, ' | ');
  end if;
  raise exception 'PROBELAUF_OK: % Prüfungen bestanden, alles zurückgenommen', v_n;
end $probe$;
"""


def main() -> None:
    migration = "" if "--ohne" in sys.argv else MIGRATION.read_text(encoding="utf-8")
    assert "$mig$" not in migration and "$probe$" not in migration
    liste = lambda xs: ", ".join("'" + x + "'" for x in xs)  # noqa: E731
    probe = (PROBE.replace("__INTERN__", liste(INTERN)).replace("__FUNKTIONEN__", liste(FUNKTIONEN))
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
        sys.exit(m.group(0).replace(" | ", "\n  ") if m else "Der Probelauf ist abgebrochen:\n" + text)
    sys.exit("Der Probelauf lief ohne den erwarteten Abbruch durch. Bitte prüfen, ob etwas stehen geblieben ist.")


if __name__ == "__main__":
    main()
