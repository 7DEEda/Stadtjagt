-- ============================================================
--  STADTJAGD – Nachtrag 17: eigener Koffer-Hinweis und Spieldauer
--
--  1. Der Hinweis auf dem Koffer-Bildschirm war bisher der Ortshinweis der
--     letzten Station, den das Team gerade schon als Wegbeschreibung gelesen
--     hatte. Jetzt ein eigener Text in game_state.case_hint, im Reiter
--     Stationen pflegbar.
--  2. Feste Spieldauer (game_state.duration_min, Vorgabe 180): ab admin_start
--     zeigen alle Handys einen Countdown, am Ende "Zeit ist um". Die Logik
--     bleibt unberührt, das Spiel endet erst mit admin_finish.
--
--  admin_set_settings(p_pin, p_duration_min, p_case_hint) setzt beides.
--  team_state liefert caseHint (aus game_state), durationMin, startedAt,
--  endsAt; member_state und member_state_by_team erben das.
--  3. Tipp je Station (stations.tip, optional): Die Teamleitung kann ihn nach
--     der ersten Denkpause aufdecken (reveal_tip). progress zählt dafür die
--     Pausen (pauses) und merkt sich das Aufdecken (tip_at). team_state
--     liefert tipAvailable (Tipp vorhanden und Pause gehabt) und tip (nur
--     nach dem Aufdecken). admin_save_station bekommt p_tip, die alte
--     Signatur fällt weg.
--
--  Einspielen: nach Nachtrag 16. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

-- ---------- 3. Tipp je Station ----------
alter table stations add column if not exists tip text not null default '';
alter table progress add column if not exists pauses int not null default 0;
alter table progress add column if not exists tip_at timestamptz;

drop function if exists admin_save_station(text, uuid, text, double precision, double precision, int, text, text, text, int);

create or replace function admin_save_station(
  p_pin text, p_id uuid, p_name text, p_lat double precision, p_lng double precision,
  p_radius int, p_hint text, p_riddle text, p_answer text, p_digit int, p_tip text default '') returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  update stations set
    name = coalesce(nullif(btrim(p_name),''), name),
    lat = p_lat, lng = p_lng,
    radius_m = greatest(5, coalesce(p_radius, 50)),
    location_hint = coalesce(p_hint, ''),
    riddle = coalesce(p_riddle, ''),
    answer = coalesce(p_answer, ''),
    digit = greatest(0, least(9, coalesce(p_digit, 0))),
    tip = btrim(coalesce(p_tip, ''))
  where id = p_id;
  return admin_state(p_pin);
end $$;

grant execute on function admin_save_station(text, uuid, text, double precision, double precision, int, text, text, text, int, text)
  to anon, authenticated;

-- Tipp aufdecken: nur an der aktuellen, eingecheckten Station, nur nach einer Denkpause (im Testmodus immer)
create or replace function reveal_tip(p_code text) returns json
language plpgsql security definer set search_path = public as $$
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
end $$;

grant execute on function reveal_tip(text) to anon, authenticated;

