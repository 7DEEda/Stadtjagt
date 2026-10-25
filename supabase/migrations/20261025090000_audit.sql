-- Code-Audit 25.10.2026 (vom Nutzer freigegeben). Ausgangspunkt ist der Schema-Abzug vom 25.10. (Branch schema-abzug,
-- supabase/schema/funktionen/), der Zeichen für Zeichen mit live übereinstimmt. Signaturen unverändert, nur
-- create or replace; die Rechte stehen danach ausdrücklich wie im Abzug. Mehrfach ausführbar, löscht keine Daten.
-- Probelauf: tools/pruefstand/audit2510_db.py (--ohne zeigt rot).
--
--  1. admin_set_selfie: Löschdatum heute oder früher (Prager Zeit) abgelehnt, sonst waren alle Fotos sofort weg. Das
--     schon gespeicherte Datum geht nur beim Ausschalten durch.
--  2. admin_set_test_mode: mit Plätzen in keinem Zustand umschalten (bisher nur in running gesperrt).
--  3. admin_draw, admin_delete_participant, admin_delete_test_participants: Teamleitung zuerst unter Personen mit
--     Geräte-Schlüssel; team_set_leader lehnt ein Ziel ohne Geräte-Schlüssel ab. admin_set_leader bleibt frei (Notweg).
--  4. admin_draw: Team-Codes mit sechs Ziffern; alte vierstellige gelten bis zum nächsten Auslosen (team_by_code
--     vergleicht nur Buchstaben und Ziffern, ohne feste Länge).
--  5. register_participant: ab 200 Personen ist die Selbstanmeldung voll.
--  6. register_participant: neue Meldung bei gleichem Namen.

CREATE OR REPLACE FUNCTION public.admin_set_selfie(p_pin text, p_on boolean, p_delete_on date)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_heute date := (now() at time zone 'Europe/Prague')::date;
begin
  perform require_admin(p_pin);
  -- Audit 25.10.: ein Löschdatum heute (oder früher) löschte beim nächsten Abruf alle Fotos. Heute zählt nach
  -- Prager Zeit, wie das Datumsfeld im Browser; gelöscht wird weiter in team_state/admin_state mit current_date
  -- (UTC), also am gewählten Tag ab 1 Uhr (Winterzeit) bzw. 2 Uhr (Sommerzeit), nie früher. Dasselbe Datum wie
  -- gespeichert geht beim Ausschalten durch, sonst ließe sich das Gruppenselfie nach dem Löschtag nicht mehr
  -- ausschalten. Beim Einschalten nicht: ein altes Datum aus einer Probe würde sonst am Eventtag angenommen.
  if p_delete_on is not null and p_delete_on <= v_heute
     and (coalesce(p_on, false)
          or p_delete_on is distinct from (select photos_delete_on from game_state where id = 1)) then
    raise exception 'Das Löschdatum muss nach heute liegen.' using errcode='P0001';
  end if;
  -- Einschalten mitten im Spiel: was schon gelöst ist, braucht kein Foto mehr, sonst stünden alle Teams
  -- plötzlich vor einem Selfie für längst verlassene Stationen
  if coalesce(p_on, false) and not (select selfie_on from game_state where id = 1) then
    update progress set selfie_at = solved_at where solved_at is not null and selfie_at is null;
  end if;
  update game_state set selfie_on = coalesce(p_on, false), photos_delete_on = p_delete_on where id = 1;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_set_selfie(p_pin text, p_on boolean, p_delete_on date) from public, anon, authenticated;
grant execute on function public.admin_set_selfie(p_pin text, p_on boolean, p_delete_on date) to public, anon, authenticated;

CREATE OR REPLACE FUNCTION public.admin_set_test_mode(p_pin text, p_on boolean)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  -- Nachtrag 32: Plätze aus dem Testlauf überlebten das Ausschalten und standen dann in der echten Rangliste. Im
  -- laufenden Spiel mit Plätzen darum in keine Richtung umschalten (Entscheidung 04.10.2026: auch nicht einschalten,
  -- sonst käme die Spielleitung nur über „Fortschritt zurücksetzen“ wieder heraus). Ohne Platz ist beides frei.
  -- Audit 25.10.: in jedem Zustand, nicht nur running. Sonst ging es so: Testlauf beenden, Testmodus aus,
  -- „Spiel fortsetzen“, und die Testplätze stehen im echten Spiel. In drawn und registration ist finishes leer.
  if exists (select 1 from game_state where id = 1 and test_mode is distinct from coalesce(p_on, false))
     and exists (select 1 from finishes) then
    if coalesce(p_on, false) then
      raise exception 'Es gibt schon Plätze. Den Testmodus jetzt einzuschalten würde die Rangliste durcheinanderbringen.'
        using errcode='P0001';
    end if;
    raise exception 'Im Testlauf gibt es schon Plätze. Erst im Reiter Daten löschen „Fortschritt zurücksetzen“, dann den Testmodus ausschalten.'
      using errcode='P0001';
  end if;
  update game_state set test_mode = coalesce(p_on, false) where id = 1;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_set_test_mode(p_pin text, p_on boolean) from public, anon, authenticated;
