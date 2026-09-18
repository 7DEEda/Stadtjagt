-- ============================================================
--  STADTJAGD – Nachtrag 3: Teamgröße beim Auslosen wählbar
--
--  Bisher rechnete admin_draw die Teamzahl fest als round(Personen / 10).
--  Bei 13 Angemeldeten ergibt round(1,3) genau 1, also blieb es immer bei
--  einem Team, egal wie oft man auslöste. Das sah wie ein Fehler aus, war
--  aber die Regel.
--
--  Jetzt lässt sich beim Auslosen angeben, wie viele Personen pro Team
--  gewünscht sind (p_size) oder wie viele Teams es geben soll (p_teams).
--  Ohne Angabe bleibt es bei der alten Faustregel.
--
--  Die alte Fassung mit nur einem Parameter muss weg, sonst weiß PostgREST
--  bei einem Aufruf mit nur p_pin nicht, welche der beiden gemeint ist.
--  Das löscht keine Daten, nur die Funktionsdefinition.
--
--  Einspielen: nach Nachtrag 1 und 2. Mehrfach ausführbar.
-- ============================================================

drop function if exists admin_draw(text);

create or replace function admin_draw(p_pin text, p_teams int default null, p_size int default null)
returns json language plpgsql security definer set search_path = public as $$
declare v_count int; v_teams int; v_animals text[] := array[
    'Fuchs','Dachs','Luchs','Eule','Biber','Falke','Hirsch','Otter','Wolf','Specht','Igel','Marder',
    'Reiher','Kranich','Iltis','Steinbock'];
        v_max int; v_status text; i int; v_id uuid; v_ids uuid[]; v_code text;
begin
  perform require_admin(p_pin);
  select status into v_status from game_state where id = 1;
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

grant execute on function admin_draw(text, int, int) to anon, authenticated;

-- PostgREST kennt die Signaturen aus einem Zwischenspeicher, der nach einer
-- Änderung neu gelesen werden muss.
notify pgrst, 'reload schema';
