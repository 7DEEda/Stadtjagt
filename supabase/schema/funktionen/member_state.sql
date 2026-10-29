-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.member_state(p_token text, p_akku integer DEFAULT NULL::integer, p_laedt boolean DEFAULT NULL::boolean)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v participants; t teams;
        v_akku int := case when p_akku between 0 and 100 then p_akku end;
begin
  if coalesce(p_token, '') = '' then
    raise exception 'Unbekanntes Gerät.' using errcode = 'P0001';
  end if;
  select * into v from participants where token = p_token;
  if not found then
    raise exception 'Unbekanntes Gerät.' using errcode = 'P0001';
  end if;
  -- Rollen und Akku 29.10.: letzter Abruf und Akku merken. Ohne gültigen Akku (iPhone, ungültiger Wert) bleibt der
  -- bekannte Stand. Höchstens eine Schreibung je 20 s und Person, außer der Akku ändert sich.
  update participants set gesehen_at = now(),
         akku       = coalesce(v_akku, akku),
         akku_laedt = case when v_akku is null then akku_laedt else coalesce(p_laedt, false) end,
         akku_at    = case when v_akku is null then akku_at else now() end
   where id = v.id
     and (gesehen_at is null or gesehen_at < now() - interval '20 seconds'
          or (v_akku is not null and (akku is distinct from v_akku or akku_laedt is distinct from coalesce(p_laedt, false))));
  if v.team_id is null then
    return json_build_object('name', v.name, 'team', null, 'ichLeite', false);
  end if;
  select * into t from teams where id = v.team_id;
  return ((team_state(t.code)::jsonb #- '{team,code}')
          || jsonb_build_object('name', v.name, 'ichLeite', t.leader_participant_id = v.id))::json;
end $function$;
revoke all on function public.member_state(p_token text, p_akku integer, p_laedt boolean) from public, anon, authenticated;
grant execute on function public.member_state(p_token text, p_akku integer, p_laedt boolean) to public, anon, authenticated;
