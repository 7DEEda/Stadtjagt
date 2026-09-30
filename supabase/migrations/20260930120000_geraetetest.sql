-- ============================================================
--  STADTJAGD – Nachtrag 23: Geräte-Test
--
--  geraete-test.html prüft auf einem Handy, was das Spiel vom Gerät braucht,
--  und legt das Ergebnis hier als Testlauf ab. Die Seite darf nur schreiben:
--  die Tabelle hat keine Rechte für anon, der Weg hinein ist device_test_save.
--  Gelesen wird mit tools/testlaeufe.py über die Management-API.
--
--  Der Schlüssel eines Laufs entsteht auf dem Handy. Wer ihn nicht kennt, kann
--  den Lauf nicht überschreiben. Größe und Anzahl sind gedeckelt, damit
--  niemand die Tabelle vollschreibt.
--
--  device_test_echo nimmt Daten an und wirft sie weg: damit misst der
--  Kamera-Test, wie lange ein Foto zum Hochladen bräuchte, ohne eines zu speichern.
--
--  Einspielen: nach Nachtrag 22. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

create table if not exists device_test_runs (
  run_key       text primary key check (run_key ~ '^[A-Z0-9]{12}$'),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  suite_version int not null default 0,
  label         text not null default '',
  payload       jsonb not null
);

alter table device_test_runs enable row level security;
revoke all on device_test_runs from anon, authenticated;

create or replace function device_test_save(p_key text, p_payload jsonb) returns json
language plpgsql security definer set search_path = public as $$
begin
  if p_key is null or p_key !~ '^[A-Z0-9]{12}$' then
    raise exception 'Ungültiger Schlüssel.' using errcode='P0001';
  end if;
  if p_payload is null or jsonb_typeof(p_payload) <> 'object' then
    raise exception 'Der Lauf fehlt.' using errcode='P0001';
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
end $$;

create or replace function device_test_echo(p_data text) returns json
language plpgsql security definer set search_path = public as $$
begin
  if octet_length(coalesce(p_data, '')) > 1048576 then
    raise exception 'Zu groß.' using errcode='P0001';
  end if;
  return json_build_object('bytes', octet_length(coalesce(p_data, '')), 'serverTime', clock_timestamp());
end $$;

grant execute on function device_test_save(text, jsonb) to anon, authenticated;
grant execute on function device_test_echo(text) to anon, authenticated;
