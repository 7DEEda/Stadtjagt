-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

create or replace view public.stations as
SELECT id,
    "position",
    name,
    lat,
    lng,
    radius_m,
    location_hint,
    riddle,
    answer,
    digit,
    tip,
    reveal_start_m,
    reveal_clear_m,
    route
   FROM stations_alle
  WHERE (route = aktive_route());
revoke all on table public.stations from anon, authenticated;
