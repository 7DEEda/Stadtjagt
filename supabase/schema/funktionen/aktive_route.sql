-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=nein, authenticated=nein
CREATE OR REPLACE FUNCTION public.aktive_route()
 RETURNS text
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
  select case when coalesce((select test_mode from game_state where id = 1), false)
                   and exists (select 1 from stations_alle where route = 'test')
              then 'test' else 'echt' end
$function$;
revoke all on function public.aktive_route() from public, anon, authenticated;
