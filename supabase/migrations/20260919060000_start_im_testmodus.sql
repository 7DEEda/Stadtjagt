-- ============================================================
--  STADTJAGD – Nachtrag 16: Starten im Testmodus wieder erlaubt
--
--  Nachtrag 13 ließ admin_start bei eingeschaltetem Testmodus abbrechen.
--  Solange getestet wird, soll der Testmodus aber dauerhaft an bleiben
--  können, auch über Start und Neustart hinweg (Entscheidung 19.09.2026).
--  Jetzt: Starten geht, die Antwort trägt eine Warnung, die App zeigt sie
--  rot; der Hinweis "Testmodus an" im Kopf bleibt ohnehin.
--
--  Einspielen: nach Nachtrag 15. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

create or replace function admin_start(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
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
end $$;

notify pgrst, 'reload schema';
