-- ============================================================
--  STADTJAGD – Nachtrag 19: Hintergrund umschaltbar
--
--  Die drei Entwürfe aus mockups/hintergrund-varianten.html liegen jetzt als
--  hintergrund/a.svg, b.svg, c.svg im Repo; "klassisch" ist die bisherige
--  Wanderkarte, die fest in index.html steht. Die Spielleitung wählt im Reiter
--  Stationen (admin_set_background), alle Handys übernehmen die Wahl mit der
--  nächsten Abfrage: game_state.background steht in public_state, team_state
--  und admin_state (Fassungen aus Nachtrag 6 bzw. 17 plus dieses Feld).
--
--  Einspielen: nach Nachtrag 18. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

alter table game_state add column if not exists background text not null default 'klassisch'
  check (background in ('klassisch', 'a', 'b', 'c'));

create or replace function admin_set_background(p_pin text, p_background text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  if p_background not in ('klassisch', 'a', 'b', 'c') then
    raise exception 'Unbekannter Hintergrund.' using errcode='P0001';
  end if;
  update game_state set background = p_background where id = 1;
  return admin_state(p_pin);
end $$;

grant execute on function admin_set_background(text, text) to anon, authenticated;

-- ---------- public_state (Nachtrag 6) plus background ----------
create or replace function public_state() returns json
language sql security definer set search_path = public as $$
  select json_build_object(
    'background', g.background,
    'status', g.status,
    'startedAt', g.started_at,
    'finishedAt', g.finished_at,
    'winnerTeamId', g.winner_team_id,
    'prizeCount', g.prize_count,
    'participantCount', (select count(*) from participants),
    'stationCount', (select count(*) from stations),
    'teams', coalesce((
      select json_agg(to_json(x)) from (
        select t.id, t.name,
          (select p.name from participants p where p.id = t.leader_participant_id) as "leaderName",
          coalesce((select json_agg(p2.name order by p2.name)
                    from participants p2 where p2.team_id = t.id), '[]'::json) as members
        from teams t order by t.name
      ) x), '[]'::json),
    'ranking', coalesce((
      select json_agg(to_json(r)) from (
        select t.id as "teamId", t.name as "teamName", f.place, f.finished_at as "finishedAt",
          (select count(*) from progress pr where pr.team_id = t.id and pr.solved_at is not null) as solved,
          (select max(pr.solved_at) from progress pr where pr.team_id = t.id) as "lastSolvedAt",
          coalesce(f.place <= g.prize_count, false) as "isWinner"
        from teams t left join finishes f on f.team_id = t.id
        order by f.place asc nulls last,
                 (select count(*) from progress pr where pr.team_id = t.id and pr.solved_at is not null) desc,
                 (select max(pr.solved_at) from progress pr where pr.team_id = t.id) asc nulls last
      ) r), '[]'::json)
  ) from game_state g where g.id = 1;
$$;

-- ---------- team_state (Nachtrag 17) plus background ----------
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
    'background', g.background,
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

-- ---------- admin_state (Nachtrag 17) plus background ----------
create or replace function admin_state(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  return (select json_build_object(
    'background', g.background, 'status', g.status, 'startedAt', g.started_at, 'finishedAt', g.finished_at,
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
