-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_rename_participant(p_pin text, p_id uuid, p_name text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_name text := btrim(regexp_replace(coalesce(p_name,''), '\s+', ' ', 'g'));
begin
  perform require_admin(p_pin);
  if length(v_name) < 2 or length(v_name) > 60 then
    raise exception 'Bitte einen Namen mit 2 bis 60 Zeichen eingeben.' using errcode='P0001';
  end if;
  if norm(v_name) = '' then
    raise exception 'Bitte einen Namen mit lateinischen Buchstaben oder Ziffern eingeben.' using errcode='P0001';
  end if;
  if exists (select 1 from participants where name_key = norm(v_name) and id <> p_id) then
    raise exception 'Diesen Namen gibt es schon.' using errcode='P0001';
  end if;
  update participants set name = v_name, name_key = norm(v_name) where id = p_id;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_rename_participant(p_pin text, p_id uuid, p_name text) from public, anon, authenticated;
grant execute on function public.admin_rename_participant(p_pin text, p_id uuid, p_name text) to public, anon, authenticated;
