#!/usr/bin/env python3
"""
Erzeugt supabase/migrations/20261002140000_startpunkt.sql (Nachtrag 29: Startpunkt eintragbar).

    python tools/migration_startpunkt.py

Startpunkt je Route (echte Route und Teststation) in game_state, admin_set_start zum Speichern,
admin_state liefert start und testStart. admin_state wird aus der neuesten Fassung
(20261002120000_teststation.sql) übernommen und um die zwei Felder ergänzt.
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
MIG = REPO / "supabase" / "migrations"
ZIEL = MIG / "20261002140000_startpunkt.sql"

KOPF = """-- Nachtrag 29: Startpunkt eintragbar, je Route (echte Route und Teststation). Bisher fest im Client
-- (Mama Shelter Prague, TSE Berlin). Wirkt auf das Haus auf der Karte der Spielleitung und auf die
-- erste Etappe (Vorschlag für die Kreise beim Entschlüsseln).

alter table game_state add column start_name text not null default 'Start';
alter table game_state add column start_lat double precision;
alter table game_state add column start_lng double precision;
alter table game_state add column test_start_name text not null default 'Start';
alter table game_state add column test_start_lat double precision;
alter table game_state add column test_start_lng double precision;
update game_state set start_name = 'Mama Shelter Prague', start_lat = 50.102458, start_lng = 14.431681,
  test_start_name = 'TSE Berlin, Grenzallee 4', test_start_lat = 52.4698774, test_start_lng = 13.4627621 where id = 1;

create or replace function admin_set_start(p_pin text, p_route text, p_name text, p_lat double precision, p_lng double precision)
returns json language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  if p_route not in ('echt', 'test') then
    raise exception 'Unbekannte Route.' using errcode = 'P0001';
  end if;
  if p_lat is null or p_lng is null or p_lat not between -90 and 90 or p_lng not between -180 and 180 then
    raise exception 'Bitte Breite und Länge des Startpunkts eintragen.' using errcode = 'P0001';
  end if;
  if p_route = 'echt' then
    update game_state set start_name = coalesce(nullif(btrim(p_name), ''), start_name), start_lat = p_lat, start_lng = p_lng where id = 1;
  else
    update game_state set test_start_name = coalesce(nullif(btrim(p_name), ''), test_start_name), test_start_lat = p_lat, test_start_lng = p_lng where id = 1;
  end if;
  return admin_state(p_pin);
end $$;
grant execute on function admin_set_start(text, text, text, double precision, double precision) to anon, authenticated;
"""

ALT = "    'aktiveStationen', coalesce("
NEU = """    'start', json_build_object('name', g.start_name, 'lat', g.start_lat, 'lng', g.start_lng),
    'testStart', json_build_object('name', g.test_start_name, 'lat', g.test_start_lat, 'lng', g.test_start_lng),
    'aktiveStationen', coalesce("""


def main() -> None:
    text = (MIG / "20261002120000_teststation.sql").read_text(encoding="utf-8")
    a = [m.start() for m in re.finditer(r"create or replace function admin_state\(", text)][-1]
    e = text.index("$$;", text.index("$$", a) + 2) + 3
    f = text[a:e]
    if f.count(ALT) != 1:
        sys.exit("admin_state: Einfügestelle 'aktiveStationen' nicht genau einmal gefunden")
    f = f.replace(ALT, NEU)
    ZIEL.write_text(KOPF + "\n-- ---------- admin_state (aus 20261002120000_teststation.sql) plus start und testStart ----------\n"
                    + f + "\n\nnotify pgrst, 'reload schema';\n", encoding="utf-8", newline="\n")
    print("geschrieben:", ZIEL.relative_to(REPO))


if __name__ == "__main__":
    main()
