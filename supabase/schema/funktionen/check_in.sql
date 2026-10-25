-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.check_in(p_code text, p_lat double precision, p_lng double precision, p_acc double precision)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; g game_state; cur stations; d double precision; tol double precision;
begin
  t := team_by_code(p_code);
  select * into g from game_state where id = 1;
  if g.status <> 'running' then
    return json_build_object('ok', false, 'message', 'Das Spiel läuft gerade nicht.', 'state', team_state(p_code));
  end if;
  cur := current_station(t.id);
  if cur.id is null then
    return json_build_object('ok', false, 'message', 'Alle Stationen sind gelöst.', 'state', team_state(p_code));
  end if;
  -- Schon eingecheckt (Wiederholung nach verlorener Antwort): gleiche Antwort, ohne die Entfernung neu zu prüfen;
  -- das GPS darf inzwischen gesprungen sein
  if exists (select 1 from progress where team_id = t.id and station_id = cur.id and checked_in_at is not null) then
    return json_build_object('ok', true,
      'message', case when g.test_mode then 'Testmodus: eingecheckt ohne Entfernungsprüfung.'
                      else 'Angekommen. Das Rätsel ist frei.' end,
      'state', team_state(p_code));
  end if;
  if not g.test_mode then
    if cur.lat is null or cur.lng is null then
      return json_build_object('ok', false, 'message',
        'Für diese Station sind noch keine Koordinaten gesetzt. Bitte die Spielleitung fragen.',
        'state', team_state(p_code));
    end if;
    if p_lat is null or p_lng is null then
      return json_build_object('ok', false, 'message', 'Ohne Standort kein Check-in. Bitte GPS freigeben.',
        'state', team_state(p_code));
    end if;
    d := dist_m(p_lat, p_lng, cur.lat, cur.lng);
    tol := cur.radius_m + least(greatest(coalesce(p_acc,0),0), 25);
    if d > tol then
      return json_build_object('ok', false, 'distance', round(d::numeric,0),
        'message', 'Noch nicht am Ziel: ' || round(d::numeric,0) || ' m entfernt.',
        'state', team_state(p_code));
    end if;
  end if;
  insert into progress(team_id, station_id, checked_in_at)
  values (t.id, cur.id, now())
  on conflict (team_id, station_id) do update set checked_in_at = coalesce(progress.checked_in_at, now());
  return json_build_object('ok', true, 'distance', round(d::numeric,0),
    'message', case when g.test_mode then 'Testmodus: eingecheckt ohne Entfernungsprüfung.'
                    else 'Angekommen. Das Rätsel ist frei.' end,
    'state', team_state(p_code));
end $function$;
revoke all on function public.check_in(p_code text, p_lat double precision, p_lng double precision, p_acc double precision) from public, anon, authenticated;
grant execute on function public.check_in(p_code text, p_lat double precision, p_lng double precision, p_acc double precision) to public, anon, authenticated;
