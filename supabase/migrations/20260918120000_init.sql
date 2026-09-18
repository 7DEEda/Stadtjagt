-- ============================================================
--  STADTJAGD – Datenbank für das digital geführte Geocaching
--  Einmal komplett im Supabase SQL-Editor ausführen.
--  Die gesamte Spiellogik liegt hier. Lösungen, Ziffern und der
--  Koffercode verlassen die Datenbank nie.
-- ============================================================

-- ---------- Aufräumen (macht das Skript wiederholbar) ----------
drop table if exists team_positions cascade;
drop table if exists progress cascade;
drop table if exists participants cascade;
drop table if exists teams cascade;
drop table if exists stations cascade;
drop table if exists game_state cascade;

-- ---------- Tabellen ----------
create table teams (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  code text not null unique,
  leader_participant_id uuid,
  created_at timestamptz not null default now()
);

create table participants (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  name_key text not null unique,
  team_id uuid references teams(id) on delete set null,
  created_at timestamptz not null default now()
);

create table stations (
  id uuid primary key default gen_random_uuid(),
  position int not null unique,
  name text not null,
  lat double precision,
  lng double precision,
  radius_m int not null default 50,
  location_hint text not null default '',
  riddle text not null default '',
  answer text not null default '',
  digit int not null default 0 check (digit between 0 and 9)
);

create table progress (
  team_id uuid not null references teams(id) on delete cascade,
  station_id uuid not null references stations(id) on delete cascade,
  checked_in_at timestamptz,
  solved_at timestamptz,
  failed_attempts int not null default 0,
  locked_until timestamptz,
  primary key (team_id, station_id)
);

create table team_positions (
  team_id uuid primary key references teams(id) on delete cascade,
  lat double precision not null,
  lng double precision not null,
  accuracy_m double precision,
  updated_at timestamptz not null default now()
);

create table game_state (
  id int primary key default 1 check (id = 1),
  status text not null default 'registration'
    check (status in ('registration','drawn','running','finished')),
  started_at timestamptz,
  finished_at timestamptz,
  winner_team_id uuid references teams(id) on delete set null,
  admin_pin text not null default '2026'
);

insert into game_state (id) values (1);

-- ---------- Rechte: Clients dürfen KEINE Tabelle direkt lesen ----------
alter table teams           enable row level security;
alter table participants    enable row level security;
alter table stations        enable row level security;
alter table progress        enable row level security;
alter table team_positions  enable row level security;
alter table game_state      enable row level security;
-- Keine Policies = kein Zugriff für anon/authenticated. Alles läuft über
-- die Funktionen weiter unten (security definer).

revoke all on all tables in schema public from anon, authenticated;

-- ---------- Hilfsfunktionen ----------
create or replace function norm(t text) returns text
language sql immutable as $$
  select regexp_replace(
    replace(replace(replace(replace(replace(replace(replace(
      lower(coalesce(t,'')),
      'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss'),'á','a'),'é','e'),'è','e'),
    '[^a-z0-9]+', '', 'g');
$$;

create or replace function dist_m(lat1 double precision, lng1 double precision,
                                  lat2 double precision, lng2 double precision)
returns double precision language sql immutable as $$
  select 2 * 6371000 * asin(least(1, sqrt(
    power(sin(radians(lat2-lat1)/2), 2) +
    cos(radians(lat1)) * cos(radians(lat2)) * power(sin(radians(lng2-lng1)/2), 2)
  )));
$$;

-- Team anhand des Codes holen
create or replace function team_by_code(p_code text) returns teams
language plpgsql security definer set search_path = public as $$
declare t teams;
begin
  select * into t from teams where upper(code) = upper(btrim(p_code));
  if not found then
    raise exception 'Unbekannter Team-Code.' using errcode = 'P0001';
  end if;
  return t;
end $$;

-- Aktuelle (erste ungelöste) Station eines Teams
create or replace function current_station(p_team uuid) returns stations
language sql security definer set search_path = public as $$
  select s.* from stations s
  left join progress pr on pr.station_id = s.id and pr.team_id = p_team
  where pr.solved_at is null
  order by s.position
  limit 1;
$$;

create or replace function require_admin(p_pin text) returns void
language plpgsql security definer set search_path = public as $$
begin
  if not exists (select 1 from game_state where id = 1 and admin_pin = btrim(coalesce(p_pin,''))) then
    raise exception 'Falsche PIN.' using errcode = 'P0001';
  end if;
end $$;

-- ---------- Öffentliche Ansicht ----------
-- Achtung: Team-Codes sind hier absichtlich NICHT enthalten.
create or replace function public_state() returns json
language sql security definer set search_path = public as $$
  select json_build_object(
    'status', g.status,
    'startedAt', g.started_at,
    'finishedAt', g.finished_at,
    'winnerTeamId', g.winner_team_id,
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
        select t.id as "teamId", t.name as "teamName",
          (select count(*) from progress pr where pr.team_id = t.id and pr.solved_at is not null) as solved,
          (select max(pr.solved_at) from progress pr where pr.team_id = t.id) as "lastSolvedAt",
          (g.winner_team_id = t.id) as "isWinner"
        from teams t
        order by (g.winner_team_id = t.id) desc,
                 (select count(*) from progress pr where pr.team_id = t.id and pr.solved_at is not null) desc,
                 (select max(pr.solved_at) from progress pr where pr.team_id = t.id) asc nulls last
      ) r), '[]'::json)
  ) from game_state g where g.id = 1;
