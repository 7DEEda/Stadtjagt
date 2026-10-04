#!/usr/bin/env python3
"""
Probelauf für Nachtrag 31 (current_station sperren) gegen die echte Datenbank, ohne Spuren.

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

MIGRATION = sql.REPO / "supabase" / "migrations" / "20261004090000_current_station_sperren.sql"

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
  -- die Spielfunktionen selbst bleiben für anon offen
  if not has_function_privilege('anon', 'team_state(text)', 'execute') then
    raise exception 'PROBE FEHLT: team_state für anon gesperrt'; end if;
  v_n := v_n + 1;
  raise exception 'PROBELAUF_OK: % Prüfungen bestanden, alles zurückgenommen', v_n;
end $probe$;
"""


def main() -> None:
    # ohne Argument mit Migration; "--ohne" zeigt den Stand der Datenbank ohne Migration (rot)
    migration = "" if "--ohne" in sys.argv else MIGRATION.read_text(encoding="utf-8")
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
