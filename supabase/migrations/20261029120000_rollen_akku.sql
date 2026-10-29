-- Rollen und Akku, 29.10.2026 (Plan docs/superpowers/plans/2026-10-29-rollen-akku.md, Task 1, mit den Entscheidungen
-- F1 bis F7). Ausgangspunkt ist der Schema-Abzug (supabase/schema/funktionen/), der mit der Live-Datenbank übereinstimmt.
-- Mehrfach ausführbar, löscht keine Daten. Probelauf: tools/pruefstand/rollen_akku_db.py (--ohne zeigt rot).
-- Nicht ohne Friedrichs Ja einspielen (Plan Task 9).
--
--  1. participants: akku, akku_laedt, akku_at, gesehen_at.
--  2. member_state(p_token, p_akku, p_laedt): Signaturwechsel (die alte Fassung mit einem Argument wird gedroppt, sonst
--     PGRST203). Schreibt Akku und gesehen_at (höchstens alle 20 s, außer der Akku ändert sich), liefert ichLeite.
--  3. report_position(..., p_akku, p_laedt): Signaturwechsel; der Akku geht auf die Teamleitung des Teams.
--  4. team_state: neues Feld geraete (members bleibt). admin_state: participants[].hatHandy, teams[].leaderAkku.
--  5. F7: member_state_by_team (Mitlese-Link) entfällt, jede Überladung. teams.read_token, team.readToken und der
--     read_token-Pfad in team_photo bleiben vorerst (Plan, Nachtrag F7).

alter table participants add column if not exists akku smallint;
alter table participants add column if not exists akku_laedt boolean;
alter table participants add column if not exists akku_at timestamptz;
alter table participants add column if not exists gesehen_at timestamptz;

drop function if exists public.member_state(text);
drop function if exists public.report_position(text, double precision, double precision, double precision, text);

CREATE OR REPLACE FUNCTION public.member_state(p_token text, p_akku integer DEFAULT NULL::integer, p_laedt boolean DEFAULT NULL::boolean)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v participants; t teams;
        v_akku int := case when p_akku between 0 and 100 then p_akku end;
