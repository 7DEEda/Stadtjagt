-- ============================================================
--  STADTJAGD – Nachtrag 14: Teamleitung zuweisen und abgeben, Mitlese-Link je Team
--
--  1. Die Spielleitung kann je Team die Leitung bestimmen (admin_set_leader),
--     die Teamleitung kann sie an jemanden aus dem Team abgeben
--     (team_set_leader). Der Team-Code bleibt derselbe: Wer die Leitung
--     übernimmt, bekommt den Code und loggt sich damit ein.
--  2. Jedes Team hat einen Mitlese-Schlüssel (teams.read_token). Die
--     Teamleitung sieht ihn als Link; wer ihn öffnet, liest auf seinem Handy
--     mit, auch ohne eigenen Geräte-Schlüssel aus der Anmeldung (am Rechner
--     angemeldet, anderer Browser, von der Spielleitung nachgetragen).
--     member_state_by_team liefert dasselbe wie member_state, ohne Namen.
--     Team-Code und Mitlese-Schlüssel verlassen die Datenbank nur zur
--     Teamleitung (team_state) und zur Spielleitung (admin_state).
--
--  Einspielen: nach Nachtrag 13. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

-- ---------- Mitlese-Schlüssel je Team ----------
alter table teams add column if not exists read_token text unique
  default replace(gen_random_uuid()::text, '-', '');
update teams set read_token = replace(gen_random_uuid()::text, '-', '') where read_token is null;

-- ---------- team_state: Fassung aus Nachtrag 7 plus readToken ----------
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
        'riddle', case when row_p.checked_in_at is not null then cur.riddle else null end) end,
    'checkedIn', row_p.checked_in_at is not null,
    'failedAttempts', coalesce(row_p.failed_attempts, 0),
    'lockedUntil', row_p.locked_until,
    'allSolved', v_all,
    'caseHint', (select s.location_hint from stations s order by s.position desc limit 1),
    'place', v_place,
    'prizeCount', g.prize_count,
    'prizesLeft', greatest(g.prize_count - v_done, 0),
    'winnerTeamId', g.winner_team_id,
    'isWinner', coalesce(v_place <= g.prize_count, false),
    'testMode', g.test_mode
  );
end $$;

-- ---------- Mitlesen: mit Geräte-Schlüssel (Anmeldung) oder Mitlese-Schlüssel (Link) ----------
create or replace function member_state(p_token text) returns json
language plpgsql security definer set search_path = public as $$
declare v participants; t teams;
begin
  if coalesce(p_token, '') = '' then
    raise exception 'Unbekanntes Gerät.' using errcode = 'P0001';
  end if;
  select * into v from participants where token = p_token;
  if not found then
    raise exception 'Unbekanntes Gerät.' using errcode = 'P0001';
  end if;
  if v.team_id is null then
    return json_build_object('name', v.name, 'team', null);
  end if;
  select * into t from teams where id = v.team_id;
  return ((team_state(t.code)::jsonb #- '{team,code}' #- '{team,readToken}')
          || jsonb_build_object('name', v.name))::json;
end $$;

create or replace function member_state_by_team(p_read_token text) returns json
language plpgsql security definer set search_path = public as $$
declare t teams;
begin
  if coalesce(p_read_token, '') = '' then
    raise exception 'Unbekannter Mitlese-Link.' using errcode = 'P0001';
  end if;
  select * into t from teams where read_token = p_read_token;
  if not found then
    raise exception 'Unbekannter Mitlese-Link.' using errcode = 'P0001';
  end if;
  return ((team_state(t.code)::jsonb #- '{team,code}' #- '{team,readToken}')
          || jsonb_build_object('name', null))::json;
end $$;

grant execute on function member_state_by_team(text) to anon, authenticated;

-- ---------- Teamleitung bestimmen ----------
create or replace function admin_set_leader(p_pin text, p_team uuid, p_participant uuid) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  if not exists (select 1 from participants where id = p_participant and team_id = p_team) then
    raise exception 'Diese Person ist nicht in diesem Team.' using errcode='P0001';
  end if;
  update teams set leader_participant_id = p_participant where id = p_team;
  return admin_state(p_pin);
end $$;

grant execute on function admin_set_leader(text, uuid, uuid) to anon, authenticated;

-- Die Teamleitung gibt ab: an jemanden aus dem eigenen Team, nach Namen
create or replace function team_set_leader(p_code text, p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare t teams; v_id uuid;
begin
  t := team_by_code(p_code);
  select id into v_id from participants where team_id = t.id and name_key = norm(p_name);
  if v_id is null then
    raise exception 'Diese Person ist nicht in eurem Team.' using errcode='P0001';
  end if;
  update teams set leader_participant_id = v_id where id = t.id;
  return team_state(p_code);
end $$;

grant execute on function team_set_leader(text, text) to anon, authenticated;

-- ---------- admin_state: Fassung aus Nachtrag 7 plus readToken je Team ----------
create or replace function admin_state(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  return (select json_build_object(
    'status', g.status, 'startedAt', g.started_at, 'finishedAt', g.finished_at,
    'winnerTeamId', g.winner_team_id,
    'prizeCount', g.prize_count,
    'testMode', g.test_mode,
    'participants', coalesce((select json_agg(to_json(x)) from (
        select p.id, p.name, p.team_id as "teamId",
               (select t.name from teams t where t.id = p.team_id) as "teamName"
        from participants p order by p.name) x), '[]'::json),
    'stations', coalesce((select json_agg(to_json(s2)) from (
        select s.id, s.position, s.name, s.lat, s.lng, s.radius_m as "radiusM",
               s.location_hint as "locationHint", s.riddle, s.answer, s.digit
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
