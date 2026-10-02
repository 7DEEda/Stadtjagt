-- Nachtrag 28: Teststation. Spec: docs/superpowers/specs/2026-10-02-teststation-kompass-waechter-design.md, Teil 1.
-- stations heißt jetzt stations_alle (echte Route und Teststation). Die Sicht stations zeigt nur die aktive
-- Route; alle Spielfunktionen lesen weiter stations.
-- ACHTUNG für spätere Migrationen: die Sicht ist "select *" zum Zeitpunkt des Anlegens. Wer eine Spalte an
-- stations_alle anfügt, MUSS danach
--   create or replace view stations as select * from stations_alle where route = aktive_route();
-- ausführen, sonst passt current_station (liefert den Typ der Sicht) nicht mehr und das Spiel steht.
-- Wird die Sicht einmal gelöscht und neu angelegt (statt "or replace"), danach unbedingt
--   revoke all on stations from anon, authenticated;
-- Supabase gibt neuen Objekten Leserechte, dann wären Rätsel und Lösungen ohne PIN lesbar.

alter table stations rename to stations_alle;
alter table stations_alle add column route text not null default 'echt';
alter table stations_alle add constraint stations_route_pruefen check (route in ('echt', 'test'));
alter table stations_alle drop constraint stations_position_key;
alter table stations_alle add constraint stations_route_position_key unique (route, position);

create or replace function aktive_route() returns text
language sql stable security definer set search_path = public as $$
  select case when coalesce((select test_mode from game_state where id = 1), false)
                   and exists (select 1 from stations_alle where route = 'test')
              then 'test' else 'echt' end
$$;

create view stations as select * from stations_alle where route = aktive_route();
-- Sichten haben keine Zeilenrechte: ohne das hier könnte jede und jeder Rätsel und Lösungen lesen
revoke all on stations from anon, authenticated;
revoke all on function aktive_route() from public, anon, authenticated;

-- current_station lieferte den Zeilentyp der Tabelle (jetzt stations_alle); neu mit dem Typ der Sicht,
-- damit Tabelle und Sicht nicht auseinanderlaufen. Aufrufer sind plpgsql und hängen nicht daran.
drop function current_station(uuid);
-- admin_photo bekommt p_route dazu: alte Fassung weg, sonst gäbe es zwei
drop function admin_photo(text, uuid, int, boolean);
create function current_station(p_team uuid) returns stations
language sql security definer set search_path = public as $$
  select s.* from stations s
  left join progress pr on pr.station_id = s.id and pr.team_id = p_team
  where pr.solved_at is null
  order by s.position
  limit 1;
$$;

insert into stations_alle (route, position, name, lat, lng, radius_m, location_hint, riddle, answer, digit, tip)
values ('test', 1, 'EDEKA Grenzallee', 52.470116, 13.462131, 50, 'Ortshinweis folgt', 'Rätsel folgt', '', 1, '');

-- ---------- team_state (aus 20261001120000_zahlenantwort.sql, für die Teststation angepasst) ----------
create or replace function team_state(p_code text) returns json
language plpgsql security definer set search_path = public as $$
declare t teams; g game_state; cur stations; row_p progress;
        v_total int; v_solved int; v_sum int; v_all boolean; v_place int; v_done int;
        v_pend stations; v_ersetzbar int;
