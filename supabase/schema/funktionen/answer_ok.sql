-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=nein, authenticated=nein
CREATE OR REPLACE FUNCTION public.answer_ok(p_answer text, p_solutions text)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
AS $function$
  select exists (
    select 1 from unnest(string_to_array(coalesce(p_solutions, ''), '|')) as l
    where norm(l) <> '' and norm(l) = norm(p_answer));
$function$;
revoke all on function public.answer_ok(p_answer text, p_solutions text) from public, anon, authenticated;
