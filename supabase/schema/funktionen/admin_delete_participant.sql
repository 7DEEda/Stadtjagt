-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_delete_participant(p_pin text, p_id uuid)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  update teams set leader_participant_id = null where leader_participant_id = p_id;
  delete from participants where id = p_id;
  update teams t set leader_participant_id = (
      select p.id from participants p where p.team_id = t.id order by random() limit 1)
    where t.leader_participant_id is null;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_delete_participant(p_pin text, p_id uuid) from public, anon, authenticated;
grant execute on function public.admin_delete_participant(p_pin text, p_id uuid) to public, anon, authenticated;
