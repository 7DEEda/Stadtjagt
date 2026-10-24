-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.device_test_save(p_key text, p_payload jsonb)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  if p_key is null or p_key !~ '^[A-Z0-9]{12}$' then
    raise exception 'Ungültiger Schlüssel.' using errcode='P0001';
  end if;
  if p_payload is null or jsonb_typeof(p_payload) <> 'object' then
    raise exception 'Der Lauf fehlt.' using errcode='P0001';
  end if;
  -- Nachtrag 32: die Form, die tools/testlaeufe.py liest; sonst brach die Übersicht an einer einzigen Zeile ab
  if jsonb_typeof(p_payload->'tests') is distinct from 'object' or jsonb_typeof(p_payload->'bilanz') is distinct from 'object'
     or jsonb_typeof(p_payload->'suite') is distinct from 'number' then
    raise exception 'Der Lauf hat nicht die erwartete Form.' using errcode='P0001';
  end if;
  if exists (select 1 from jsonb_each(p_payload->'tests') e where jsonb_typeof(e.value) <> 'object') then
    raise exception 'Der Lauf hat nicht die erwartete Form.' using errcode='P0001';
  end if;
  if octet_length(p_payload::text) > 65536 then
    raise exception 'Der Lauf ist zu groß.' using errcode='P0001';
  end if;
  if not exists (select 1 from device_test_runs where run_key = p_key)
     and (select count(*) from device_test_runs) >= 2000 then
    raise exception 'Die Tabelle der Testläufe ist voll.' using errcode='P0001';
  end if;
  insert into device_test_runs (run_key, suite_version, label, payload)
  values (
    p_key,
    case when p_payload->>'suite' ~ '^[0-9]{1,6}$' then (p_payload->>'suite')::int else 0 end,
    left(coalesce(p_payload->>'label', ''), 80),
    p_payload)
  on conflict (run_key) do update
    set updated_at = now(), suite_version = excluded.suite_version,
        label = excluded.label, payload = excluded.payload;
  return json_build_object('ok', true, 'serverTime', now());
end $function$;
revoke all on function public.device_test_save(p_key text, p_payload jsonb) from public, anon, authenticated;
grant execute on function public.device_test_save(p_key text, p_payload jsonb) to public, anon, authenticated;