$$;

create or replace function register_participant(p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare v_name text := btrim(regexp_replace(coalesce(p_name,''), '\s+', ' ', 'g'));
begin
  if length(v_name) < 2 or length(v_name) > 60 then
    raise exception 'Bitte einen Namen mit 2 bis 60 Zeichen eingeben.' using errcode='P0001';
  end if;
  if (select status from game_state where id=1) <> 'registration' then
    raise exception 'Die Anmeldung ist geschlossen. Melde dich bei der Spielleitung.' using errcode='P0001';
  end if;
  if exists (select 1 from participants where name_key = norm(v_name)) then
    raise exception 'Dieser Name ist schon angemeldet. Nimm z. B. den Nachnamen dazu.' using errcode='P0001';
  end if;
  insert into participants(name, name_key) values (v_name, norm(v_name));
  return json_build_object('name', v_name, 'count', (select count(*) from participants));
end $$;

create or replace function lookup_participant(p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare v participants; t teams;
begin
  select * into v from participants where name_key = norm(p_name);
  if not found then return json_build_object('found', false); end if;
  select * into t from teams where id = v.team_id;
  return json_build_object(
    'found', true, 'name', v.name,
    'team', case when t.id is null then null else json_build_object(
      'name', t.name,
      'leaderName', (select p.name from participants p where p.id = t.leader_participant_id),
      'members', coalesce((select json_agg(p2.name order by p2.name)
                           from participants p2 where p2.team_id = t.id), '[]'::json)
    ) end);
end $$;

-- ---------- Team-Ansicht ----------
create or replace function team_state(p_code text) returns json
language plpgsql security definer set search_path = public as $$
declare t teams; g game_state; cur stations; row_p progress;
        v_total int; v_solved int; v_sum int; v_all boolean;
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

  return json_build_object(
    'team', json_build_object('id', t.id, 'name', t.name, 'code', t.code,
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
    'winnerTeamId', g.winner_team_id,
    'isWinner', g.winner_team_id = t.id
  );
end $$;

create or replace function check_in(p_code text, p_lat double precision,
                                    p_lng double precision, p_acc double precision)
returns json language plpgsql security definer set search_path = public as $$
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
  if cur.lat is null or cur.lng is null then
    return json_build_object('ok', false, 'message',
      'Für diese Station sind noch keine Koordinaten gesetzt. Bitte die Spielleitung fragen.',
      'state', team_state(p_code));
  end if;
  d := dist_m(p_lat, p_lng, cur.lat, cur.lng);
  tol := cur.radius_m + least(greatest(coalesce(p_acc,0),0), 25);
  if d > tol then
    return json_build_object('ok', false, 'distance', round(d::numeric,0),
      'message', 'Noch nicht am Ziel: ' || round(d::numeric,0) || ' m entfernt.',
      'state', team_state(p_code));
  end if;
  insert into progress(team_id, station_id, checked_in_at)
  values (t.id, cur.id, now())
  on conflict (team_id, station_id) do update set checked_in_at = coalesce(progress.checked_in_at, now());
  return json_build_object('ok', true, 'distance', round(d::numeric,0),
    'message', 'Angekommen. Das Rätsel ist frei.', 'state', team_state(p_code));
end $$;

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
  select * into row_p from progress where team_id = t.id and station_id = cur.id;
  if row_p.checked_in_at is null then
    return json_build_object('ok', false, 'message', 'Erst am Ort einchecken, dann gibt es das Rätsel.',
      'state', team_state(p_code));
  end if;
  if row_p.locked_until is not null and row_p.locked_until > now() then
    return json_build_object('ok', false,
      'message', 'Denkpause: noch ' || ceil(extract(epoch from row_p.locked_until - now())) || ' Sekunden.',
      'state', team_state(p_code));
  end if;

  if norm(p_answer) = norm(cur.answer) and norm(cur.answer) <> '' then
    update progress set solved_at = now(), failed_attempts = 0, locked_until = null
      where team_id = t.id and station_id = cur.id;
    return json_build_object('ok', true, 'message', 'Richtig. Eine Ziffer ist frei.', 'state', team_state(p_code));
  end if;

  v_attempts := case when row_p.locked_until is not null and row_p.locked_until <= now()
                     then 1 else row_p.failed_attempts + 1 end;
  v_locked := v_attempts >= 3;
  update progress
    set failed_attempts = case when v_locked then 0 else v_attempts end,
        locked_until    = case when v_locked then now() + interval '2 minutes' else null end
    where team_id = t.id and station_id = cur.id;
  return json_build_object('ok', false,
    'message', case when v_locked then 'Dreimal falsch. Zwei Minuten Denkpause für euer Team.'
                    else 'Leider falsch. Noch ' || (3 - v_attempts) || ' Versuch(e).' end,
    'state', team_state(p_code));
end $$;

create or replace function submit_final(p_code text, p_value text)
returns json language plpgsql security definer set search_path = public as $$
declare t teams; g game_state; v_total int; v_solved int; v_expected text; v_won boolean;
begin
  t := team_by_code(p_code);
  select * into g from game_state where id = 1;
  select count(*) into v_total from stations;
  select count(*) into v_solved from progress where team_id = t.id and solved_at is not null;
  if v_total = 0 or v_solved <> v_total then
    return json_build_object('ok', false, 'won', false, 'message', 'Ihr habt noch nicht alle Ziffern.',
      'state', team_state(p_code));
  end if;
  select string_agg(s.digit::text, '' order by s.position) into v_expected from stations s;
  v_expected := v_expected || ((select sum(digit) from stations) % 10)::text;

  if regexp_replace(coalesce(p_value,''), '[^0-9]', '', 'g') <> v_expected then
    return json_build_object('ok', false, 'won', false,
      'message', 'Der Koffer bleibt zu. Prüft die letzte Ziffer.', 'state', team_state(p_code));
  end if;

  -- Sieger atomar: das Update greift nur, wenn noch kein Sieger eingetragen ist
  update game_state set winner_team_id = t.id, status = 'finished', finished_at = now()
    where id = 1 and winner_team_id is null;
  v_won := found;
  if not v_won then
    select (winner_team_id = t.id) into v_won from game_state where id = 1;
  end if;
  return json_build_object('ok', true, 'won', v_won,
    'message', case when v_won then 'Koffer offen. Ihr habt gewonnen!'
                    else 'Code korrekt, aber ein anderes Team war schneller.' end,
    'state', team_state(p_code));
end $$;

-- Standortmeldung für die Live-Karte (nur während des Spiels)
create or replace function report_position(p_code text, p_lat double precision,
                                           p_lng double precision, p_acc double precision)
returns void language plpgsql security definer set search_path = public as $$
declare t teams;
begin
  if (select status from game_state where id = 1) <> 'running' then return; end if;
  t := team_by_code(p_code);
  insert into team_positions(team_id, lat, lng, accuracy_m, updated_at)
  values (t.id, p_lat, p_lng, p_acc, now())
  on conflict (team_id) do update
    set lat = excluded.lat, lng = excluded.lng,
        accuracy_m = excluded.accuracy_m, updated_at = now();
end $$;

-- ---------- Spielleitung ----------
create or replace function admin_state(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  return (select json_build_object(
    'status', g.status, 'startedAt', g.started_at, 'finishedAt', g.finished_at,
    'winnerTeamId', g.winner_team_id,
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
        select t.id, t.name, t.code,
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
             from team_positions tp where tp.team_id = t.id) as position
        from teams t order by t.name) y), '[]'::json)
  ) from game_state g where g.id = 1);
