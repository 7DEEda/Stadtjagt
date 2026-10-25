-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=nein, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.rb_befehl(p_pin text, p_befehl text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare r rueckblick_steuerung;
begin
  perform require_admin(p_pin);
  if p_befehl is null or p_befehl not in ('weiter', 'zurueck', 'pause', 'schwarz', 'start', 'ende') then
    raise exception 'Unbekannter Befehl.' using errcode = 'P0001';
  end if;
  insert into rueckblick_steuerung (id) values (1) on conflict (id) do nothing;
  select * into r from rueckblick_steuerung where id = 1 for update;
  if r.befehl_um is not null and r.befehl_um > clock_timestamp() - interval '250 milliseconds' then
    return json_build_object('ok', false, 'nr', r.nr);
  end if;
  update rueckblick_steuerung set nr = nr + 1, befehl = p_befehl, befehl_um = clock_timestamp() where id = 1
    returning * into r;
  return json_build_object('ok', true, 'nr', r.nr);
end $function$;
revoke all on function public.rb_befehl(p_pin text, p_befehl text) from public, anon, authenticated;
grant execute on function public.rb_befehl(p_pin text, p_befehl text) to anon, authenticated;
