-- Nachtrag 32: Bugjagd 03.10.2026, Funde 9, 12, 14 und 16. Erzeugt von tools/migration_bugjagd2.py, nicht von Hand
-- ändern. Probelauf: tools/pruefstand/bugjagd2_db.py. Mehrfach ausführbar, löscht keine Daten.
--   Fund 9   register_participant nimmt den Geräte-Schlüssel des Handys (p_token). Gehört der Schlüssel schon
--            einer Person: Erfolg wie beim ersten Mal (Antwort im Funkloch verloren, auch nach Umbenennen). Nie einen neuen Schlüssel für
--            einen vorhandenen Namen. Ohne p_token wie bisher (alte Clients).
--   Fund 12  device_test_save nimmt nur Läufe in der Form, die tools/testlaeufe.py erwartet.
--   Fund 14  admin_set_test_mode: im laufenden Spiel mit Plätzen kein Umschalten, weder aus noch an.
--   Fund 16  submit_answer: leere Antwort ist außerhalb des Testmodus kein Fehlversuch.
-- Regel (SPIEL.md §9): nach jedem drop + create einer Funktion die Rechte ausdrücklich setzen.

-- Neue Signatur: die alte Fassung muss weg, sonst fände PostgREST zwei Kandidaten für einen Aufruf mit p_name
drop function if exists register_participant(text);

-- ---------- register_participant (aus 20260919100000_bugjagd.sql) ----------
create or replace function register_participant(p_name text, p_token text default null) returns json
language plpgsql security definer set search_path = public as $$
declare v_name text := btrim(regexp_replace(coalesce(p_name,''), '\s+', ' ', 'g'));
        -- zwei zufällige UUIDs ohne Striche: 64 Hex-Zeichen, 244 Bit Zufall
        v_token text := replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', '');
        v_da participants;
begin
  if length(v_name) < 2 or length(v_name) > 60 then
    raise exception 'Bitte einen Namen mit 2 bis 60 Zeichen eingeben.' using errcode='P0001';
  end if;
  if norm(v_name) = '' then
    raise exception 'Bitte einen Namen mit lateinischen Buchstaben oder Ziffern eingeben.' using errcode='P0001';
  end if;
  -- Nachtrag 32: das Handy schickt seinen Geräte-Schlüssel selbst mit (gleiches Format wie unserer)
  if p_token is not null then
    if p_token !~ '^[0-9a-f]{64}$' then
      raise exception 'Ungültiger Geräte-Schlüssel. Bitte die Seite neu laden.' using errcode='P0001';
    end if;
    v_token := p_token;
  end if;
  -- Läuft gerade das Auslosen, warten wir, bis es durch ist; die Statusabfrage
  -- danach sieht dann schon 'drawn'. Anmeldungen untereinander warten nicht.
  perform 1 from game_state where id = 1 for share;
  -- Wiederholung derselben Anmeldung (Antwort ging verloren): der Schlüssel gehört schon einer Person, also Erfolg
  -- wie beim ersten Mal, auch wenn inzwischen ausgelost ist oder die Spielleitung den Namen berichtigt hat (dann mit
  -- dem neuen Namen). Wer den Schlüssel nicht kennt, bekommt für einen vorhandenen Namen weiter den Fehler unten.
  if p_token is not null then
    select * into v_da from participants where token = p_token;
    if found then
      return json_build_object('name', v_da.name, 'token', v_da.token, 'count', (select count(*) from participants));
    end if;
  end if;
  if (select status from game_state where id = 1) <> 'registration' then
    raise exception 'Die Anmeldung ist geschlossen. Melde dich über den Hilfe-Knopf bei der Spielleitung, sie trägt dich nach.'
      using errcode='P0001';
  end if;
  if exists (select 1 from participants where name_key = norm(v_name)) then
    raise exception 'Dieser Name ist schon angemeldet. Hast du dich schon eingetragen? Dann bist du dabei.'
      using errcode='P0001';
  end if;
  begin
    insert into participants(name, name_key, token) values (v_name, norm(v_name), v_token);
  exception when unique_violation then
    -- Nachtrag 32: gleichzeitig angemeldet. Gehört der Schlüssel inzwischen einer Person, ist es dieselbe Anmeldung.
    select * into v_da from participants where token = v_token;
    if found then
      return json_build_object('name', v_da.name, 'token', v_da.token, 'count', (select count(*) from participants));
    end if;
    raise exception 'Dieser Name ist schon angemeldet. Hast du dich schon eingetragen? Dann bist du dabei.'
      using errcode='P0001';
  end;
  return json_build_object('name', v_name, 'token', v_token, 'count', (select count(*) from participants));
end $$;
grant execute on function register_participant(text, text) to anon, authenticated;

