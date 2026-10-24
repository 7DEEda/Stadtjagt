-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.team_photo(p_code text, p_token text, p_read_token text, p_position integer, p_full boolean DEFAULT false)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_team uuid;
begin
  if coalesce(p_code, '') <> '' then
    v_team := (team_by_code(p_code)).id;
  elsif coalesce(p_token, '') <> '' then
    select team_id into v_team from participants where token = p_token;
  elsif coalesce(p_read_token, '') <> '' then
    select id into v_team from teams where read_token = p_read_token;
  end if;
  if v_team is null then raise exception 'Kein Zugang zu diesem Album.' using errcode='P0001'; end if;
  return json_build_object('data', (select encode(case when p_full then ph.photo else ph.thumb end, 'base64')
          from station_photos ph join stations s on s.id = ph.station_id
          where ph.team_id = v_team and s.position = p_position));
end $function$;
revoke all on function public.team_photo(p_code text, p_token text, p_read_token text, p_position integer, p_full boolean) from public, anon, authenticated;
grant execute on function public.team_photo(p_code text, p_token text, p_read_token text, p_position integer, p_full boolean) to public, anon, authenticated;
