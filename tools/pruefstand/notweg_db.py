#!/usr/bin/env python3
"""
Probelauf für die Migration 20261109090000_notweg_schluessel.sql (Notweg-Schlüssel, 09.11.2026, Befund S1 der
W5-Sicherheitsprüfung) gegen die echte Datenbank, ohne Spuren. Spielt vorher W5 und bugjagd3 ein, auf denen sie aufsetzt.

    python tools/pruefstand/notweg_db.py          mit Migration (grün)
    python tools/pruefstand/notweg_db.py --ohne   W5 und bugjagd3 ohne diese Migration (rot: admin_notweg fehlt)

Wie w5_eingaben_db.py: EIN DO-Block spielt die Migrationen ein, legt erfundene Teams und Personen an, setzt das Spiel im
Block auf running (Testmodus an), prüft und wirft am Ende absichtlich einen Fehler (Marker PROBELAUF_OK oder
PROBE FEHLT). Der Server rollt alles zurück. Die Admin-PIN liest der Block selbst aus game_state, sie verlässt die
Datenbank nicht. Während des Laufs ist die Zeile game_state gesperrt; nicht während eines laufenden Spiels starten.

Geprüft:
   1  admin_notweg: falsche PIN "Falsche PIN.", unbekannter Code "Unbekannter Team-Code.", beides ohne Schlüssel
   2  richtige PIN: Schlüssel "nw-…", Zeile mit Team und gilt_bis 12 Stunden nach jetzt, Antwort mit team und giltBis
   3  mit dem Schlüssel (ohne PIN) gehen alle acht Eingaben durch, report_position schreibt die Position
   4  derselbe Schlüssel mit dem Code eines anderen Teams, ein abgelaufener, ein erfundener "nw-…": "Notweg-Schlüssel
      gilt nicht mehr"; ein erfundener Schlüssel ohne "nw-" weiter mit dem W5-Text
   5  notweg_ende löscht genau diesen Schlüssel, danach abgelehnt; ein zweiter Schlüssel bleibt
   6  unverändert: Schlüssel der Leitung, Admin-PIN, Code allein abgelehnt, falscher Code mit Schlüssel über die Bremse
   7  admin_notweg räumt abgelaufene Schlüssel weg; ein gelöschtes Team nimmt seine Schlüssel mit
   9  admin_set_pin löscht alle Notweg-Schlüssel, danach abgelehnt (Prüfung 09.11., M1)
   8  Rechte: Tabelle für anon/authenticated gesperrt, admin_notweg und notweg_ende offen, SECURITY DEFINER,
      search_path; team_eingabe weiter intern
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sql  # noqa: E402

MIG = sql.REPO / "supabase" / "migrations"
VORHER = [MIG / "20261103090000_w5_eingaben_schluessel.sql", MIG / "20261107090000_bugjagd3.sql"]
MIGRATION = MIG / "20261109090000_notweg_schluessel.sql"
W5 = "Eingeben kann nur die Teamleitung auf ihrem eigenen Handy. Wenn du die Leitung bist: App neu laden."
NW = "Der Notweg-Schlüssel gilt nicht mehr. Bitte die Admin-PIN noch einmal eingeben."
OFFEN = ["admin_notweg(text,text)", "notweg_ende(text)"]


def chk(bedingung: str, text: str, ist: str = "") -> str:
    z = f" || ': ' || coalesce(({ist})::text, 'null')" if ist else ""
    return f"  if not coalesce(({bedingung}), false) then v_f := v_f || ('{text}'::text{z}); end if; v_n := v_n + 1;"


def abgelehnt(aufruf: str, kennung: str, meldung: str) -> str:
    return (f"  begin perform {aufruf}; v_f := v_f || '{kennung} angenommen'::text; "
            f"exception when others then if sqlerrm <> '{meldung}' then v_f := v_f || ('{kennung} falscher Text: ' || sqlerrm); end if; end; "
            "v_n := v_n + 1;")


def offen(aufruf: str, kennung: str) -> str:
    """Darf an eigenen Regeln scheitern, nicht am Recht."""
    return (f"  begin perform {aufruf}; exception when others then if sqlerrm in ('{W5}', '{NW}') or sqlerrm like 'Falsche PIN%' "
            f"or sqlerrm like '%function%does not exist%' then v_f := v_f || ('{kennung}: ' || sqlerrm); end if; end; v_n := v_n + 1;")


def alle(tok: str, code: str = "v_code") -> list:
    return [f"check_in({code}, null, null, null, {tok}, null)",
            f"submit_answer({code}, 'probe', null, {tok}, null)",
            f"reveal_tip({code}, {tok}, null)",
            f"submit_final({code}, '000000', null, null, null, {tok}, null)",
            f"team_selfie({code}, 999, '', '', {tok}, null)",
            f"team_selfie_skip({code}, 999, {tok}, null)",
            f"team_set_leader({code}, v_na, {tok}, null)",
            f"report_position({code}, 50.2, 14.5, 10, null, {tok}, null)"]


def pruefungen() -> str:
    c = []
    a = c.append
    a("-- 1: admin_notweg abgelehnt")
    a(abgelehnt("admin_notweg('falsch-' || md5(random()::text), v_code)", "1A falsche PIN", "Falsche PIN."))
    a(abgelehnt("admin_notweg(v_pin, 'GIBT-ES-NICHT-77')", "1B unbekannter Code", "Unbekannter Team-Code."))
    a(chk("not exists (select 1 from notweg_schluessel)", "1C ohne Erfolg kein Schlüssel angelegt"))

    a("-- 2: Schlüssel holen")
    a("  r := admin_notweg(v_pin, v_code); v_k := r->>'token';")
    a(chk("v_k like 'nw-%' and length(v_k) > 60", "2A Schlüssel mit nw- und lang genug", "v_k"))
    a(chk("(select team_id from notweg_schluessel where token = v_k) = v_id", "2B Zeile mit dem richtigen Team"))
    a(chk("(select gilt_bis from notweg_schluessel where token = v_k) = now() + interval '12 hours'", "2C gilt 12 Stunden"))
    a(chk("r->>'team' = 'Probelauf' and r->>'giltBis' is not null", "2D Antwort mit team und giltBis", "r::text"))
    a("  r := admin_notweg(v_pin, lower(v_code)); v_k2 := r->>'token';")
    a(chk("v_k2 like 'nw-%' and v_k2 <> v_k", "2E zweiter Schlüssel, Code klein geschrieben"))

    a("-- 3: Eingaben mit dem Schlüssel")
    for i, x in enumerate(alle("v_k")):
        a(offen(x, f"3{chr(65 + i)} Notweg: {x.split('(')[0]}"))
    a(chk("exists (select 1 from team_positions where team_id = v_id and lat = 50.2)", "3I Position geschrieben"))

    a("-- 4: Schlüssel gilt nicht")
    a(abgelehnt("reveal_tip(v_code2, v_k, null)", "4A Schlüssel mit fremdem Team-Code", NW))
    a(abgelehnt("reveal_tip(v_code, 'nw-' || md5(random()::text), null)", "4B erfundener Schlüssel", NW))
    a(abgelehnt("reveal_tip(v_code, 'erfunden-' || md5(random()::text), null)", "4C erfundener Schlüssel ohne nw-", W5))
    a("  update notweg_schluessel set gilt_bis = now() - interval '1 second' where token = v_k2;")
    a(abgelehnt("reveal_tip(v_code, v_k2, null)", "4D abgelaufener Schlüssel", NW))
    a(offen("reveal_tip(v_code, v_k2, v_pin)", "4E abgelaufener Schlüssel mit PIN"))

    a("-- 5: notweg_ende")
    a("  r := admin_notweg(v_pin, v_code); v_k3 := r->>'token';")
    a("  perform notweg_ende(v_k);")
    a(chk("not exists (select 1 from notweg_schluessel where token = v_k)", "5A Schlüssel gelöscht"))
    a(chk("exists (select 1 from notweg_schluessel where token = v_k3)", "5B anderer Schlüssel bleibt"))
    a(abgelehnt("reveal_tip(v_code, v_k, null)", "5C gelöschter Schlüssel", NW))
    a("  perform notweg_ende('nw-gibt-es-nicht'); perform notweg_ende(null);")

    a("-- 6: unverändert")
    a(offen("reveal_tip(v_code, v_ta, null)", "6A Schlüssel der Leitung"))
    a(offen("reveal_tip(v_code, null, v_pin)", "6B Admin-PIN"))
    a(abgelehnt("reveal_tip(v_code, null, null)", "6C Code allein", W5))
    a(abgelehnt("reveal_tip(v_code, v_tb, null)", "6D Schlüssel eines Mitglieds", W5))
    a("  r := reveal_tip('GIBT-ES-NICHT-88', v_k3, null);")
    a(chk("r->>'message' = 'Unbekannter Team-Code.'", "6E falscher Code mit Notweg-Schlüssel: Bremse antwortet", "r::text"))

    a("-- 7: Aufräumen")
    a("  perform admin_notweg(v_pin, v_code2);")
    a(chk("not exists (select 1 from notweg_schluessel where token = v_k2)", "7A abgelaufener Schlüssel weggeräumt"))
    a("  delete from team_positions where team_id = v_id2; delete from participants where team_id = v_id2;")
    a("  update teams set leader_participant_id = null where id = v_id2; delete from teams where id = v_id2;")
    a(chk("not exists (select 1 from notweg_schluessel s where not exists (select 1 from teams t where t.id = s.team_id))",
          "7B gelöschtes Team nimmt seine Schlüssel mit"))

    a("-- 8: Rechte")
    a("  foreach rr in array array['anon', 'authenticated'] loop")
    a("    if has_table_privilege(rr, 'public.notweg_schluessel', 'select') or has_table_privilege(rr, 'public.notweg_schluessel', 'insert') "
      "or has_table_privilege(rr, 'public.notweg_schluessel', 'delete') then v_f := v_f || ('8A ' || rr || ' darf notweg_schluessel'); end if; v_n := v_n + 1;")
    a("  end loop;")
    a(chk("(select relrowsecurity from pg_class where oid = 'public.notweg_schluessel'::regclass)", "8B RLS an"))
    a("  foreach f in array array[__OFFEN__] loop")
    a("    foreach rr in array array['anon', 'authenticated'] loop")
    a("      if not has_function_privilege(rr, f, 'execute') then v_f := v_f || ('8C ' || rr || ' darf ' || f || ' nicht'); end if; v_n := v_n + 1;")
    a("    end loop;")
    a("    if not (select prosecdef from pg_proc where oid = f::regprocedure) then v_f := v_f || ('8D nicht SECURITY DEFINER: ' || f); end if;")
    a("    if not coalesce((select 'search_path=public' = any (proconfig) from pg_proc where oid = f::regprocedure), false) then "
      "v_f := v_f || ('8E search_path fehlt: ' || f); end if;")
    a("    v_n := v_n + 2;")
    a("  end loop;")
    a("  foreach rr in array array['anon', 'authenticated', 'public'] loop")
    a("    if has_function_privilege(rr, 'team_eingabe(text,text,text)', 'execute') then v_f := v_f || ('8F ' || rr || ' darf team_eingabe'); end if; v_n := v_n + 1;")
    a("  end loop;")
    a(chk("(select count(*) from pg_proc where pronamespace = 'public'::regnamespace and proname in ('admin_notweg', 'notweg_ende')) = 2",
          "8G je genau eine Fassung"))

    a("-- 9: neue PIN widerruft alle Schlüssel")
    a("  r := admin_notweg(v_pin, v_code); v_k := r->>'token';")
    a("  perform admin_set_pin(v_pin, 'probe-neue-pin-' || md5(random()::text));")
    a(chk("not exists (select 1 from notweg_schluessel)", "9A nach neuer PIN keine Schlüssel mehr"))
    a(abgelehnt("reveal_tip(v_code, v_k, null)", "9B Schlüssel nach neuer PIN", NW))
    a(chk("(select admin_pin from game_state where id = 1) <> v_pin", "9C PIN geändert (wird zurückgerollt)"))
    return "\n".join(c)


PROBE = r"""
do $probe$
declare v_n int := 0; v_f text[] := '{}'; r json; f text; rr text; v_pin text; v_k text; v_k2 text; v_k3 text;
        v_code text := 'PROBE-' || substr(md5(random()::text), 1, 8); v_code2 text := 'PROBE-' || substr(md5(random()::text), 1, 8);
        v_id uuid; v_id2 uuid; v_a uuid; v_b uuid;
        v_na text := 'Probe Anna ' || substr(md5(random()::text), 1, 6); v_nb text := 'Probe Ben ' || substr(md5(random()::text), 1, 6);
        v_ta text := 'probe-' || md5(random()::text); v_tb text := 'probe-' || md5(random()::text);
