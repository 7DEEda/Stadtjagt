-- ============================================================
--  STADTJAGD – Nachtrag 18: Teamleitung loggt sich ohne Tippen ein
--
--  Wer sich auf dem eigenen Handy angemeldet hat, ist über den Geräte-
--  Schlüssel bekannt. Ist diese Person gerade Teamleitung, gibt leader_code
--  den Team-Code heraus, und die App loggt damit unter #/team ein. Tippen
--  bleibt der Ausweg für Handys ohne Anmeldung (Code von der Spielleitung)
--  und für die Spielleitung selbst. Gibt die Leitung ab, bekommt die neue
--  Leitung den Code auf demselben Weg, ohne ihn weitersagen zu müssen.
--
--  Einspielen: nach Nachtrag 17. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

create or replace function leader_code(p_token text) returns json
language plpgsql security definer set search_path = public as $$
declare v participants; t teams;
begin
  if coalesce(p_token, '') = '' then
    raise exception 'Unbekanntes Gerät.' using errcode = 'P0001';
  end if;
  select * into v from participants where token = p_token;
  if not found then
    raise exception 'Unbekanntes Gerät.' using errcode = 'P0001';
  end if;
  select * into t from teams where id = v.team_id and leader_participant_id = v.id;
  if not found then
    raise exception 'Du bist gerade keine Teamleitung.' using errcode = 'P0001';
  end if;
  return json_build_object('code', t.code, 'teamName', t.name, 'name', v.name);
end $$;

grant execute on function leader_code(text) to anon, authenticated;

notify pgrst, 'reload schema';
