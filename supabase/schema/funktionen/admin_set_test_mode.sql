-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_set_test_mode(p_pin text, p_on boolean)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  -- Nachtrag 32: Plätze aus dem Testlauf überlebten das Ausschalten und standen dann in der echten Rangliste. Im
  -- laufenden Spiel mit Plätzen darum in keine Richtung umschalten (Entscheidung 04.10.2026: auch nicht einschalten,
  -- sonst käme die Spielleitung nur über „Fortschritt zurücksetzen“ wieder heraus). Ohne Platz ist beides frei.
  if exists (select 1 from game_state where id = 1 and status = 'running' and test_mode is distinct from coalesce(p_on, false))
     and exists (select 1 from finishes) then
    if coalesce(p_on, false) then
      raise exception 'Im laufenden Spiel gibt es schon Plätze. Den Testmodus jetzt einzuschalten würde die Rangliste durcheinanderbringen.'
        using errcode='P0001';
    end if;
    raise exception 'Im Testlauf gibt es schon Plätze. Erst im Reiter Daten löschen „Fortschritt zurücksetzen“, dann den Testmodus ausschalten.'
      using errcode='P0001';
  end if;
  update game_state set test_mode = coalesce(p_on, false) where id = 1;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_set_test_mode(p_pin text, p_on boolean) from public, anon, authenticated;
grant execute on function public.admin_set_test_mode(p_pin text, p_on boolean) to public, anon, authenticated;