begin
  t := team_by_code(p_code);
  select * into g from game_state where id = 1;
  -- Nachtrag 25: fällige Fotos verschwinden beim nächsten Abruf
  delete from station_photos where (select photos_delete_on from game_state where id = 1) <= current_date;
  select count(*) into v_total from stations;
  select count(*) into v_solved from progress pr join stations s on s.id = pr.station_id where pr.team_id = t.id and pr.solved_at is not null;
  select coalesce(sum(s.digit),0) into v_sum from stations s
    join progress pr on pr.station_id = s.id and pr.team_id = t.id and pr.solved_at is not null;
  -- Nachtrag 25: niedrigste gelöste Station ohne Gruppenfoto. Solange eine offen ist, hält die App
  -- deren Ziffer zurück und zeigt den Selfie-Schritt. Zeitmessung und Rangliste hängen weiter an solved_at.
  if g.selfie_on then
    select s.* into v_pend from stations s
      join progress pr on pr.station_id = s.id and pr.team_id = t.id
      where pr.solved_at is not null and pr.selfie_at is null order by s.position limit 1;
  end if;
  -- Ersetzen darf man das Foto der zuletzt gelösten Station, bis an einer späteren eingecheckt ist
  select max(s.position) into v_ersetzbar from stations s
    join progress pr on pr.station_id = s.id and pr.team_id = t.id where pr.solved_at is not null;
  if exists (select 1 from progress pr join stations s on s.id = pr.station_id
             where pr.team_id = t.id and s.position > v_ersetzbar and pr.checked_in_at is not null) then
    v_ersetzbar := null;
  end if;
  v_all := v_total > 0 and v_solved = v_total and v_pend.id is null;
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
               case when pr.solved_at is not null and (not g.selfie_on or pr.selfie_at is not null)
                    then s.digit else null end as d
        from stations s left join progress pr on pr.station_id = s.id and pr.team_id = t.id
      ) q),
    'finalDigit', case when v_all then v_sum % 10 else null end,
    'station', case when cur.id is null or g.status <> 'running' then null else json_build_object(
        'position', cur.position, 'name', cur.name, 'locationHint', cur.location_hint,
        'lat', cur.lat, 'lng', cur.lng, 'radiusM', cur.radius_m,
        -- Nachtrag 26: ab wann sich der Name auf dem Handy entschlüsselt (null = sofort lesbar)
        'revealStartM', cur.reveal_start_m, 'revealClearM', cur.reveal_clear_m,
        -- Nachtrag 27: Lösung nur aus Ziffern (auch mehrere, mit | getrennt): das Handy zeigt die Zifferntastatur.
        -- Verrät nur, dass eine Zahl gesucht ist, das sagt das Rätsel meist ohnehin.
        'numeric', btrim(cur.answer) ~ '^[0-9]+( *[|] *[0-9]+)*$',
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
    'testMode', g.test_mode,
    'selfie', json_build_object(
      'on', g.selfie_on,
      'pending', case when v_pend.id is null then null
                      else json_build_object('position', v_pend.position, 'name', v_pend.name) end,
      'replaceable', case when g.selfie_on then v_ersetzbar else null end,
      'deleteOn', g.photos_delete_on,
      'photos', coalesce((select json_agg(json_build_object('position', s.position, 'takenAt', ph.taken_at)
                                          order by s.position)
                          from station_photos ph join stations s on s.id = ph.station_id
                          where ph.team_id = t.id), '[]'::json))
  );
end $$;

-- ---------- submit_final (aus 20260919030000_wasserdicht.sql, für die Teststation angepasst) ----------
create or replace function submit_final(p_code text, p_value text,
                                        p_lat double precision default null,
                                        p_lng double precision default null,
                                        p_acc double precision default null)
returns json language plpgsql security definer set search_path = public as $$
declare t teams; g game_state; v_total int; v_solved int; v_expected text; v_place int;
        ziel stations; d double precision; tol double precision;
