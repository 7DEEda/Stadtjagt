-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=nein, authenticated=nein
CREATE OR REPLACE FUNCTION public.dist_m(lat1 double precision, lng1 double precision, lat2 double precision, lng2 double precision)
 RETURNS double precision
 LANGUAGE sql
 IMMUTABLE
AS $function$
  select 2 * 6371000 * asin(least(1, sqrt(
    power(sin(radians(lat2-lat1)/2), 2) +
    cos(radians(lat1)) * cos(radians(lat2)) * power(sin(radians(lng2-lng1)/2), 2)
  )));
$function$;
revoke all on function public.dist_m(lat1 double precision, lng1 double precision, lat2 double precision, lng2 double precision) from public, anon, authenticated;
