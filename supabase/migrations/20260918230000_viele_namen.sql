-- ============================================================
--  STADTJAGD – Nachtrag 9: viele Namen auf einmal eintragen
--
--  Für Tests und für Listen, die die Spielleitung schon hat: ein Name pro
--  Zeile. Leere Zeilen, zu kurze oder zu lange Namen und Namen, die es
--  schon gibt (auch doppelt in der Liste), werden übersprungen und
--  gezählt. Sind schon Teams ausgelost, kommt jede neue Person wie ein
--  Nachzügler ins gerade kleinste Team.
--
--  Einspielen: nach Nachtrag 8. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

create or replace function admin_add_participants(p_pin text, p_names text) returns json
language plpgsql security definer set search_path = public as $$
declare v_zeile text; v_name text; v_team uuid; v_neu int := 0; v_doppelt int := 0; v_ungueltig int := 0;
begin
  perform require_admin(p_pin);
  foreach v_zeile in array regexp_split_to_array(coalesce(p_names, ''), '\r?\n') loop
    v_name := btrim(regexp_replace(v_zeile, '\s+', ' ', 'g'));
    continue when v_name = '';
    if length(v_name) < 2 or length(v_name) > 60 then
      v_ungueltig := v_ungueltig + 1; continue;
    end if;
    if exists (select 1 from participants where name_key = norm(v_name)) then
      v_doppelt := v_doppelt + 1; continue;
    end if;
    v_team := null;
    select t.id into v_team from teams t
      left join participants p on p.team_id = t.id
      group by t.id order by count(p.id) asc limit 1;
    insert into participants(name, name_key, team_id) values (v_name, norm(v_name), v_team);
    v_neu := v_neu + 1;
  end loop;
  return json_build_object('added', v_neu, 'duplicates', v_doppelt, 'invalid', v_ungueltig,
                           'state', admin_state(p_pin));
end $$;

grant execute on function admin_add_participants(text, text) to anon, authenticated;

notify pgrst, 'reload schema';
