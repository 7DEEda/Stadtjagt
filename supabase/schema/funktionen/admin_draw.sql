-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_draw(p_pin text, p_teams integer DEFAULT NULL::integer, p_size integer DEFAULT NULL::integer)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
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
end $function$;
revoke all on function public.admin_draw(p_pin text, p_teams integer, p_size integer) from public, anon, authenticated;
grant execute on function public.admin_draw(p_pin text, p_teams integer, p_size integer) to public, anon, authenticated;
