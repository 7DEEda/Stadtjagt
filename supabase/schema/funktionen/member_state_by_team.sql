-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.member_state_by_team(p_read_token text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams;
begin
  if coalesce(p_read_token, '') = '' then
    raise exception 'Unbekannter Mitlese-Link.' using errcode = 'P0001';
  end if;
  select * into t from teams where read_token = p_read_token;
  if not found then
    raise exception 'Unbekannter Mitlese-Link.' using errcode = 'P0001';
  end if;
  return ((team_state(t.code)::jsonb #- '{team,code}' #- '{team,readToken}')
          || jsonb_build_object('name', null))::json;
end $function$;
revoke all on function public.member_state_by_team(p_read_token text) from public, anon, authenticated;
grant execute on function public.member_state_by_team(p_read_token text) to public, anon, authenticated;
