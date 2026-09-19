-- ============================================================
--  STADTJAGD – Nachtrag 20: Funde der Bugjagd vom 19.09.2026
--
--  1. norm faltet alle gängigen lateinischen Diakritika auf den
--     Grundbuchstaben, auch die tschechischen (ř č š ž ě í ý ů ň ...).
--     Vorher löschte norm sie: 'Křižík' wurde zu 'kik', 'Krizik' zu
--     'krizik', eine richtige Antwort zählte als falsch. ä ö ü ß bleiben
--     ae oe ue ss wie bisher. Die name_key werden nachgezogen.
--  2. Ein Name ohne einen einzigen Buchstaben oder Ziffer (nur Kyrillisch,
--     nur Emoji) ergab den leeren Schlüssel, die zweite solche Person bekam
--     "Dann bist du dabei", ohne dabei zu sein. Jetzt abgelehnt, in allen
--     vier Wegen und zusätzlich per Trigger auf participants.
--  3. Auslosen und Anmelden sperren game_state: admin_draw mit for update
--     gleich zu Beginn, die Anmelde-Wege mit for share. Vorher konnten zwei
--     gleichzeitige Auslosungen doppelt so viele Teams anlegen, und eine
--     Anmeldung während des Auslosens blieb ohne Team.
--  4. admin_solve_station und admin_unlock_station bekommen die Station
--     (p_position), die die Spielleitung gemeint hat. Ist das Team schon
--     weiter, lehnen sie ab. Vorher schenkte ein zweiter Klick nach einem
--     Netzfehler oder eine veraltete Ansicht die nächste Station.
--     p_position ist optional, damit eine alte Seite im Browser weiterläuft.
--  5. Die Admin-PIN braucht beim Ändern mindestens 12 Zeichen, auch bei
--     einem direkten UPDATE (Trigger). Eine bestehende kurze PIN bleibt
--     gültig, bis sie geändert wird.
--
--  Einspielen: nach Nachtrag 19. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

