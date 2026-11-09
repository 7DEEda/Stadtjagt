-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=nein, authenticated=nein
CREATE OR REPLACE FUNCTION public.team_code_bremse(p_code text)
 RETURNS text
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_quelle text := team_code_quelle(); f team_code_fehlversuche; v_min int;
        v_norm text := regexp_replace(upper(coalesce(p_code, '')), '[^A-Z0-9]', '', 'g');
        c_grenze constant int := 30; c_fenster constant interval := interval '10 minutes';
begin
  select * into f from team_code_fehlversuche where quelle = v_quelle;
  if found and f.anzahl >= c_grenze and f.seit > now() - c_fenster then
    v_min := greatest(1, ceil(extract(epoch from f.seit + c_fenster - now()) / 60))::int;
    return 'Zu viele falsche Team-Codes aus diesem Netz. Bitte in '
      || case when v_min = 1 then 'einer Minute' else v_min || ' Minuten' end || ' noch einmal versuchen.';
  end if;
  if v_norm <> '' and exists (select 1 from teams where regexp_replace(upper(code), '[^A-Z0-9]', '', 'g') = v_norm) then
    return null;
  end if;
  if v_norm <> '' then
    delete from team_code_fehlversuche where seit < now() - interval '1 hour';
    insert into team_code_fehlversuche as z (quelle, seit, anzahl) values (v_quelle, now(), 1)
      on conflict (quelle) do update set
        anzahl = case when z.seit <= now() - c_fenster then 1 else z.anzahl + 1 end,
        seit   = case when z.seit <= now() - c_fenster then now() else z.seit end;
  end if;
  return 'Unbekannter Team-Code.';
end $function$;
revoke all on function public.team_code_bremse(p_code text) from public, anon, authenticated;
