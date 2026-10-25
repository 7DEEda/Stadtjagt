-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.game_state_pin_pruefen()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
begin
  if new.admin_pin is distinct from old.admin_pin and length(btrim(coalesce(new.admin_pin, ''))) < 12 then
    raise exception 'Die Admin-PIN braucht mindestens 12 Zeichen, am besten eine Passphrase.' using errcode='P0001';
  end if;
  return new;
end $function$;
revoke all on function public.game_state_pin_pruefen() from public, anon, authenticated;
grant execute on function public.game_state_pin_pruefen() to public, anon, authenticated;
