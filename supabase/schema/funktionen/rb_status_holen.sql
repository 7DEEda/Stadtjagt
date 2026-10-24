-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.rb_status_holen(p_pin text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare r rueckblick_steuerung;
begin
  perform require_admin(p_pin);
  insert into rueckblick_steuerung (id) values (1) on conflict (id) do nothing;
  update rueckblick_steuerung set handy_um = clock_timestamp() where id = 1 returning * into r;
  return json_build_object('status', r.status,
    'alter_s', case when r.status_um is null then null else round(extract(epoch from clock_timestamp() - r.status_um)::numeric, 1) end);
end $function$;
revoke all on function public.rb_status_holen(p_pin text) from public, anon, authenticated;
grant execute on function public.rb_status_holen(p_pin text) to anon, authenticated;
