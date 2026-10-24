-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_add_participant(p_pin text, p_name text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_name text := btrim(regexp_replace(coalesce(p_name,''), '\s+', ' ', 'g'));
        v_team uuid;
begin
  perform require_admin(p_pin);
  if length(v_name) < 2 or length(v_name) > 60 then
    raise exception 'Bitte einen Namen mit 2 bis 60 Zeichen eingeben.' using errcode='P0001';
  end if;
  if norm(v_name) = '' then
    raise exception 'Bitte einen Namen mit lateinischen Buchstaben oder Ziffern eingeben.' using errcode='P0001';
  end if;
  perform 1 from game_state where id = 1 for share;   -- nicht mitten in ein Auslosen
  if exists (select 1 from participants where name_key = norm(v_name)) then
    raise exception 'Dieser Name ist schon angemeldet.' using errcode='P0001';
  end if;
  select t.id into v_team from teams t
    left join participants p on p.team_id = t.id
    group by t.id order by count(p.id) asc limit 1;
  insert into participants(name, name_key, team_id) values (v_name, norm(v_name), v_team);
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_add_participant(p_pin text, p_name text) from public, anon, authenticated;
grant execute on function public.admin_add_participant(p_pin text, p_name text) to public, anon, authenticated;
