-- ============================================================
--  STADTJAGD – Nachtrag 25: Gruppenselfie an jeder Station
--
--  Nach der richtigen Antwort macht das Team ein Gruppenfoto, erst danach
--  erscheint die Ziffer. Die Fotos sehen nur das eigene Team und die
--  Spielleitung. Spezifikation: docs/superpowers/specs/2026-09-30-gruppenselfie-design.md
--
--  Abschaltbar: game_state.selfie_on, Standard aus. Solange der Schalter aus
--  ist, verhält sich das Spiel wie vor diesem Nachtrag.
--
--  Was sich NICHT ändert: submit_answer setzt solved_at wie bisher, daran
--  hängen Zeitmessung und Rangliste. Neu ist progress.selfie_at. team_state
--  hält bei eingeschaltetem Selfie die Ziffer zurück, bis selfie_at gesetzt
--  ist, und meldet die offene Station als selfie.pending.
--
--  Die Fotos liegen in station_photos und hängen per Fremdschlüssel an
--  progress: Zurücksetzen, neu Auslosen und Leeren der Anmeldung nehmen sie
--  mit, ohne dass diese Funktionen angefasst werden. Keine Rechte für anon,
--  der Weg führt über die Funktionen unten, mit denselben Zugängen wie das
--  Spiel (Team-Code, Geräte-Schlüssel, Mitlese-Link, Admin-PIN).
--
--  Löschen: photos_delete_on. Ist der Tag erreicht, entfernen team_state und
--  admin_state die Fotos beim nächsten Abruf.
--
--  team_state und public_state: Fassungen aus Nachtrag 19 plus die markierten
--  Stellen. admin_state: Fassung aus Nachtrag 21 plus drei Felder.
--
--  Einspielen: nach Nachtrag 23. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

alter table progress add column if not exists selfie_at timestamptz;
alter table game_state add column if not exists selfie_on boolean not null default false;
alter table game_state add column if not exists photos_delete_on date;

create table if not exists station_photos (
  team_id    uuid not null,
  station_id uuid not null,
  photo      bytea not null,
  thumb      bytea not null,
  taken_at   timestamptz not null default now(),
  primary key (team_id, station_id),
  foreign key (team_id, station_id) references progress(team_id, station_id) on delete cascade
);
alter table station_photos enable row level security;
revoke all on station_photos from anon, authenticated;

-- ---------- Foto speichern oder ersetzen ----------
create or replace function team_selfie(p_code text, p_position int, p_photo text, p_thumb text) returns json
language plpgsql security definer set search_path = public as $$
declare t teams; s stations; pr progress; v_photo bytea; v_thumb bytea;
begin
  t := team_by_code(p_code);
  if not (select selfie_on from game_state where id = 1) then
    raise exception 'Gruppenfotos sind ausgeschaltet.' using errcode='P0001';
  end if;
  select * into s from stations where position = p_position;
  if not found then raise exception 'Diese Station gibt es nicht.' using errcode='P0001'; end if;
  select * into pr from progress where team_id = t.id and station_id = s.id for update;
  if not found or pr.solved_at is null then
    raise exception 'Erst das Rätsel lösen, dann das Foto.' using errcode='P0001';
  end if;
  begin
    v_photo := decode(p_photo, 'base64'); v_thumb := decode(p_thumb, 'base64');
  exception when others then
    raise exception 'Das Foto ist beschädigt angekommen.' using errcode='P0001';
  end;
  if v_photo is null or v_thumb is null
     or substring(v_photo from 1 for 3) <> '\xffd8ff'::bytea
     or substring(v_thumb from 1 for 3) <> '\xffd8ff'::bytea then
    raise exception 'Das ist kein JPEG-Foto.' using errcode='P0001';
  end if;
  if octet_length(v_photo) > 716800 or octet_length(v_thumb) > 61440 then
    raise exception 'Das Foto ist zu groß.' using errcode='P0001';
  end if;
  -- Ersetzen nur, bis das Team an einer späteren Station eingecheckt hat. Nachreichen geht immer.
  if exists (select 1 from station_photos where team_id = t.id and station_id = s.id)
     and exists (select 1 from progress p2 join stations s2 on s2.id = p2.station_id
                 where p2.team_id = t.id and s2.position > s.position and p2.checked_in_at is not null) then
    raise exception 'Dieses Foto lässt sich nicht mehr ersetzen, ihr seid schon an der nächsten Station.' using errcode='P0001';
  end if;
  insert into station_photos (team_id, station_id, photo, thumb) values (t.id, s.id, v_photo, v_thumb)
    on conflict (team_id, station_id) do update
      set photo = excluded.photo, thumb = excluded.thumb, taken_at = now();
  update progress set selfie_at = coalesce(selfie_at, now()) where team_id = t.id and station_id = s.id;
  return team_state(p_code);
