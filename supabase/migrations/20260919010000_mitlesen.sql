-- ============================================================
--  STADTJAGD – Nachtrag 11: das ganze Team liest mit
--
--  Alle im Team sollen sehen, was die Teamleitung sieht (Station,
--  Ortshinweis, Rätsel nach dem Check-in, Ziffern, Koffer, Platz), aber
--  nur die Teamleitung gibt etwas ein.
--
--  Warum nicht über den Namen: Alle Namen stehen öffentlich in den
--  Teamlisten, und alle Teams laufen dieselbe Route mit denselben Rätseln
--  und Ziffern. Wer über den Namen eines Mitglieds des schnellsten Teams
--  mitlesen könnte, hätte dessen Lösungen und Ziffern. Deshalb bekommt jede
--  Anmeldung einen zufälligen Geräte-Schlüssel (participants.token), den nur
--  das Handy kennt, auf dem sie passiert ist. member_state liefert damit
--  team_state ohne den Team-Code.
--
--  Wer von der Spielleitung eingetragen wurde (Nachzügler im Admin-Bereich,
--  Sammeleingabe, Testdaten), hat keinen Schlüssel und liest nicht mit.
--
--  Einspielen: nach Nachtrag 10. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

alter table participants add column if not exists token text unique;

create or replace function register_participant(p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare v_name text := btrim(regexp_replace(coalesce(p_name,''), '\s+', ' ', 'g'));
        v_status text; v_team uuid;
        -- zwei zufällige UUIDs ohne Striche: 64 Hex-Zeichen, 244 Bit Zufall
        v_token text := replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', '');
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
  insert into participants(name, name_key, team_id, token) values (v_name, norm(v_name), v_team, v_token);
  return json_build_object('name', v_name, 'token', v_token, 'count', (select count(*) from participants),
    'team', (select json_build_object('name', t.name,
               'leaderName', (select p.name from participants p where p.id = t.leader_participant_id),
               'members', coalesce((select json_agg(p2.name order by p2.name)
                                    from participants p2 where p2.team_id = t.id), '[]'::json))
             from teams t where t.id = v_team));
end $$;

-- Was die Teamleitung sieht, ohne Team-Code. Eingaben gehen weiter nur mit dem Code.
create or replace function member_state(p_token text) returns json
language plpgsql security definer set search_path = public as $$
declare v participants; t teams;
begin
  if coalesce(p_token, '') = '' then
    raise exception 'Unbekanntes Gerät.' using errcode = 'P0001';
  end if;
  select * into v from participants where token = p_token;
  if not found then
    raise exception 'Unbekanntes Gerät.' using errcode = 'P0001';
  end if;
  if v.team_id is null then
    return json_build_object('name', v.name, 'team', null);
  end if;
  select * into t from teams where id = v.team_id;
  return ((team_state(t.code)::jsonb #- '{team,code}') || jsonb_build_object('name', v.name))::json;
end $$;

grant execute on function member_state(text) to anon, authenticated;

notify pgrst, 'reload schema';
