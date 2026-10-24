-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.reveal_tip(p_code text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; g game_state; cur stations; row_p progress;
begin
  t := team_by_code(p_code);
  select * into g from game_state where id = 1;
  if g.status <> 'running' then
    return json_build_object('ok', false, 'message', 'Das Spiel läuft gerade nicht.', 'state', team_state(p_code));
  end if;
  cur := current_station(t.id);
  select * into row_p from progress where team_id = t.id and station_id = cur.id;
  if cur.id is null or row_p.checked_in_at is null then
    return json_build_object('ok', false, 'message', 'Hier gibt es gerade keinen Tipp.', 'state', team_state(p_code));
  end if;
  if btrim(cur.tip) = '' then
    return json_build_object('ok', false, 'message', 'Für dieses Rätsel gibt es keinen Tipp.', 'state', team_state(p_code));
  end if;
  if not g.test_mode and row_p.pauses < 1 then
    return json_build_object('ok', false, 'message', 'Den Tipp gibt es nach der ersten Denkpause.', 'state', team_state(p_code));
  end if;
  update progress set tip_at = coalesce(tip_at, now()) where team_id = t.id and station_id = cur.id;
  return json_build_object('ok', true, 'message', 'Tipp aufgedeckt.', 'state', team_state(p_code));
end $function$;
revoke all on function public.reveal_tip(p_code text) from public, anon, authenticated;
grant execute on function public.reveal_tip(p_code text) to public, anon, authenticated;
