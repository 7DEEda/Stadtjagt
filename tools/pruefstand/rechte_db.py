#!/usr/bin/env python3
"""
Probelauf für Nachtrag 31 (current_station sperren) gegen die echte Datenbank, ohne Spuren. Seitdem um jede neue
Migration mit Funktionen ergänzt (zuletzt Rollen und Akku 29.10., 20261029120000_rollen_akku.sql).

    python tools/pruefstand/rechte_db.py

EIN DO-Block spielt die Migration ein, prüft die Rechte aller internen Hilfsfunktionen und wirft am Ende
absichtlich einen Fehler. Auch wenn eine Prüfung scheitert, endet der Block mit einer Ausnahme: der Server
rollt die ganze Anweisung zurück. Ohne Migration (MIGRATION leer) zeigt er, was offen ist.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import sql  # noqa: E402

# Die Migrationen, die diese Datenbank noch nicht (oder zuletzt neu) bekommen hat; der Probelauf spielt sie nacheinander ein.
# Nach dem Einspielen einer Migration, die Funktionen neu anlegt, hier ergänzen (SPIEL.md §9).
MIGRATIONEN = ["20261004090000_current_station_sperren.sql", "20261015090000_namenssuche_grenze.sql",
               "20261016090000_eingaben_wiederholen.sql", "20261017090000_rueckblick_steuerung.sql",
               "20261025090000_audit.sql", "20261029120000_rollen_akku.sql"]
MIGRATION = [sql.REPO / "supabase" / "migrations" / n for n in MIGRATIONEN]

# Interne Hilfsfunktionen: dürfen weder anon noch authenticated ausführen
INTERN = ["norm(text)", "dist_m(double precision,double precision,double precision,double precision)",
          "team_by_code(text)", "current_station(uuid)", "require_admin(text)", "answer_ok(text,text)",
          "aktive_route()"]

PROBE = r"""
do $probe$
declare f text; r text; v_n int := 0;
begin
  execute $mig$__MIGRATION__$mig$;
  foreach f in array array[__INTERN__] loop
    foreach r in array array['anon', 'authenticated'] loop
      if has_function_privilege(r, f, 'execute') then
        raise exception 'PROBE FEHLT: % darf % ausführen', r, f; end if;
      v_n := v_n + 1;
    end loop;
  end loop;
  -- die Spielfunktionen selbst bleiben für anon offen (jede Überladung, die es gibt)
  foreach f in array array['team_state', 'lookup_participant', 'submit_answer', 'check_in', 'register_participant', 'submit_final',
                           'rb_befehl', 'rb_poll', 'rb_status_setzen', 'rb_status_holen', 'rb_ende'] loop
    if not exists (select 1 from pg_proc p where p.pronamespace = 'public'::regnamespace and p.proname = f) then
      raise exception 'PROBE FEHLT: Funktion % gibt es nicht', f; end if;
    if exists (select 1 from pg_proc p where p.pronamespace = 'public'::regnamespace and p.proname = f
               and not has_function_privilege('anon', p.oid, 'execute')) then
      raise exception 'PROBE FEHLT: % für anon gesperrt', f; end if;
    v_n := v_n + 1;
  end loop;
  -- submit_answer gibt es nur noch mit p_position (alte Fassung weg, sonst Mehrdeutigkeit bei PostgREST)
  if (select count(*) from pg_proc p where p.pronamespace = 'public'::regnamespace and p.proname = 'submit_answer') <> 1 then
    raise exception 'PROBE FEHLT: submit_answer nicht genau einmal'; end if;
  v_n := v_n + 1;
  -- Rollen und Akku 29.10.: member_state und report_position nur noch in der neuen Fassung, member_state_by_team (F7) ist weg
  if (select count(*) from pg_proc p where p.pronamespace = 'public'::regnamespace and p.proname in ('member_state', 'report_position')) <> 2
     or exists (select 1 from pg_proc p where p.pronamespace = 'public'::regnamespace and p.proname = 'member_state_by_team') then
    raise exception 'PROBE FEHLT: member_state/report_position nicht genau einmal oder member_state_by_team noch da'; end if;
  v_n := v_n + 1;
  -- Nachtrag 37: die Tabelle der Fernbedienung ist für anon und authenticated gesperrt, der Weg sind die rb_*-Funktionen
  if to_regclass('public.rueckblick_steuerung') is null then raise exception 'PROBE FEHLT: Tabelle rueckblick_steuerung gibt es nicht'; end if;
  foreach r in array array['anon', 'authenticated'] loop
    if has_table_privilege(r, 'public.rueckblick_steuerung', 'select') or has_table_privilege(r, 'public.rueckblick_steuerung', 'update') then
      raise exception 'PROBE FEHLT: % darf rueckblick_steuerung lesen oder ändern', r; end if;
    v_n := v_n + 1;
  end loop;
  raise exception 'PROBELAUF_OK: % Prüfungen bestanden, alles zurückgenommen', v_n;
end $probe$;
"""


def main() -> None:
    # ohne Argument mit Migration; "--ohne" zeigt den Stand der Datenbank ohne Migration (rot)
    migration = "" if "--ohne" in sys.argv else "\n".join(m.read_text(encoding="utf-8") for m in MIGRATION)
    assert "$mig$" not in migration and "$probe$" not in migration
    intern = ", ".join("'" + f + "'" for f in INTERN)
    probe = PROBE.replace("__INTERN__", intern).replace(
        "execute $mig$__MIGRATION__$mig$;", f"execute $mig${migration}$mig$;" if migration.strip() else "")
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