begin
  t := team_by_code(p_code);
  select place into v_place from finishes where team_id = t.id;

  if v_place is null then
    select * into g from game_state where id = 1;
    if g.status <> 'running' then
      return json_build_object('ok', false, 'won', false, 'message', 'Das Spiel läuft gerade nicht.',
        'state', team_state(p_code));
    end if;
    select count(*) into v_total from stations;
    select count(*) into v_solved from progress pr join stations s on s.id = pr.station_id where pr.team_id = t.id and pr.solved_at is not null;
    if v_total = 0 or v_solved <> v_total then
      return json_build_object('ok', false, 'won', false, 'message', 'Ihr habt noch nicht alle Ziffern.',
        'state', team_state(p_code));
    end if;

    -- Am Koffer stehen: gleiche Regel wie beim Check-in, im Testmodus nicht
    if not g.test_mode then
      select * into ziel from stations order by position desc limit 1;
      if ziel.lat is not null and ziel.lng is not null then
        if p_lat is null or p_lng is null then
          return json_build_object('ok', false, 'won', false,
            'message', 'Ohne Standort kein Koffer. Bitte GPS freigeben.', 'state', team_state(p_code));
        end if;
        d := dist_m(p_lat, p_lng, ziel.lat, ziel.lng);
        tol := ziel.radius_m + least(greatest(coalesce(p_acc,0),0), 25);
        if d > tol then
          return json_build_object('ok', false, 'won', false, 'distance', round(d::numeric,0),
            'message', 'Den Code gebt ihr am Koffer ein: noch ' || round(d::numeric,0) || ' m bis dahin.',
            'state', team_state(p_code));
        end if;
      end if;
    end if;

    select string_agg(s.digit::text, '' order by s.position) into v_expected from stations s;
    v_expected := v_expected || ((select sum(digit) from stations) % 10)::text;
    if regexp_replace(coalesce(p_value,''), '[^0-9]', '', 'g') <> v_expected then
      return json_build_object('ok', false, 'won', false,
        'message', 'Der Koffer bleibt zu. Prüft die letzte Ziffer.', 'state', team_state(p_code));
    end if;

    -- Platz vergeben. Die Sperre lässt gleichzeitige Eingaben warten, bis die
    -- vorige fertig ist; danach sieht die nächste deren Platz schon.
    perform 1 from game_state where id = 1 for update;
    select place into v_place from finishes where team_id = t.id;   -- doppelt abgeschickt?
    if v_place is null then
      select coalesce(max(place), 0) + 1 into v_place from finishes;
      insert into finishes(team_id, place) values (t.id, v_place);
      if v_place = 1 then
        update game_state set winner_team_id = t.id where id = 1;
      end if;
    end if;
  end if;

  select * into g from game_state where id = 1;
  return json_build_object('ok', true, 'won', v_place <= g.prize_count, 'place', v_place,
    'message', case when v_place <= g.prize_count
                    then 'Der Koffer ist offen. Platz ' || v_place || '!'
                    else 'Richtig, aber die Koffer sind vergeben. Ihr seid auf Platz ' || v_place || '.' end,
    'state', team_state(p_code));
end $$;

-- ---------- public_state (aus 20260930180000_gruppenselfie.sql, für die Teststation angepasst) ----------
create or replace function public_state() returns json
language sql security definer set search_path = public as $$
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
$$;

