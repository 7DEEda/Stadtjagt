-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.rb_status_setzen(p_pin text, p_status jsonb)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare r rueckblick_steuerung;
begin
  perform require_admin(p_pin);
  if p_status is null or jsonb_typeof(p_status) <> 'object' then
    raise exception 'Der Status fehlt.' using errcode = 'P0001';
  end if;
  if octet_length(p_status::text) > 20480 then
    raise exception 'Der Status ist zu groß.' using errcode = 'P0001';
  end if;
  insert into rueckblick_steuerung (id) values (1) on conflict (id) do nothing;
  update rueckblick_steuerung set status = p_status, status_um = clock_timestamp() where id = 1 returning * into r;
  return json_build_object('ok', true,
    'handy_alter_s', case when r.handy_um is null then null else round(extract(epoch from clock_timestamp() - r.handy_um)::numeric, 1) end);
end $function$;
revoke all on function public.rb_status_setzen(p_pin text, p_status jsonb) from public, anon, authenticated;
grant execute on function public.rb_status_setzen(p_pin text, p_status jsonb) to anon, authenticated;
