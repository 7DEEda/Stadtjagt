-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_unlock_station(p_pin text, p_team uuid, p_position integer DEFAULT NULL::integer)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare cur stations;
begin
  perform require_admin(p_pin);
  perform 1 from teams where id = p_team for update;
  cur := current_station(p_team);
  if cur.id is null then raise exception 'Dieses Team hat alle Stationen gelöst.' using errcode='P0001'; end if;
  if p_position is not null and cur.position <> p_position then
    raise exception 'Das Team ist schon bei Station %. Nichts freigeschaltet.', cur.position using errcode='P0001';
  end if;
  insert into progress(team_id, station_id, checked_in_at) values (p_team, cur.id, now())
    on conflict (team_id, station_id) do update set checked_in_at = coalesce(progress.checked_in_at, now());
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_unlock_station(p_pin text, p_team uuid, p_position integer) from public, anon, authenticated;
grant execute on function public.admin_unlock_station(p_pin text, p_team uuid, p_position integer) to public, anon, authenticated;
