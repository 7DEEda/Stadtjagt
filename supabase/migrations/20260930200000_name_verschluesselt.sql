-- ============================================================
--  STADTJAGD – Nachtrag 26: Stationsname entschlüsselt sich mit der Annäherung
--
--  Der Name der nächsten Station steht auf dem Handy zuerst als flimmernde
--  Zeichen da und löst sich auf, je näher das Team kommt; erst dann erscheint
--  auch der Ortshinweis. Mockups: mockups/name-verschluesselt.html und
--  mockups/station-karte.html.
--
--  Je Station zwei Entfernungen: reveal_start_m (hier beginnt es) und
--  reveal_clear_m (ab hier ganz lesbar). Beide leer heißt: nicht verschlüsselt,
--  wie bisher. Die Spielleitung stellt sie im Reiter Stationen auf einer Karte ein.
--
--  Entscheidung Friedrich, 30.09.2026: nur die Anzeige. Der Name geht weiter
--  im Klartext ans Handy, das Handy verschleiert ihn selbst nach seinem eigenen
--  Standort. Wer in die Daten schaut, kann ihn lesen; das ist in Kauf genommen.
--
--  team_state und admin_state: Fassungen aus Nachtrag 25 plus die beiden Felder.
--  admin_save_station: Fassung aus Nachtrag 17 plus zwei Parameter. Die alte
--  Fassung mit elf Parametern wird entfernt, sonst gäbe es zwei gleichnamige
--  Funktionen und die Schnittstelle wüsste nicht, welche gemeint ist.
--
--  Einspielen: nach Nachtrag 25. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

alter table stations add column if not exists reveal_start_m int;
alter table stations add column if not exists reveal_clear_m int;
alter table stations drop constraint if exists stations_reveal_pruefen;
alter table stations add constraint stations_reveal_pruefen check (
  (reveal_start_m is null and reveal_clear_m is null)
  or (reveal_clear_m > 0 and reveal_start_m > reveal_clear_m and reveal_start_m <= 5000));

drop function if exists admin_save_station(text, uuid, text, double precision, double precision, int, text, text, text, int, text);

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
  update stations set
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

grant execute on function admin_save_station(text, uuid, text, double precision, double precision, int, text, text, text, int, text, int, int)
  to anon, authenticated;

-- ---------- team_state (Nachtrag 25) plus revealStartM und revealClearM an der Station ----------
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
  select count(*) into v_solved from progress where team_id = t.id and solved_at is not null;
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

-- ---------- admin_state (Nachtrag 25) plus die beiden Felder je Station ----------
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
               s.reveal_start_m as "revealStartM", s.reveal_clear_m as "revealClearM"
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
