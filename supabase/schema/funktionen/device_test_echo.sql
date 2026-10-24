-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.device_test_echo(p_data text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  if octet_length(coalesce(p_data, '')) > 1048576 then
    raise exception 'Zu groß.' using errcode='P0001';
  end if;
  return json_build_object('bytes', octet_length(coalesce(p_data, '')), 'serverTime', clock_timestamp());
end $function$;
revoke all on function public.device_test_echo(p_data text) from public, anon, authenticated;
grant execute on function public.device_test_echo(p_data text) to public, anon, authenticated;
