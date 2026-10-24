-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.team_set_leader(p_code text, p_name text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; v_id uuid;
begin
  t := team_by_code(p_code);
  select id into v_id from participants where team_id = t.id and name_key = norm(p_name);
  if v_id is null then
    raise exception 'Diese Person ist nicht in eurem Team.' using errcode='P0001';
  end if;
  update teams set leader_participant_id = v_id where id = t.id;
  return team_state(p_code);
end $function$;
revoke all on function public.team_set_leader(p_code text, p_name text) from public, anon, authenticated;
grant execute on function public.team_set_leader(p_code text, p_name text) to public, anon, authenticated;