-- submit_answer: Fassung aus Nachtrag 15, zählt jetzt die Denkpausen
create or replace function submit_answer(p_code text, p_answer text)
returns json language plpgsql security definer set search_path = public as $$
declare t teams; g game_state; cur stations; row_p progress;
        v_attempts int; v_locked boolean;
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
  -- Sperre: gleichzeitige Antworten desselben Teams laufen nacheinander, der Zähler stimmt
  select * into row_p from progress where team_id = t.id and station_id = cur.id for update;
  if row_p.checked_in_at is null then
    return json_build_object('ok', false, 'message', 'Erst am Ort einchecken, dann gibt es das Rätsel.',
      'state', team_state(p_code));
  end if;
  if not g.test_mode and row_p.locked_until is not null and row_p.locked_until > now() then
    return json_build_object('ok', false,
      'message', 'Denkpause: noch ' || ceil(extract(epoch from row_p.locked_until - now())) || ' Sekunden.',
      'state', team_state(p_code));
  end if;

  if g.test_mode or answer_ok(p_answer, cur.answer) then
    update progress set solved_at = now(), failed_attempts = 0, locked_until = null
      where team_id = t.id and station_id = cur.id;
    return json_build_object('ok', true,
      'message', case when g.test_mode then 'Testmodus: jede Antwort zählt. Eine Ziffer ist frei.'
                      else 'Richtig. Eine Ziffer ist frei.' end,
      'state', team_state(p_code));
  end if;

  v_attempts := case when row_p.locked_until is not null and row_p.locked_until <= now()
                     then 1 else row_p.failed_attempts + 1 end;
  v_locked := v_attempts >= 3;
  update progress
    set failed_attempts = case when v_locked then 0 else v_attempts end,
        locked_until    = case when v_locked then now() + interval '2 minutes' else null end,
        pauses          = pauses + case when v_locked then 1 else 0 end
    where team_id = t.id and station_id = cur.id;
  return json_build_object('ok', false,
    'message', case when v_locked then 'Dreimal falsch. Zwei Minuten Denkpause für euer Team.'
                        || case when btrim(cur.tip) <> '' then ' Danach könnt ihr einen Tipp aufdecken.' else '' end
                    else 'Leider falsch. Noch ' || (3 - v_attempts)
                         || case when 3 - v_attempts = 1 then ' Versuch.' else ' Versuche.' end end,
    'state', team_state(p_code));
end $$;

alter table game_state add column if not exists duration_min int not null default 180
  check (duration_min between 10 and 720);
alter table game_state add column if not exists case_hint text not null default
  'Die Koffer stehen bei der Spielleitung an der letzten Station. Zeigt dort euren Platz-Bildschirm.';

