-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.team_selfie_skip(p_code text, p_position integer)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams;
begin
  t := team_by_code(p_code);
  update progress pr set selfie_at = coalesce(pr.selfie_at, now())
    from stations s
    where s.id = pr.station_id and s.position = p_position and pr.team_id = t.id and pr.solved_at is not null;
  if not found then raise exception 'Erst das Rätsel lösen.' using errcode='P0001'; end if;
  return team_state(p_code);
end $function$;
revoke all on function public.team_selfie_skip(p_code text, p_position integer) from public, anon, authenticated;
grant execute on function public.team_selfie_skip(p_code text, p_position integer) to public, anon, authenticated;
