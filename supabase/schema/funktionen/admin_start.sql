-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_start(p_pin text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_missing text; g game_state; v_warn text[] := array[]::text[];
begin
  perform require_admin(p_pin);
  select * into g from game_state where id = 1;
  if g.status <> 'drawn' then
    raise exception 'Starten geht nur, wenn Teams ausgelost sind und das Spiel noch nicht läuft.'
      using errcode='P0001';
  end if;
  if not exists (select 1 from teams) then
    raise exception 'Erst Teams auslosen.' using errcode='P0001';
  end if;
  select string_agg(position::text, ', ' order by position) into v_missing
    from stations where lat is null or lng is null;
  if g.test_mode then
    v_warn := array_append(v_warn, 'Der Testmodus ist an: Entfernung und Antworten werden nicht geprüft. Vor dem Event ausschalten.');
  end if;
  if v_missing is not null then
    v_warn := array_append(v_warn, 'Station(en) ' || v_missing || ' haben keine Koordinaten.');
  end if;
  delete from finishes where true;
  update game_state set status = 'running', started_at = now(),
    finished_at = null, winner_team_id = null where id = 1;
  return json_build_object('warning',
    case when cardinality(v_warn) = 0 then null else 'Achtung: ' || array_to_string(v_warn, ' ') end,
    'state', admin_state(p_pin));
end $function$;
revoke all on function public.admin_start(p_pin text) from public, anon, authenticated;
grant execute on function public.admin_start(p_pin text) to public, anon, authenticated;
