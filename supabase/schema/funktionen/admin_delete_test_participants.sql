-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_delete_test_participants(p_pin text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_n int;
begin
  perform require_admin(p_pin);
  update teams t set leader_participant_id = null
    where leader_participant_id in (select id from participants where name like '%(Test)');
  delete from participants where name like '%(Test)';
  get diagnostics v_n = row_count;
  -- Teams, deren Leitung weg ist, bekommen eine neue aus den Verbliebenen
  update teams t set leader_participant_id = (
      select p.id from participants p where p.team_id = t.id order by random() limit 1)
    where t.leader_participant_id is null;
  return json_build_object('deleted', v_n, 'state', admin_state(p_pin));
end $function$;
revoke all on function public.admin_delete_test_participants(p_pin text) from public, anon, authenticated;
grant execute on function public.admin_delete_test_participants(p_pin text) to public, anon, authenticated;
