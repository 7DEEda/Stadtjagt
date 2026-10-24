-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_photo(p_pin text, p_team uuid, p_position integer, p_full boolean DEFAULT false, p_route text DEFAULT 'echt'::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  return json_build_object('data', (select encode(case when p_full then ph.photo else ph.thumb end, 'base64')
          from station_photos ph join stations_alle s on s.id = ph.station_id and s.route = coalesce(p_route, 'echt')
          where ph.team_id = p_team and s.position = p_position));
end $function$;
revoke all on function public.admin_photo(p_pin text, p_team uuid, p_position integer, p_full boolean, p_route text) from public, anon, authenticated;
grant execute on function public.admin_photo(p_pin text, p_team uuid, p_position integer, p_full boolean, p_route text) to public, anon, authenticated;
