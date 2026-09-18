-- ============================================================
--  STADTJAGD – Nachtrag 12: Anmeldung schließt wieder mit dem Auslosen
--
--  Nachtrag 10 hatte die Selbstanmeldung bis zum Spielende geöffnet. Seit
--  Nachtrag 11 bekommt jede Anmeldung einen Geräte-Schlüssel zum Mitlesen.
--  Zusammen ergab das eine Lücke: Wer mitten im Spiel einen erfundenen
--  Namen anmeldete, landete in irgendeinem Team und las dort Rätsel und
--  Ziffern mit. Da alle Teams dieselben Ziffern haben, genügte ein
--  schnelles Team für den Koffer-Code.
--
--  Jetzt: selbst anmelden nur, solange die Anmeldung offen ist. Danach
--  meldet man sich über den Hilfe-Knopf, und die Spielleitung trägt
--  Nachzügler im Admin-Bereich ein (admin_add_participant, ins kleinste
--  Team). Solche Nachzügler haben keinen Geräte-Schlüssel und lesen nicht
--  mit; sie sehen ihr Team über die Namenssuche.
--
--  Einspielen: nach Nachtrag 11. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

create or replace function register_participant(p_name text) returns json
language plpgsql security definer set search_path = public as $$
declare v_name text := btrim(regexp_replace(coalesce(p_name,''), '\s+', ' ', 'g'));
        -- zwei zufällige UUIDs ohne Striche: 64 Hex-Zeichen, 244 Bit Zufall
        v_token text := replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', '');
begin
  if length(v_name) < 2 or length(v_name) > 60 then
    raise exception 'Bitte einen Namen mit 2 bis 60 Zeichen eingeben.' using errcode='P0001';
  end if;
  if (select status from game_state where id = 1) <> 'registration' then
    raise exception 'Die Anmeldung ist geschlossen. Melde dich über den Hilfe-Knopf bei der Spielleitung, sie trägt dich nach.'
      using errcode='P0001';
  end if;
  if exists (select 1 from participants where name_key = norm(v_name)) then
    raise exception 'Dieser Name ist schon angemeldet. Hast du dich schon eingetragen? Dann bist du dabei.'
      using errcode='P0001';
  end if;
  insert into participants(name, name_key, token) values (v_name, norm(v_name), v_token);
  return json_build_object('name', v_name, 'token', v_token, 'count', (select count(*) from participants));
end $$;

notify pgrst, 'reload schema';
