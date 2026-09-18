-- ============================================================
--  STADTJAGD – Nachtrag 6: drei Koffer, Plätze statt eines Siegers
--
--  Bisher gewann das erste Team mit dem richtigen Koffer-Code, das Spiel
--  sprang sofort auf "finished", und alle anderen sahen "Ein anderes Team
--  war schneller". Jetzt gibt es mehrere Koffer mit absteigendem
--  Preisgeld (Vorgabe 3, game_state.prize_count). Alle Koffer haben
--  denselben Code; die Spielleitung steht dabei und gibt den passenden
--  Koffer nach dem Platz in der App frei.
--
--  - finishes: je Team der Platz und die Uhrzeit, zu der der Code stimmte.
--  - submit_final vergibt den nächsten freien Platz. Die Zeilensperre auf
--    game_state reiht gleichzeitige Eingaben hintereinander ein, place ist
--    zusätzlich unique: zwei Teams können nie denselben Platz bekommen.
--  - Das Spiel läuft weiter, bis die Spielleitung "Spiel beenden" drückt.
--    Platz 1 steht weiter in winner_team_id, damit Bestehendes nicht bricht.
--  - Nach dem Beenden nimmt submit_final keine Codes mehr an.
--
--  Einspielen: nach Nachtrag 5. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

create table if not exists finishes (
  team_id uuid primary key references teams(id) on delete cascade,
  place int not null unique check (place >= 1),
  finished_at timestamptz not null default now()
);
alter table finishes enable row level security;
revoke all on finishes from anon, authenticated;

alter table game_state add column if not exists prize_count int not null default 3
  check (prize_count between 0 and 16);

-- ---------- Koffer-Code eingeben ----------
create or replace function submit_final(p_code text, p_value text)
returns json language plpgsql security definer set search_path = public as $$
declare t teams; g game_state; v_total int; v_solved int; v_expected text; v_place int;
begin
  t := team_by_code(p_code);
  -- Schon im Ziel: der Platz bleibt, egal was jetzt eingegeben wird
  select place into v_place from finishes where team_id = t.id;

  if v_place is null then
    select * into g from game_state where id = 1;
    if g.status <> 'running' then
      return json_build_object('ok', false, 'won', false, 'message', 'Das Spiel läuft gerade nicht.',
        'state', team_state(p_code));
    end if;
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
                    then 'Platz ' || v_place || '! Zeigt diesen Bildschirm der Spielleitung am Koffer.'
                    else 'Platz ' || v_place || '. Ihr seid im Ziel, die Koffer sind schon vergeben.' end,
    'state', team_state(p_code));
end $$;

-- ---------- Team-Ansicht: Platz und übrige Koffer ----------
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
    'place', v_place,
    'prizeCount', g.prize_count,
    'prizesLeft', greatest(g.prize_count - v_done, 0),
    'winnerTeamId', g.winner_team_id,
    'isWinner', coalesce(v_place <= g.prize_count, false)
  );
end $$;

-- ---------- Öffentliche Ansicht: Rangliste nach Platz ----------
-- Achtung: Team-Codes sind hier absichtlich NICHT enthalten.
create or replace function public_state() returns json
language sql security definer set search_path = public as $$
  select json_build_object(
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

-- ---------- Spielleitung: Platz je Team ----------
create or replace function admin_state(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  return (select json_build_object(
    'status', g.status, 'startedAt', g.started_at, 'finishedAt', g.finished_at,
    'winnerTeamId', g.winner_team_id,
    'prizeCount', g.prize_count,
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
             from team_positions tp where tp.team_id = t.id) as position,
          (select f.place from finishes f where f.team_id = t.id) as place,
          (select f.finished_at from finishes f where f.team_id = t.id) as "finishedAt"
        from teams t order by t.name) y), '[]'::json)
  ) from game_state g where g.id = 1);
end $$;

-- ---------- Starten und Zurücksetzen leeren auch die Plätze ----------
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
  delete from finishes where true;
  update game_state set status = 'running', started_at = now(),
    finished_at = null, winner_team_id = null where id = 1;
  return json_build_object('warning',
    case when v_missing is null then null
         else 'Achtung: Station(en) ' || v_missing || ' haben keine Koordinaten.' end,
    'state', admin_state(p_pin));
end $$;

create or replace function admin_reset(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  delete from progress where true;
  delete from finishes where true;
  delete from team_positions where true;
  delete from position_log where true;
  update game_state set status = 'drawn', started_at = null, finished_at = null,
    winner_team_id = null where id = 1;
  return admin_state(p_pin);
end $$;

-- admin_draw und admin_clear_participants löschen die Teams, die Plätze
-- gehen per "on delete cascade" mit.

notify pgrst, 'reload schema';
