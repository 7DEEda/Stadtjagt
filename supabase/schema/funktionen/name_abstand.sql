-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=nein, authenticated=nein
CREATE OR REPLACE FUNCTION public.name_abstand(a text, b text)
 RETURNS integer
 LANGUAGE plpgsql
 IMMUTABLE
 SET search_path TO 'public'
AS $function$
declare la int := length(a); lb int := length(b); vorher int[]; jetzt int[]; i int; j int; kosten int;
begin
  if la = 0 then return lb; end if;
  if lb = 0 then return la; end if;
  vorher := array(select generate_series(0, lb));
  for i in 1..la loop
    jetzt := array[i];
    for j in 1..lb loop
      kosten := case when substr(a, i, 1) = substr(b, j, 1) then 0 else 1 end;
      jetzt := jetzt || least(jetzt[j] + 1, vorher[j + 1] + 1, vorher[j] + kosten);
    end loop;
    vorher := jetzt;
  end loop;
  return vorher[lb + 1];
end $function$;
revoke all on function public.name_abstand(a text, b text) from public, anon, authenticated;
