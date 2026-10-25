-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_save_station(p_pin text, p_id uuid, p_name text, p_lat double precision, p_lng double precision, p_radius integer, p_hint text, p_riddle text, p_answer text, p_digit integer, p_tip text DEFAULT ''::text, p_reveal_start integer DEFAULT NULL::integer, p_reveal_clear integer DEFAULT NULL::integer)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  perform require_admin(p_pin);
  if (p_reveal_start is null) <> (p_reveal_clear is null) then
    raise exception 'Für das Entschlüsseln braucht es beide Entfernungen oder keine.' using errcode='P0001';
  end if;
  if p_reveal_start is not null and (p_reveal_clear <= 0 or p_reveal_start <= p_reveal_clear or p_reveal_start > 5000) then
    raise exception 'Der Name muss weiter draußen beginnen, als er lesbar wird (höchstens 5000 m).' using errcode='P0001';
  end if;
  update stations_alle set
    name = coalesce(nullif(btrim(p_name),''), name),
    lat = p_lat, lng = p_lng,
    radius_m = greatest(5, coalesce(p_radius, 50)),
    location_hint = coalesce(p_hint, ''),
    riddle = coalesce(p_riddle, ''),
    answer = coalesce(p_answer, ''),
    digit = greatest(0, least(9, coalesce(p_digit, 0))),
    tip = btrim(coalesce(p_tip, '')),
    reveal_start_m = p_reveal_start, reveal_clear_m = p_reveal_clear
  where id = p_id;
  return admin_state(p_pin);
end $function$;
revoke all on function public.admin_save_station(p_pin text, p_id uuid, p_name text, p_lat double precision, p_lng double precision, p_radius integer, p_hint text, p_riddle text, p_answer text, p_digit integer, p_tip text, p_reveal_start integer, p_reveal_clear integer) from public, anon, authenticated;
grant execute on function public.admin_save_station(p_pin text, p_id uuid, p_name text, p_lat double precision, p_lng double precision, p_radius integer, p_hint text, p_riddle text, p_answer text, p_digit integer, p_tip text, p_reveal_start integer, p_reveal_clear integer) to public, anon, authenticated;
