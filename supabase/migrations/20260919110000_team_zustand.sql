-- ============================================================
--  STADTJAGD – Nachtrag 21: Zustand der Teams für die Spielleitung
--
--  admin_state liefert je Team zusätzlich checkedInAt (Check-in an der
--  aktuellen Station, null solange das Team unterwegs ist) und lastSolvedAt
--  (letzte gelöste Station). Der Reiter Teams zeigt damit „unterwegs zu
--  Station 2 seit 14 min“ oder „an Station 2 seit 22 min“ und je nach Lage
--  nur „Freischalten“ oder nur „Rätsel werten“ (UI-Durchsicht 19.09.2026).
--
--  Einspielen: nach Nachtrag 20. Mehrfach ausführbar, löscht keine Daten.
--  Eine ältere Seite ignoriert die neuen Felder, die neue Seite fällt ohne
--  sie auf die bisherige Anzeige zurück.
-- ============================================================

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
          -- Nachtrag 21: seit wann das Team an seiner aktuellen Station steht (null = noch unterwegs)
          -- und wann es zuletzt eine Station gelöst hat; daraus zeigt der Reiter Teams "an Station 2 seit 14 min"
          (select pr.checked_in_at from stations s
             left join progress pr on pr.station_id = s.id and pr.team_id = t.id
             where pr.solved_at is null order by s.position limit 1) as "checkedInAt",
          (select max(pr.solved_at) from progress pr where pr.team_id = t.id) as "lastSolvedAt",
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
