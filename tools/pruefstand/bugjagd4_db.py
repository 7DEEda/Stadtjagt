#!/usr/bin/env python3
"""
Probelauf für die Migration 20261107100000_bugjagd4.sql (Bugjagd 07.11.2026, Funde 2, 3 und 7) gegen die echte
Datenbank, ohne Spuren.

    python tools/pruefstand/bugjagd4_db.py          mit Migration (grün)
    python tools/pruefstand/bugjagd4_db.py --ohne   Stand der Datenbank ohne Migration (rot)

Wie bugjagd3_db.py: EIN DO-Block spielt die Migration ein, setzt das Spiel im Block auf die einzelnen Zustände, prüft
und wirft am Ende absichtlich einen Fehler (Marker PROBELAUF_OK oder PROBE FEHLT). Der Server rollt alles zurück, auch
die Migration und die geänderte Station. Während des Laufs (etwa eine Sekunde) ist die Zeile game_state gesperrt;
nicht während eines laufenden Spiels starten.

Geprüft:
   R   admin_finish, admin_reset, admin_save_station für anon offen (PIN-Schutz innen), search_path gesetzt;
       falsche PIN bei allen dreien weiter "Falsche PIN."
   F2  admin_finish lehnt in registration, drawn und finished ab (Status bleibt), beendet aus running
   F3  admin_reset lehnt in registration ab (Status bleibt), setzt aus drawn, running und finished auf drawn
   F7  admin_save_station lehnt Breite 500, -90.5, Länge -200, 180.5 und NaN ab (Station unverändert), nimmt
       Grenzwerte (90, -180), normale Werte und null (Station ohne Standort)
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import sql  # noqa: E402

MIGRATION = sql.REPO / "supabase" / "migrations" / "20261107100000_bugjagd4.sql"
FUNKTIONEN = ["admin_finish(text)", "admin_reset(text)",
              "admin_save_station(text,uuid,text,double precision,double precision,integer,text,text,text,integer,text,integer,integer)"]
T_FINISH = "Beenden geht nur im laufenden Spiel. Ein anderes Gerät hat den Spielstand inzwischen geändert."
T_RESET = "Vor dem Auslosen gibt es nichts zurückzusetzen."
T_KOORD = "Die Breite muss zwischen -90 und 90 liegen, die Länge zwischen -180 und 180."


def chk(bedingung: str, text: str, ist: str = "") -> str:
    """Eine Prüfung: bei Misserfolg wird der Fund gesammelt, der Lauf geht weiter."""
    z = f" || ': ' || coalesce(({ist})::text, 'null')" if ist else ""
    return f"  if not coalesce(({bedingung}), false) then v_f := v_f || ('{text}'::text{z}); end if; v_n := v_n + 1;"


def wirft(aufruf: str, soll: str, text: str) -> str:
    """Der Aufruf muss genau mit dieser Meldung abbrechen; was er bis dahin tat, nimmt die Ausnahme mit zurück."""
    return (f"  begin perform {aufruf}; v_f := v_f || ('{text}: keine Ausnahme'::text); "
            f"exception when others then if sqlerrm <> '{soll}' then v_f := v_f || ('{text}: ' || sqlerrm); end if; end; v_n := v_n + 1;")


def speichern(lat: str, lng: str) -> str:
    return (f"admin_save_station(v_pin, v_st, 'Probe Station', {lat}, {lng}, 40, 'Hinweis', 'Rätsel', 'loesung', 3, '', null, null)")


def pruefungen() -> str:
    c = []
    a = c.append
    status = "(select status from game_state where id = 1)"

    a("-- R: Rechte, falsche PIN")
    a("  foreach f in array array[__FUNKTIONEN__] loop")
    a("    if not has_function_privilege('anon', f, 'execute') then v_f := v_f || ('R anon darf ' || f || ' nicht ausführen'); end if; v_n := v_n + 1;")
    a("    if not coalesce((select 'search_path=public' = any (proconfig) from pg_proc where oid = f::regprocedure), false) then "
      "v_f := v_f || ('R search_path fehlt: ' || f); end if; v_n := v_n + 1;")
    a("  end loop;")
    a("  update game_state set status = 'running', started_at = now(), finished_at = null where id = 1;")
    a(wirft("admin_finish(v_falsch)", "Falsche PIN.", "R admin_finish mit falscher PIN"))
    a(wirft("admin_reset(v_falsch)", "Falsche PIN.", "R admin_reset mit falscher PIN"))
    a(wirft(speichern("50.1", "14.4").replace("v_pin", "v_falsch"), "Falsche PIN.", "R admin_save_station mit falscher PIN"))

    a("-- F2: admin_finish nur aus running")
    for s in ("registration", "drawn", "finished"):
        a(f"  update game_state set status = '{s}' where id = 1;")
        a(wirft("admin_finish(v_pin)", T_FINISH, f"F2 admin_finish aus {s}"))
        a(chk(f"{status} = '{s}'", f"F2 Status nach Ablehnung aus {s}", status))
    a("  update game_state set status = 'running', started_at = now(), finished_at = null where id = 1;")
    a("  r := admin_finish(v_pin);")
    a(chk(f"{status} = 'finished' and (select finished_at from game_state where id = 1) is not null and r->>'status' = 'finished'",
          "F2 admin_finish aus running", status))

    a("-- F3: admin_reset nicht aus registration")
    a("  update game_state set status = 'registration', started_at = null, finished_at = null where id = 1;")
    a(wirft("admin_reset(v_pin)", T_RESET, "F3 admin_reset aus registration"))
    a(chk(f"{status} = 'registration'", "F3 Status nach Ablehnung", status))
    for s in ("drawn", "running", "finished"):
        a(f"  update game_state set status = '{s}', started_at = case when '{s}' = 'drawn' then null else now() end where id = 1;")
        a("  r := admin_reset(v_pin);")
        a(chk(f"{status} = 'drawn' and (select started_at from game_state where id = 1) is null and r->>'status' = 'drawn'",
              f"F3 admin_reset aus {s}", status))
    a(chk("not exists (select 1 from progress) and not exists (select 1 from finishes)", "F3 Fortschritt und Plätze gelöscht"))

    a("-- F7: Wertebereich der Koordinaten")
    a("  select id, lat, lng into v_st, v_lat, v_lng from stations_alle where route = 'echt' order by position limit 1;")
    a(chk("v_st is not null", "F7 keine echte Station zum Prüfen"))
    for lat, lng, name in (("500", "14.4", "Breite 500"), ("-90.5", "14.4", "Breite -90.5"), ("50.1", "-200", "Länge -200"),
                           ("50.1", "180.5", "Länge 180.5"), ("'NaN'::double precision", "14.4", "Breite NaN"),
                           ("50.1", "'Infinity'::double precision", "Länge unendlich")):
        a(wirft(speichern(lat, lng), T_KOORD, f"F7 {name}"))
    a(chk("(select lat from stations_alle where id = v_st) is not distinct from v_lat and (select lng from stations_alle where id = v_st) is not distinct from v_lng",
          "F7 Station nach Ablehnung unverändert", "(select lat from stations_alle where id = v_st)"))
    a(f"  r := {speichern('90', '-180')};")
    a(chk("(select lat from stations_alle where id = v_st) = 90 and (select lng from stations_alle where id = v_st) = -180", "F7 Grenzwerte 90 und -180"))
    a(f"  r := {speichern('50.087512', '14.421254')};")
    a(chk("(select lat from stations_alle where id = v_st) = 50.087512 and (select lng from stations_alle where id = v_st) = 14.421254 "
          "and (select name from stations_alle where id = v_st) = 'Probe Station'", "F7 normale Werte gespeichert"))
    a(f"  r := {speichern('null', 'null')};")
    a(chk("(select lat from stations_alle where id = v_st) is null and (select lng from stations_alle where id = v_st) is null", "F7 ohne Standort (null)"))
    return "\n".join(c)


PROBE = r"""
do $probe$
declare v_n int := 0; v_f text[] := '{}'; r json; f text; v_pin text; v_st uuid; v_lat double precision; v_lng double precision;
        v_falsch text := 'falsch-' || md5(random()::text);
begin
  __MIGRATION__
  v_pin := (select admin_pin from game_state where id = 1);
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
    probe = (PROBE.replace("__PRUEFUNGEN__", pruefungen())
             .replace("__FUNKTIONEN__", ", ".join("'" + x + "'" for x in FUNKTIONEN))
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
