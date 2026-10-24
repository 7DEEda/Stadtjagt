-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=nein, authenticated=nein
CREATE OR REPLACE FUNCTION public.team_by_code(p_code text)
 RETURNS teams
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams;
begin
  select * into t from teams
    where regexp_replace(upper(code), '[^A-Z0-9]', '', 'g')
        = regexp_replace(upper(coalesce(p_code, '')), '[^A-Z0-9]', '', 'g');
  if not found then
    raise exception 'Unbekannter Team-Code.' using errcode = 'P0001';
  end if;
  return t;
end $function$;
revoke all on function public.team_by_code(p_code text) from public, anon, authenticated;
