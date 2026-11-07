-- Bugjagd 07.11.2026 (SPIEL.md §25), Funde 2, 3 und 7. Läuft nach 20261107090000_bugjagd3.sql, hängt aber nicht davon
-- ab. Mehrfach ausführbar, löscht keine Daten, ändert keine Signatur (create or replace behält die Rechte; sie werden
-- trotzdem ausdrücklich gesetzt, SPIEL.md §9). Vorlage: die Live-Fassungen in supabase/schema/funktionen/.
-- Probelauf: tools/pruefstand/bugjagd4_db.py, dazu rechte_db.py. Einspielen: python tools/sql.py <datei>, danach
-- python tools/schema_abzug.py.
--
-- Fund 2: admin_finish setzte den Status aus jedem Zustand auf finished. Ein zweites Leitungsgerät mit offenem
--   Beenden-Dialog machte so aus einem gerade zurückgesetzten (drawn) oder geleerten Spiel (registration) ein
--   beendetes. Jetzt nur noch aus running, geprüft unter Zeilensperre wie in admin_draw.
-- Fund 3: admin_reset setzte auch aus registration auf drawn; ohne Teams war die Anmeldung dann zu. Jetzt lehnt es in
--   registration ab, ebenfalls unter Zeilensperre (ein ungesperrtes Lesen sähe unter READ COMMITTED noch den alten
--   Stand, wenn admin_clear_participants gleichzeitig läuft).
-- Fund 7: admin_save_station nahm jede Zahl als Koordinate. Jetzt Breite -90 bis 90 und Länge -180 bis 180 (wie
--   admin_set_start); null bleibt erlaubt (Station ohne Standort, die App zeigt dann "Ohne Koordinaten").

-- ==================== Fund 2: admin_finish nur aus running ====================
create or replace function public.admin_finish(p_pin text)
 returns json
 language plpgsql
 security definer
 set search_path to 'public'
as $function$
declare v_status text;
begin
  perform require_admin(p_pin);
  select status into v_status from game_state where id = 1 for update;
  if v_status is distinct from 'running' then
    raise exception 'Beenden geht nur im laufenden Spiel. Ein anderes Gerät hat den Spielstand inzwischen geändert.' using errcode='P0001';
  end if;
  update game_state set status = 'finished', finished_at = now() where id = 1;
  -- Standortdaten bleiben absichtlich stehen, damit die Routen auswertbar sind.
  -- Löschen über admin_clear_positions ("Standortdaten löschen").
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_finish(p_pin text) from public, anon, authenticated;
grant execute on function public.admin_finish(p_pin text) to public, anon, authenticated;

-- ==================== Fund 3: admin_reset nicht aus registration ====================
create or replace function public.admin_reset(p_pin text)
 returns json
 language plpgsql
 security definer
 set search_path to 'public'
as $function$
declare v_status text;
begin
  perform require_admin(p_pin);
  select status into v_status from game_state where id = 1 for update;
  if v_status = 'registration' then
    raise exception 'Vor dem Auslosen gibt es nichts zurückzusetzen.' using errcode='P0001';
  end if;
  delete from progress where true;
  delete from finishes where true;
  delete from team_positions where true;
  delete from position_log where true;
  update game_state set status = 'drawn', started_at = null, finished_at = null,
    winner_team_id = null where id = 1;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_reset(p_pin text) from public, anon, authenticated;
grant execute on function public.admin_reset(p_pin text) to public, anon, authenticated;

-- ==================== Fund 7: admin_save_station mit Wertebereich ====================
create or replace function public.admin_save_station(p_pin text, p_id uuid, p_name text, p_lat double precision, p_lng double precision, p_radius integer, p_hint text, p_riddle text, p_answer text, p_digit integer, p_tip text default ''::text, p_reveal_start integer default null::integer, p_reveal_clear integer default null::integer)
 returns json
 language plpgsql
 security definer
 set search_path to 'public'
as $function$
begin
  perform require_admin(p_pin);
  if (p_lat is not null and not (p_lat between -90 and 90)) or (p_lng is not null and not (p_lng between -180 and 180)) then
    raise exception 'Die Breite muss zwischen -90 und 90 liegen, die Länge zwischen -180 und 180.' using errcode='P0001';
  end if;
  if (p_reveal_start is null) <> (p_reveal_clear is null) then
    raise exception 'Für das Entschlüsseln braucht es beide Entfernungen oder keine.' using errcode='P0001';
  end if;
  if p_reveal_start is not null and (p_reveal_clear <= 0 or p_reveal_start <= p_reveal_clear or p_reveal_start > 5000) then
    raise exception 'Der Name muss weiter draußen beginnen, als er lesbar wird (höchstens 5000 m).' using errcode='P0001';
  end if;
  update stations_alle set
    name = coalesce(nullif(btrim(p_name),''), name),
    lat = p_lat, lng = p_lng,
    radius_m = greatest(5, coalesce(p_radius, 50)),
    location_hint = coalesce(p_hint, ''),
    riddle = coalesce(p_riddle, ''),
    answer = coalesce(p_answer, ''),
    digit = greatest(0, least(9, coalesce(p_digit, 0))),
    tip = btrim(coalesce(p_tip, '')),
    reveal_start_m = p_reveal_start, reveal_clear_m = p_reveal_clear
  where id = p_id;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_save_station(p_pin text, p_id uuid, p_name text, p_lat double precision, p_lng double precision, p_radius integer, p_hint text, p_riddle text, p_answer text, p_digit integer, p_tip text, p_reveal_start integer, p_reveal_clear integer) from public, anon, authenticated;
grant execute on function public.admin_save_station(p_pin text, p_id uuid, p_name text, p_lat double precision, p_lng double precision, p_radius integer, p_hint text, p_riddle text, p_answer text, p_digit integer, p_tip text, p_reveal_start integer, p_reveal_clear integer) to public, anon, authenticated;
