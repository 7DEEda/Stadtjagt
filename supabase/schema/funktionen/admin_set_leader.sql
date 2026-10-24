-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_set_leader(p_pin text, p_team uuid, p_participant uuid)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  if not exists (select 1 from participants where id = p_participant and team_id = p_team) then
    raise exception 'Diese Person ist nicht in diesem Team.' using errcode='P0001';
  end if;
  update teams set leader_participant_id = p_participant where id = p_team;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_set_leader(p_pin text, p_team uuid, p_participant uuid) from public, anon, authenticated;
grant execute on function public.admin_set_leader(p_pin text, p_team uuid, p_participant uuid) to public, anon, authenticated;