-- ---------- admin_state (aus 20260930200000_name_verschluesselt.sql, für die Teststation angepasst) ----------
create or replace function admin_state(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  delete from station_photos where (select photos_delete_on from game_state where id = 1) <= current_date;
  return (select json_build_object(
    'background', g.background, 'status', g.status, 'startedAt', g.started_at, 'finishedAt', g.finished_at,
    'durationMin', g.duration_min,
    'endsAt', case when g.started_at is null then null else g.started_at + make_interval(mins => g.duration_min) end,
    'caseHint', g.case_hint,
    'winnerTeamId', g.winner_team_id,
    'prizeCount', g.prize_count,
    'testMode', g.test_mode,
    'selfieOn', g.selfie_on,
    'photosDeleteOn', g.photos_delete_on,
    'photoCount', (select count(*) from station_photos),
    'participants', coalesce((select json_agg(to_json(x)) from (
        select p.id, p.name, p.team_id as "teamId",
               (select t.name from teams t where t.id = p.team_id) as "teamName"
        from participants p order by p.name) x), '[]'::json),
    'stations', coalesce((select json_agg(to_json(s2)) from (
        select s.id, s.position, s.name, s.lat, s.lng, s.radius_m as "radiusM",
               s.location_hint as "locationHint", s.riddle, s.answer, s.digit, s.tip,
               s.reveal_start_m as "revealStartM", s.reveal_clear_m as "revealClearM", s.route
        from stations_alle s where s.route = 'echt' order by s.position) s2), '[]'::json),
    'testStation', (select to_json(s3) from (
        select s.id, s.position, s.name, s.lat, s.lng, s.radius_m as "radiusM",
               s.location_hint as "locationHint", s.riddle, s.answer, s.digit, s.tip,
               s.reveal_start_m as "revealStartM", s.reveal_clear_m as "revealClearM", s.route
        from stations_alle s where s.route = 'test' order by s.position limit 1) s3),
    'route', aktive_route(),
    'aktiveStationen', coalesce((select json_agg(to_json(s4)) from (
        select s.id, s.position, s.name, s.lat, s.lng, s.radius_m as "radiusM"
        from stations s order by s.position) s4), '[]'::json),
    'caseCode', (select string_agg(s.digit::text, '' order by s.position) from stations s)
                || ((select coalesce(sum(digit),0) from stations) % 10)::text,
    'teams', coalesce((select json_agg(to_json(y)) from (
        select t.id, t.name, t.code, t.read_token as "readToken",
          t.leader_participant_id as "leaderId",
          (select p.name from participants p where p.id = t.leader_participant_id) as "leaderName",
          (select count(*) from participants p where p.team_id = t.id) as "memberCount",
          coalesce((select json_agg(p2.name order by p2.name)
                    from participants p2 where p2.team_id = t.id), '[]'::json) as members,
          (select count(*) from progress pr join stations s on s.id = pr.station_id where pr.team_id = t.id and pr.solved_at is not null) as solved,
          (select s.position from stations s
             left join progress pr on pr.station_id = s.id and pr.team_id = t.id
             where pr.solved_at is null order by s.position limit 1) as "currentPosition",
          -- Nachtrag 21: seit wann das Team an seiner aktuellen Station steht (null = noch unterwegs)
          -- und wann es zuletzt eine Station gelöst hat; daraus zeigt der Reiter Teams "an Station 2 seit 14 min"
          (select pr.checked_in_at from stations s
             left join progress pr on pr.station_id = s.id and pr.team_id = t.id
             where pr.solved_at is null order by s.position limit 1) as "checkedInAt",
          (select max(pr.solved_at) from progress pr join stations s on s.id = pr.station_id where pr.team_id = t.id) as "lastSolvedAt",
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

-- ---------- admin_save_station (aus 20260930200000_name_verschluesselt.sql, für die Teststation angepasst) ----------
create or replace function admin_save_station(
  p_pin text, p_id uuid, p_name text, p_lat double precision, p_lng double precision,
  p_radius int, p_hint text, p_riddle text, p_answer text, p_digit int, p_tip text default '',
  p_reveal_start int default null, p_reveal_clear int default null) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  if (p_reveal_start is null) <> (p_reveal_clear is null) then
    raise exception 'Für das Entschlüsseln braucht es beide Entfernungen oder keine.' using errcode='P0001';
  end if;
  if p_reveal_start is not null and (p_reveal_clear <= 0 or p_reveal_start <= p_reveal_clear or p_reveal_start > 5000) then
    raise exception 'Der Name muss weiter draußen beginnen, als er lesbar wird (höchstens 5000 m).' using errcode='P0001';
  end if;
  update stations_alle set
    name = coalesce(nullif(btrim(p_name),''), name),
    lat = p_lat, lng = p_lng,
    radius_m = greatest(5, coalesce(p_radius, 50)),
    location_hint = coalesce(p_hint, ''),
    riddle = coalesce(p_riddle, ''),
    answer = coalesce(p_answer, ''),
    digit = greatest(0, least(9, coalesce(p_digit, 0))),
    tip = btrim(coalesce(p_tip, '')),
    reveal_start_m = p_reveal_start, reveal_clear_m = p_reveal_clear
  where id = p_id;
  return admin_state(p_pin);
end $$;

-- ---------- admin_photos (aus 20260930180000_gruppenselfie.sql, für die Teststation angepasst) ----------
create or replace function admin_photos(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  return coalesce((select json_agg(to_json(x)) from (
    select t.id as "teamId", t.name as "teamName", s.position, s.name as "stationName", s.route, ph.taken_at as "takenAt"
    from station_photos ph join teams t on t.id = ph.team_id join stations_alle s on s.id = ph.station_id
    order by t.name, s.route, s.position) x), '[]'::json);
end $$;

-- ---------- admin_photo (aus 20260930180000_gruppenselfie.sql, für die Teststation angepasst) ----------
create or replace function admin_photo(p_pin text, p_team uuid, p_position int, p_full boolean default false, p_route text default 'echt')
returns json language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  return json_build_object('data', (select encode(case when p_full then ph.photo else ph.thumb end, 'base64')
          from station_photos ph join stations_alle s on s.id = ph.station_id and s.route = coalesce(p_route, 'echt')
          where ph.team_id = p_team and s.position = p_position));
end $$;

-- ---------- admin_draw (aus 20260919100000_bugjagd.sql, für die Teststation angepasst) ----------
create or replace function admin_draw(p_pin text, p_teams int default null, p_size int default null)
returns json language plpgsql security definer set search_path = public as $$
declare v_count int; v_teams int; v_animals text[] := array[
    'Fuchs','Wolf','Eule','Tiger','Panda','Einhorn','Flamingo','Pinguin',
    'Delfin','Adler','Igel','Otter','Krake','Biber','Koala','Drache'];
        v_max int; v_status text; i int; v_id uuid; v_ids uuid[]; v_code text;
begin
  perform require_admin(p_pin);
  -- Sperre gleich zu Beginn: eine zweite Auslosung wartet und ersetzt dann
  -- die Teams der ersten, Anmeldungen (for share) warten oder sind schon durch.
  select status into v_status from game_state where id = 1 for update;
  if v_status in ('running','finished') then
    raise exception 'Nach dem Start kann nicht neu ausgelost werden.' using errcode='P0001';
  end if;
  select count(*) into v_count from participants;
  if v_count < (case when (select test_mode from game_state where id = 1) then 1 else 2 end) then raise exception 'Es sind noch zu wenige Personen angemeldet.' using errcode='P0001'; end if;

  -- Wie viele Teams? Angabe schlägt Faustregel.
  v_max := least(v_count, array_length(v_animals, 1));
  if p_teams is not null and p_teams > 0 then
    v_teams := p_teams;
  elsif p_size is not null and p_size > 0 then
    v_teams := ceil(v_count::numeric / p_size)::int;
  else
    v_teams := round(v_count / 10.0)::int;      -- wie bisher, etwa zehn pro Team
  end if;
  v_teams := greatest(1, least(v_teams, v_max));

  update participants set team_id = null where team_id is not null;
  delete from teams where true;

  for i in 1..v_teams loop
    loop
      v_code := upper(v_animals[i]) || '-' || lpad((floor(random()*9000)+1000)::int::text, 4, '0');
      exit when not exists (select 1 from teams where code = v_code);
    end loop;
    insert into teams(name, code) values (v_animals[i], v_code) returning id into v_id;
    v_ids := array_append(v_ids, v_id);
  end loop;

  -- zufällig verteilen, reihum, damit die Teams gleich groß werden
  with shuffled as (
    select p.id, row_number() over (order by random()) - 1 as rn from participants p
  )
  update participants p set team_id = v_ids[(s.rn % v_teams) + 1]
  from shuffled s where s.id = p.id;

  -- Teamleitung auslosen
  update teams t set leader_participant_id = (
    select p.id from participants p where p.team_id = t.id order by random() limit 1)
    where true;

  update game_state set status = 'drawn' where id = 1;
  return admin_state(p_pin);
end $$;

grant execute on function admin_photo(text, uuid, int, boolean, text) to anon, authenticated;

notify pgrst, 'reload schema';
