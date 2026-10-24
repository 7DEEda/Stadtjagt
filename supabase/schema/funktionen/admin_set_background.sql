-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_set_background(p_pin text, p_background text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  if p_background not in ('klassisch', 'a', 'b', 'c') then
    raise exception 'Unbekannter Hintergrund.' using errcode='P0001';
  end if;
  update game_state set background = p_background where id = 1;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_set_background(p_pin text, p_background text) from public, anon, authenticated;
grant execute on function public.admin_set_background(p_pin text, p_background text) to public, anon, authenticated;