create or replace function admin_set_settings(p_pin text, p_duration_min int, p_case_hint text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  if p_duration_min is null or p_duration_min < 10 or p_duration_min > 720 then
    raise exception 'Die Spieldauer muss zwischen 10 und 720 Minuten liegen.' using errcode='P0001';
  end if;
  update game_state set duration_min = p_duration_min,
    case_hint = coalesce(nullif(btrim(p_case_hint), ''), case_hint) where id = 1;
  return admin_state(p_pin);
end $$;

grant execute on function admin_set_settings(text, int, text) to anon, authenticated;

-- ---------- team_state: Fassung aus Nachtrag 14 plus caseHint aus game_state, Spieldauer ----------
create or replace function team_state(p_code text) returns json
language plpgsql security definer set search_path = public as $$
declare t teams; g game_state; cur stations; row_p progress;
        v_total int; v_solved int; v_sum int; v_all boolean; v_place int; v_done int;
begin
  t := team_by_code(p_code);
  select * into g from game_state where id = 1;
  select count(*) into v_total from stations;
  select count(*) into v_solved from progress where team_id = t.id and solved_at is not null;
  select coalesce(sum(s.digit),0) into v_sum from stations s
    join progress pr on pr.station_id = s.id and pr.team_id = t.id and pr.solved_at is not null;
  v_all := v_total > 0 and v_solved = v_total;
  cur := current_station(t.id);
  select * into row_p from progress where team_id = t.id and station_id = cur.id;
  select place into v_place from finishes where team_id = t.id;
  select count(*) into v_done from finishes;

  return json_build_object(
    'team', json_build_object('id', t.id, 'name', t.name, 'code', t.code, 'readToken', t.read_token,
      'leaderName', (select p.name from participants p where p.id = t.leader_participant_id),
      'members', coalesce((select json_agg(p2.name order by p2.name)
                           from participants p2 where p2.team_id = t.id), '[]'::json)),
    'status', g.status,
    'startedAt', g.started_at,
    'durationMin', g.duration_min,
    'endsAt', case when g.started_at is null then null else g.started_at + make_interval(mins => g.duration_min) end,
    'totalStations', v_total,
    'solvedCount', v_solved,
    -- Ziffern: nur für gelöste Stationen, die sechste erst wenn alles gelöst ist
    'digits', (select json_agg(d order by pos) from (
        select s.position as pos,
               case when pr.solved_at is not null then s.digit else null end as d
        from stations s left join progress pr on pr.station_id = s.id and pr.team_id = t.id
      ) q),
    'finalDigit', case when v_all then v_sum % 10 else null end,
    'station', case when cur.id is null or g.status <> 'running' then null else json_build_object(
        'position', cur.position, 'name', cur.name, 'locationHint', cur.location_hint,
        'lat', cur.lat, 'lng', cur.lng, 'radiusM', cur.radius_m,
        -- Rätsel erst nach dem Check-in
        'riddle', case when row_p.checked_in_at is not null then cur.riddle else null end,
        -- Tipp: ob es einen gibt und er schon offen wäre, und der Text erst nach dem Aufdecken
        'tipAvailable', btrim(cur.tip) <> '' and row_p.checked_in_at is not null and (g.test_mode or coalesce(row_p.pauses, 0) >= 1),
        'tip', case when row_p.tip_at is not null then cur.tip else null end) end,
    'checkedIn', row_p.checked_in_at is not null,
    'failedAttempts', coalesce(row_p.failed_attempts, 0),
    'lockedUntil', row_p.locked_until,
    'pauses', coalesce(row_p.pauses, 0),
    'allSolved', v_all,
    'caseHint', g.case_hint,
    'place', v_place,
    'prizeCount', g.prize_count,
    'prizesLeft', greatest(g.prize_count - v_done, 0),
    'winnerTeamId', g.winner_team_id,
    'isWinner', coalesce(v_place <= g.prize_count, false),
    'testMode', g.test_mode
  );
end $$;

-- ---------- admin_state: Fassung aus Nachtrag 14 plus durationMin, endsAt, caseHint ----------
create or replace function admin_state(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  return (select json_build_object(
    'status', g.status, 'startedAt', g.started_at, 'finishedAt', g.finished_at,
    'durationMin', g.duration_min,
    'endsAt', case when g.started_at is null then null else g.started_at + make_interval(mins => g.duration_min) end,
    'caseHint', g.case_hint,
    'winnerTeamId', g.winner_team_id,
    'prizeCount', g.prize_count,
    'testMode', g.test_mode,
    'participants', coalesce((select json_agg(to_json(x)) from (
        select p.id, p.name, p.team_id as "teamId",
               (select t.name from teams t where t.id = p.team_id) as "teamName"
        from participants p order by p.name) x), '[]'::json),
    'stations', coalesce((select json_agg(to_json(s2)) from (
        select s.id, s.position, s.name, s.lat, s.lng, s.radius_m as "radiusM",
               s.location_hint as "locationHint", s.riddle, s.answer, s.digit, s.tip
        from stations s order by s.position) s2), '[]'::json),
    'caseCode', (select string_agg(s.digit::text, '' order by s.position) from stations s)
                || ((select coalesce(sum(digit),0) from stations) % 10)::text,
    'teams', coalesce((select json_agg(to_json(y)) from (
        select t.id, t.name, t.code, t.read_token as "readToken",
          t.leader_participant_id as "leaderId",
          (select p.name from participants p where p.id = t.leader_participant_id) as "leaderName",
          (select count(*) from participants p where p.team_id = t.id) as "memberCount",
          coalesce((select json_agg(p2.name order by p2.name)
                    from participants p2 where p2.team_id = t.id), '[]'::json) as members,
          (select count(*) from progress pr where pr.team_id = t.id and pr.solved_at is not null) as solved,
          (select s.position from stations s
             left join progress pr on pr.station_id = s.id and pr.team_id = t.id
             where pr.solved_at is null order by s.position limit 1) as "currentPosition",
          (select max(greatest(coalesce(pr.solved_at, to_timestamp(0)),
                               coalesce(pr.checked_in_at, to_timestamp(0))))
             from progress pr where pr.team_id = t.id) as "lastActivity",
          (select json_build_object('lat', tp.lat, 'lng', tp.lng,
                                    'accuracy', tp.accuracy_m, 'updatedAt', tp.updated_at)
             from team_positions tp where tp.team_id = t.id) as position,
          (select f.place from finishes f where f.team_id = t.id) as place,
          (select f.finished_at from finishes f where f.team_id = t.id) as "finishedAt"
        from teams t order by t.name) y), '[]'::json)
  ) from game_state g where g.id = 1);
end $$;

notify pgrst, 'reload schema';
