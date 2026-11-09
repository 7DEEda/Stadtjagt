-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
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