begin
  if coalesce(p_token, '') = '' then
    raise exception 'Unbekanntes Gerät.' using errcode = 'P0001';
  end if;
  select * into v from participants where token = p_token;
  if not found then
    raise exception 'Unbekanntes Gerät.' using errcode = 'P0001';
  end if;
  -- Rollen und Akku 29.10.: letzter Abruf und Akku merken. Ohne gültigen Akku (iPhone, ungültiger Wert) bleibt der
  -- bekannte Stand. Höchstens eine Schreibung je 20 s und Person, außer der Akku ändert sich.
  update participants set gesehen_at = now(),
         akku       = coalesce(v_akku, akku),
         akku_laedt = case when v_akku is null then akku_laedt else coalesce(p_laedt, false) end,
         akku_at    = case when v_akku is null then akku_at else now() end
   where id = v.id
     and (gesehen_at is null or gesehen_at < now() - interval '20 seconds'
          or (v_akku is not null and (akku is distinct from v_akku or akku_laedt is distinct from coalesce(p_laedt, false))));
  if v.team_id is null then
    return json_build_object('name', v.name, 'team', null, 'ichLeite', false);
  end if;
  select * into t from teams where id = v.team_id;
  return ((team_state(t.code)::jsonb #- '{team,code}' #- '{team,readToken}')
          || jsonb_build_object('name', v.name, 'ichLeite', t.leader_participant_id = v.id))::json;
end $function$;
revoke all on function public.member_state(p_token text, p_akku integer, p_laedt boolean) from public, anon, authenticated;
grant execute on function public.member_state(p_token text, p_akku integer, p_laedt boolean) to public, anon, authenticated;

CREATE OR REPLACE FUNCTION public.report_position(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_kompass text DEFAULT NULL::text, p_akku integer DEFAULT NULL::integer, p_laedt boolean DEFAULT NULL::boolean)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; v_akku int := case when p_akku between 0 and 100 then p_akku end;
begin
  if (select status from game_state where id = 1) <> 'running' then return; end if;
  t := team_by_code(p_code);
  -- Rollen und Akku 29.10.: der Akku gehört der Teamleitung (leader_participant_id), auch ohne brauchbare Position.
  -- Das Notweg-Tablet schickt keinen Akku. Höchstens eine Schreibung je 20 s, außer der Akku ändert sich.
  if v_akku is not null and t.leader_participant_id is not null then
    update participants set akku = v_akku, akku_laedt = coalesce(p_laedt, false), akku_at = now(), gesehen_at = now()
     where id = t.leader_participant_id
       and (gesehen_at is null or gesehen_at < now() - interval '20 seconds'
            or akku is distinct from v_akku or akku_laedt is distinct from coalesce(p_laedt, false));
  end if;
  if p_lat is null or p_lng is null or abs(p_lat) > 90 or abs(p_lng) > 180
     or (abs(p_lat) < 0.01 and abs(p_lng) < 0.01)
     or p_acc is null or p_acc <= 0 or p_acc > 1000 then
    return;
  end if;
  insert into team_positions(team_id, lat, lng, accuracy_m, updated_at, kompass)
  values (t.id, p_lat, p_lng, p_acc, now(), case when p_kompass in ('ok', 'unzuverlaessig') then p_kompass end)
  on conflict (team_id) do update
    set lat = excluded.lat, lng = excluded.lng, accuracy_m = excluded.accuracy_m, updated_at = now(), kompass = excluded.kompass;
  insert into position_log(team_id, lat, lng, accuracy_m) values (t.id, p_lat, p_lng, p_acc);
end $function$;
revoke all on function public.report_position(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_kompass text, p_akku integer, p_laedt boolean) from public, anon, authenticated;
grant execute on function public.report_position(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_kompass text, p_akku integer, p_laedt boolean) to public, anon, authenticated;

CREATE OR REPLACE FUNCTION public.team_state(p_code text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
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
    -- Rollen und Akku 29.10.: je Gerät Anmeldung, Verbindung und Akku (members bleibt unverändert, alte Fassungen lesen es)
    'geraete', coalesce((select json_agg(json_build_object(
        'name', p3.name,
        'angemeldet', p3.token is not null,
        'verbunden', coalesce(p3.gesehen_at > now() - interval '2 minutes', false),
        'akku',  case when p3.akku_at > now() - interval '10 minutes' then p3.akku end,
        'laedt', case when p3.akku_at > now() - interval '10 minutes' then p3.akku_laedt end) order by p3.name)
      from participants p3 where p3.team_id = t.id), '[]'::json),
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
end $function$;
revoke all on function public.team_state(p_code text) from public, anon, authenticated;
grant execute on function public.team_state(p_code text) to public, anon, authenticated;

CREATE OR REPLACE FUNCTION public.admin_state(p_pin text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
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
               (select t.name from teams t where t.id = p.team_id) as "teamName",
               (p.token is not null) as "hatHandy"
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
    'start', json_build_object('name', g.start_name, 'lat', g.start_lat, 'lng', g.start_lng),
    'testStart', json_build_object('name', g.test_start_name, 'lat', g.test_start_lat, 'lng', g.test_start_lng),
    'aktiveStationen', coalesce((select json_agg(to_json(s4)) from (
        select s.id, s.position, s.name, s.lat, s.lng, s.radius_m as "radiusM"
        from stations s order by s.position) s4), '[]'::json),
    'caseCode', (select string_agg(s.digit::text, '' order by s.position) from stations s)
                || ((select coalesce(sum(digit),0) from stations) % 10)::text,
    'teams', coalesce((select json_agg(to_json(y)) from (
        select t.id, t.name, t.code, t.read_token as "readToken",
          t.leader_participant_id as "leaderId",
          (select p.name from participants p where p.id = t.leader_participant_id) as "leaderName",
          -- Rollen und Akku 29.10.: Akku der Teamleitung, nur bis 10 min Alter (sonst null)
          (select json_build_object('akku', p.akku, 'laedt', p.akku_laedt, 'at', p.akku_at)
             from participants p
             where p.id = t.leader_participant_id and p.akku is not null
               and p.akku_at > now() - interval '10 minutes') as "leaderAkku",
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
          -- Umbau Weiterentwicklung: Fehlversuche und Pause an der aktuellen Station, für "Braucht dich"
          coalesce((select pr.failed_attempts from stations s
             left join progress pr on pr.station_id = s.id and pr.team_id = t.id
             where pr.solved_at is null order by s.position limit 1), 0) as "failedAttempts",
          (select pr.locked_until from stations s
             left join progress pr on pr.station_id = s.id and pr.team_id = t.id
             where pr.solved_at is null order by s.position limit 1) as "lockedUntil",
          (select json_build_object('lat', tp.lat, 'lng', tp.lng,
                                    'accuracy', tp.accuracy_m, 'updatedAt', tp.updated_at, 'kompass', tp.kompass)
             from team_positions tp where tp.team_id = t.id) as position,
          (select f.place from finishes f where f.team_id = t.id) as place,
          (select f.finished_at from finishes f where f.team_id = t.id) as "finishedAt"
        from teams t order by t.name) y), '[]'::json)
  ) from game_state g where g.id = 1);
end $function$;
revoke all on function public.admin_state(p_pin text) from public, anon, authenticated;
grant execute on function public.admin_state(p_pin text) to public, anon, authenticated;

-- F7: Mitlese-Link streichen, jede Überladung von member_state_by_team
do $drop$
declare r record;
begin
  for r in select p.oid::regprocedure as sig from pg_proc p
           where p.pronamespace = 'public'::regnamespace and p.proname = 'member_state_by_team' loop
    execute format('drop function %s', r.sig);
  end loop;
end $drop$;

notify pgrst, 'reload schema';
