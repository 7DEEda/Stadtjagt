#!/usr/bin/env python3
"""
Probelauf für die Migration 20261107090000_bugjagd3.sql (Bugjagd 03.11.2026, Funde 3 und 7, norm mit NFC) gegen die
echte Datenbank, ohne Spuren. Spielt vorher W5 ein (20261103090000_w5_eingaben_schluessel.sql), auf der sie aufsetzt.

    python tools/pruefstand/bugjagd3_db.py          mit Migration (grün)
    python tools/pruefstand/bugjagd3_db.py --ohne   Stand der Datenbank ohne Migration (rot)

Wie rollen_akku_db.py: EIN DO-Block spielt die Migration ein, legt erfundene Teams an, setzt das Spiel im Block auf
drawn bzw. running, prüft und wirft am Ende absichtlich einen Fehler (Marker PROBELAUF_OK oder PROBE FEHLT). Der
Server rollt alles zurück, auch die Migration. Während des Laufs (etwa eine Sekunde) ist die Zeile game_state
gesperrt; nicht während eines laufenden Spiels starten.

Die Kopfzeilen von PostgREST (request.headers) setzt der Lauf mit set_config von Hand. Nicht prüfbar ist hier, dass
PostgREST bei response.status 400 und normalem Ende festschreibt (laut Doku: jede Transaktion ohne Fehler endet
mit COMMIT); das zeigt erst ein Aufruf über die API nach dem Einspielen.

Geprüft:
   A1  Hilfsfunktionen und Tabelle für anon/authenticated gesperrt, Spielfunktionen weiter offen
   A2  richtiger Code: team_state wie bisher, nichts gezählt, response.status nicht gesetzt
   A3  falscher Code: Antwort mit message "Unbekannter Team-Code.", response.status 400, keine Ausnahme, gezählt
   A4  Quelle: cf-connecting-ip vor x-forwarded-for (erster Eintrag), ohne Kopfzeilen 'ohne'
   A5  leerer Code zählt nicht
   A6  30 Fehlversuche: danach auch der richtige Code gesperrt (Text mit Minuten), andere Quelle nicht betroffen
   A7  nach 10 Minuten wieder offen, der nächste Fehlversuch beginnt bei 1; alte Zeilen (über 1 h) verschwinden
   A8  alle zehn Spielfunktionen mit Team-Code antworten bei falschem Code ohne Ausnahme und zählen
   B1  admin_start warnt bei Gruppenselfie an und Löschdatum heute (Prager Zeit), startet trotzdem
   B2  admin_start ohne diese Warnung bei Löschdatum morgen oder Selfie aus
   B3  team_selfie lehnt bei erreichtem Löschdatum ab und legt kein Foto an
   B4  team_selfie mit Löschdatum morgen speichert das Foto weiter
   C1  norm: zerlegte und vorkomponierte Umlaute ergeben denselben Schlüssel (bruecke, strasse, Čech), ASCII unverändert
   C2  answer_ok mit zerlegter Antwort; Anmeldung mit zerlegtem Namen findet die Dublette
   C3  nach der Migration hat jede Person name_key = norm(name), außer Konflikten (Zahl steht in der OK-Zeile)
   W5  ohne Schlüssel und PIN weiter abgewiesen, mit PIN und mit Schlüssel der Leitung offen; team_eingabe gesperrt
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sql  # noqa: E402
from rechte_db import INTERN  # noqa: E402

W5 = sql.REPO / "supabase" / "migrations" / "20261103090000_w5_eingaben_schluessel.sql"
MIGRATION = sql.REPO / "supabase" / "migrations" / "20261107090000_bugjagd3.sql"
NEU_INTERN = ["team_code_quelle()", "team_code_bremse(text)", "team_code_abgelehnt(text)", "team_eingabe(text,text,text)"]
SPIEL = ["team_state(text)", "check_in(text,double precision,double precision,double precision,text,text)",
         "reveal_tip(text,text,text)", "submit_answer(text,text,integer,text,text)",
         "submit_final(text,text,double precision,double precision,double precision,text,text)",
         "team_selfie_skip(text,integer,text,text)", "team_set_leader(text,text,text,text)",
         "team_selfie(text,integer,text,text,text,text)", "team_photo(text,text,text,integer,boolean)",
         "report_position(text,double precision,double precision,double precision,text,text,text)", "admin_start(text)"]


def chk(bedingung: str, text: str, ist: str = "") -> str:
    """Eine Prüfung: bei Misserfolg wird der Fund gesammelt, der Lauf geht weiter."""
    z = f" || ': ' || coalesce(({ist})::text, 'null')" if ist else ""
    return f"  if not coalesce(({bedingung}), false) then v_f := v_f || ('{text}'::text{z}); end if; v_n := v_n + 1;"


def kopf(json_text: str) -> str:
    return f"  perform set_config('request.headers', '{json_text}', true); perform set_config('response.status', '', true);"


ANZ = "(select anzahl from team_code_fehlversuche where quelle = '{q}')"


def pruefungen() -> str:
    c = []
    a = c.append
    unbek = "r->>'message' = 'Unbekannter Team-Code.' and current_setting('response.status', true) = '400'"

    a("-- A1: Rechte")
    a("  foreach f in array array[__NEU_INTERN__, __INTERN__] loop")
    a("    foreach rr in array array['anon', 'authenticated'] loop")
    a("      if has_function_privilege(rr, f, 'execute') then v_f := v_f || ('A1 ' || rr || ' darf ' || f || ' ausführen'); end if; v_n := v_n + 1;")
    a("    end loop;")
    a("  end loop;")
    a("  foreach f in array array[__NEU_INTERN__] loop")
    a("    if not (select prosecdef from pg_proc where oid = f::regprocedure) then v_f := v_f || ('A1 nicht SECURITY DEFINER: ' || f); end if; v_n := v_n + 1;")
    a("  end loop;")
    a("  foreach f in array array[__SPIEL__] loop")
    a("    if not has_function_privilege('anon', f, 'execute') then v_f := v_f || ('A1 anon darf ' || f || ' nicht ausführen'); end if; v_n := v_n + 1;")
    a("    if not coalesce((select 'search_path=public' = any (proconfig) from pg_proc where oid = f::regprocedure), false) then "
      "v_f := v_f || ('A1 search_path fehlt: ' || f); end if; v_n := v_n + 1;")
    a("  end loop;")
    a("  foreach rr in array array['anon', 'authenticated'] loop")
    a("    if has_table_privilege(rr, 'public.team_code_fehlversuche', 'select') or has_table_privilege(rr, 'public.team_code_fehlversuche', 'insert') "
      "then v_f := v_f || ('A1 ' || rr || ' darf team_code_fehlversuche lesen oder schreiben'); end if; v_n := v_n + 1;")
    a("  end loop;")
    a("  delete from team_code_fehlversuche where true;")

    a("-- A2: richtiger Code")
    a(kopf('{"cf-connecting-ip":"203.0.113.7"}'))
    a("  r := team_state(v_code);")
    a(chk("r->'team'->>'id' = v_id::text and r->>'message' is null", "A2 team_state mit richtigem Code", "left(r::text, 200)"))
    a(chk("coalesce(current_setting('response.status', true), '') = ''", "A2 response.status gesetzt", "current_setting('response.status', true)"))
    a(chk("not exists (select 1 from team_code_fehlversuche)", "A2 richtiger Code gezählt"))
    a("  r := team_state(lower(replace(v_code, '-', ' ')));")
    a(chk("r->'team'->>'id' = v_id::text", "A2 Code klein und mit Leerzeichen"))

    a("-- A3: falscher Code")
    a("  begin r := team_state('PROBE-FALSCH1'); exception when others then r := null; v_f := v_f || ('A3 Ausnahme statt Antwort: ' || sqlerrm); end;")
    a(chk(unbek, "A3 Antwort und Status bei falschem Code", "r::text || ' / ' || current_setting('response.status', true)"))
    a(chk(f"{ANZ.format(q='203.0.113.7')} = 1", "A3 Fehlversuch gezählt", ANZ.format(q='203.0.113.7')))

    a("-- A4: Quelle")
    a(kopf('{"x-forwarded-for":"198.51.100.1, 10.0.0.1","cf-connecting-ip":"203.0.113.8"}'))
    a(chk("team_code_quelle() = '203.0.113.8'", "A4 cf-connecting-ip zuerst", "team_code_quelle()"))
    a(kopf('{"x-forwarded-for":"198.51.100.1, 10.0.0.1"}'))
    a(chk("team_code_quelle() = '198.51.100.1'", "A4 erster Eintrag von x-forwarded-for", "team_code_quelle()"))
    a("  perform set_config('request.headers', '', true);")
    a(chk("team_code_quelle() = 'ohne'", "A4 ohne Kopfzeilen", "team_code_quelle()"))
    a("  perform set_config('request.headers', 'kein json', true);")
    a(chk("team_code_quelle() = 'ohne'", "A4 kaputte Kopfzeilen", "team_code_quelle()"))

    a("-- A5: leerer Code")
    a(kopf('{"cf-connecting-ip":"203.0.113.9"}'))
    a("  r := team_state(''); r2 := team_state(null);")
    a(chk(unbek + " and r2->>'message' = 'Unbekannter Team-Code.'", "A5 leerer Code: Meldung", "r::text"))
    a(chk(f"{ANZ.format(q='203.0.113.9')} is null", "A5 leerer Code gezählt"))

    a("-- A6: Sperre nach 30 Fehlversuchen")
    a(kopf('{"cf-connecting-ip":"203.0.113.7"}'))
    a("  for i in 2..29 loop perform team_state('PROBE-FALSCH' || i); end loop;")
    a("  r := team_state(v_code);")
    a(chk("r->'team'->>'id' = v_id::text", "A6 nach 29 Fehlversuchen noch offen", "left(r::text, 200)"))
    a("  perform team_state('PROBE-FALSCH30');")
    a(chk(f"{ANZ.format(q='203.0.113.7')} = 30", "A6 30 gezählt", ANZ.format(q='203.0.113.7')))
    a("  perform set_config('response.status', '', true); r := team_state(v_code);")
    a(chk("r->>'message' like 'Zu viele falsche Team-Codes aus diesem Netz. Bitte in 10 Minuten%' and current_setting('response.status', true) = '400' "
          "and r->'team' is null", "A6 richtiger Code während der Sperre", "r::text"))
    a("  r := submit_answer(v_code, 'x', 1, null, v_pin);")
    a(chk("r->>'message' like 'Zu viele falsche Team-Codes%'", "A6 submit_answer gesperrt", "r::text"))
    a("  update team_code_fehlversuche set seit = now() - interval '9 minutes 30 seconds' where quelle = '203.0.113.7';")
    a("  r := team_state(v_code);")
    a(chk("r->>'message' like '%Bitte in einer Minute noch einmal%'", "A6 Restzeit mindestens 1 Minute", "r::text"))
    a(kopf('{"cf-connecting-ip":"203.0.113.50"}'))
    a("  r := team_state(v_code);")
    a(chk("r->'team'->>'id' = v_id::text", "A6 andere Quelle gesperrt"))

    a("-- A7: Fenster vorbei")
    a(kopf('{"cf-connecting-ip":"203.0.113.7"}'))
    a("  update team_code_fehlversuche set seit = now() - interval '10 minutes 1 second' where quelle = '203.0.113.7';")
    a("  r := team_state(v_code);")
    a(chk("r->'team'->>'id' = v_id::text", "A7 nach 10 Minuten wieder offen", "left(r::text, 200)"))
    a("  perform team_state('PROBE-FALSCH31');")
    a(chk(f"{ANZ.format(q='203.0.113.7')} = 1 and (select seit from team_code_fehlversuche where quelle = '203.0.113.7') = now()",
          "A7 neues Fenster beginnt bei 1", ANZ.format(q='203.0.113.7')))
    a("  insert into team_code_fehlversuche values ('198.51.100.99', now() - interval '2 hours', 5);")
    a("  perform team_state('PROBE-FALSCH32');")
    a(chk("not exists (select 1 from team_code_fehlversuche where quelle = '198.51.100.99')", "A7 alte Zeile nicht aufgeräumt"))

    a("-- A8: alle Spielfunktionen")
    a("  update game_state set status = 'running', started_at = coalesce(started_at, now()), selfie_on = true, photos_delete_on = null where id = 1;")
    a(kopf('{"cf-connecting-ip":"203.0.113.60"}'))
    for nr, aufruf in enumerate([
            "check_in('PROBE-FALSCH', 50.1, 14.4, 5)", "reveal_tip('PROBE-FALSCH')", "submit_answer('PROBE-FALSCH', 'x', 1)",
            "submit_final('PROBE-FALSCH', '123', 50.1, 14.4, 5)", "team_selfie_skip('PROBE-FALSCH', 1)",
            "team_set_leader('PROBE-FALSCH', 'Niemand')", "team_selfie('PROBE-FALSCH', 1, 'x', 'x')",
            "team_photo('PROBE-FALSCH', null, null, 1, false)"], start=1):
        fn = aufruf.split("(")[0]
        a(f"  perform set_config('response.status', '', true);")
        a(f"  begin r := {aufruf}; exception when others then r := null; v_f := v_f || ('A8 {fn} wirft: ' || sqlerrm); end;")
        a(chk(unbek, f"A8 {fn} antwortet mit Meldung und Status", "r::text"))
    a("  perform set_config('response.status', '', true);")
    a("  begin perform report_position('PROBE-FALSCH', 50.1, 14.4, 5, 'ok'); exception when others then v_f := v_f || ('A8 report_position wirft: ' || sqlerrm); end;")
    a(chk("current_setting('response.status', true) = '400'", "A8 report_position setzt Status 400"))
    a(chk(f"{ANZ.format(q='203.0.113.60')} = 9", "A8 neun Fehlversuche gezählt", ANZ.format(q='203.0.113.60')))
    a("  perform report_position(v_code, 50.1, 14.4, 5, 'ok', null, v_pin);")
    a(chk("exists (select 1 from team_positions where team_id = v_id)", "A8 report_position mit richtigem Code"))

    a("-- B1/B2: admin_start")
    a("  perform set_config('request.headers', '', true);")
    a("  v_pin := (select admin_pin from game_state where id = 1);")
    a("  update game_state set status = 'drawn', test_mode = false, selfie_on = true, photos_delete_on = (now() at time zone 'Europe/Prague')::date where id = 1;")
    a("  r := admin_start(v_pin);")
    a(chk("r->>'warning' like '%Löschdatum der Gruppenfotos (' || to_char((now() at time zone 'Europe/Prague')::date, 'DD.MM.YYYY') || ') ist erreicht%' "
          "and (select status from game_state where id = 1) = 'running'", "B1 Warnung bei Löschdatum heute, Spiel läuft", "r->>'warning'"))
    a("  update game_state set status = 'drawn', photos_delete_on = (now() at time zone 'Europe/Prague')::date - 3 where id = 1;")
    a("  r := admin_start(v_pin);")
    a(chk("r->>'warning' like '%Löschdatum der Gruppenfotos%'", "B1 Warnung bei Löschdatum vorgestern", "r->>'warning'"))
    a("  update game_state set status = 'drawn', photos_delete_on = (now() at time zone 'Europe/Prague')::date + 1 where id = 1;")
    a("  r := admin_start(v_pin);")
    a(chk("coalesce(r->>'warning', '') not like '%Löschdatum%'", "B2 keine Warnung bei Löschdatum morgen", "r->>'warning'"))
    a("  update game_state set status = 'drawn', selfie_on = false, photos_delete_on = (now() at time zone 'Europe/Prague')::date - 1 where id = 1;")
    a("  r := admin_start(v_pin);")
    a(chk("coalesce(r->>'warning', '') not like '%Löschdatum%'", "B2 keine Warnung bei Selfie aus", "r->>'warning'"))

    a("-- B3/B4: team_selfie")
    a("  select id into v_st from stations where position = 1;")
    a("  delete from progress where team_id = v_id;")
    a("  insert into progress (team_id, station_id, checked_in_at, solved_at) values (v_id, v_st, now(), now());")
    a("  update game_state set status = 'running', selfie_on = true, photos_delete_on = (now() at time zone 'Europe/Prague')::date where id = 1;")
    a("  begin perform team_selfie(v_code, 1, v_jpg, v_jpg, null, v_pin); v_f := v_f || 'B3 Foto trotz erreichtem Löschdatum angenommen'::text; "
      "exception when others then if sqlerrm not like 'Das Löschdatum der Fotos ist erreicht%' then v_f := v_f || ('B3 falscher Text: ' || sqlerrm); end if; end;")
    a("  v_n := v_n + 1;")
    a(chk("not exists (select 1 from station_photos where team_id = v_id)", "B3 Foto angelegt"))
    a("  update game_state set photos_delete_on = (now() at time zone 'Europe/Prague')::date + 1 where id = 1;")
    a("  r := team_selfie(v_code, 1, v_jpg, v_jpg, null, v_pin);")
    a(chk("exists (select 1 from station_photos where team_id = v_id) and r->'team'->>'id' = v_id::text", "B4 Foto mit Löschdatum morgen", "left(r::text, 200)"))
    a("  update game_state set photos_delete_on = null where id = 1;")
    a("  delete from station_photos where team_id = v_id;")
    a("  r := team_selfie(v_code, 1, v_jpg, v_jpg, null, v_pin);")
    a(chk("exists (select 1 from station_photos where team_id = v_id)", "B4 Foto ohne Löschdatum"))

    a("-- W5 bleibt: ohne Schlüssel und PIN abgewiesen, mit PIN oder Schlüssel der Leitung offen")
    a("  perform set_config('request.headers', '{\"cf-connecting-ip\":\"203.0.113.70\"}', true);")
    a("  begin perform reveal_tip(v_code); v_f := v_f || 'W5 Eingabe ohne Schlüssel und PIN angenommen'::text; "
      "exception when others then if sqlerrm <> 'Eingeben kann nur die Teamleitung auf ihrem eigenen Handy.' then v_f := v_f || ('W5 falscher Text: ' || sqlerrm); end if; end;")
    a("  v_n := v_n + 1;")
    a(chk(f"{ANZ.format(q='203.0.113.70')} is null", "W5 richtiger Code ohne Schlüssel als Fehlversuch gezählt"))
    a("  begin perform reveal_tip(v_code, null, 'falsch-' || md5(random()::text)); v_f := v_f || 'W5 falsche PIN angenommen'::text; "
      "exception when others then if sqlerrm <> 'Falsche PIN.' then v_f := v_f || ('W5 falscher Text bei PIN: ' || sqlerrm); end if; end;")
    a("  v_n := v_n + 1;")
    a("  insert into participants (name, name_key, team_id, token) values ('Probe Leitung Bremse', norm('Probe Leitung Bremse'), v_id, v_tok) returning id into v_pa;")
    a("  update teams set leader_participant_id = v_pa where id = v_id;")
    a("  r := team_selfie_skip(v_code, 1, v_tok);")
    a(chk("r->'team'->>'id' = v_id::text", "W5 Leitung mit Schlüssel gibt ein", "left(r::text, 200)"))
    a("  perform set_config('response.status', '', true); r := team_selfie_skip('PROBE-FALSCH', 1, v_tok);")
    a(chk(unbek, "W5 falscher Code mit Schlüssel: Meldung und Status", "r::text"))

    a("-- C: norm mit NFC")
    a("  v_nfd := 'Br' || chr(117) || chr(776) || 'cke';")   # u + kombinierendes Trema
    a(chk("v_nfd <> 'Brücke' and norm(v_nfd) = 'bruecke' and norm('Brücke') = 'bruecke'", "C1 Brücke zerlegt und vorkomponiert", "norm(v_nfd)"))
    a(chk("norm('Stra' || chr(223) || 'e') = 'strasse' and norm('C' || chr(780) || 'ech') = 'cech' and norm('Čech') = 'cech'", "C1 ß und Č", "norm('C' || chr(780) || 'ech')"))
    a(chk("norm('Jürgen-Müller 3') = 'juergenmueller3' and norm('ABC def') = 'abcdef' and norm(null) = ''", "C1 bisherige Werte unverändert"))
    a(chk("norm('O' || chr(776) || 'zil') = norm('Özil')", "C1 Großbuchstabe zerlegt", "norm('O' || chr(776) || 'zil')"))
    a(chk("answer_ok(v_nfd, 'Brücke') and answer_ok('Brücke', v_nfd)", "C2 answer_ok mit zerlegter Antwort"))
    a("  insert into participants (name, name_key) values ('Jürgen Probelauf', norm('Jürgen Probelauf'));")
    a(chk("exists (select 1 from participants where name_key = norm('J' || chr(117) || chr(776) || 'rgen Probelauf'))",
          "C2 zerlegter Name trifft die Dublette"))
    a(chk("(select count(*) from participants where name_key is distinct from norm(name)) = v_konflikt",
          "C3 Schlüssel nachgezogen", "(select count(*) from participants where name_key is distinct from norm(name))"))
    return "\n".join(c)


PROBE = r"""
do $probe$
declare v_n int := 0; v_f text[] := '{}'; r json; r2 json; f text; rr text; i int; v_pin text; v_st uuid; v_id uuid;
        v_pa uuid; v_tok text := 'probe-' || md5(random()::text); v_nfd text; v_neu int; v_konflikt int;
        v_code text := 'PROBE-' || upper(substr(md5(random()::text), 1, 8));
        v_jpg text := encode('\xffd8ffe000104a464946'::bytea, 'base64');
