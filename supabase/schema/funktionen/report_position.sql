-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.report_position(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_kompass text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams;
begin
  if (select status from game_state where id = 1) <> 'running' then return; end if;
  if p_lat is null or p_lng is null or abs(p_lat) > 90 or abs(p_lng) > 180
     or (abs(p_lat) < 0.01 and abs(p_lng) < 0.01)
     or p_acc is null or p_acc <= 0 or p_acc > 1000 then
    return;
  end if;
  t := team_by_code(p_code);
  insert into team_positions(team_id, lat, lng, accuracy_m, updated_at, kompass)
  values (t.id, p_lat, p_lng, p_acc, now(), case when p_kompass in ('ok', 'unzuverlaessig') then p_kompass end)
  on conflict (team_id) do update
    set lat = excluded.lat, lng = excluded.lng, accuracy_m = excluded.accuracy_m, updated_at = now(), kompass = excluded.kompass;
  insert into position_log(team_id, lat, lng, accuracy_m) values (t.id, p_lat, p_lng, p_acc);
end $function$;
revoke all on function public.report_position(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_kompass text) from public, anon, authenticated;
grant execute on function public.report_position(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_kompass text) to public, anon, authenticated;
