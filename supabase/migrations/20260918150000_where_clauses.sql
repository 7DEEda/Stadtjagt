-- ============================================================
--  STADTJAGD – Nachtrag 1: WHERE-Klauseln für pg-safeupdate
--
--  Supabase lädt für API-Verbindungen (Rolle authenticator, also alles,
--  was über PostgREST/RPC läuft) die Erweiterung safeupdate. Sie lehnt
--  UPDATE und DELETE ohne WHERE ab, auch innerhalb von security-definer-
--  Funktionen: "UPDATE requires a WHERE clause". Die Init-Migration wurde
--  über eine direkte Datenbankverbindung getestet, dort greift safeupdate
--  nicht, deshalb fiel es nicht auf.
--
--  Betroffen: admin_draw, admin_finish, admin_reset, admin_clear_positions.
--  Die Funktionen werden mit gleicher Signatur ersetzt (create or replace),
--  die Ausführungsrechte für anon bleiben dabei erhalten. "where true"
--  ist die übliche Schreibweise für "alle Zeilen" unter safeupdate.
--  Regel für neue Funktionen: jedes UPDATE und DELETE braucht ein WHERE.
--
--  Einspielen: Inhalt im Supabase SQL-Editor ausführen. Mehrfach möglich,
--  löscht keine Daten.
-- ============================================================

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

  update participants set team_id = null where team_id is not null;
  delete from teams where true;

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
    select p.id from participants p where p.team_id = t.id order by random() limit 1)
    where true;

  update game_state set status = 'drawn' where id = 1;
  return admin_state(p_pin);
end $$;

create or replace function admin_finish(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  update game_state set status = 'finished', finished_at = now() where id = 1;
  delete from team_positions where true;   -- Standortdaten nach dem Spiel löschen
  return admin_state(p_pin);
end $$;

create or replace function admin_reset(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  delete from progress where true;
  delete from team_positions where true;
  update game_state set status = 'drawn', started_at = null, finished_at = null,
    winner_team_id = null where id = 1;
  return admin_state(p_pin);
end $$;

create or replace function admin_clear_positions(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  delete from team_positions where true;
  return admin_state(p_pin);
end $$;
