-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.admin_notweg(p_pin text, p_code text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare t teams; v_token text; v_bis timestamptz := now() + interval '12 hours';
begin
  perform require_admin(p_pin);
  t := team_by_code(p_code);
  delete from notweg_schluessel where gilt_bis < now();
  v_token := 'nw-' || replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', '');
  insert into notweg_schluessel (token, team_id, gilt_bis) values (v_token, t.id, v_bis);
  return json_build_object('token', v_token, 'team', t.name, 'giltBis', v_bis);
end $function$;
revoke all on function public.admin_notweg(p_pin text, p_code text) from public, anon, authenticated;
grant execute on function public.admin_notweg(p_pin text, p_code text) to public, anon, authenticated;
