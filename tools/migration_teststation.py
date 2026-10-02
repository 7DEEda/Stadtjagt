#!/usr/bin/env python3
"""
Erzeugt supabase/migrations/20261002120000_teststation.sql.

    python tools/migration_teststation.py

Kopf: Tabelle umbenennen, Spalte route, Sicht stations, aktive_route(), Teststation EDEKA.
Danach die neuesten Fassungen von team_state, submit_final, public_state, admin_state und
admin_save_station, jeweils mit genau gezählten Ersetzungen (bricht ab, wenn eine fehlt).
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
MIG = REPO / "supabase" / "migrations"
ZIEL = MIG / "20261002120000_teststation.sql"

KOPF = """-- Nachtrag 28: Teststation. Spec: docs/superpowers/specs/2026-10-02-teststation-kompass-waechter-design.md, Teil 1.
-- stations heißt jetzt stations_alle (echte Route und Teststation). Die Sicht stations zeigt nur die aktive
-- Route; alle Spielfunktionen lesen weiter stations.
-- ACHTUNG für spätere Migrationen: die Sicht ist "select *" zum Zeitpunkt des Anlegens. Wer eine Spalte an
-- stations_alle anfügt, MUSS danach
--   create or replace view stations as select * from stations_alle where route = aktive_route();
-- ausführen, sonst passt current_station (liefert den Typ der Sicht) nicht mehr und das Spiel steht.
-- Wird die Sicht einmal gelöscht und neu angelegt (statt "or replace"), danach unbedingt
--   revoke all on stations from anon, authenticated;
-- Supabase gibt neuen Objekten Leserechte, dann wären Rätsel und Lösungen ohne PIN lesbar.

alter table stations rename to stations_alle;
alter table stations_alle add column route text not null default 'echt';
alter table stations_alle add constraint stations_route_pruefen check (route in ('echt', 'test'));
alter table stations_alle drop constraint stations_position_key;
alter table stations_alle add constraint stations_route_position_key unique (route, position);

create or replace function aktive_route() returns text
language sql stable security definer set search_path = public as $$
  select case when coalesce((select test_mode from game_state where id = 1), false)
                   and exists (select 1 from stations_alle where route = 'test')
              then 'test' else 'echt' end
$$;

create view stations as select * from stations_alle where route = aktive_route();
-- Sichten haben keine Zeilenrechte: ohne das hier könnte jede und jeder Rätsel und Lösungen lesen
revoke all on stations from anon, authenticated;
revoke all on function aktive_route() from public, anon, authenticated;

-- current_station lieferte den Zeilentyp der Tabelle (jetzt stations_alle); neu mit dem Typ der Sicht,
-- damit Tabelle und Sicht nicht auseinanderlaufen. Aufrufer sind plpgsql und hängen nicht daran.
drop function current_station(uuid);
-- admin_photo bekommt p_route dazu: alte Fassung weg, sonst gäbe es zwei
drop function admin_photo(text, uuid, int, boolean);
create function current_station(p_team uuid) returns stations
language sql security definer set search_path = public as $$
  select s.* from stations s
  left join progress pr on pr.station_id = s.id and pr.team_id = p_team
  where pr.solved_at is null
  order by s.position
  limit 1;
$$;

