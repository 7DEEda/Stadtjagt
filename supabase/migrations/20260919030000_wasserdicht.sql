-- ============================================================
--  STADTJAGD – Nachtrag 13: Randfälle abgedichtet
--
--  Ergebnis der Durchsicht des Konzepts am 18.09.2026:
--
--  1. Koffer-Code nur am Ziel: submit_final verlangt jetzt wie check_in eine
--     Position im Radius der letzten Station. Vorher konnte ein Team, das die
--     Ziffern per Nachricht bekam, von überall einen Platz holen. Die alte
--     Fassung ohne Position fällt weg.
--  2. admin_start nur aus 'drawn' und nur bei ausgeschaltetem Testmodus.
--     Vorher prüfte nur der Knopf den Zustand; ein Start aus 'finished' hätte
--     die Plätze gelöscht, ein Start im Testmodus hätte den Tag ruiniert.
--  3. admin_resume: 'finished' zurück auf 'running', nichts wird gelöscht.
--     Für ein versehentlich bestätigtes "Spiel beenden".
--  4. admin_solve_station: die aktuelle Station eines Teams als gelöst werten
--     (Check-in und Rätsel), wenn ein Rätsel klemmt.
--  5. Mehrere Lösungen je Rätsel, mit | getrennt ("5|fünf|five").
--  6. admin_delete_test_participants: nur die Namen mit "(Test)" entfernen,
--     echte Anmeldungen bleiben.
--  7. admin_rename_participant prüft Länge und Doppelte wie die Anmeldung.
--  8. norm faltet Großbuchstaben mit Umlaut und Akzent selbst, damit "FÜNF"
--     auch dann "fünf" trifft, wenn lower() der Datenbank-Locale das nicht
--     tut (Locale C: lower('FÜNF') = 'fÜnf').
--
--  Einspielen: nach Nachtrag 12. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

