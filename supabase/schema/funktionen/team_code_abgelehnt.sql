-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=nein, authenticated=nein
CREATE OR REPLACE FUNCTION public.team_code_abgelehnt(p_text text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform set_config('response.status', '400', true);
  return json_build_object('code', 'P0001', 'message', coalesce(nullif(p_text, ''), 'Unbekannter Team-Code.'),
                           'details', null, 'hint', null);
end $function$;
revoke all on function public.team_code_abgelehnt(p_text text) from public, anon, authenticated;
