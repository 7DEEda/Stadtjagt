-- W5, 03.11.2026: Eingaben nur noch von der Teamleitung auf ihrem Handy (Geräte-Schlüssel) oder mit Admin-PIN.
-- Bisher reichte bei jeder Eingabe der Team-Code; wer ihn von Hand eintippte, konnte neben der Teamleitung eingeben.
-- Ausgangspunkt ist der Schema-Abzug (supabase/schema/funktionen/), der mit der Live-Datenbank übereinstimmt (03.11.).
-- Mehrfach ausführbar, löscht keine Daten. Probelauf: tools/pruefstand/w5_eingaben_db.py (--ohne zeigt rot).
-- Nicht ohne Friedrichs Ja einspielen. Reihenfolge: erst die App (sendet p_token und p_pin, fällt bei einer Datenbank
-- ohne diese Migration von selbst auf den alten Aufruf zurück), dann diese Migration. Eine ältere App ohne Schlüssel
-- kann danach nicht mehr eingeben.
--
--  1. team_eingabe(p_code, p_token, p_pin): intern (nicht für anon). Team per Code wie team_by_code; dann muss
--     p_token der Geräte-Schlüssel der aktuellen Teamleitung dieses Teams sein, oder p_pin die Admin-PIN (Notweg der
--     Spielleitung am Tablet, require_admin). Sonst Fehler "Eingeben kann nur die Teamleitung auf ihrem eigenen Handy."
--  2. check_in, submit_answer, reveal_tip, submit_final, team_selfie, team_selfie_skip, team_set_leader,
--     report_position: je zwei neue Parameter p_token und p_pin (Vorgabe null) am Ende; die alte Fassung wird gedroppt
--     (sonst zwei Überladungen, PGRST203). Im Rumpf ersetzt team_eingabe(...) die Zeile team_by_code(p_code), sonst
--     ist alles wie im Schema-Abzug.
--  3. Unverändert: team_state (lesen bleibt mit Code), team_photo, member_state, leader_code, admin_*.

CREATE OR REPLACE FUNCTION public.team_eingabe(p_code text, p_token text, p_pin text)
 RETURNS teams
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams;
begin
  t := team_by_code(p_code);
  if coalesce(p_token, '') <> '' and t.leader_participant_id is not null
     and exists (select 1 from participants where id = t.leader_participant_id and token = p_token) then
    return t;
  end if;
  if coalesce(btrim(p_pin), '') <> '' then
    perform require_admin(p_pin);
    return t;
  end if;
  raise exception 'Eingeben kann nur die Teamleitung auf ihrem eigenen Handy.' using errcode = 'P0001';
end $function$;
revoke all on function public.team_eingabe(p_code text, p_token text, p_pin text) from public, anon, authenticated;

drop function if exists public.check_in(text, double precision, double precision, double precision);

