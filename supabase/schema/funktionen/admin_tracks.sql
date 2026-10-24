-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_tracks(p_pin text, p_since timestamp with time zone DEFAULT NULL::timestamp with time zone)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  return (select json_build_object(
    'now', now(),
    'status', g.status,
    'startedAt', g.started_at,
    'finishedAt', g.finished_at,
    'winnerTeamId', g.winner_team_id,
    'teams', coalesce((select json_agg(to_json(y)) from (
        select t.id, t.name,
          coalesce((select json_agg(json_build_array(
                       round(pl.lat::numeric, 6),
                       round(pl.lng::numeric, 6),
                       (extract(epoch from pl.recorded_at) * 1000)::bigint)
                     order by pl.recorded_at)
                    from position_log pl
                    where pl.team_id = t.id
                      and (p_since is null or pl.recorded_at > p_since)), '[]'::json) as points,
          (select count(*) from position_log pl2 where pl2.team_id = t.id) as "pointCount",
          coalesce((select json_agg(json_build_object(
                       'position', s.position,
                       'checkedInAt', pr.checked_in_at,
                       'solvedAt', pr.solved_at) order by s.position)
                    from progress pr join stations s on s.id = pr.station_id
                    where pr.team_id = t.id and pr.checked_in_at is not null), '[]'::json) as stations
        from teams t order by t.name) y), '[]'::json)
  ) from game_state g where g.id = 1);
end $function$;
revoke all on function public.admin_tracks(p_pin text, p_since timestamp with time zone) from public, anon, authenticated;
grant execute on function public.admin_tracks(p_pin text, p_since timestamp with time zone) to public, anon, authenticated;
