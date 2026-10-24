-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_set_pin(p_pin text, p_new text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  if length(btrim(coalesce(p_new,''))) < 12 then
    raise exception 'Die neue PIN braucht mindestens 12 Zeichen, am besten eine Passphrase.' using errcode='P0001';
  end if;
  update game_state set admin_pin = btrim(p_new) where id = 1;
  return admin_state(btrim(p_new));
end $function$;
revoke all on function public.admin_set_pin(p_pin text, p_new text) from public, anon, authenticated;
grant execute on function public.admin_set_pin(p_pin text, p_new text) to public, anon, authenticated;
