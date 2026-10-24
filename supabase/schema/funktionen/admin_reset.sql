-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_reset(p_pin text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  delete from progress where true;
  delete from finishes where true;
  delete from team_positions where true;
  delete from position_log where true;
  update game_state set status = 'drawn', started_at = null, finished_at = null,
    winner_team_id = null where id = 1;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_reset(p_pin text) from public, anon, authenticated;
grant execute on function public.admin_reset(p_pin text) to public, anon, authenticated;