end $$;

create or replace function admin_draw(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
declare v_count int; v_teams int; v_animals text[] := array[
    'Fuchs','Dachs','Luchs','Eule','Biber','Falke','Hirsch','Otter','Wolf','Specht','Igel','Marder',
    'Reiher','Kranich','Iltis','Steinbock'];
        v_status text; i int; v_id uuid; v_ids uuid[]; v_code text;
begin
  perform require_admin(p_pin);
  select status into v_status from game_state where id = 1;
  if v_status in ('running','finished') then
    raise exception 'Nach dem Start kann nicht neu ausgelost werden.' using errcode='P0001';
  end if;
  select count(*) into v_count from participants;
  if v_count < 2 then raise exception 'Es sind noch zu wenige Personen angemeldet.' using errcode='P0001'; end if;

  update participants set team_id = null;
  delete from teams;

  v_teams := greatest(1, round(v_count / 10.0)::int);
  v_teams := least(v_teams, array_length(v_animals, 1));

  for i in 1..v_teams loop
    loop
      v_code := upper(v_animals[i]) || '-' || lpad((floor(random()*9000)+1000)::int::text, 4, '0');
      exit when not exists (select 1 from teams where code = v_code);
    end loop;
    insert into teams(name, code) values (v_animals[i], v_code) returning id into v_id;
    v_ids := array_append(v_ids, v_id);
  end loop;

  -- zufällig verteilen, reihum
  with shuffled as (
    select p.id, row_number() over (order by random()) - 1 as rn from participants p
  )
  update participants p set team_id = v_ids[(s.rn % v_teams) + 1]
  from shuffled s where s.id = p.id;

  -- Teamleitung auslosen
  update teams t set leader_participant_id = (
    select p.id from participants p where p.team_id = t.id order by random() limit 1);

  update game_state set status = 'drawn' where id = 1;
  return admin_state(p_pin);
end $$;

create or replace function admin_start(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
declare v_missing text;
begin
  perform require_admin(p_pin);
  if not exists (select 1 from teams) then
    raise exception 'Erst Teams auslosen.' using errcode='P0001';
  end if;
  select string_agg(position::text, ', ' order by position) into v_missing
    from stations where lat is null or lng is null;
  update game_state set status = 'running', started_at = now(),
    finished_at = null, winner_team_id = null where id = 1;
  return json_build_object('warning',
    case when v_missing is null then null
         else 'Achtung: Station(en) ' || v_missing || ' haben keine Koordinaten.' end,
    'state', admin_state(p_pin));
end $$;

create or replace function admin_finish(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  update game_state set status = 'finished', finished_at = now() where id = 1;
  delete from team_positions;   -- Standortdaten nach dem Spiel löschen
  return admin_state(p_pin);
end $$;

create or replace function admin_reset(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  delete from progress;
  delete from team_positions;
  update game_state set status = 'drawn', started_at = null, finished_at = null,
    winner_team_id = null where id = 1;
  return admin_state(p_pin);
end $$;

create or replace function admin_clear_positions(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  delete from team_positions;
  return admin_state(p_pin);
end $$;

create or replace function admin_add_participant(p_pin text, p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare v_name text := btrim(regexp_replace(coalesce(p_name,''), '\s+', ' ', 'g'));
        v_team uuid;
begin
  perform require_admin(p_pin);
  if length(v_name) < 2 then raise exception 'Bitte einen Namen eingeben.' using errcode='P0001'; end if;
  if exists (select 1 from participants where name_key = norm(v_name)) then
    raise exception 'Dieser Name ist schon angemeldet.' using errcode='P0001';
  end if;
  select t.id into v_team from teams t
    left join participants p on p.team_id = t.id
    group by t.id order by count(p.id) asc limit 1;
  insert into participants(name, name_key, team_id) values (v_name, norm(v_name), v_team);
  return admin_state(p_pin);
end $$;

create or replace function admin_rename_participant(p_pin text, p_id uuid, p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare v_name text := btrim(regexp_replace(coalesce(p_name,''), '\s+', ' ', 'g'));
begin
  perform require_admin(p_pin);
  update participants set name = v_name, name_key = norm(v_name) where id = p_id;
  return admin_state(p_pin);
end $$;

create or replace function admin_delete_participant(p_pin text, p_id uuid) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  update teams set leader_participant_id = null where leader_participant_id = p_id;
  delete from participants where id = p_id;
  update teams t set leader_participant_id = (
      select p.id from participants p where p.team_id = t.id order by random() limit 1)
    where t.leader_participant_id is null;
  return admin_state(p_pin);
end $$;

create or replace function admin_save_station(
  p_pin text, p_id uuid, p_name text, p_lat double precision, p_lng double precision,
  p_radius int, p_hint text, p_riddle text, p_answer text, p_digit int) returns json
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
    digit = greatest(0, least(9, coalesce(p_digit, 0)))
  where id = p_id;
  return admin_state(p_pin);
end $$;

create or replace function admin_unlock_station(p_pin text, p_team uuid) returns json
language plpgsql security definer set search_path = public as $$
declare cur stations;
begin
  perform require_admin(p_pin);
  cur := current_station(p_team);
  if cur.id is null then raise exception 'Dieses Team hat alle Stationen gelöst.' using errcode='P0001'; end if;
  insert into progress(team_id, station_id, checked_in_at) values (p_team, cur.id, now())
    on conflict (team_id, station_id) do update set checked_in_at = coalesce(progress.checked_in_at, now());
  return admin_state(p_pin);
end $$;

create or replace function admin_set_pin(p_pin text, p_new text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  if length(btrim(coalesce(p_new,''))) < 4 then
    raise exception 'Die neue PIN braucht mindestens 4 Zeichen.' using errcode='P0001';
  end if;
  update game_state set admin_pin = btrim(p_new) where id = 1;
  return admin_state(btrim(p_new));
end $$;

-- ---------- Ausführungsrechte ----------
revoke all on function norm(text), dist_m(double precision,double precision,double precision,double precision),
  team_by_code(text), current_station(uuid), require_admin(text) from public, anon, authenticated;

grant execute on function
  public_state(), register_participant(text), lookup_participant(text),
  team_state(text), check_in(text,double precision,double precision,double precision),
  submit_answer(text,text), submit_final(text,text),
  report_position(text,double precision,double precision,double precision),
  admin_state(text), admin_draw(text), admin_start(text), admin_finish(text), admin_reset(text),
  admin_clear_positions(text), admin_add_participant(text,text),
  admin_rename_participant(text,uuid,text), admin_delete_participant(text,uuid),
  admin_save_station(text,uuid,text,double precision,double precision,int,text,text,text,int),
  admin_unlock_station(text,uuid), admin_set_pin(text,text)
to anon, authenticated;

-- ---------- Platzhalter-Stationen ----------
insert into stations(position, name, location_hint, riddle, answer, digit) values
 (1,'Alter Marktplatz','Sucht den Brunnen, an dem vier Löwen Wasser speien.','Wie viele Stufen führen zum Brunnenrand hinauf?','3',4),
 (2,'Stadtbibliothek','Wo Bücher wohnen, aber niemand laut sein darf.','Welche Jahreszahl steht über dem Haupteingang?','1908',7),
 (3,'Steinbrücke','Folgt dem Fluss, bis ihr trockenen Fußes auf Stein ans andere Ufer kommt.','Wie viele Bögen hat die Brücke?','5',2),
 (4,'Aussichtsturm','Der höchste Punkt der Stadt, den man ohne Seilbahn erreicht.','Welches Tier sitzt oben auf der Wetterfahne?','Hahn',9),
 (5,'Rosengarten (Koffer)','Wo die Sonne die Uhrzeit schreibt und es nach Blumen duftet.','Wie viele Bänke stehen rund um die Sonnenuhr?','6',1);
