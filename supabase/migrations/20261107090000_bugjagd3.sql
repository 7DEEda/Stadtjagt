-- Bugjagd 03.11.2026 (SPIEL.md §24), Funde 3, 7 und ein Nachtrag zu norm(). Läuft NACH W5
-- (20261103090000_w5_eingaben_schluessel.sql) und bricht ohne W5 ab. Mehrfach ausführbar, löscht keine Daten,
-- ändert keine Signatur. Erzeugt von einem Skript aus der W5-Migration (die acht Eingaben, team_eingabe) und den
-- Live-Fassungen in supabase/schema/funktionen/ (team_state, team_photo, admin_start, norm); nicht von Hand ändern.
-- Probelauf: tools/pruefstand/bugjagd3_db.py (spielt W5 davor ein), dazu rechte_db.py. Einspielen: erst die App,
-- dann W5, dann diese Datei (python tools/sql.py <datei>), danach python tools/schema_abzug.py.
--
-- Teil A (Fund 3): Bremse gegen das Durchprobieren von Team-Codes.
--   Ein falscher Code warf sofort eine Ausnahme; die nähme jeden Zähler mit zurück, weil PostgREST die Transaktion
--   bei einer Ausnahme zurückrollt. Darum fragt zuerst team_code_bremse: sie zählt falsche Codes je Quelle (Absender-
--   IP aus den Kopfzeilen) in team_code_fehlversuche und gibt den Fehlertext zurück, statt zu werfen.
--   - team_eingabe (W5, alle acht Eingaben laufen hindurch) gibt dann ein leeres Team zurück und merkt den Text in
--     sj.code_fehler; jede der acht Eingaben hat dafür genau eine Zeile mehr ("if t.id is null then ...").
--   - team_state und team_photo (lesen, ohne team_eingabe) fragen die Bremse direkt.
--   - Abgelehnt wird über team_code_abgelehnt: normales Ende mit HTTP 400 (response.status) und einer Antwort im
--     Format eines PostgREST-Fehlers. Die Transaktion wird festgeschrieben, die App sieht wie bisher
--     "Unbekannter Team-Code.".
--   Ab 30 falschen Codes je Quelle in 10 Minuten ist jeder Code von dort bis zum Ende des Fensters gesperrt, auch ein
--   richtiger (sonst bliebe ein Treffer erkennbar).
-- Teil B (Fund 7): abgelaufenes Foto-Löschdatum. admin_start warnt, wenn das Gruppenselfie an ist und das Löschdatum
--   heute oder früher liegt (Prager Zeit); team_selfie (W5-Fassung) lehnt dann ab, statt das Foto einzufügen und im
--   selben Aufruf wieder zu löschen.
-- Teil C (Nachtrag zweite Bugjagd): norm() bildet zuerst die vorkomponierte Form (NFC). Zerlegte Umlaute (NFD, etwa
--   aus einem Mac-PDF eingefügt) ergaben bisher "brucke" statt "bruecke": die Antwort passte nicht, ein Name galt
--   nicht als Dublette. Danach bekommen Personen, deren name_key nicht mehr norm(name) ist, den neuen Schlüssel, aber
--   nur, wenn ihn niemand sonst hat (sonst bleibt der alte, nichts bricht).
-- Regel (SPIEL.md §9): Rechte nach jeder Funktion ausdrücklich setzen.

do $w5$
begin
  if to_regprocedure('public.team_eingabe(text,text,text)') is null then
    raise exception 'Erst W5 einspielen (20261103090000_w5_eingaben_schluessel.sql), dann diese Migration.';
  end if;
end $w5$;

-- ==================== Teil A: Bremse für Team-Codes ====================

create table if not exists team_code_fehlversuche (
  quelle text primary key,
  seit   timestamptz not null default now(),   -- Beginn des 10-Minuten-Fensters
  anzahl int not null default 0
);
alter table team_code_fehlversuche enable row level security;
revoke all on table team_code_fehlversuche from public, anon, authenticated;

-- Quelle eines Aufrufs: cf-connecting-ip setzt Cloudflare vor Supabase (vom Absender nicht zu fälschen), sonst der
-- erste Eintrag von x-forwarded-for; ohne Kopfzeilen (SQL-Editor, Probelauf) 'ohne'.
create or replace function team_code_quelle() returns text
language plpgsql stable security definer set search_path = public as $$
declare h json;
begin
  begin
    h := coalesce(nullif(current_setting('request.headers', true), ''), '{}')::json;
  exception when others then h := '{}'::json;
  end;
  return left(coalesce(nullif(btrim(h->>'cf-connecting-ip'), ''),
                       nullif(btrim(split_part(coalesce(h->>'x-forwarded-for', ''), ',', 1)), ''),
                       'ohne'), 100);
