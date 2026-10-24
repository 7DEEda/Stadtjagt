-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.leader_code(p_token text)
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
  select * into t from teams where id = v.team_id and leader_participant_id = v.id;
  if not found then
    raise exception 'Du bist gerade keine Teamleitung.' using errcode = 'P0001';
  end if;
  return json_build_object('code', t.code, 'teamName', t.name, 'name', v.name);
end $function$;
revoke all on function public.leader_code(p_token text) from public, anon, authenticated;
grant execute on function public.leader_code(p_token text) to public, anon, authenticated;