-- ---------- device_test_save (aus 20260930120000_geraetetest.sql) ----------
create or replace function device_test_save(p_key text, p_payload jsonb) returns json
language plpgsql security definer set search_path = public as $$
begin
  if p_key is null or p_key !~ '^[A-Z0-9]{12}$' then
    raise exception 'Ungültiger Schlüssel.' using errcode='P0001';
  end if;
  if p_payload is null or jsonb_typeof(p_payload) <> 'object' then
    raise exception 'Der Lauf fehlt.' using errcode='P0001';
  end if;
  -- Nachtrag 32: die Form, die tools/testlaeufe.py liest; sonst brach die Übersicht an einer einzigen Zeile ab
  if jsonb_typeof(p_payload->'tests') is distinct from 'object' or jsonb_typeof(p_payload->'bilanz') is distinct from 'object'
     or jsonb_typeof(p_payload->'suite') is distinct from 'number' then
    raise exception 'Der Lauf hat nicht die erwartete Form.' using errcode='P0001';
  end if;
  if exists (select 1 from jsonb_each(p_payload->'tests') e where jsonb_typeof(e.value) <> 'object') then
    raise exception 'Der Lauf hat nicht die erwartete Form.' using errcode='P0001';
  end if;
  if octet_length(p_payload::text) > 65536 then
    raise exception 'Der Lauf ist zu groß.' using errcode='P0001';
  end if;
  if not exists (select 1 from device_test_runs where run_key = p_key)
     and (select count(*) from device_test_runs) >= 2000 then
    raise exception 'Die Tabelle der Testläufe ist voll.' using errcode='P0001';
  end if;
  insert into device_test_runs (run_key, suite_version, label, payload)
  values (
    p_key,
    case when p_payload->>'suite' ~ '^[0-9]{1,6}$' then (p_payload->>'suite')::int else 0 end,
    left(coalesce(p_payload->>'label', ''), 80),
    p_payload)
  on conflict (run_key) do update
    set updated_at = now(), suite_version = excluded.suite_version,
        label = excluded.label, payload = excluded.payload;
  return json_build_object('ok', true, 'serverTime', now());
end $$;
grant execute on function device_test_save(text, jsonb) to anon, authenticated;

-- ---------- admin_set_test_mode (aus 20260918210000_testmodus.sql) ----------
create or replace function admin_set_test_mode(p_pin text, p_on boolean) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  -- Nachtrag 32: Plätze aus dem Testlauf überlebten das Ausschalten und standen dann in der echten Rangliste. Im
  -- laufenden Spiel mit Plätzen darum in keine Richtung umschalten (Entscheidung 04.10.2026: auch nicht einschalten,
  -- sonst käme die Spielleitung nur über „Fortschritt zurücksetzen“ wieder heraus). Ohne Platz ist beides frei.
  if exists (select 1 from game_state where id = 1 and status = 'running' and test_mode is distinct from coalesce(p_on, false))
     and exists (select 1 from finishes) then
    if coalesce(p_on, false) then
      raise exception 'Im laufenden Spiel gibt es schon Plätze. Den Testmodus jetzt einzuschalten würde die Rangliste durcheinanderbringen.'
        using errcode='P0001';
    end if;
    raise exception 'Im Testlauf gibt es schon Plätze. Erst im Reiter Daten löschen „Fortschritt zurücksetzen“, dann den Testmodus ausschalten.'
      using errcode='P0001';
  end if;
  update game_state set test_mode = coalesce(p_on, false) where id = 1;
  return admin_state(p_pin);
end $$;
grant execute on function admin_set_test_mode(text, boolean) to anon, authenticated;

-- ---------- submit_answer (aus 20260919070000_koffer_hinweis_spieldauer.sql) ----------
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
  -- Sperre: gleichzeitige Antworten desselben Teams laufen nacheinander, der Zähler stimmt
  select * into row_p from progress where team_id = t.id and station_id = cur.id for update;
  if row_p.checked_in_at is null then
    return json_build_object('ok', false, 'message', 'Erst am Ort einchecken, dann gibt es das Rätsel.',
      'state', team_state(p_code));
  end if;
  if not g.test_mode and row_p.locked_until is not null and row_p.locked_until > now() then
    return json_build_object('ok', false,
      'message', 'Denkpause: noch ' || ceil(extract(epoch from row_p.locked_until - now())) || ' Sekunden.',
      'state', team_state(p_code));
  end if;

  if g.test_mode or answer_ok(p_answer, cur.answer) then
    update progress set solved_at = now(), failed_attempts = 0, locked_until = null
      where team_id = t.id and station_id = cur.id;
    return json_build_object('ok', true,
      'message', case when g.test_mode then 'Testmodus: jede Antwort zählt. Eine Ziffer ist frei.'
                      else 'Richtig. Eine Ziffer ist frei.' end,
      'state', team_state(p_code));
  end if;

  -- Nachtrag 32: ein leeres Feld (oder nur Satzzeichen) ist kein Versuch. Erst hier, nach dem Erfolgszweig: im
  -- Testmodus zählt auch ein leeres Feld als richtig.
  if coalesce(norm(p_answer), '') = '' then
    return json_build_object('ok', false, 'message', 'Bitte gebt eine Antwort ein.', 'state', team_state(p_code));
  end if;

  v_attempts := case when row_p.locked_until is not null and row_p.locked_until <= now()
                     then 1 else row_p.failed_attempts + 1 end;
  v_locked := v_attempts >= 3;
  update progress
    set failed_attempts = case when v_locked then 0 else v_attempts end,
        locked_until    = case when v_locked then now() + interval '2 minutes' else null end,
        pauses          = pauses + case when v_locked then 1 else 0 end
    where team_id = t.id and station_id = cur.id;
  return json_build_object('ok', false,
    'message', case when v_locked then 'Dreimal falsch. Zwei Minuten Denkpause für euer Team.'
                        || case when btrim(cur.tip) <> '' then ' Danach könnt ihr einen Tipp aufdecken.' else '' end
                    else 'Leider falsch. Noch ' || (3 - v_attempts)
                         || case when 3 - v_attempts = 1 then ' Versuch.' else ' Versuche.' end end,
    'state', team_state(p_code));
end $$;
grant execute on function submit_answer(text, text) to anon, authenticated;

notify pgrst, 'reload schema';