end $$;
revoke all on function team_code_quelle() from public, anon, authenticated;

-- null, wenn der Code gilt und die Quelle nicht gesperrt ist; sonst der Text für die App. Ein falscher Code wird
-- gezählt (und bleibt gezählt, weil die Aufrufer danach nicht werfen). Leere Codes zählen nicht.
create or replace function team_code_bremse(p_code text) returns text
language plpgsql security definer set search_path = public as $$
declare v_quelle text := team_code_quelle(); f team_code_fehlversuche; v_min int;
        v_norm text := regexp_replace(upper(coalesce(p_code, '')), '[^A-Z0-9]', '', 'g');
        c_grenze constant int := 30; c_fenster constant interval := interval '10 minutes';
begin
  select * into f from team_code_fehlversuche where quelle = v_quelle;
  if found and f.anzahl >= c_grenze and f.seit > now() - c_fenster then
    v_min := greatest(1, ceil(extract(epoch from f.seit + c_fenster - now()) / 60))::int;
    return 'Zu viele falsche Team-Codes aus diesem Netz. Bitte in '
      || case when v_min = 1 then 'einer Minute' else v_min || ' Minuten' end || ' noch einmal versuchen.';
  end if;
  if v_norm <> '' and exists (select 1 from teams where regexp_replace(upper(code), '[^A-Z0-9]', '', 'g') = v_norm) then
    return null;
  end if;
  if v_norm <> '' then
    delete from team_code_fehlversuche where seit < now() - interval '1 hour';
    insert into team_code_fehlversuche as z (quelle, seit, anzahl) values (v_quelle, now(), 1)
      on conflict (quelle) do update set
        anzahl = case when z.seit <= now() - c_fenster then 1 else z.anzahl + 1 end,
        seit   = case when z.seit <= now() - c_fenster then now() else z.seit end;
  end if;
  return 'Unbekannter Team-Code.';
end $$;
revoke all on function team_code_bremse(text) from public, anon, authenticated;

