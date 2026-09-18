-- ============================================================
--  STADTJAGD – Nachtrag 4: bekanntere Tiernamen für die Teams
--
--  Die alte Liste hatte Tiere ohne eigenes Emoji (Reiher, Marder, Luchs,
--  Iltis, Specht, Kranich, Steinbock). Für die fehlte am Ende nur eine
--  Pfote als Platzhalter. Die neue Liste enthält nur Tiere, die ein
--  eigenes, bekanntes Emoji haben, und keine Umlaute, damit die Team-Codes
--  auf jeder Handytastatur leicht zu tippen sind.
--
--  Fuchs, Wolf, Eule, Tiger, Panda, Einhorn, Flamingo, Pinguin, Delfin,
--  Adler, Igel, Otter, Krake, Biber, Koala, Drache.
--
--  Die Zuordnung Name zu Emoji steht im Frontend als TEAM_EMOJI in
--  index.html. Wer hier Namen ändert, muss sie dort ebenfalls eintragen.
--
--  Wirkt erst beim nächsten Auslosen. Bestehende Teams behalten ihre Namen.
--  Einspielen: nach Nachtrag 3. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

create or replace function admin_draw(p_pin text, p_teams int default null, p_size int default null)
returns json language plpgsql security definer set search_path = public as $$
declare v_count int; v_teams int; v_animals text[] := array[
    'Fuchs','Wolf','Eule','Tiger','Panda','Einhorn','Flamingo','Pinguin',
    'Delfin','Adler','Igel','Otter','Krake','Biber','Koala','Drache'];
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

notify pgrst, 'reload schema';