CREATE OR REPLACE FUNCTION public.check_in(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_token text DEFAULT NULL::text, p_pin text DEFAULT NULL::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; g game_state; cur stations; d double precision; tol double precision;
begin
  t := team_eingabe(p_code, p_token, p_pin);
  select * into g from game_state where id = 1;
  if g.status <> 'running' then
    return json_build_object('ok', false, 'message', 'Das Spiel läuft gerade nicht.', 'state', team_state(p_code));
  end if;
  cur := current_station(t.id);
  if cur.id is null then
    return json_build_object('ok', false, 'message', 'Alle Stationen sind gelöst.', 'state', team_state(p_code));
  end if;
  -- Schon eingecheckt (Wiederholung nach verlorener Antwort): gleiche Antwort, ohne die Entfernung neu zu prüfen;
  -- das GPS darf inzwischen gesprungen sein
  if exists (select 1 from progress where team_id = t.id and station_id = cur.id and checked_in_at is not null) then
    return json_build_object('ok', true,
      'message', case when g.test_mode then 'Testmodus: eingecheckt ohne Entfernungsprüfung.'
                      else 'Angekommen. Das Rätsel ist frei.' end,
      'state', team_state(p_code));
  end if;
  if not g.test_mode then
    if cur.lat is null or cur.lng is null then
      return json_build_object('ok', false, 'message',
        'Für diese Station sind noch keine Koordinaten gesetzt. Bitte die Spielleitung fragen.',
        'state', team_state(p_code));
    end if;
    if p_lat is null or p_lng is null then
      return json_build_object('ok', false, 'message', 'Ohne Standort kein Check-in. Bitte GPS freigeben.',
        'state', team_state(p_code));
    end if;
    d := dist_m(p_lat, p_lng, cur.lat, cur.lng);
    tol := cur.radius_m + least(greatest(coalesce(p_acc,0),0), 25);
    if d > tol then
      return json_build_object('ok', false, 'distance', round(d::numeric,0),
        'message', 'Noch nicht am Ziel: ' || round(d::numeric,0) || ' m entfernt.',
        'state', team_state(p_code));
    end if;
  end if;
  insert into progress(team_id, station_id, checked_in_at)
  values (t.id, cur.id, now())
  on conflict (team_id, station_id) do update set checked_in_at = coalesce(progress.checked_in_at, now());
  return json_build_object('ok', true, 'distance', round(d::numeric,0),
    'message', case when g.test_mode then 'Testmodus: eingecheckt ohne Entfernungsprüfung.'
                    else 'Angekommen. Das Rätsel ist frei.' end,
    'state', team_state(p_code));
end $function$;
revoke all on function public.check_in(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_token text, p_pin text) from public, anon, authenticated;
grant execute on function public.check_in(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_token text, p_pin text) to public, anon, authenticated;

drop function if exists public.submit_answer(text, text, integer);

CREATE OR REPLACE FUNCTION public.submit_answer(p_code text, p_answer text, p_position integer DEFAULT NULL::integer, p_token text DEFAULT NULL::text, p_pin text DEFAULT NULL::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; g game_state; cur stations; row_p progress;
        v_attempts int; v_locked boolean;
        fr stations; fr_p progress; v_norm text := coalesce(norm(p_answer), ''); v_rest int;
begin
  t := team_eingabe(p_code, p_token, p_pin);
  select * into g from game_state where id = 1;
  if g.status <> 'running' then
    return json_build_object('ok', false, 'message', 'Das Spiel läuft gerade nicht.', 'state', team_state(p_code));
  end if;
  cur := current_station(t.id);

  -- Wiederholung: die App nennt die Station, an der getippt wurde. Ist das Team inzwischen weiter (die erste Antwort
  -- kam an, nur ihre Antwort nicht; oder die Spielleitung hat gewertet), nie gegen das nächste Rätsel prüfen.
  if p_position is not null and (cur.id is null or cur.position <> p_position) then
    select * into fr from stations where position = p_position;
    select * into fr_p from progress where team_id = t.id and station_id = fr.id;
    if fr_p.solved_at is not null and (g.test_mode or answer_ok(p_answer, fr.answer)) then
      return json_build_object('ok', true,
        'message', case when g.test_mode then 'Testmodus: jede Antwort zählt. Eine Ziffer ist frei.'
                      else 'Richtig. Eine Ziffer ist frei.' end,
        'state', team_state(p_code));
    end if;
    return json_build_object('ok', false,
      'message', case when fr_p.solved_at is not null then 'Diese Station ist schon gelöst.'
                      else 'Das Rätsel hat gewechselt. Lest es noch mal.' end,
      'state', team_state(p_code));
  end if;

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
    update progress set solved_at = now(), failed_attempts = 0, locked_until = null, last_wrong = null
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

  -- Dieselbe falsche Antwort wie zuletzt zählt nicht noch einmal: im Funkloch kam die erste an, nur ihre Antwort
  -- nicht. Antwortet genau wie beim ersten Mal. Eine laufende Denkpause greift schon oben.
  if v_norm = row_p.last_wrong then
    v_rest := case when row_p.locked_until is not null and row_p.locked_until <= now() then 3
                   else 3 - row_p.failed_attempts end;
    return json_build_object('ok', false,
      'message', 'Leider falsch. Noch ' || v_rest || case when v_rest = 1 then ' Versuch.' else ' Versuche.' end,
      'state', team_state(p_code));
  end if;

  v_attempts := case when row_p.locked_until is not null and row_p.locked_until <= now()
                     then 1 else row_p.failed_attempts + 1 end;
  v_locked := v_attempts >= 3;
  update progress
    set failed_attempts = case when v_locked then 0 else v_attempts end,
        locked_until    = case when v_locked then now() + interval '2 minutes' else null end,
        pauses          = pauses + case when v_locked then 1 else 0 end,
        last_wrong      = v_norm
    where team_id = t.id and station_id = cur.id;
  return json_build_object('ok', false,
    'message', case when v_locked then 'Dreimal falsch. Zwei Minuten Denkpause für euer Team.'
                        || case when btrim(cur.tip) <> '' then ' Danach könnt ihr einen Tipp aufdecken.' else '' end
                    else 'Leider falsch. Noch ' || (3 - v_attempts)
                         || case when 3 - v_attempts = 1 then ' Versuch.' else ' Versuche.' end end,
    'state', team_state(p_code));
end $function$;
revoke all on function public.submit_answer(p_code text, p_answer text, p_position integer, p_token text, p_pin text) from public, anon, authenticated;
grant execute on function public.submit_answer(p_code text, p_answer text, p_position integer, p_token text, p_pin text) to public, anon, authenticated;

drop function if exists public.reveal_tip(text);

CREATE OR REPLACE FUNCTION public.reveal_tip(p_code text, p_token text DEFAULT NULL::text, p_pin text DEFAULT NULL::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; g game_state; cur stations; row_p progress;
begin
  t := team_eingabe(p_code, p_token, p_pin);
  select * into g from game_state where id = 1;
  if g.status <> 'running' then
    return json_build_object('ok', false, 'message', 'Das Spiel läuft gerade nicht.', 'state', team_state(p_code));
  end if;
  cur := current_station(t.id);
  select * into row_p from progress where team_id = t.id and station_id = cur.id;
  if cur.id is null or row_p.checked_in_at is null then
    return json_build_object('ok', false, 'message', 'Hier gibt es gerade keinen Tipp.', 'state', team_state(p_code));
  end if;
  if btrim(cur.tip) = '' then
    return json_build_object('ok', false, 'message', 'Für dieses Rätsel gibt es keinen Tipp.', 'state', team_state(p_code));
  end if;
  if not g.test_mode and row_p.pauses < 1 then
    return json_build_object('ok', false, 'message', 'Den Tipp gibt es nach der ersten Denkpause.', 'state', team_state(p_code));
  end if;
  update progress set tip_at = coalesce(tip_at, now()) where team_id = t.id and station_id = cur.id;
  return json_build_object('ok', true, 'message', 'Tipp aufgedeckt.', 'state', team_state(p_code));
end $function$;
revoke all on function public.reveal_tip(p_code text, p_token text, p_pin text) from public, anon, authenticated;
grant execute on function public.reveal_tip(p_code text, p_token text, p_pin text) to public, anon, authenticated;

drop function if exists public.submit_final(text, text, double precision, double precision, double precision);

CREATE OR REPLACE FUNCTION public.submit_final(p_code text, p_value text, p_lat double precision DEFAULT NULL::double precision, p_lng double precision DEFAULT NULL::double precision, p_acc double precision DEFAULT NULL::double precision, p_token text DEFAULT NULL::text, p_pin text DEFAULT NULL::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; g game_state; v_total int; v_solved int; v_expected text; v_place int;
        ziel stations; d double precision; tol double precision;
begin
  t := team_eingabe(p_code, p_token, p_pin);
  select place into v_place from finishes where team_id = t.id;

  if v_place is null then
    select * into g from game_state where id = 1;
    if g.status <> 'running' then
      return json_build_object('ok', false, 'won', false, 'message', 'Das Spiel läuft gerade nicht.',
        'state', team_state(p_code));
    end if;
    select count(*) into v_total from stations;
    select count(*) into v_solved from progress pr join stations s on s.id = pr.station_id where pr.team_id = t.id and pr.solved_at is not null;
    if v_total = 0 or v_solved <> v_total then
      return json_build_object('ok', false, 'won', false, 'message', 'Ihr habt noch nicht alle Ziffern.',
        'state', team_state(p_code));
    end if;

    -- Am Koffer stehen: gleiche Regel wie beim Check-in, im Testmodus nicht
    if not g.test_mode then
      select * into ziel from stations order by position desc limit 1;
      if ziel.lat is not null and ziel.lng is not null then
        if p_lat is null or p_lng is null then
          return json_build_object('ok', false, 'won', false,
            'message', 'Ohne Standort kein Koffer. Bitte GPS freigeben.', 'state', team_state(p_code));
        end if;
        d := dist_m(p_lat, p_lng, ziel.lat, ziel.lng);
        tol := ziel.radius_m + least(greatest(coalesce(p_acc,0),0), 25);
        if d > tol then
          return json_build_object('ok', false, 'won', false, 'distance', round(d::numeric,0),
            'message', 'Den Code gebt ihr am Koffer ein: noch ' || round(d::numeric,0) || ' m bis dahin.',
            'state', team_state(p_code));
        end if;
      end if;
    end if;

    select string_agg(s.digit::text, '' order by s.position) into v_expected from stations s;
    v_expected := v_expected || ((select sum(digit) from stations) % 10)::text;
    if regexp_replace(coalesce(p_value,''), '[^0-9]', '', 'g') <> v_expected then
      return json_build_object('ok', false, 'won', false,
        'message', 'Der Koffer bleibt zu. Prüft die letzte Ziffer.', 'state', team_state(p_code));
    end if;

    -- Platz vergeben. Die Sperre lässt gleichzeitige Eingaben warten, bis die
    -- vorige fertig ist; danach sieht die nächste deren Platz schon.
    perform 1 from game_state where id = 1 for update;
    select place into v_place from finishes where team_id = t.id;   -- doppelt abgeschickt?
    if v_place is null then
      select coalesce(max(place), 0) + 1 into v_place from finishes;
      insert into finishes(team_id, place) values (t.id, v_place);
      if v_place = 1 then
        update game_state set winner_team_id = t.id where id = 1;
      end if;
    end if;
  end if;

  select * into g from game_state where id = 1;
  return json_build_object('ok', true, 'won', v_place <= g.prize_count, 'place', v_place,
    'message', case when v_place <= g.prize_count
                    then 'Der Koffer ist offen. Platz ' || v_place || '!'
                    else 'Richtig, aber die Koffer sind vergeben. Ihr seid auf Platz ' || v_place || '.' end,
    'state', team_state(p_code));
end $function$;
revoke all on function public.submit_final(p_code text, p_value text, p_lat double precision, p_lng double precision, p_acc double precision, p_token text, p_pin text) from public, anon, authenticated;
grant execute on function public.submit_final(p_code text, p_value text, p_lat double precision, p_lng double precision, p_acc double precision, p_token text, p_pin text) to public, anon, authenticated;

drop function if exists public.team_selfie(text, integer, text, text);

CREATE OR REPLACE FUNCTION public.team_selfie(p_code text, p_position integer, p_photo text, p_thumb text, p_token text DEFAULT NULL::text, p_pin text DEFAULT NULL::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; s stations; pr progress; v_photo bytea; v_thumb bytea;
begin
  t := team_eingabe(p_code, p_token, p_pin);
  if not (select selfie_on from game_state where id = 1) then
    raise exception 'Gruppenfotos sind ausgeschaltet.' using errcode='P0001';
  end if;
  select * into s from stations where position = p_position;
  if not found then raise exception 'Diese Station gibt es nicht.' using errcode='P0001'; end if;
  select * into pr from progress where team_id = t.id and station_id = s.id for update;
  if not found or pr.solved_at is null then
    raise exception 'Erst das Rätsel lösen, dann das Foto.' using errcode='P0001';
  end if;
  begin
    v_photo := decode(p_photo, 'base64'); v_thumb := decode(p_thumb, 'base64');
  exception when others then
    raise exception 'Das Foto ist beschädigt angekommen.' using errcode='P0001';
  end;
  if v_photo is null or v_thumb is null
     or substring(v_photo from 1 for 3) <> '\xffd8ff'::bytea
     or substring(v_thumb from 1 for 3) <> '\xffd8ff'::bytea then
    raise exception 'Das ist kein JPEG-Foto.' using errcode='P0001';
  end if;
  if octet_length(v_photo) > 716800 or octet_length(v_thumb) > 61440 then
    raise exception 'Das Foto ist zu groß.' using errcode='P0001';
  end if;
  -- Ersetzen nur, bis das Team an einer späteren Station eingecheckt hat. Nachreichen geht immer.
  if exists (select 1 from station_photos where team_id = t.id and station_id = s.id)
     and exists (select 1 from progress p2 join stations s2 on s2.id = p2.station_id
                 where p2.team_id = t.id and s2.position > s.position and p2.checked_in_at is not null) then
    raise exception 'Dieses Foto lässt sich nicht mehr ersetzen, ihr seid schon an der nächsten Station.' using errcode='P0001';
  end if;
  insert into station_photos (team_id, station_id, photo, thumb) values (t.id, s.id, v_photo, v_thumb)
    on conflict (team_id, station_id) do update
      set photo = excluded.photo, thumb = excluded.thumb, taken_at = now();
  update progress set selfie_at = coalesce(selfie_at, now()) where team_id = t.id and station_id = s.id;
  return team_state(p_code);
end $function$;
revoke all on function public.team_selfie(p_code text, p_position integer, p_photo text, p_thumb text, p_token text, p_pin text) from public, anon, authenticated;
grant execute on function public.team_selfie(p_code text, p_position integer, p_photo text, p_thumb text, p_token text, p_pin text) to public, anon, authenticated;

drop function if exists public.team_selfie_skip(text, integer);

CREATE OR REPLACE FUNCTION public.team_selfie_skip(p_code text, p_position integer, p_token text DEFAULT NULL::text, p_pin text DEFAULT NULL::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams;
begin
  t := team_eingabe(p_code, p_token, p_pin);
  update progress pr set selfie_at = coalesce(pr.selfie_at, now())
    from stations s
    where s.id = pr.station_id and s.position = p_position and pr.team_id = t.id and pr.solved_at is not null;
  if not found then raise exception 'Erst das Rätsel lösen.' using errcode='P0001'; end if;
  return team_state(p_code);
end $function$;
revoke all on function public.team_selfie_skip(p_code text, p_position integer, p_token text, p_pin text) from public, anon, authenticated;
grant execute on function public.team_selfie_skip(p_code text, p_position integer, p_token text, p_pin text) to public, anon, authenticated;

drop function if exists public.team_set_leader(text, text);

CREATE OR REPLACE FUNCTION public.team_set_leader(p_code text, p_name text, p_token text DEFAULT NULL::text, p_pin text DEFAULT NULL::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; v_id uuid; v_token text;
begin
  t := team_eingabe(p_code, p_token, p_pin);
  select id, token into v_id, v_token from participants where team_id = t.id and name_key = norm(p_name);
  if v_id is null then
    raise exception 'Diese Person ist nicht in eurem Team.' using errcode='P0001';
  end if;
  -- Audit 25.10.: ohne Geräte-Schlüssel kommt die neue Leitung auf ihrem Handy nicht in die Team-Ansicht, das alte
  -- Handy ist aber schon abgemeldet. Die Spielleitung kann trotzdem jeden wählen (admin_set_leader, Notweg).
  if v_token is null then
    raise exception 'Diese Person hat sich nicht selbst angemeldet und kann nicht eingeben.' using errcode='P0001';
  end if;
  update teams set leader_participant_id = v_id where id = t.id;
  return team_state(p_code);
end $function$;
revoke all on function public.team_set_leader(p_code text, p_name text, p_token text, p_pin text) from public, anon, authenticated;
grant execute on function public.team_set_leader(p_code text, p_name text, p_token text, p_pin text) to public, anon, authenticated;

drop function if exists public.report_position(text, double precision, double precision, double precision, text);

CREATE OR REPLACE FUNCTION public.report_position(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_kompass text DEFAULT NULL::text, p_token text DEFAULT NULL::text, p_pin text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams;
begin
  if (select status from game_state where id = 1) <> 'running' then return; end if;
  if p_lat is null or p_lng is null or abs(p_lat) > 90 or abs(p_lng) > 180
     or (abs(p_lat) < 0.01 and abs(p_lng) < 0.01)
     or p_acc is null or p_acc <= 0 or p_acc > 1000 then
    return;
  end if;
  t := team_eingabe(p_code, p_token, p_pin);
  insert into team_positions(team_id, lat, lng, accuracy_m, updated_at, kompass)
  values (t.id, p_lat, p_lng, p_acc, now(), case when p_kompass in ('ok', 'unzuverlaessig') then p_kompass end)
  on conflict (team_id) do update
    set lat = excluded.lat, lng = excluded.lng, accuracy_m = excluded.accuracy_m, updated_at = now(), kompass = excluded.kompass;
  insert into position_log(team_id, lat, lng, accuracy_m) values (t.id, p_lat, p_lng, p_acc);
end $function$;
revoke all on function public.report_position(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_kompass text, p_token text, p_pin text) from public, anon, authenticated;
grant execute on function public.report_position(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_kompass text, p_token text, p_pin text) to public, anon, authenticated;

notify pgrst, 'reload schema';
