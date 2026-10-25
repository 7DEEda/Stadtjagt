-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.rb_poll(p_pin text, p_seit bigint)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare r rueckblick_steuerung;
begin
  perform require_admin(p_pin);
  select * into r from rueckblick_steuerung where id = 1;
  if not found then return null; end if;
  if p_seit is null or r.nr < p_seit then return json_build_object('nr', r.nr, 'befehl', null); end if;
  if r.nr = p_seit then return null; end if;
  if r.befehl_um is null or r.befehl_um < clock_timestamp() - interval '30 seconds' then
    return json_build_object('nr', r.nr, 'befehl', null);
  end if;
  return json_build_object('nr', r.nr, 'befehl', r.befehl);
end $function$;
revoke all on function public.rb_poll(p_pin text, p_seit bigint) from public, anon, authenticated;
grant execute on function public.rb_poll(p_pin text, p_seit bigint) to anon, authenticated;
