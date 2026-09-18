-- ============================================================
--  STADTJAGD – Nachtrag 8: Durchsicht Bedienung (18.09.2026)
--
--  - team_by_code vergleicht nur Buchstaben und Ziffern: "EULE 8765",
--    "eule8765" und "EULE-8765" sind derselbe Code. Auf dem Handy wird
--    der Bindestrich gern vergessen.
--  - lookup_participant findet auch Namensteile. Passt genau ein Name,
--    kommt er direkt; passen mehrere, kommen bis zu acht Vorschläge.
--    Die Namen je Team stehen ohnehin in public_state, es wird also
--    nichts sichtbar, was nicht schon öffentlich ist.
--  - register_participant: bei einem schon angemeldeten Namen der
--    Hinweis, dass man sich vermutlich schon eingetragen hat.
--  - submit_answer: "Noch 1 Versuch." statt "Noch 1 Versuch(e)."
--  - report_position verwirft unbrauchbare Punkte: fehlende Werte,
--    0/0 (manche Geräte melden das ohne Fix), Genauigkeit 0 oder
--    schlechter als 1 km. Ein einziger solcher Punkt zog die Karte der
--    Spielleitung vorher auf den halben Globus.
--
--  Einspielen: nach Nachtrag 7. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

create or replace function team_by_code(p_code text) returns teams
language plpgsql security definer set search_path = public as $$
declare t teams;
begin
  select * into t from teams
    where regexp_replace(upper(code), '[^A-Z0-9]', '', 'g')
        = regexp_replace(upper(coalesce(p_code, '')), '[^A-Z0-9]', '', 'g');
  if not found then
    raise exception 'Unbekannter Team-Code.' using errcode = 'P0001';
  end if;
  return t;
end $$;

create or replace function register_participant(p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare v_name text := btrim(regexp_replace(coalesce(p_name,''), '\s+', ' ', 'g'));
begin
  if length(v_name) < 2 or length(v_name) > 60 then
    raise exception 'Bitte einen Namen mit 2 bis 60 Zeichen eingeben.' using errcode='P0001';
  end if;
  if (select status from game_state where id=1) <> 'registration' then
    raise exception 'Die Anmeldung ist geschlossen. Melde dich bei der Spielleitung.' using errcode='P0001';
  end if;
  if exists (select 1 from participants where name_key = norm(v_name)) then
    raise exception 'Dieser Name ist schon angemeldet. Hast du dich schon eingetragen? Dann bist du dabei.'
      using errcode='P0001';
  end if;
  insert into participants(name, name_key) values (v_name, norm(v_name));
  return json_build_object('name', v_name, 'count', (select count(*) from participants));
end $$;

create or replace function lookup_participant(p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare v participants; t teams; v_key text := norm(p_name); v_treffer int; v_namen json;
begin
  select * into v from participants where name_key = v_key;
  if not found and length(v_key) >= 3 then
    -- kein genauer Treffer: Namensteile, etwa nur der Vorname
    select count(*) into v_treffer from participants where name_key like '%' || v_key || '%';
    if v_treffer = 1 then
      select * into v from participants where name_key like '%' || v_key || '%';
    elsif v_treffer > 1 then
      select json_agg(name order by name) into v_namen from (
        select name from participants where name_key like '%' || v_key || '%' order by name limit 8) x;
      return json_build_object('found', false, 'candidates', v_namen, 'more', v_treffer > 8);
    end if;
  end if;
  if v.id is null then return json_build_object('found', false); end if;
  select * into t from teams where id = v.team_id;
  return json_build_object(
    'found', true, 'name', v.name,
    'team', case when t.id is null then null else json_build_object(
      'name', t.name,
      'leaderName', (select p.name from participants p where p.id = t.leader_participant_id),
      'members', coalesce((select json_agg(p2.name order by p2.name)
                           from participants p2 where p2.team_id = t.id), '[]'::json)
    ) end);
end $$;

create or replace function submit_answer(p_code text, p_answer text)
returns json language plpgsql security definer set search_path = public as $$
declare t teams; g game_state; cur stations; row_p progress;
        v_attempts int; v_locked boolean;
begin
  t := team_by_code(p_code);
  select * into g from game_state where id = 1;
  if g.status <> 'running' then
    return json_build_object('ok', false, 'message', 'Das Spiel läuft gerade nicht.', 'state', team_state(p_code));
  end if;
  cur := current_station(t.id);
  if cur.id is null then
    return json_build_object('ok', false, 'message', 'Alle Stationen sind gelöst.', 'state', team_state(p_code));
  end if;
  select * into row_p from progress where team_id = t.id and station_id = cur.id;
  if row_p.checked_in_at is null then
    return json_build_object('ok', false, 'message', 'Erst am Ort einchecken, dann gibt es das Rätsel.',
      'state', team_state(p_code));
  end if;
  if not g.test_mode and row_p.locked_until is not null and row_p.locked_until > now() then
    return json_build_object('ok', false,
      'message', 'Denkpause: noch ' || ceil(extract(epoch from row_p.locked_until - now())) || ' Sekunden.',
      'state', team_state(p_code));
  end if;

  if g.test_mode or (norm(p_answer) = norm(cur.answer) and norm(cur.answer) <> '') then
    update progress set solved_at = now(), failed_attempts = 0, locked_until = null
      where team_id = t.id and station_id = cur.id;
    return json_build_object('ok', true,
      'message', case when g.test_mode then 'Testmodus: jede Antwort zählt. Eine Ziffer ist frei.'
                      else 'Richtig. Eine Ziffer ist frei.' end,
      'state', team_state(p_code));
  end if;

  v_attempts := case when row_p.locked_until is not null and row_p.locked_until <= now()
                     then 1 else row_p.failed_attempts + 1 end;
  v_locked := v_attempts >= 3;
  update progress
    set failed_attempts = case when v_locked then 0 else v_attempts end,
        locked_until    = case when v_locked then now() + interval '2 minutes' else null end
    where team_id = t.id and station_id = cur.id;
  return json_build_object('ok', false,
    'message', case when v_locked then 'Dreimal falsch. Zwei Minuten Denkpause für euer Team.'
                    else 'Leider falsch. Noch ' || (3 - v_attempts)
                         || case when 3 - v_attempts = 1 then ' Versuch.' else ' Versuche.' end end,
    'state', team_state(p_code));
end $$;

create or replace function report_position(p_code text, p_lat double precision,
                                           p_lng double precision, p_acc double precision)
returns void language plpgsql security definer set search_path = public as $$
declare t teams;
begin
  if (select status from game_state where id = 1) <> 'running' then return; end if;
  -- unbrauchbare Punkte still verwerfen
  if p_lat is null or p_lng is null or abs(p_lat) > 90 or abs(p_lng) > 180
     or (abs(p_lat) < 0.01 and abs(p_lng) < 0.01)
     or p_acc is null or p_acc <= 0 or p_acc > 1000 then
    return;
  end if;
  t := team_by_code(p_code);
  insert into team_positions(team_id, lat, lng, accuracy_m, updated_at)
  values (t.id, p_lat, p_lng, p_acc, now())
  on conflict (team_id) do update
    set lat = excluded.lat, lng = excluded.lng,
        accuracy_m = excluded.accuracy_m, updated_at = now();
  insert into position_log(team_id, lat, lng, accuracy_m)
  values (t.id, p_lat, p_lng, p_acc);
end $$;

notify pgrst, 'reload schema';
