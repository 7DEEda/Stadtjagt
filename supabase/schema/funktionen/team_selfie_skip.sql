-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.team_selfie_skip(p_code text, p_position integer, p_token text DEFAULT NULL::text, p_pin text DEFAULT NULL::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams;
begin
  t := team_eingabe(p_code, p_token, p_pin);
  if t.id is null then return team_code_abgelehnt(current_setting('sj.code_fehler', true)); end if;   -- Bremse (Bugjagd 03.11.)
  update progress pr set selfie_at = coalesce(pr.selfie_at, now())
    from stations s
    where s.id = pr.station_id and s.position = p_position and pr.team_id = t.id and pr.solved_at is not null;
  if not found then raise exception 'Erst das Rätsel lösen.' using errcode='P0001'; end if;
  return team_state(p_code);
end $function$;
revoke all on function public.team_selfie_skip(p_code text, p_position integer, p_token text, p_pin text) from public, anon, authenticated;
grant execute on function public.team_selfie_skip(p_code text, p_position integer, p_token text, p_pin text) to public, anon, authenticated;