grant execute on function public.admin_set_test_mode(p_pin text, p_on boolean) to public, anon, authenticated;

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
      -- Audit 25.10.: sechs statt vier Ziffern, schwerer zu raten. Alte Codes gelten bis zum nächsten Auslosen.
      v_code := upper(v_animals[i]) || '-' || lpad((floor(random()*900000)+100000)::int::text, 6, '0');
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

  -- Teamleitung auslosen. Audit 25.10.: zuerst unter denen mit Geräte-Schlüssel (selbst angemeldet), nur die
  -- können auf dem eigenen Handy eingeben; wer nachgetragen wurde, nur, wenn es im Team niemanden sonst gibt.
  update teams t set leader_participant_id = (
    select p.id from participants p where p.team_id = t.id order by (p.token is null), random() limit 1)
    where true;

  update game_state set status = 'drawn' where id = 1;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_draw(p_pin text, p_teams integer, p_size integer) from public, anon, authenticated;
grant execute on function public.admin_draw(p_pin text, p_teams integer, p_size integer) to public, anon, authenticated;

CREATE OR REPLACE FUNCTION public.admin_delete_participant(p_pin text, p_id uuid)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  update teams set leader_participant_id = null where leader_participant_id = p_id;
  delete from participants where id = p_id;
  update teams t set leader_participant_id = (
      -- Audit 25.10.: Nachfolge zuerst unter denen mit Geräte-Schlüssel, wie beim Auslosen
      select p.id from participants p where p.team_id = t.id order by (p.token is null), random() limit 1)
    where t.leader_participant_id is null;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_delete_participant(p_pin text, p_id uuid) from public, anon, authenticated;
grant execute on function public.admin_delete_participant(p_pin text, p_id uuid) to public, anon, authenticated;

CREATE OR REPLACE FUNCTION public.admin_delete_test_participants(p_pin text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_n int;
begin
  perform require_admin(p_pin);
  update teams t set leader_participant_id = null
    where leader_participant_id in (select id from participants where name like '%(Test)');
  delete from participants where name like '%(Test)';
  get diagnostics v_n = row_count;
  -- Teams, deren Leitung weg ist, bekommen eine neue aus den Verbliebenen
  update teams t set leader_participant_id = (
      -- Audit 25.10.: Nachfolge zuerst unter denen mit Geräte-Schlüssel, wie beim Auslosen
      select p.id from participants p where p.team_id = t.id order by (p.token is null), random() limit 1)
    where t.leader_participant_id is null;
  return json_build_object('deleted', v_n, 'state', admin_state(p_pin));
end $function$;
revoke all on function public.admin_delete_test_participants(p_pin text) from public, anon, authenticated;
grant execute on function public.admin_delete_test_participants(p_pin text) to public, anon, authenticated;

CREATE OR REPLACE FUNCTION public.team_set_leader(p_code text, p_name text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; v_id uuid; v_token text;
begin
  t := team_by_code(p_code);
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
revoke all on function public.team_set_leader(p_code text, p_name text) from public, anon, authenticated;
grant execute on function public.team_set_leader(p_code text, p_name text) to public, anon, authenticated;

CREATE OR REPLACE FUNCTION public.register_participant(p_name text, p_token text DEFAULT NULL::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
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
  -- Audit 25.10.: Obergrenze, damit ein Skript die Liste nicht volllaufen lässt. Weiche Grenze: gleichzeitige
  -- Anmeldungen warten nicht aufeinander, es können ein paar mehr werden. Die Spielleitung trägt weiter nach.
  if (select count(*) from participants) >= 200 then
    raise exception 'Die Anmeldung ist voll. Melde dich bei der Spielleitung.' using errcode='P0001';
  end if;
  if exists (select 1 from participants where name_key = norm(v_name)) then
    raise exception 'Diesen Namen gibt es schon. Warst du das selbst, bist du schon dabei. Sonst ergänze etwas, zum Beispiel einen zweiten Vornamen.'
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
    raise exception 'Diesen Namen gibt es schon. Warst du das selbst, bist du schon dabei. Sonst ergänze etwas, zum Beispiel einen zweiten Vornamen.'
      using errcode='P0001';
  end;
  return json_build_object('name', v_name, 'token', v_token, 'count', (select count(*) from participants));
end $function$;
revoke all on function public.register_participant(p_name text, p_token text) from public, anon, authenticated;
grant execute on function public.register_participant(p_name text, p_token text) to public, anon, authenticated;

notify pgrst, 'reload schema';
