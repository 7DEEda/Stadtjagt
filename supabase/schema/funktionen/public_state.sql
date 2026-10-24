-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.public_state()
 RETURNS json
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
  select json_build_object(
    'background', g.background,
    'selfieOn', g.selfie_on,
    'photosDeleteOn', g.photos_delete_on,
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
          (select count(*) from progress pr join stations s on s.id = pr.station_id where pr.team_id = t.id and pr.solved_at is not null) as solved,
          (select max(pr.solved_at) from progress pr join stations s on s.id = pr.station_id where pr.team_id = t.id) as "lastSolvedAt",
          coalesce(f.place <= g.prize_count, false) as "isWinner"
        from teams t left join finishes f on f.team_id = t.id
        order by f.place asc nulls last,
                 (select count(*) from progress pr join stations s on s.id = pr.station_id where pr.team_id = t.id and pr.solved_at is not null) desc,
                 (select max(pr.solved_at) from progress pr join stations s on s.id = pr.station_id where pr.team_id = t.id) asc nulls last
      ) r), '[]'::json)
  ) from game_state g where g.id = 1;
$function$;
revoke all on function public.public_state() from public, anon, authenticated;
grant execute on function public.public_state() to public, anon, authenticated;