insert into stations_alle (route, position, name, lat, lng, radius_m, location_hint, riddle, answer, digit, tip)
values ('test', 1, 'EDEKA Grenzallee', 52.470116, 13.462131, 50, 'Ortshinweis folgt', 'Rätsel folgt', '', 1, '');
"""

# (Funktion, Datei mit der neuesten Fassung, [(alt, neu, Anzahl)])
SOLVED_ALT = "select count(*) into v_solved from progress where team_id = t.id and solved_at is not null;"
SOLVED_NEU = ("select count(*) into v_solved from progress pr join stations s on s.id = pr.station_id "
              "where pr.team_id = t.id and pr.solved_at is not null;")
PR_SOLVED_ALT = "(select count(*) from progress pr where pr.team_id = t.id and pr.solved_at is not null)"
PR_SOLVED_NEU = ("(select count(*) from progress pr join stations s on s.id = pr.station_id "
                 "where pr.team_id = t.id and pr.solved_at is not null)")
PR_LAST_ALT = "(select max(pr.solved_at) from progress pr where pr.team_id = t.id)"
PR_LAST_NEU = "(select max(pr.solved_at) from progress pr join stations s on s.id = pr.station_id where pr.team_id = t.id)"

ADMIN_FELDER_ALT = """               s.reveal_start_m as "revealStartM", s.reveal_clear_m as "revealClearM"
        from stations s order by s.position) s2), '[]'::json),"""
ADMIN_FELDER_NEU = """               s.reveal_start_m as "revealStartM", s.reveal_clear_m as "revealClearM", s.route
        from stations_alle s where s.route = 'echt' order by s.position) s2), '[]'::json),
    'testStation', (select to_json(s3) from (
        select s.id, s.position, s.name, s.lat, s.lng, s.radius_m as "radiusM",
               s.location_hint as "locationHint", s.riddle, s.answer, s.digit, s.tip,
               s.reveal_start_m as "revealStartM", s.reveal_clear_m as "revealClearM", s.route
        from stations_alle s where s.route = 'test' order by s.position limit 1) s3),
    'route', aktive_route(),
    'aktiveStationen', coalesce((select json_agg(to_json(s4)) from (
        select s.id, s.position, s.name, s.lat, s.lng, s.radius_m as "radiusM"
        from stations s order by s.position) s4), '[]'::json),"""

AUFGABEN = [
    ("team_state", "20261001120000_zahlenantwort.sql", [(SOLVED_ALT, SOLVED_NEU, 1)]),
    ("submit_final", "20260919030000_wasserdicht.sql", [(SOLVED_ALT, SOLVED_NEU, 1)]),
    ("public_state", "20260930180000_gruppenselfie.sql", [(PR_SOLVED_ALT, PR_SOLVED_NEU, 2), (PR_LAST_ALT, PR_LAST_NEU, 2)]),
    ("admin_state", "20260930200000_name_verschluesselt.sql",
     [(ADMIN_FELDER_ALT, ADMIN_FELDER_NEU, 1), (PR_SOLVED_ALT, PR_SOLVED_NEU, 1), (PR_LAST_ALT, PR_LAST_NEU, 1)]),
    ("admin_save_station", "20260930200000_name_verschluesselt.sql", [("  update stations set", "  update stations_alle set", 1)]),
    # Fotos der Spielleitung immer von der echten Route: Event-Fotos verschwinden im Testmodus nicht (Review M-3)
    # Fotos der Spielleitung: alle Routen, mit route; die Teststation erscheint als eigene Kachel (Friedrich 02.10.)
    ("admin_photos", "20260930180000_gruppenselfie.sql",
     [("join stations s on s.id = ph.station_id", "join stations_alle s on s.id = ph.station_id", 1),
      ('s.name as "stationName",', 's.name as "stationName", s.route,', 1),
      ("order by t.name, s.position", "order by t.name, s.route, s.position", 1)]),
    ("admin_photo", "20260930180000_gruppenselfie.sql",
     [("create or replace function admin_photo(p_pin text, p_team uuid, p_position int, p_full boolean default false)",
       "create or replace function admin_photo(p_pin text, p_team uuid, p_position int, p_full boolean default false, p_route text default 'echt')", 1),
      ("join stations s on s.id = ph.station_id", "join stations_alle s on s.id = ph.station_id and s.route = coalesce(p_route, 'echt')", 1)]),
    # im Testmodus reicht eine Person (ein Team zum Ausprobieren), sonst wie bisher zwei
    ("admin_draw", "20260919100000_bugjagd.sql",
     [("  if v_count < 2 then raise exception 'Es sind noch zu wenige Personen angemeldet.' using errcode='P0001'; end if;",
       "  if v_count < (case when (select test_mode from game_state where id = 1) then 1 else 2 end) then "
       "raise exception 'Es sind noch zu wenige Personen angemeldet.' using errcode='P0001'; end if;", 1)]),
]


def fassung(name: str, datei: str) -> str:
    text = (MIG / datei).read_text(encoding="utf-8")
    # die letzte Definition in der Datei: von "create or replace function name(" bis zum schließenden "$$;"
    # (plpgsql endet mit "end $$;", language sql nur mit "$$;"); das öffnende "as $$" zählt nicht
    starts = [m.start() for m in re.finditer(rf"create or replace function {name}\(", text)]
    if not starts:
        sys.exit(f"{name} nicht in {datei}")
    a = starts[-1]
    auf = text.index("$$", a) + 2
    e = text.index("$$;", auf) + len("$$;")
    return text[a:e]


def main() -> None:
    teile = [KOPF]
    for name, datei, ersetzungen in AUFGABEN:
        f = fassung(name, datei)
        for alt, neu, n in ersetzungen:
            if f.count(alt) != n:
                sys.exit(f"{name}: '{alt[:50]}' kommt {f.count(alt)}x vor, erwartet {n}x")
            f = f.replace(alt, neu)
        teile.append(f"-- ---------- {name} (aus {datei}, für die Teststation angepasst) ----------\n{f}\n")
    teile.append("grant execute on function admin_photo(text, uuid, int, boolean, text) to anon, authenticated;\n")
    teile.append("notify pgrst, 'reload schema';\n")
    ZIEL.write_text("\n".join(teile), encoding="utf-8", newline="\n")
    print("geschrieben:", ZIEL.relative_to(REPO))


if __name__ == "__main__":
    main()
