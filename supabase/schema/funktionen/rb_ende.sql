-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.rb_ende(p_pin text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  update rueckblick_steuerung set status = null, status_um = null, befehl = null, befehl_um = null, handy_um = null
    where id = 1;
  return json_build_object('ok', true);
end $function$;
revoke all on function public.rb_ende(p_pin text) from public, anon, authenticated;
grant execute on function public.rb_ende(p_pin text) to anon, authenticated;
