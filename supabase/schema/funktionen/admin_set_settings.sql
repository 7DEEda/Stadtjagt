-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_set_settings(p_pin text, p_duration_min integer, p_case_hint text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  if p_duration_min is null or p_duration_min < 10 or p_duration_min > 720 then
    raise exception 'Die Spieldauer muss zwischen 10 und 720 Minuten liegen.' using errcode='P0001';
  end if;
  update game_state set duration_min = p_duration_min,
    case_hint = coalesce(nullif(btrim(p_case_hint), ''), case_hint) where id = 1;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_set_settings(p_pin text, p_duration_min integer, p_case_hint text) from public, anon, authenticated;
grant execute on function public.admin_set_settings(p_pin text, p_duration_min integer, p_case_hint text) to public, anon, authenticated;
