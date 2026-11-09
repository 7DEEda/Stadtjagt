-- Notweg-Schlüssel, 09.11.2026 (SPIEL.md §26). Läuft NACH W5 (20261103090000_w5_eingaben_schluessel.sql) und NACH
-- 20261107090000_bugjagd3.sql (Bremse in team_eingabe) und bricht sonst ab. Mehrfach ausführbar, löscht keine
-- Spieldaten, ändert keine Signatur der acht Eingaben. Probelauf: tools/pruefstand/notweg_db.py, dazu rechte_db.py.
-- Nicht ohne Friedrichs Ja einspielen. Reihenfolge: App, W5, bugjagd3, diese Datei (bugjagd4 ist unabhängig).
--
-- Befund S1 der W5-Sicherheitsprüfung (07.11.): Am Notweg-Tablet (Spielleitung gibt mit Team-Code für ein Team ein)
-- lag die Admin-PIN im sessionStorage, der Tab war damit auch für #/admin angemeldet. Jetzt tauscht das Tablet die
-- PIN einmal gegen einen Schlüssel, der nur für Eingaben dieses einen Teams gilt, 12 Stunden lang. Die PIN bleibt
-- nicht im Gerät.
--
--  1. Tabelle notweg_schluessel (token, team_id, erstellt, gilt_bis): für anon und authenticated gesperrt. Ein
--     gelöschtes Team nimmt seine Schlüssel mit (on delete cascade).
--  2. admin_notweg(p_pin, p_code): PIN prüfen (require_admin), Team per Code (team_by_code, sonst
--     "Unbekannter Team-Code."), abgelaufene Schlüssel aufräumen, neuen Schlüssel anlegen. Antwort
--     {token, team, giltBis}. Der Schlüssel beginnt mit "nw-", damit team_eingabe ihn vom Geräte-Schlüssel
--     einer Person unterscheidet.
--  3. notweg_ende(p_token): löscht genau diesen Schlüssel (Abmelden am Tablet). Wer ihn kennt, darf ihn wegwerfen.
--  4. team_eingabe (Fassung aus bugjagd3 mit Bremse): nimmt neben dem Schlüssel der Leitung und der Admin-PIN auch
--     einen gültigen Notweg-Schlüssel dieses Teams an. Ein Notweg-Schlüssel, der abgelaufen, gelöscht oder für ein
--     anderes Team ist: "Der Notweg-Schlüssel gilt nicht mehr. Bitte die Admin-PIN noch einmal eingeben." Die
--     Admin-PIN als p_pin bleibt erlaubt (ältere App, Datenbank ohne diese Migration).
--  5. admin_set_pin (Fassung aus init/bugjagd, unverändert bis auf eine Zeile): eine neue PIN löscht alle
--     Notweg-Schlüssel. So widerruft die Spielleitung ein verlorenes Tablet (Prüfung 09.11., M1).
-- Regel (SPIEL.md §9): Rechte nach jeder Funktion ausdrücklich setzen.

do $vor$
begin
  if to_regprocedure('public.team_eingabe(text,text,text)') is null or to_regprocedure('public.team_code_bremse(text)') is null then
    raise exception 'Erst W5 und 20261107090000_bugjagd3.sql einspielen, dann diese Migration.';
  end if;
end $vor$;

create table if not exists notweg_schluessel (
  token    text primary key,
  team_id  uuid not null references teams(id) on delete cascade,
  erstellt timestamptz not null default now(),
  gilt_bis timestamptz not null
);
alter table notweg_schluessel enable row level security;
revoke all on table notweg_schluessel from public, anon, authenticated;

CREATE OR REPLACE FUNCTION public.admin_notweg(p_pin text, p_code text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; v_token text; v_bis timestamptz := now() + interval '12 hours';
begin
  perform require_admin(p_pin);
  t := team_by_code(p_code);
  delete from notweg_schluessel where gilt_bis < now();
  v_token := 'nw-' || replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', '');
  insert into notweg_schluessel (token, team_id, gilt_bis) values (v_token, t.id, v_bis);
  return json_build_object('token', v_token, 'team', t.name, 'giltBis', v_bis);
end $function$;
revoke all on function public.admin_notweg(p_pin text, p_code text) from public, anon, authenticated;
grant execute on function public.admin_notweg(p_pin text, p_code text) to public, anon, authenticated;

CREATE OR REPLACE FUNCTION public.notweg_ende(p_token text)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  delete from notweg_schluessel where token = p_token;
end $function$;
revoke all on function public.notweg_ende(p_token text) from public, anon, authenticated;
grant execute on function public.notweg_ende(p_token text) to public, anon, authenticated;

-- ---------- team_eingabe (bugjagd3-Fassung mit Bremse, dazu der Notweg-Schlüssel) ----------
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
  -- Notweg-Schlüssel (09.11.): nur für dieses Team und nur bis gilt_bis
  if p_token like 'nw-%'
     and exists (select 1 from notweg_schluessel where token = p_token and team_id = t.id and gilt_bis > now()) then
    return t;
  end if;
  if coalesce(btrim(p_pin), '') <> '' then
    perform require_admin(p_pin);
    return t;
  end if;
  if p_token like 'nw-%' then
    raise exception 'Der Notweg-Schlüssel gilt nicht mehr. Bitte die Admin-PIN noch einmal eingeben.' using errcode = 'P0001';
  end if;
  raise exception 'Eingeben kann nur die Teamleitung auf ihrem eigenen Handy. Wenn du die Leitung bist: App neu laden.' using errcode = 'P0001';
end $function$;
revoke all on function public.team_eingabe(p_code text, p_token text, p_pin text) from public, anon, authenticated;

-- ---------- admin_set_pin (Schema-Abzug, dazu: alle Notweg-Schlüssel löschen) ----------
CREATE OR REPLACE FUNCTION public.admin_set_pin(p_pin text, p_new text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  if length(btrim(coalesce(p_new,''))) < 12 then
    raise exception 'Die neue PIN braucht mindestens 12 Zeichen, am besten eine Passphrase.' using errcode='P0001';
  end if;
  update game_state set admin_pin = btrim(p_new) where id = 1;
  delete from notweg_schluessel;   -- neue PIN: jedes Notweg-Tablet braucht eine neue Freigabe
  return admin_state(btrim(p_new));
end $function$;
revoke all on function public.admin_set_pin(p_pin text, p_new text) from public, anon, authenticated;
grant execute on function public.admin_set_pin(p_pin text, p_new text) to public, anon, authenticated;
