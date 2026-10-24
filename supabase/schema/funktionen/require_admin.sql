-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=nein, authenticated=nein
CREATE OR REPLACE FUNCTION public.require_admin(p_pin text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  if not exists (select 1 from game_state where id = 1 and admin_pin = btrim(coalesce(p_pin,''))) then
    raise exception 'Falsche PIN.' using errcode = 'P0001';
  end if;
end $function$;
revoke all on function public.require_admin(p_pin text) from public, anon, authenticated;
