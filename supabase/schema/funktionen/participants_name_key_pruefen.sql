-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.participants_name_key_pruefen()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
begin
  if coalesce(new.name_key, '') = '' then
    raise exception 'Bitte einen Namen mit lateinischen Buchstaben oder Ziffern eingeben.' using errcode='P0001';
  end if;
  return new;
end $function$;
revoke all on function public.participants_name_key_pruefen() from public, anon, authenticated;
grant execute on function public.participants_name_key_pruefen() to public, anon, authenticated;
