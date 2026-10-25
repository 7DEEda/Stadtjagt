-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.member_state(p_token text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v participants; t teams;
begin
  if coalesce(p_token, '') = '' then
    raise exception 'Unbekanntes Gerät.' using errcode = 'P0001';
  end if;
  select * into v from participants where token = p_token;
  if not found then
    raise exception 'Unbekanntes Gerät.' using errcode = 'P0001';
  end if;
  if v.team_id is null then
    return json_build_object('name', v.name, 'team', null);
  end if;
  select * into t from teams where id = v.team_id;
  return ((team_state(t.code)::jsonb #- '{team,code}' #- '{team,readToken}')
          || jsonb_build_object('name', v.name))::json;
end $function$;
revoke all on function public.member_state(p_token text) from public, anon, authenticated;
grant execute on function public.member_state(p_token text) to public, anon, authenticated;
