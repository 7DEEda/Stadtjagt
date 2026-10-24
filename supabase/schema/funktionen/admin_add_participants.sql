-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_add_participants(p_pin text, p_names text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_zeile text; v_name text; v_team uuid; v_neu int := 0; v_doppelt int := 0; v_ungueltig int := 0;
begin
  perform require_admin(p_pin);
  perform 1 from game_state where id = 1 for share;   -- nicht mitten in ein Auslosen
  foreach v_zeile in array regexp_split_to_array(coalesce(p_names, ''), '\r?\n') loop
    v_name := btrim(regexp_replace(v_zeile, '\s+', ' ', 'g'));
    continue when v_name = '';
    if length(v_name) < 2 or length(v_name) > 60 or norm(v_name) = '' then
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
end $function$;
revoke all on function public.admin_add_participants(p_pin text, p_names text) from public, anon, authenticated;
grant execute on function public.admin_add_participants(p_pin text, p_names text) to public, anon, authenticated;
