-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=nein, authenticated=nein
CREATE OR REPLACE FUNCTION public.team_code_quelle()
 RETURNS text
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare h json;
begin
  begin
    h := coalesce(nullif(current_setting('request.headers', true), ''), '{}')::json;
  exception when others then h := '{}'::json;
  end;
  return left(coalesce(nullif(btrim(h->>'cf-connecting-ip'), ''),
                       nullif(btrim(split_part(coalesce(h->>'x-forwarded-for', ''), ',', 1)), ''),
                       'ohne'), 100);
end $function$;
revoke all on function public.team_code_quelle() from public, anon, authenticated;