begin
  __W5__
  -- Teil C: wie viele Schlüssel ändern sich, wie viele kollidieren (vor der Migration, mit der neuen Rechnung)
  select count(*) filter (where name_key is distinct from normalize_probe), count(*) filter (where name_key is distinct from normalize_probe
           and exists (select 1 from participants q where q.id <> x.id and q.name_key = x.normalize_probe))
    into v_neu, v_konflikt
    from (select p.id, p.name_key, regexp_replace(translate(replace(replace(replace(replace(lower(translate(normalize(coalesce(p.name,''), NFC),
          'ÄÖÜÀÁÂÃÅĀĂĄÇĆČĎĐÈÉÊËĒĖĘĚÌÍÎÏĪĮĹĽŁÑŃŇÒÓÔÕØŌŐŔŘŚŠŞȘŤŢȚÙÚÛŮŪŰŲÝŸŹŻŽ',
          'äöüàáâãåāăąçćčďđèéêëēėęěìíîïīįĺľłñńňòóôõøōőŕřśšşșťţțùúûůūűųýÿźżž')),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss'),
          'àáâãåāăąçćčďđèéêëēėęěìíîïīįıĺľłñńňòóôõøōőŕřśšşșťţțùúûůūűųýÿźżž',
          'aaaaaaaacccddeeeeeeeeiiiiiiilllnnnooooooorrsssstttuuuuuuuyyzzz'), '[^a-z0-9]+', '', 'g') as normalize_probe
          from participants p) x;
  __MIGRATION__
  insert into teams (name, code, read_token) values ('Probelauf Bremse', v_code, md5(random()::text)) returning id into v_id;
  v_pin := (select admin_pin from game_state where id = 1);
__PRUEFUNGEN__
  if array_length(v_f, 1) > 0 then
    raise exception 'PROBE FEHLT (% von % Prüfungen): %', array_length(v_f, 1), v_n, array_to_string(v_f, ' | ');
  end if;
  raise exception 'PROBELAUF_OK: % Prüfungen bestanden, alles zurückgenommen (Teil C: % Schlüssel neu, % Konflikte)', v_n, v_neu, v_konflikt;
end $probe$;
"""


def liste(xs):
    return ", ".join("'" + x + "'" for x in xs)


def main() -> None:
    w5 = W5.read_text(encoding="utf-8")
    migration = "" if "--ohne" in sys.argv else MIGRATION.read_text(encoding="utf-8")
    assert "$mig$" not in migration + w5 and "$probe$" not in migration + w5
    probe = (PROBE.replace("__PRUEFUNGEN__", pruefungen()).replace("__INTERN__", liste(INTERN))
             .replace("__NEU_INTERN__", liste(NEU_INTERN)).replace("__SPIEL__", liste(SPIEL))
             .replace("__W5__", f"execute $mig${w5}$mig$;")
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
