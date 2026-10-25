-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_set_start(p_pin text, p_route text, p_name text, p_lat double precision, p_lng double precision)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
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
end $function$;
revoke all on function public.admin_set_start(p_pin text, p_route text, p_name text, p_lat double precision, p_lng double precision) from public, anon, authenticated;
grant execute on function public.admin_set_start(p_pin text, p_route text, p_name text, p_lat double precision, p_lng double precision) to public, anon, authenticated;
