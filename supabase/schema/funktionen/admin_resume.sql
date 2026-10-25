-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_resume(p_pin text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  if (select status from game_state where id = 1) <> 'finished' then
    raise exception 'Fortsetzen geht nur, wenn das Spiel beendet ist.' using errcode='P0001';
  end if;
  update game_state set status = 'running', finished_at = null where id = 1;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_resume(p_pin text) from public, anon, authenticated;
grant execute on function public.admin_resume(p_pin text) to public, anon, authenticated;
