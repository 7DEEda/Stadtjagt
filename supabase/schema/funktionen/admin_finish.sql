-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_finish(p_pin text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_status text;
begin
  perform require_admin(p_pin);
  select status into v_status from game_state where id = 1 for update;
  if v_status is distinct from 'running' then
    raise exception 'Beenden geht nur im laufenden Spiel. Ein anderes Gerät hat den Spielstand inzwischen geändert.' using errcode='P0001';
  end if;
  update game_state set status = 'finished', finished_at = now() where id = 1;
  -- Standortdaten bleiben absichtlich stehen, damit die Routen auswertbar sind.
  -- Löschen über admin_clear_positions ("Standortdaten löschen").
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_finish(p_pin text) from public, anon, authenticated;
grant execute on function public.admin_finish(p_pin text) to public, anon, authenticated;
