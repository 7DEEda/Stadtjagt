-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=nein, authenticated=nein
CREATE OR REPLACE FUNCTION public.current_station(p_team uuid)
 RETURNS stations
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
  select s.* from stations s
  left join progress pr on pr.station_id = s.id and pr.team_id = p_team
  where pr.solved_at is null
  order by s.position
  limit 1;
$function$;
revoke all on function public.current_station(p_team uuid) from public, anon, authenticated;
