-- ============================================================
--  STADTJAGD – Nachtrag 10: Nachzügler melden sich selbst an
--
--  Bisher war die Anmeldung zu, sobald ausgelost war ("Die Anmeldung ist
--  geschlossen"). Jetzt geht sie bis zum Spielende: vor dem Auslosen wie
--  bisher ohne Team, danach kommt die Person wie ein Nachzügler aus dem
--  Admin-Bereich ins gerade kleinste Team, und die Antwort nennt das Team
--  gleich mit (Name, Leitung, Mitglieder, ohne Team-Code).
--  Nach "Spiel beenden" bleibt die Anmeldung zu.
--
--  Einspielen: nach Nachtrag 9. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

create or replace function register_participant(p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare v_name text := btrim(regexp_replace(coalesce(p_name,''), '\s+', ' ', 'g'));
        v_status text; v_team uuid;
begin
  if length(v_name) < 2 or length(v_name) > 60 then
    raise exception 'Bitte einen Namen mit 2 bis 60 Zeichen eingeben.' using errcode='P0001';
  end if;
  select status into v_status from game_state where id = 1;
  if v_status = 'finished' then
    raise exception 'Das Spiel ist vorbei, die Anmeldung ist geschlossen.' using errcode='P0001';
  end if;
  if exists (select 1 from participants where name_key = norm(v_name)) then
    raise exception 'Dieser Name ist schon angemeldet. Hast du dich schon eingetragen? Dann bist du dabei.'
      using errcode='P0001';
  end if;
  -- nach dem Auslosen: ins Team mit den wenigsten Leuten
  if v_status <> 'registration' then
    select t.id into v_team from teams t
      left join participants p on p.team_id = t.id
      group by t.id order by count(p.id) asc limit 1;
  end if;
  insert into participants(name, name_key, team_id) values (v_name, norm(v_name), v_team);
  return json_build_object('name', v_name, 'count', (select count(*) from participants),
    'team', (select json_build_object('name', t.name,
               'leaderName', (select p.name from participants p where p.id = t.leader_participant_id),
               'members', coalesce((select json_agg(p2.name order by p2.name)
                                    from participants p2 where p2.team_id = t.id), '[]'::json))
             from teams t where t.id = v_team));
end $$;

notify pgrst, 'reload schema';
