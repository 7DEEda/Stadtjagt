-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_photos(p_pin text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  return coalesce((select json_agg(to_json(x)) from (
    select t.id as "teamId", t.name as "teamName", s.position, s.name as "stationName", s.route, ph.taken_at as "takenAt"
    from station_photos ph join teams t on t.id = ph.team_id join stations_alle s on s.id = ph.station_id
    order by t.name, s.route, s.position) x), '[]'::json);
end $function$;
revoke all on function public.admin_photos(p_pin text) from public, anon, authenticated;
grant execute on function public.admin_photos(p_pin text) to public, anon, authenticated;