end $$;

-- ---------- Ohne Hochladen weiter (Funkloch, Kamera streikt): die Ziffer hängt nie am Foto ----------
create or replace function team_selfie_skip(p_code text, p_position int) returns json
language plpgsql security definer set search_path = public as $$
declare t teams;
begin
  t := team_by_code(p_code);
  update progress pr set selfie_at = coalesce(pr.selfie_at, now())
    from stations s
    where s.id = pr.station_id and s.position = p_position and pr.team_id = t.id and pr.solved_at is not null;
  if not found then raise exception 'Erst das Rätsel lösen.' using errcode='P0001'; end if;
  return team_state(p_code);
end $$;

-- ---------- Ein Foto des eigenen Teams: Teamleitung (Code), Mitglied (Geräte-Schlüssel) oder Mitlese-Link ----------
create or replace function team_photo(p_code text, p_token text, p_read_token text, p_position int, p_full boolean default false)
returns json language plpgsql security definer set search_path = public as $$
declare v_team uuid;
begin
  if coalesce(p_code, '') <> '' then
    v_team := (team_by_code(p_code)).id;
  elsif coalesce(p_token, '') <> '' then
    select team_id into v_team from participants where token = p_token;
  elsif coalesce(p_read_token, '') <> '' then
    select id into v_team from teams where read_token = p_read_token;
  end if;
  if v_team is null then raise exception 'Kein Zugang zu diesem Album.' using errcode='P0001'; end if;
  return json_build_object('data', (select encode(case when p_full then ph.photo else ph.thumb end, 'base64')
          from station_photos ph join stations s on s.id = ph.station_id
          where ph.team_id = v_team and s.position = p_position));
end $$;

-- ---------- Spielleitung ----------
create or replace function admin_photos(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  return coalesce((select json_agg(to_json(x)) from (
    select t.id as "teamId", t.name as "teamName", s.position, s.name as "stationName", ph.taken_at as "takenAt"
    from station_photos ph join teams t on t.id = ph.team_id join stations s on s.id = ph.station_id
    order by t.name, s.position) x), '[]'::json);
end $$;

create or replace function admin_photo(p_pin text, p_team uuid, p_position int, p_full boolean default false)
returns json language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  return json_build_object('data', (select encode(case when p_full then ph.photo else ph.thumb end, 'base64')
          from station_photos ph join stations s on s.id = ph.station_id
          where ph.team_id = p_team and s.position = p_position));
end $$;

create or replace function admin_set_selfie(p_pin text, p_on boolean, p_delete_on date) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  -- Einschalten mitten im Spiel: was schon gelöst ist, braucht kein Foto mehr, sonst stünden alle Teams
  -- plötzlich vor einem Selfie für längst verlassene Stationen
  if coalesce(p_on, false) and not (select selfie_on from game_state where id = 1) then
    update progress set selfie_at = solved_at where solved_at is not null and selfie_at is null;
  end if;
  update game_state set selfie_on = coalesce(p_on, false), photos_delete_on = p_delete_on where id = 1;
  return admin_state(p_pin);
end $$;

create or replace function admin_delete_photos(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  delete from station_photos where true;
  return admin_state(p_pin);
end $$;

grant execute on function team_selfie(text, int, text, text) to anon, authenticated;
grant execute on function team_selfie_skip(text, int) to anon, authenticated;
grant execute on function team_photo(text, text, text, int, boolean) to anon, authenticated;
grant execute on function admin_photos(text) to anon, authenticated;
grant execute on function admin_photo(text, uuid, int, boolean) to anon, authenticated;
grant execute on function admin_set_selfie(text, boolean, date) to anon, authenticated;
grant execute on function admin_delete_photos(text) to anon, authenticated;

-- ---------- team_state (Nachtrag 19) plus Selfie: Ziffern-Regel, Feld selfie, fällige Fotos löschen ----------
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

-- ---------- public_state (Nachtrag 19) plus selfieOn und photosDeleteOn für den Hinweis bei der Anmeldung ----------
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

-- ---------- admin_state (Nachtrag 21) plus selfieOn, photosDeleteOn, photoCount ----------
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
