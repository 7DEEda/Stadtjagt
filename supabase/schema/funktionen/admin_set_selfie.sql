-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_set_selfie(p_pin text, p_on boolean, p_delete_on date)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_heute date := (now() at time zone 'Europe/Prague')::date;
begin
  perform require_admin(p_pin);
  -- Audit 25.10.: ein Löschdatum heute (oder früher) löschte beim nächsten Abruf alle Fotos. Heute zählt nach
  -- Prager Zeit, wie das Datumsfeld im Browser; gelöscht wird weiter in team_state/admin_state mit current_date
  -- (UTC), also am gewählten Tag ab 1 Uhr (Winterzeit) bzw. 2 Uhr (Sommerzeit), nie früher. Dasselbe Datum wie
  -- gespeichert geht beim Ausschalten durch, sonst ließe sich das Gruppenselfie nach dem Löschtag nicht mehr
  -- ausschalten. Beim Einschalten nicht: ein altes Datum aus einer Probe würde sonst am Eventtag angenommen.
  if p_delete_on is not null and p_delete_on <= v_heute
     and (coalesce(p_on, false)
          or p_delete_on is distinct from (select photos_delete_on from game_state where id = 1)) then
    raise exception 'Das Löschdatum muss nach heute liegen.' using errcode='P0001';
  end if;
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