-- ---------- 8. norm unabhängig von der Locale ----------
create or replace function norm(t text) returns text
language sql immutable as $$
  select regexp_replace(
    replace(replace(replace(replace(replace(replace(replace(
      lower(translate(coalesce(t,''), 'ÄÖÜÁÉÈ', 'äöüáéè')),
      'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss'),'á','a'),'é','e'),'è','e'),
    '[^a-z0-9]+', '', 'g');
$$;

-- ---------- 1. Koffer-Code nur am Ziel ----------
drop function if exists submit_final(text, text);

create or replace function submit_final(p_code text, p_value text,
                                        p_lat double precision default null,
                                        p_lng double precision default null,
                                        p_acc double precision default null)
returns json language plpgsql security definer set search_path = public as $$
declare t teams; g game_state; v_total int; v_solved int; v_expected text; v_place int;
        ziel stations; d double precision; tol double precision;
begin
  t := team_by_code(p_code);
  select place into v_place from finishes where team_id = t.id;

  if v_place is null then
    select * into g from game_state where id = 1;
    if g.status <> 'running' then
      return json_build_object('ok', false, 'won', false, 'message', 'Das Spiel läuft gerade nicht.',
        'state', team_state(p_code));
    end if;
    select count(*) into v_total from stations;
    select count(*) into v_solved from progress where team_id = t.id and solved_at is not null;
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
end $$;

grant execute on function submit_final(text, text, double precision, double precision, double precision)
  to anon, authenticated;

-- ---------- 2. Starten nur aus 'drawn', nie im Testmodus ----------
create or replace function admin_start(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
declare v_missing text; g game_state;
begin
  perform require_admin(p_pin);
  select * into g from game_state where id = 1;
  if g.status <> 'drawn' then
    raise exception 'Starten geht nur, wenn Teams ausgelost sind und das Spiel noch nicht läuft.'
      using errcode='P0001';
  end if;
  if g.test_mode then
    raise exception 'Der Testmodus ist noch an. Erst im Reiter Stationen ausschalten, dann starten.'
      using errcode='P0001';
  end if;
  if not exists (select 1 from teams) then
    raise exception 'Erst Teams auslosen.' using errcode='P0001';
  end if;
  select string_agg(position::text, ', ' order by position) into v_missing
    from stations where lat is null or lng is null;
  delete from finishes where true;
  update game_state set status = 'running', started_at = now(),
    finished_at = null, winner_team_id = null where id = 1;
  return json_build_object('warning',
    case when v_missing is null then null
         else 'Achtung: Station(en) ' || v_missing || ' haben keine Koordinaten.' end,
    'state', admin_state(p_pin));
end $$;

-- ---------- 3. Versehentlich beendet: weiterspielen ----------
create or replace function admin_resume(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  if (select status from game_state where id = 1) <> 'finished' then
    raise exception 'Fortsetzen geht nur, wenn das Spiel beendet ist.' using errcode='P0001';
  end if;
  update game_state set status = 'running', finished_at = null where id = 1;
  return admin_state(p_pin);
end $$;

grant execute on function admin_resume(text) to anon, authenticated;

-- ---------- 4. Rätsel für ein Team werten ----------
create or replace function admin_solve_station(p_pin text, p_team uuid) returns json
language plpgsql security definer set search_path = public as $$
declare cur stations;
begin
  perform require_admin(p_pin);
  cur := current_station(p_team);
  if cur.id is null then raise exception 'Dieses Team hat alle Stationen gelöst.' using errcode='P0001'; end if;
  insert into progress(team_id, station_id, checked_in_at, solved_at, failed_attempts, locked_until)
    values (p_team, cur.id, now(), now(), 0, null)
    on conflict (team_id, station_id) do update
      set checked_in_at = coalesce(progress.checked_in_at, now()), solved_at = now(),
          failed_attempts = 0, locked_until = null;
  return admin_state(p_pin);
end $$;

grant execute on function admin_solve_station(text, uuid) to anon, authenticated;

-- ---------- 5. Mehrere Lösungen je Rätsel ----------
-- true, wenn die Antwort eine der mit | getrennten Lösungen trifft. Leere Teile zählen nie.
create or replace function answer_ok(p_answer text, p_solutions text) returns boolean
language sql immutable as $$
  select exists (
    select 1 from unnest(string_to_array(coalesce(p_solutions, ''), '|')) as l
    where norm(l) <> '' and norm(l) = norm(p_answer));
$$;

revoke all on function answer_ok(text, text) from public, anon, authenticated;

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

  if g.test_mode or answer_ok(p_answer, cur.answer) then
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

-- ---------- 6. Nur die Testdaten entfernen ----------
create or replace function admin_delete_test_participants(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
declare v_n int;
begin
  perform require_admin(p_pin);
  update teams t set leader_participant_id = null
    where leader_participant_id in (select id from participants where name like '%(Test)');
  delete from participants where name like '%(Test)';
  get diagnostics v_n = row_count;
  -- Teams, deren Leitung weg ist, bekommen eine neue aus den Verbliebenen
  update teams t set leader_participant_id = (
      select p.id from participants p where p.team_id = t.id order by random() limit 1)
    where t.leader_participant_id is null;
  return json_build_object('deleted', v_n, 'state', admin_state(p_pin));
end $$;

grant execute on function admin_delete_test_participants(text) to anon, authenticated;

-- ---------- 7. Umbenennen mit denselben Regeln wie die Anmeldung ----------
create or replace function admin_rename_participant(p_pin text, p_id uuid, p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare v_name text := btrim(regexp_replace(coalesce(p_name,''), '\s+', ' ', 'g'));
begin
  perform require_admin(p_pin);
  if length(v_name) < 2 or length(v_name) > 60 then
    raise exception 'Bitte einen Namen mit 2 bis 60 Zeichen eingeben.' using errcode='P0001';
  end if;
  if exists (select 1 from participants where name_key = norm(v_name) and id <> p_id) then
    raise exception 'Diesen Namen gibt es schon.' using errcode='P0001';
  end if;
  update participants set name = v_name, name_key = norm(v_name) where id = p_id;
  return admin_state(p_pin);
end $$;

notify pgrst, 'reload schema';