-- ---------- 1. norm mit Diakritika ----------
-- Erst Großbuchstaben selbst falten (lower() der Locale C tut es nicht),
-- dann ä ö ü ß wie bisher ausschreiben, dann den Rest auf den Grundbuchstaben.
create or replace function norm(t text) returns text
language sql immutable as $$
  select regexp_replace(
    translate(
      replace(replace(replace(replace(
        lower(translate(coalesce(t,''),
          'ÄÖÜÀÁÂÃÅĀĂĄÇĆČĎĐÈÉÊËĒĖĘĚÌÍÎÏĪĮĹĽŁÑŃŇÒÓÔÕØŌŐŔŘŚŠŞȘŤŢȚÙÚÛŮŪŰŲÝŸŹŻŽ',
          'äöüàáâãåāăąçćčďđèéêëēėęěìíîïīįĺľłñńňòóôõøōőŕřśšşșťţțùúûůūűųýÿźżž')),
        'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss'),
      'àáâãåāăąçćčďđèéêëēėęěìíîïīįıĺľłñńňòóôõøōőŕřśšşșťţțùúûůūűųýÿźżž',
      'aaaaaaaacccddeeeeeeeeiiiiiiilllnnnooooooorrsssstttuuuuuuuyyzzz'),
    '[^a-z0-9]+', '', 'g');
$$;

revoke all on function norm(text) from public, anon, authenticated;

-- Schlüssel nachziehen. Fielen zwei Namen erst mit der neuen Faltung
-- zusammen ('Jiří' und 'Jiri'), bricht das am unique ab; dann vorher mit
--   select norm(name), array_agg(name) from participants group by 1 having count(*) > 1;
-- nachsehen und einen der beiden umbenennen.
update participants set name_key = norm(name) where name_key <> norm(name);

-- ---------- 2. kein leerer Schlüssel ----------
create or replace function participants_name_key_pruefen() returns trigger
language plpgsql as $$
begin
  if coalesce(new.name_key, '') = '' then
    raise exception 'Bitte einen Namen mit lateinischen Buchstaben oder Ziffern eingeben.' using errcode='P0001';
  end if;
  return new;
end $$;

drop trigger if exists participants_name_key_pruefen on participants;
create trigger participants_name_key_pruefen before insert or update of name, name_key on participants
  for each row execute function participants_name_key_pruefen();

-- ---------- 3. Auslosen sperrt game_state ----------
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
  if v_count < 2 then raise exception 'Es sind noch zu wenige Personen angemeldet.' using errcode='P0001'; end if;

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

create or replace function register_participant(p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare v_name text := btrim(regexp_replace(coalesce(p_name,''), '\s+', ' ', 'g'));
        -- zwei zufällige UUIDs ohne Striche: 64 Hex-Zeichen, 244 Bit Zufall
        v_token text := replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', '');
begin
  if length(v_name) < 2 or length(v_name) > 60 then
    raise exception 'Bitte einen Namen mit 2 bis 60 Zeichen eingeben.' using errcode='P0001';
  end if;
  if norm(v_name) = '' then
    raise exception 'Bitte einen Namen mit lateinischen Buchstaben oder Ziffern eingeben.' using errcode='P0001';
  end if;
  -- Läuft gerade das Auslosen, warten wir, bis es durch ist; die Statusabfrage
  -- danach sieht dann schon 'drawn'. Anmeldungen untereinander warten nicht.
  perform 1 from game_state where id = 1 for share;
  if (select status from game_state where id = 1) <> 'registration' then
    raise exception 'Die Anmeldung ist geschlossen. Melde dich über den Hilfe-Knopf bei der Spielleitung, sie trägt dich nach.'
      using errcode='P0001';
  end if;
  if exists (select 1 from participants where name_key = norm(v_name)) then
    raise exception 'Dieser Name ist schon angemeldet. Hast du dich schon eingetragen? Dann bist du dabei.'
      using errcode='P0001';
  end if;
  insert into participants(name, name_key, token) values (v_name, norm(v_name), v_token);
  return json_build_object('name', v_name, 'token', v_token, 'count', (select count(*) from participants));
end $$;

create or replace function admin_add_participant(p_pin text, p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare v_name text := btrim(regexp_replace(coalesce(p_name,''), '\s+', ' ', 'g'));
        v_team uuid;
begin
  perform require_admin(p_pin);
  if length(v_name) < 2 or length(v_name) > 60 then
    raise exception 'Bitte einen Namen mit 2 bis 60 Zeichen eingeben.' using errcode='P0001';
  end if;
  if norm(v_name) = '' then
    raise exception 'Bitte einen Namen mit lateinischen Buchstaben oder Ziffern eingeben.' using errcode='P0001';
  end if;
  perform 1 from game_state where id = 1 for share;   -- nicht mitten in ein Auslosen
  if exists (select 1 from participants where name_key = norm(v_name)) then
    raise exception 'Dieser Name ist schon angemeldet.' using errcode='P0001';
  end if;
  select t.id into v_team from teams t
    left join participants p on p.team_id = t.id
    group by t.id order by count(p.id) asc limit 1;
  insert into participants(name, name_key, team_id) values (v_name, norm(v_name), v_team);
  return admin_state(p_pin);
end $$;

create or replace function admin_add_participants(p_pin text, p_names text) returns json
language plpgsql security definer set search_path = public as $$
declare v_zeile text; v_name text; v_team uuid; v_neu int := 0; v_doppelt int := 0; v_ungueltig int := 0;
begin
  perform require_admin(p_pin);
  perform 1 from game_state where id = 1 for share;   -- nicht mitten in ein Auslosen
  foreach v_zeile in array regexp_split_to_array(coalesce(p_names, ''), '\r?\n') loop
    v_name := btrim(regexp_replace(v_zeile, '\s+', ' ', 'g'));
    continue when v_name = '';
    if length(v_name) < 2 or length(v_name) > 60 or norm(v_name) = '' then
      v_ungueltig := v_ungueltig + 1; continue;
    end if;
    if exists (select 1 from participants where name_key = norm(v_name)) then
      v_doppelt := v_doppelt + 1; continue;
    end if;
    v_team := null;
    select t.id into v_team from teams t
      left join participants p on p.team_id = t.id
      group by t.id order by count(p.id) asc limit 1;
    insert into participants(name, name_key, team_id) values (v_name, norm(v_name), v_team);
    v_neu := v_neu + 1;
  end loop;
  return json_build_object('added', v_neu, 'duplicates', v_doppelt, 'invalid', v_ungueltig,
                           'state', admin_state(p_pin));
end $$;

create or replace function admin_rename_participant(p_pin text, p_id uuid, p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare v_name text := btrim(regexp_replace(coalesce(p_name,''), '\s+', ' ', 'g'));
begin
  perform require_admin(p_pin);
  if length(v_name) < 2 or length(v_name) > 60 then
    raise exception 'Bitte einen Namen mit 2 bis 60 Zeichen eingeben.' using errcode='P0001';
  end if;
  if norm(v_name) = '' then
    raise exception 'Bitte einen Namen mit lateinischen Buchstaben oder Ziffern eingeben.' using errcode='P0001';
  end if;
  if exists (select 1 from participants where name_key = norm(v_name) and id <> p_id) then
    raise exception 'Diesen Namen gibt es schon.' using errcode='P0001';
  end if;
  update participants set name = v_name, name_key = norm(v_name) where id = p_id;
  return admin_state(p_pin);
end $$;

-- ---------- 4. Werten und Freischalten nur für die gemeinte Station ----------
drop function if exists admin_solve_station(text, uuid);
create or replace function admin_solve_station(p_pin text, p_team uuid, p_position int default null) returns json
language plpgsql security definer set search_path = public as $$
declare cur stations;
begin
  perform require_admin(p_pin);
  perform 1 from teams where id = p_team for update;   -- zwei Klicks laufen nacheinander, nicht gleichzeitig
  cur := current_station(p_team);
  if cur.id is null then raise exception 'Dieses Team hat alle Stationen gelöst.' using errcode='P0001'; end if;
  if p_position is not null and cur.position <> p_position then
    raise exception 'Das Team ist schon bei Station %. Nichts gewertet.', cur.position using errcode='P0001';
  end if;
  insert into progress(team_id, station_id, checked_in_at, solved_at, failed_attempts, locked_until)
    values (p_team, cur.id, now(), now(), 0, null)
    on conflict (team_id, station_id) do update
      set checked_in_at = coalesce(progress.checked_in_at, now()), solved_at = now(),
          failed_attempts = 0, locked_until = null;
  return admin_state(p_pin);
end $$;

grant execute on function admin_solve_station(text, uuid, int) to anon, authenticated;

drop function if exists admin_unlock_station(text, uuid);
create or replace function admin_unlock_station(p_pin text, p_team uuid, p_position int default null) returns json
language plpgsql security definer set search_path = public as $$
declare cur stations;
begin
  perform require_admin(p_pin);
  perform 1 from teams where id = p_team for update;
  cur := current_station(p_team);
  if cur.id is null then raise exception 'Dieses Team hat alle Stationen gelöst.' using errcode='P0001'; end if;
  if p_position is not null and cur.position <> p_position then
    raise exception 'Das Team ist schon bei Station %. Nichts freigeschaltet.', cur.position using errcode='P0001';
  end if;
  insert into progress(team_id, station_id, checked_in_at) values (p_team, cur.id, now())
    on conflict (team_id, station_id) do update set checked_in_at = coalesce(progress.checked_in_at, now());
  return admin_state(p_pin);
end $$;

grant execute on function admin_unlock_station(text, uuid, int) to anon, authenticated;

-- ---------- 5. lange Admin-PIN ----------
create or replace function admin_set_pin(p_pin text, p_new text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  if length(btrim(coalesce(p_new,''))) < 12 then
    raise exception 'Die neue PIN braucht mindestens 12 Zeichen, am besten eine Passphrase.' using errcode='P0001';
  end if;
  update game_state set admin_pin = btrim(p_new) where id = 1;
  return admin_state(btrim(p_new));
end $$;

-- Greift auch beim direkten UPDATE im SQL-Editor. Nur wenn sich die PIN
-- ändert: Statuswechsel mit einer alten kurzen PIN laufen weiter.
create or replace function game_state_pin_pruefen() returns trigger
language plpgsql as $$
begin
  if new.admin_pin is distinct from old.admin_pin and length(btrim(coalesce(new.admin_pin, ''))) < 12 then
    raise exception 'Die Admin-PIN braucht mindestens 12 Zeichen, am besten eine Passphrase.' using errcode='P0001';
  end if;
  return new;
end $$;

drop trigger if exists game_state_pin_pruefen on game_state;
create trigger game_state_pin_pruefen before update of admin_pin on game_state
  for each row execute function game_state_pin_pruefen();

notify pgrst, 'reload schema';
