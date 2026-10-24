-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_set_selfie(p_pin text, p_on boolean, p_delete_on date)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  -- Einschalten mitten im Spiel: was schon gelöst ist, braucht kein Foto mehr, sonst stünden alle Teams
  -- plötzlich vor einem Selfie für längst verlassene Stationen
  if coalesce(p_on, false) and not (select selfie_on from game_state where id = 1) then
    update progress set selfie_at = solved_at where solved_at is not null and selfie_at is null;
  end if;
  update game_state set selfie_on = coalesce(p_on, false), photos_delete_on = p_delete_on where id = 1;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_set_selfie(p_pin text, p_on boolean, p_delete_on date) from public, anon, authenticated;
grant execute on function public.admin_set_selfie(p_pin text, p_on boolean, p_delete_on date) to public, anon, authenticated;
