#!/usr/bin/env python3
"""
Probelauf für die Migration 20261103090000_w5_eingaben_schluessel.sql (W5: Eingaben nur von der Teamleitung auf ihrem
Handy oder mit Admin-PIN) gegen die echte Datenbank, ohne Spuren.

    python tools/pruefstand/w5_eingaben_db.py          mit Migration (grün)
    python tools/pruefstand/w5_eingaben_db.py --ohne   Gegentest ohne Migration (rot)

Mit --ohne läuft nur Prüfung 1, mit den alten Signaturen (Team-Code allein), gegen den heutigen Stand der Datenbank:
dort nimmt jede der acht Eingaben den Code allein an, also meldet der Lauf PROBE FEHLT mit "angenommen". Die übrigen
Prüfungen brauchen die neuen Signaturen und brächen ohne Migration mit 42883 (Funktion fehlt) ab.

Wie rollen_akku_db.py: EIN DO-Block spielt die Migration ein, legt erfundene Teams und Personen an, setzt das Spiel im
Block auf running (Testmodus an, damit der Check-in ohne GPS geht), prüft und wirft am Ende absichtlich einen Fehler
(Marker PROBELAUF_OK oder PROBE FEHLT). Der Server rollt alles zurück, auch die Migration. Die Admin-PIN liest der
Block selbst aus game_state, sie verlässt die Datenbank nicht. Während des Laufs ist die Zeile game_state gesperrt;
nicht während eines laufenden Spiels starten.

Geprüft:
   1  ohne Schlüssel und PIN (der alte Aufruf mit Team-Code allein) lehnt jede der acht Eingaben ab, mit dem Text
   2  Schlüssel der Teamleitung: alle acht Eingaben gehen durch (team_selfie und team_selfie_skip scheitern danach
      an ihren eigenen Regeln, nicht an W5); report_position schreibt die Position
   3  Schlüssel eines Mitglieds, ein unbekannter, ein leerer und der Schlüssel der Leitung eines anderen Teams: abgelehnt
   4  Admin-PIN (Notweg): geht; falsche PIN: "Falsche PIN."; PIN nur aus Leerzeichen: abgelehnt
   5  falscher Team-Code bleibt "Unbekannter Team-Code.", auch mit gültigem Schlüssel
   6  team_set_leader mit Schlüssel: danach gilt nur noch der Schlüssel der neuen Leitung
   7  Leitung ohne eigenes Handy (von der Spielleitung gesetzt): nur mit PIN
   8  benannte Aufrufe wie die App (p_token, p_pin als null) gehen
   9  je Funktion genau eine Fassung mit p_token und p_pin; Rechte, SECURITY DEFINER, search_path; team_eingabe intern
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sql  # noqa: E402
from rechte_db import INTERN  # noqa: E402

MIGRATION = sql.REPO / "supabase" / "migrations" / "20261103090000_w5_eingaben_schluessel.sql"
NEU = ["check_in(text,double precision,double precision,double precision,text,text)",
       "submit_answer(text,text,integer,text,text)", "reveal_tip(text,text,text)",
       "submit_final(text,text,double precision,double precision,double precision,text,text)",
       "team_selfie(text,integer,text,text,text,text)", "team_selfie_skip(text,integer,text,text)",
       "team_set_leader(text,text,text,text)",
       "report_position(text,double precision,double precision,double precision,text,text,text)"]
W5 = "Eingeben kann nur die Teamleitung auf ihrem eigenen Handy. Wenn du die Leitung bist: App neu laden."


def chk(bedingung: str, text: str, ist: str = "") -> str:
    """Eine Prüfung: bei Misserfolg wird der Fund gesammelt, der Lauf geht weiter."""
    z = f" || ': ' || coalesce(({ist})::text, 'null')" if ist else ""
    return f"  if not coalesce(({bedingung}), false) then v_f := v_f || ('{text}'::text{z}); end if; v_n := v_n + 1;"


def abgelehnt(aufruf: str, kennung: str, meldung: str = W5) -> str:
    """Der Aufruf muss mit genau dieser Meldung scheitern."""
    return (f"  begin perform {aufruf}; v_f := v_f || '{kennung} angenommen'::text; "
            f"exception when others then if sqlerrm <> '{meldung}' then v_f := v_f || ('{kennung} falscher Text: ' || sqlerrm); end if; end; "
            "v_n := v_n + 1;")


def nicht_w5(aufruf: str, kennung: str) -> str:
    """Der Aufruf darf scheitern, aber nicht an W5 (für Eingaben, die danach an eigenen Regeln scheitern)."""
    return (f"  begin perform {aufruf}; exception when others then if sqlerrm = '{W5}' or sqlerrm like 'Falsche PIN%' "
            f"or sqlerrm like '%function%does not exist%' then v_f := v_f || ('{kennung}: ' || sqlerrm); end if; end; v_n := v_n + 1;")


def alle(tok: str, pin: str) -> list:
    """Die acht Eingaben mit Team-Code v_code, positionell; tok und pin als SQL-Ausdruck."""
    return [f"check_in(v_code, null, null, null, {tok}, {pin})",
            f"submit_answer(v_code, 'probe', null, {tok}, {pin})",
            f"reveal_tip(v_code, {tok}, {pin})",
            f"submit_final(v_code, '000000', null, null, null, {tok}, {pin})",
            f"team_selfie(v_code, 999, '', '', {tok}, {pin})",
            f"team_selfie_skip(v_code, 999, {tok}, {pin})",
            f"team_set_leader(v_code, v_na, {tok}, {pin})",
            f"report_position(v_code, 50.1, 14.4, 10, null, {tok}, {pin})"]


def pruefungen(ohne: bool = False) -> str:
    c = []
    a = c.append

    a("-- 1: Team-Code allein")
    alt = ["check_in(v_code, null, null, null)", "submit_answer(v_code, 'probe', null)", "reveal_tip(v_code)",
           "submit_final(v_code, '000000')", "team_selfie(v_code, 999, '', '')", "team_selfie_skip(v_code, 999)",
           "team_set_leader(v_code, v_na)", "report_position(v_code, 50.1, 14.4, 10, null)"]
    for i, x in enumerate(alt):
        a(abgelehnt(x, f"1{chr(65 + i)} nur Code: {x.split('(')[0]}"))
    a(chk("not exists (select 1 from team_positions where team_id = v_id)", "1I ohne Recht keine Position geschrieben"))
    if ohne:        # Gegentest: nur die alten Aufrufe, die es ohne Migration gibt
        return "\n".join(x for x in c if x)

    a("-- 2: Schlüssel der Teamleitung")
    for i, x in enumerate(alle("v_ta", "null")):
        a(nicht_w5(x, f"2{chr(65 + i)} Leitung: {x.split('(')[0]}"))
    a(chk("exists (select 1 from team_positions where team_id = v_id and lat = 50.1)", "2I Position der Leitung geschrieben"))
    a(chk("(select checked_in_at from progress pr where pr.team_id = v_id order by checked_in_at limit 1) is not null",
          "2J Check-in der Leitung angekommen"))

    a("-- 3: falsche Schlüssel")
    for tok, k in (("v_tb", "3A Mitglied"), ("'gibt-es-nicht'", "3B unbekannt"), ("''", "3C leer"), ("v_t2", "3D Leitung anderes Team")):
        for i, x in enumerate(alle(tok, "null")):
            a(abgelehnt(x, f"{k} {i + 1} {x.split('(')[0]}"))

    a("-- 4: Admin-PIN")
    for i, x in enumerate(alle("null", "v_pin")):
        a(nicht_w5(x, f"4{chr(65 + i)} PIN: {x.split('(')[0]}"))
    a(abgelehnt("check_in(v_code, null, null, null, null, 'falsch-' || md5(random()::text))", "4I falsche PIN", "Falsche PIN."))
    a(abgelehnt("check_in(v_code, null, null, null, v_tb, 'falsch-' || md5(random()::text))", "4J Mitglied mit falscher PIN", "Falsche PIN."))
    a(abgelehnt("check_in(v_code, null, null, null, null, '   ')", "4K PIN nur Leerzeichen"))
    a(nicht_w5("check_in(v_code, null, null, null, v_ta, 'falsch-x')", "4L Leitung mit falscher PIN: Schlüssel zählt zuerst"))

    a("-- 5: falscher Code")
    a(abgelehnt("check_in('GIBT-ES-NICHT-99', null, null, null, v_ta, null)", "5A falscher Code", "Unbekannter Team-Code."))
    a(abgelehnt("check_in(v_code2, null, null, null, v_ta, null)", "5B Schlüssel der Leitung mit fremdem Code"))

    a("-- 6: team_set_leader")
    a("  update teams set leader_participant_id = v_a where id = v_id;")
    a("  perform team_set_leader(v_code, v_nb, v_ta, null);")
    a(chk("(select leader_participant_id from teams where id = v_id) = v_b", "6A Leitung an Ben übergeben"))
    a(abgelehnt("reveal_tip(v_code, v_ta, null)", "6B alte Leitung danach abgelehnt"))
    a(nicht_w5("reveal_tip(v_code, v_tb, null)", "6C neue Leitung danach angenommen"))

    a("-- 7: Leitung ohne Handy")
    a("  update teams set leader_participant_id = v_c where id = v_id;")
    a(abgelehnt("reveal_tip(v_code, null, null)", "7A Leitung ohne Handy, ohne PIN"))
    a(abgelehnt("reveal_tip(v_code, v_ta, null)", "7B Schlüssel einer früheren Leitung"))
    a(nicht_w5("reveal_tip(v_code, null, v_pin)", "7C Leitung ohne Handy mit PIN"))
    a("  update teams set leader_participant_id = null where id = v_id;")
    a(abgelehnt("reveal_tip(v_code, v_ta, null)", "7D Team ohne Leitung"))
    a("  update teams set leader_participant_id = v_a where id = v_id;")

    a("-- 8: benannte Aufrufe wie die App")
    a("  r := check_in(p_code => v_code, p_lat => null, p_lng => null, p_acc => null, p_token => v_ta, p_pin => null);")
    a(chk("r->>'message' is not null and r->>'message' <> 'Das Spiel läuft gerade nicht.'", "8A check_in benannt mit Schlüssel", "r->>'message'"))
    a("  r := reveal_tip(p_code => v_code, p_token => null, p_pin => v_pin);")
    a(chk("r is not null", "8B reveal_tip benannt mit PIN"))
    a(abgelehnt("submit_answer(p_code => v_code, p_answer => 'x', p_position => null, p_token => null, p_pin => null)",
                "8C submit_answer benannt ohne beides"))

    a("-- 9: Fassungen und Rechte")
    a("  foreach f in array array['check_in','submit_answer','reveal_tip','submit_final','team_selfie','team_selfie_skip',"
      "'team_set_leader','report_position'] loop")
    a("    if (select count(*) from pg_proc p where p.pronamespace = 'public'::regnamespace and p.proname = f) <> 1 then "
      "v_f := v_f || ('9A nicht genau eine Fassung: ' || f); end if; v_n := v_n + 1;")
    a("  end loop;")
    a("  foreach f in array array[__NEU__] loop")
    a("    if to_regprocedure(f) is null then v_f := v_f || ('9B fehlt: ' || f); v_n := v_n + 1; continue; end if;")
    a("    foreach rr in array array['anon', 'authenticated'] loop")
    a("      if not has_function_privilege(rr, f, 'execute') then v_f := v_f || ('9C ' || rr || ' darf ' || f || ' nicht ausführen'); end if; v_n := v_n + 1;")
    a("    end loop;")
    a("    if not (select prosecdef from pg_proc where oid = f::regprocedure) then v_f := v_f || ('9D nicht SECURITY DEFINER: ' || f); end if;")
    a("    if not coalesce((select 'search_path=public' = any (proconfig) from pg_proc where oid = f::regprocedure), false) then "
      "v_f := v_f || ('9E search_path fehlt: ' || f); end if;")
    a("    v_n := v_n + 2;")
    a("  end loop;")
    a("  foreach f in array array[__INTERN__, 'team_eingabe(text,text,text)'] loop")
    a("    if to_regprocedure(f) is null then v_f := v_f || ('9F fehlt: ' || f); v_n := v_n + 1; continue; end if;")
    a("    foreach rr in array array['anon', 'authenticated', 'public'] loop")
    a("      if has_function_privilege(rr, f, 'execute') then v_f := v_f || ('9G ' || rr || ' darf ' || f || ' ausführen'); end if; v_n := v_n + 1;")
    a("    end loop;")
    a("  end loop;")
    return "\n".join(x for x in c if x)


PROBE = r"""
do $probe$
declare v_n int := 0; v_f text[] := '{}'; r json; f text; rr text; v_pin text;
        v_code text := 'PROBE-' || substr(md5(random()::text), 1, 8); v_code2 text := 'PROBE-' || substr(md5(random()::text), 1, 8);
        v_id uuid; v_id2 uuid; v_a uuid; v_b uuid; v_c uuid; v_d uuid;
        v_na text := 'Probe Anna ' || substr(md5(random()::text), 1, 6); v_nb text := 'Probe Ben ' || substr(md5(random()::text), 1, 6);
        v_nc text := 'Probe Cleo ' || substr(md5(random()::text), 1, 6); v_nd text := 'Probe Dora ' || substr(md5(random()::text), 1, 6);
        v_ta text := 'probe-' || md5(random()::text); v_tb text := 'probe-' || md5(random()::text); v_t2 text := 'probe-' || md5(random()::text);
begin
  __MIGRATION__
  v_pin := (select admin_pin from game_state where id = 1);
  update game_state set status = 'running', test_mode = true, selfie_on = false, started_at = coalesce(started_at, now()) where id = 1;
  insert into teams (name, code, read_token) values ('Probelauf', v_code, md5(random()::text)) returning id into v_id;
  insert into teams (name, code, read_token) values ('Probelauf 2', v_code2, md5(random()::text)) returning id into v_id2;
  insert into participants (name, name_key, team_id, token) values (v_na, norm(v_na), v_id, v_ta) returning id into v_a;
  insert into participants (name, name_key, team_id, token) values (v_nb, norm(v_nb), v_id, v_tb) returning id into v_b;
  insert into participants (name, name_key, team_id) values (v_nc, norm(v_nc), v_id) returning id into v_c;
  insert into participants (name, name_key, team_id, token) values (v_nd, norm(v_nd), v_id2, v_t2) returning id into v_d;
  update teams set leader_participant_id = v_a where id = v_id;
  update teams set leader_participant_id = v_d where id = v_id2;

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
    probe = (PROBE.replace("__PRUEFUNGEN__", pruefungen("--ohne" in sys.argv)).replace("__INTERN__", liste(INTERN))
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
