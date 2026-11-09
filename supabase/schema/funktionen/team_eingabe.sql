-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=nein, authenticated=nein
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
