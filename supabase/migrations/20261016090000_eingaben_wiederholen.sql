-- Ausfallsicherheit (Spezifikation 2026-10-15, Abschnitt 3.3): Eingaben im Funkloch. Erzeugt von
-- tools/migration_eingaben.py, nicht von Hand ändern. Probelauf: tools/pruefstand/eingaben_db.py.
-- Mehrfach ausführbar, löscht keine Daten. Verträglich mit der vorigen App-Fassung (p_position mit default).
--   submit_answer  nimmt p_position (Station, an der getippt wurde): ist das Team inzwischen weiter, wird nie gegen
--                  das nächste Rätsel geprüft. Dieselbe falsche Antwort wie zuletzt (norm, je Team und Station)
--                  zählt nicht noch einmal und bekommt dieselbe Antwort.
--   check_in       schon eingecheckt: dieselbe Erfolgsantwort, ohne die Entfernung neu zu prüfen.
-- Regel (SPIEL.md §9): nach jedem drop + create einer Funktion die Rechte ausdrücklich setzen.

-- norm() der letzten gezählten falschen Antwort an dieser Station
alter table progress add column if not exists last_wrong text;

-- Neue Signatur: die alte Fassung muss weg, sonst fände PostgREST mit zwei Argumenten zwei Kandidaten (PGRST203)
drop function if exists submit_answer(text, text);

-- ---------- submit_answer (aus 20261004100000_bugjagd2.sql) ----------
create or replace function submit_answer(p_code text, p_answer text, p_position int default null)
returns json language plpgsql security definer set search_path = public as $$
declare t teams; g game_state; cur stations; row_p progress;
        v_attempts int; v_locked boolean;
        fr stations; fr_p progress; v_norm text := coalesce(norm(p_answer), ''); v_rest int;
begin
  t := team_by_code(p_code);
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
end $$;
grant execute on function submit_answer(text, text, int) to anon, authenticated;

-- ---------- check_in (aus 20260918210000_testmodus.sql) ----------
create or replace function check_in(p_code text, p_lat double precision,
                                    p_lng double precision, p_acc double precision)
returns json language plpgsql security definer set search_path = public as $$
declare t teams; g game_state; cur stations; d double precision; tol double precision;
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
end $$;
-- Signatur unverändert: die Rechte bleiben.

notify pgrst, 'reload schema';
