-- ============================================================
--  STADTJAGD – Nachtrag 2: Routen der Teams aufzeichnen
--
--  Bisher speicherte team_positions pro Team genau eine Zeile und
--  überschrieb sie bei jeder Meldung. Es gab also keine Historie, nur
--  den letzten Punkt. Für die Routen auf der Karte und die Zeitachse
--  kommt eine zweite Tabelle dazu, die jeden gemeldeten Punkt behält.
--
--  Entscheidung vom 18.09.2026 zum Datenschutz: "Spiel beenden" löscht
--  die Standortdaten NICHT mehr, sonst wären die Routen genau dann weg,
--  wenn man sie auswerten will. Gelöscht wird nur noch auf Knopfdruck
--  über "Standortdaten löschen" und beim Zurücksetzen. Das ist eine
--  bewusste Abweichung vom ursprünglichen Versprechen im HANDOFF.md:
--  Aus kurzen Positionsmeldungen wird ein vollständiger Bewegungsverlauf
--  der Teamleitungen. Vorher ansagen, hinterher löschen.
--
--  Einspielen: Inhalt im Supabase SQL-Editor ausführen. Setzt Nachtrag 1
--  voraus. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

-- ---------- Verlaufstabelle ----------
create table if not exists position_log (
  id bigserial primary key,
  team_id uuid not null references teams(id) on delete cascade,
  lat double precision not null,
  lng double precision not null,
  accuracy_m double precision,
  recorded_at timestamptz not null default now()
);

create index if not exists position_log_team_time on position_log (team_id, recorded_at);

-- Wie alle anderen Tabellen: RLS an, keine Policies, kein Direktzugriff.
alter table position_log enable row level security;
revoke all on position_log from anon, authenticated;
revoke all on sequence position_log_id_seq from anon, authenticated;

-- ---------- Meldung schreibt jetzt beides ----------
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
  insert into position_log(team_id, lat, lng, accuracy_m)
  values (t.id, p_lat, p_lng, p_acc);
end $$;

-- ---------- Routen abholen ----------
-- p_since leer: alles. Sonst nur Punkte danach, damit die Spielleitung
-- beim Nachladen nicht jedes Mal den ganzen Verlauf zieht.
-- Punkte kommen kompakt als [Breite, Länge, Zeit in ms] statt als Objekte.
create or replace function admin_tracks(p_pin text, p_since timestamptz default null)
returns json language plpgsql security definer set search_path = public as $$
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
end $$;

-- ---------- Beenden löscht nicht mehr ----------
create or replace function admin_finish(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  update game_state set status = 'finished', finished_at = now() where id = 1;
  -- Standortdaten bleiben absichtlich stehen, damit die Routen auswertbar sind.
  -- Löschen über admin_clear_positions ("Standortdaten löschen").
  return admin_state(p_pin);
end $$;

-- ---------- Löschen erfasst jetzt auch den Verlauf ----------
create or replace function admin_clear_positions(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  delete from team_positions where true;
  delete from position_log where true;
  return admin_state(p_pin);
end $$;

create or replace function admin_reset(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  delete from progress where true;
  delete from team_positions where true;
  delete from position_log where true;
  update game_state set status = 'drawn', started_at = null, finished_at = null,
    winner_team_id = null where id = 1;
  return admin_state(p_pin);
end $$;

-- ---------- Ausführungsrecht für den neuen Endpunkt ----------
grant execute on function admin_tracks(text, timestamptz) to anon, authenticated;