begin
  __VORHER__
  __MIGRATION__
  v_pin := (select admin_pin from game_state where id = 1);
  delete from notweg_schluessel;
  update game_state set status = 'running', test_mode = true, selfie_on = false, started_at = coalesce(started_at, now()) where id = 1;
  insert into teams (name, code, read_token) values ('Probelauf', v_code, md5(random()::text)) returning id into v_id;
  insert into teams (name, code, read_token) values ('Probelauf 2', v_code2, md5(random()::text)) returning id into v_id2;
  insert into participants (name, name_key, team_id, token) values (v_na, norm(v_na), v_id, v_ta) returning id into v_a;
  insert into participants (name, name_key, team_id, token) values (v_nb, norm(v_nb), v_id, v_tb) returning id into v_b;
  update teams set leader_participant_id = v_a where id = v_id;

__PRUEFUNGEN__

  if array_length(v_f, 1) > 0 then
    raise exception 'PROBE FEHLT (% von % Prüfungen): %', array_length(v_f, 1), v_n, array_to_string(v_f, ' | ');
  end if;
  raise exception 'PROBELAUF_OK: % Prüfungen bestanden, alles zurückgenommen', v_n;
end $probe$;
"""


def main() -> None:
    vorher = "\n".join(f"execute $mig${m.read_text(encoding='utf-8')}$mig$;" for m in VORHER)
    migration = "" if "--ohne" in sys.argv else MIGRATION.read_text(encoding="utf-8")
    assert "$mig$" not in migration and "$probe$" not in migration
    probe = (PROBE.replace("__PRUEFUNGEN__", pruefungen()).replace("__OFFEN__", ", ".join("'" + x + "'" for x in OFFEN))
             .replace("__VORHER__", vorher)
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