-- Normales Ende mit HTTP 400: PostgREST schreibt die Transaktion fest (der Zähler bleibt), rpc() in der App liest
-- message wie bei einer Ausnahme. Ohne Text (aus sj.code_fehler leer) "Unbekannter Team-Code.".
create or replace function team_code_abgelehnt(p_text text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform set_config('response.status', '400', true);
  return json_build_object('code', 'P0001', 'message', coalesce(nullif(p_text, ''), 'Unbekannter Team-Code.'),
                           'details', null, 'hint', null);
end $$;
revoke all on function team_code_abgelehnt(text) from public, anon, authenticated;

-- ---------- team_eingabe (W5, mit Bremse) ----------
CREATE OR REPLACE FUNCTION public.team_eingabe(p_code text, p_token text, p_pin text)
 RETURNS teams
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; v_bremse text;
begin
  -- Bugjagd 03.11.: falscher Code oder gesperrte Quelle: leeres Team, Text in sj.code_fehler. Die Eingabe endet
  -- dann über team_code_abgelehnt normal (HTTP 400), damit der Zähler der Bremse nicht zurückgerollt wird.
  v_bremse := team_code_bremse(p_code);
  if v_bremse is not null then
    perform set_config('sj.code_fehler', v_bremse, true);
    return null;
  end if;
  t := team_by_code(p_code);
  if coalesce(p_token, '') <> '' and t.leader_participant_id is not null
     and exists (select 1 from participants where id = t.leader_participant_id and token = p_token) then
    return t;
  end if;
  if coalesce(btrim(p_pin), '') <> '' then
    perform require_admin(p_pin);
    return t;
  end if;
  raise exception 'Eingeben kann nur die Teamleitung auf ihrem eigenen Handy. Wenn du die Leitung bist: App neu laden.' using errcode = 'P0001';
end $function$;
revoke all on function public.team_eingabe(p_code text, p_token text, p_pin text) from public, anon, authenticated;

-- ---------- check_in (W5-Fassung, eine Zeile für die Bremse) ----------
CREATE OR REPLACE FUNCTION public.check_in(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_token text DEFAULT NULL::text, p_pin text DEFAULT NULL::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; g game_state; cur stations; d double precision; tol double precision;
begin
  t := team_eingabe(p_code, p_token, p_pin);
  if t.id is null then return team_code_abgelehnt(current_setting('sj.code_fehler', true)); end if;   -- Bremse (Bugjagd 03.11.)
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

-- ---------- submit_answer (W5-Fassung, eine Zeile für die Bremse) ----------
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
  if t.id is null then return team_code_abgelehnt(current_setting('sj.code_fehler', true)); end if;   -- Bremse (Bugjagd 03.11.)
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

-- ---------- reveal_tip (W5-Fassung, eine Zeile für die Bremse) ----------
CREATE OR REPLACE FUNCTION public.reveal_tip(p_code text, p_token text DEFAULT NULL::text, p_pin text DEFAULT NULL::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; g game_state; cur stations; row_p progress;
begin
  t := team_eingabe(p_code, p_token, p_pin);
  if t.id is null then return team_code_abgelehnt(current_setting('sj.code_fehler', true)); end if;   -- Bremse (Bugjagd 03.11.)
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

-- ---------- submit_final (W5-Fassung, eine Zeile für die Bremse) ----------
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
  if t.id is null then return team_code_abgelehnt(current_setting('sj.code_fehler', true)); end if;   -- Bremse (Bugjagd 03.11.)
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

-- ---------- team_selfie_skip (W5-Fassung, eine Zeile für die Bremse) ----------
CREATE OR REPLACE FUNCTION public.team_selfie_skip(p_code text, p_position integer, p_token text DEFAULT NULL::text, p_pin text DEFAULT NULL::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams;
begin
  t := team_eingabe(p_code, p_token, p_pin);
  if t.id is null then return team_code_abgelehnt(current_setting('sj.code_fehler', true)); end if;   -- Bremse (Bugjagd 03.11.)
  update progress pr set selfie_at = coalesce(pr.selfie_at, now())
    from stations s
    where s.id = pr.station_id and s.position = p_position and pr.team_id = t.id and pr.solved_at is not null;
  if not found then raise exception 'Erst das Rätsel lösen.' using errcode='P0001'; end if;
  return team_state(p_code);
end $function$;
revoke all on function public.team_selfie_skip(p_code text, p_position integer, p_token text, p_pin text) from public, anon, authenticated;
grant execute on function public.team_selfie_skip(p_code text, p_position integer, p_token text, p_pin text) to public, anon, authenticated;

-- ---------- team_set_leader (W5-Fassung, eine Zeile für die Bremse) ----------
CREATE OR REPLACE FUNCTION public.team_set_leader(p_code text, p_name text, p_token text DEFAULT NULL::text, p_pin text DEFAULT NULL::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; v_id uuid; v_token text;
begin
  t := team_eingabe(p_code, p_token, p_pin);
  if t.id is null then return team_code_abgelehnt(current_setting('sj.code_fehler', true)); end if;   -- Bremse (Bugjagd 03.11.)
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

-- ---------- team_selfie (W5-Fassung, eine Zeile für die Bremse, Teil B: Löschdatum) ----------
CREATE OR REPLACE FUNCTION public.team_selfie(p_code text, p_position integer, p_photo text, p_thumb text, p_token text DEFAULT NULL::text, p_pin text DEFAULT NULL::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; s stations; pr progress; v_photo bytea; v_thumb bytea;
begin
  t := team_eingabe(p_code, p_token, p_pin);
  if t.id is null then return team_code_abgelehnt(current_setting('sj.code_fehler', true)); end if;   -- Bremse (Bugjagd 03.11.)
  if not (select selfie_on from game_state where id = 1) then
    raise exception 'Gruppenfotos sind ausgeschaltet.' using errcode='P0001';
  end if;
  -- Fund 7: sonst fügte der Aufruf das Foto ein und team_state löschte es gleich wieder (photos_delete_on <= current_date)
  if (select photos_delete_on from game_state where id = 1) <= (now() at time zone 'Europe/Prague')::date then
    raise exception 'Das Löschdatum der Fotos ist erreicht, das Foto würde sofort gelöscht. Die Spielleitung kann im Reiter Fotos ein späteres Datum wählen; bis dahin ohne Foto weiter.' using errcode='P0001';
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

-- ---------- report_position (W5-Fassung, eine Zeile für die Bremse) ----------
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
  if t.id is null then perform team_code_abgelehnt(current_setting('sj.code_fehler', true)); return; end if;   -- Bremse (Bugjagd 03.11.)
  insert into team_positions(team_id, lat, lng, accuracy_m, updated_at, kompass)
  values (t.id, p_lat, p_lng, p_acc, now(), case when p_kompass in ('ok', 'unzuverlaessig') then p_kompass end)
  on conflict (team_id) do update
    set lat = excluded.lat, lng = excluded.lng, accuracy_m = excluded.accuracy_m, updated_at = now(), kompass = excluded.kompass;
  insert into position_log(team_id, lat, lng, accuracy_m) values (t.id, p_lat, p_lng, p_acc);
end $function$;
revoke all on function public.report_position(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_kompass text, p_token text, p_pin text) from public, anon, authenticated;
grant execute on function public.report_position(p_code text, p_lat double precision, p_lng double precision, p_acc double precision, p_kompass text, p_token text, p_pin text) to public, anon, authenticated;

-- ---------- team_state (Live-Fassung, Bremse direkt) ----------
CREATE OR REPLACE FUNCTION public.team_state(p_code text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_bremse text; t teams; g game_state; cur stations; row_p progress;
        v_total int; v_solved int; v_sum int; v_all boolean; v_place int; v_done int;
        v_pend stations; v_ersetzbar int;
begin
  v_bremse := team_code_bremse(p_code);
  if v_bremse is not null then return team_code_abgelehnt(v_bremse); end if;
  t := team_by_code(p_code);
  select * into g from game_state where id = 1;
  -- Nachtrag 25: fällige Fotos verschwinden beim nächsten Abruf
  delete from station_photos where (select photos_delete_on from game_state where id = 1) <= current_date;
  select count(*) into v_total from stations;
  select count(*) into v_solved from progress pr join stations s on s.id = pr.station_id where pr.team_id = t.id and pr.solved_at is not null;
  select coalesce(sum(s.digit),0) into v_sum from stations s
    join progress pr on pr.station_id = s.id and pr.team_id = t.id and pr.solved_at is not null;
  -- Nachtrag 25: niedrigste gelöste Station ohne Gruppenfoto. Solange eine offen ist, hält die App
  -- deren Ziffer zurück und zeigt den Selfie-Schritt. Zeitmessung und Rangliste hängen weiter an solved_at.
  if g.selfie_on then
    select s.* into v_pend from stations s
      join progress pr on pr.station_id = s.id and pr.team_id = t.id
      where pr.solved_at is not null and pr.selfie_at is null order by s.position limit 1;
  end if;
  -- Ersetzen darf man das Foto der zuletzt gelösten Station, bis an einer späteren eingecheckt ist
  select max(s.position) into v_ersetzbar from stations s
    join progress pr on pr.station_id = s.id and pr.team_id = t.id where pr.solved_at is not null;
  if exists (select 1 from progress pr join stations s on s.id = pr.station_id
             where pr.team_id = t.id and s.position > v_ersetzbar and pr.checked_in_at is not null) then
    v_ersetzbar := null;
  end if;
  v_all := v_total > 0 and v_solved = v_total and v_pend.id is null;
  cur := current_station(t.id);
  select * into row_p from progress where team_id = t.id and station_id = cur.id;
  select place into v_place from finishes where team_id = t.id;
  select count(*) into v_done from finishes;

  return json_build_object(
    'team', json_build_object('id', t.id, 'name', t.name, 'code', t.code,
      'leaderName', (select p.name from participants p where p.id = t.leader_participant_id),
      'members', coalesce((select json_agg(p2.name order by p2.name)
                           from participants p2 where p2.team_id = t.id), '[]'::json)),
    -- Rollen und Akku 29.10.: je Gerät Anmeldung, Verbindung und Akku (members bleibt unverändert, alte Fassungen lesen es)
    'geraete', coalesce((select json_agg(json_build_object(
        'name', p3.name,
        'angemeldet', p3.token is not null,
        'verbunden', coalesce(p3.gesehen_at > now() - interval '2 minutes', false),
        'akku',  case when p3.akku_at > now() - interval '10 minutes' then p3.akku end,
        'laedt', case when p3.akku_at > now() - interval '10 minutes' then p3.akku_laedt end) order by p3.name)
      from participants p3 where p3.team_id = t.id), '[]'::json),
    'background', g.background,
    'status', g.status,
    'startedAt', g.started_at,
    'durationMin', g.duration_min,
    'endsAt', case when g.started_at is null then null else g.started_at + make_interval(mins => g.duration_min) end,
    'totalStations', v_total,
    'solvedCount', v_solved,
    -- Ziffern: nur für gelöste Stationen, die sechste erst wenn alles gelöst ist
    'digits', (select json_agg(d order by pos) from (
        select s.position as pos,
               case when pr.solved_at is not null and (not g.selfie_on or pr.selfie_at is not null)
                    then s.digit else null end as d
        from stations s left join progress pr on pr.station_id = s.id and pr.team_id = t.id
      ) q),
    'finalDigit', case when v_all then v_sum % 10 else null end,
    'station', case when cur.id is null or g.status <> 'running' then null else json_build_object(
        'position', cur.position, 'name', cur.name, 'locationHint', cur.location_hint,
        'lat', cur.lat, 'lng', cur.lng, 'radiusM', cur.radius_m,
        -- Nachtrag 26: ab wann sich der Name auf dem Handy entschlüsselt (null = sofort lesbar)
        'revealStartM', cur.reveal_start_m, 'revealClearM', cur.reveal_clear_m,
        -- Nachtrag 27: Lösung nur aus Ziffern (auch mehrere, mit | getrennt): das Handy zeigt die Zifferntastatur.
        -- Verrät nur, dass eine Zahl gesucht ist, das sagt das Rätsel meist ohnehin.
        'numeric', btrim(cur.answer) ~ '^[0-9]+( *[|] *[0-9]+)*$',
        -- Rätsel erst nach dem Check-in
        'riddle', case when row_p.checked_in_at is not null then cur.riddle else null end,
        -- Tipp: ob es einen gibt und er schon offen wäre, und der Text erst nach dem Aufdecken
        'tipAvailable', btrim(cur.tip) <> '' and row_p.checked_in_at is not null and (g.test_mode or coalesce(row_p.pauses, 0) >= 1),
        'tip', case when row_p.tip_at is not null then cur.tip else null end) end,
    'checkedIn', row_p.checked_in_at is not null,
    'failedAttempts', coalesce(row_p.failed_attempts, 0),
    'lockedUntil', row_p.locked_until,
    'pauses', coalesce(row_p.pauses, 0),
    'allSolved', v_all,
    'caseHint', g.case_hint,
    'place', v_place,
    'prizeCount', g.prize_count,
    'prizesLeft', greatest(g.prize_count - v_done, 0),
    'winnerTeamId', g.winner_team_id,
    'isWinner', coalesce(v_place <= g.prize_count, false),
    'testMode', g.test_mode,
    'selfie', json_build_object(
      'on', g.selfie_on,
      'pending', case when v_pend.id is null then null
                      else json_build_object('position', v_pend.position, 'name', v_pend.name) end,
      'replaceable', case when g.selfie_on then v_ersetzbar else null end,
      'deleteOn', g.photos_delete_on,
      'photos', coalesce((select json_agg(json_build_object('position', s.position, 'takenAt', ph.taken_at)
                                          order by s.position)
                          from station_photos ph join stations s on s.id = ph.station_id
                          where ph.team_id = t.id), '[]'::json))
  );
end $function$;
revoke all on function public.team_state(p_code text) from public, anon, authenticated;
grant execute on function public.team_state(p_code text) to public, anon, authenticated;

-- ---------- team_photo (Live-Fassung, Bremse direkt) ----------
CREATE OR REPLACE FUNCTION public.team_photo(p_code text, p_token text, p_read_token text, p_position integer, p_full boolean DEFAULT false)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_bremse text; v_team uuid;
begin
  if coalesce(p_code, '') <> '' then
    v_bremse := team_code_bremse(p_code);
    if v_bremse is not null then return team_code_abgelehnt(v_bremse); end if;
    v_team := (team_by_code(p_code)).id;
  elsif coalesce(p_token, '') <> '' then
    select team_id into v_team from participants where token = p_token;
  end if;
  if v_team is null then raise exception 'Kein Zugang zu diesem Album.' using errcode='P0001'; end if;
  return json_build_object('data', (select encode(case when p_full then ph.photo else ph.thumb end, 'base64')
          from station_photos ph join stations s on s.id = ph.station_id
          where ph.team_id = v_team and s.position = p_position));
end $function$;
revoke all on function public.team_photo(p_code text, p_token text, p_read_token text, p_position integer, p_full boolean) from public, anon, authenticated;
grant execute on function public.team_photo(p_code text, p_token text, p_read_token text, p_position integer, p_full boolean) to public, anon, authenticated;

-- ==================== Teil B: admin_start warnt vor abgelaufenem Löschdatum ====================
-- (team_selfie steht oben bei den Eingaben)
CREATE OR REPLACE FUNCTION public.admin_start(p_pin text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_missing text; g game_state; v_warn text[] := array[]::text[];
        v_heute date := (now() at time zone 'Europe/Prague')::date;
begin
  perform require_admin(p_pin);
  select * into g from game_state where id = 1;
  if g.status <> 'drawn' then
    raise exception 'Starten geht nur, wenn Teams ausgelost sind und das Spiel noch nicht läuft.'
      using errcode='P0001';
  end if;
  if not exists (select 1 from teams) then
    raise exception 'Erst Teams auslosen.' using errcode='P0001';
  end if;
  select string_agg(position::text, ', ' order by position) into v_missing
    from stations where lat is null or lng is null;
  if g.test_mode then
    v_warn := array_append(v_warn, 'Der Testmodus ist an: Entfernung und Antworten werden nicht geprüft. Vor dem Event ausschalten.');
  end if;
  -- Fund 7: ein altes Löschdatum (etwa aus einer Probe) löscht jedes Gruppenfoto gleich nach dem Hochladen
  if g.selfie_on and g.photos_delete_on is not null and g.photos_delete_on <= v_heute then
    v_warn := array_append(v_warn, 'Das Löschdatum der Gruppenfotos (' || to_char(g.photos_delete_on, 'DD.MM.YYYY')
      || ') ist erreicht: Fotos werden nicht gespeichert. Im Reiter Fotos ein Datum nach dem Abendessen wählen.');
  end if;
  if v_missing is not null then
    v_warn := array_append(v_warn, 'Station(en) ' || v_missing || ' haben keine Koordinaten.');
  end if;
  delete from finishes where true;
  update game_state set status = 'running', started_at = now(),
    finished_at = null, winner_team_id = null where id = 1;
  return json_build_object('warning',
    case when cardinality(v_warn) = 0 then null else 'Achtung: ' || array_to_string(v_warn, ' ') end,
    'state', admin_state(p_pin));
end $function$;
revoke all on function public.admin_start(p_pin text) from public, anon, authenticated;
grant execute on function public.admin_start(p_pin text) to public, anon, authenticated;

-- ==================== Teil C: norm() mit NFC ====================
-- Gleiche Kette wie bisher, nur vorher normalize(…, NFC). Für vorkomponierte Eingaben ändert sich nichts.
CREATE OR REPLACE FUNCTION public.norm(t text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$
  select regexp_replace(
    translate(
      replace(replace(replace(replace(
        lower(translate(normalize(coalesce(t,''), NFC),
          'ÄÖÜÀÁÂÃÅĀĂĄÇĆČĎĐÈÉÊËĒĖĘĚÌÍÎÏĪĮĹĽŁÑŃŇÒÓÔÕØŌŐŔŘŚŠŞȘŤŢȚÙÚÛŮŪŰŲÝŸŹŻŽ',
          'äöüàáâãåāăąçćčďđèéêëēėęěìíîïīįĺľłñńňòóôõøōőŕřśšşșťţțùúûůūűųýÿźżž')),
        'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss'),
      'àáâãåāăąçćčďđèéêëēėęěìíîïīįıĺľłñńňòóôõøōőŕřśšşșťţțùúûůūűųýÿźżž',
      'aaaaaaaacccddeeeeeeeeiiiiiiilllnnnooooooorrsssstttuuuuuuuyyzzz'),
    '[^a-z0-9]+', '', 'g');
$function$;
revoke all on function public.norm(t text) from public, anon, authenticated;

-- Schlüssel nachziehen, wo norm(name) jetzt anders ausfällt (Namen mit zerlegten Umlauten); nie auf einen Schlüssel,
-- den schon jemand hat: dann bleibt der alte (der Probelauf meldet, wie viele das wären)
update participants p set name_key = norm(p.name)
 where p.name_key is distinct from norm(p.name) and norm(p.name) <> ''
   and not exists (select 1 from participants q where q.id <> p.id and q.name_key = norm(p.name));

notify pgrst, 'reload schema';
