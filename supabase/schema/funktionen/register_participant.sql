-- Erzeugt von tools/schema_abzug.py aus der Live-Datenbank. Nicht von Hand ändern.

-- Ausführen: public=ja, anon=ja, authenticated=ja
CREATE OR REPLACE FUNCTION public.register_participant(p_name text, p_token text DEFAULT NULL::text)
 RETURNS json
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_name text := btrim(regexp_replace(coalesce(p_name,''), '\s+', ' ', 'g'));
        -- zwei zufällige UUIDs ohne Striche: 64 Hex-Zeichen, 244 Bit Zufall
        v_token text := replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', '');
        v_da participants;
begin
  if length(v_name) < 2 or length(v_name) > 60 then
    raise exception 'Bitte einen Namen mit 2 bis 60 Zeichen eingeben.' using errcode='P0001';
  end if;
  if norm(v_name) = '' then
    raise exception 'Bitte einen Namen mit lateinischen Buchstaben oder Ziffern eingeben.' using errcode='P0001';
  end if;
  -- Nachtrag 32: das Handy schickt seinen Geräte-Schlüssel selbst mit (gleiches Format wie unserer)
  if p_token is not null then
    if p_token !~ '^[0-9a-f]{64}$' then
      raise exception 'Ungültiger Geräte-Schlüssel. Bitte die Seite neu laden.' using errcode='P0001';
    end if;
    v_token := p_token;
  end if;
  -- Läuft gerade das Auslosen, warten wir, bis es durch ist; die Statusabfrage
  -- danach sieht dann schon 'drawn'. Anmeldungen untereinander warten nicht.
  perform 1 from game_state where id = 1 for share;
  -- Wiederholung derselben Anmeldung (Antwort ging verloren): der Schlüssel gehört schon einer Person, also Erfolg
  -- wie beim ersten Mal, auch wenn inzwischen ausgelost ist oder die Spielleitung den Namen berichtigt hat (dann mit
  -- dem neuen Namen). Wer den Schlüssel nicht kennt, bekommt für einen vorhandenen Namen weiter den Fehler unten.
  if p_token is not null then
    select * into v_da from participants where token = p_token;
    if found then
      return json_build_object('name', v_da.name, 'token', v_da.token, 'count', (select count(*) from participants));
    end if;
  end if;
  if (select status from game_state where id = 1) <> 'registration' then
    raise exception 'Die Anmeldung ist geschlossen. Melde dich über den Hilfe-Knopf bei der Spielleitung, sie trägt dich nach.'
      using errcode='P0001';
  end if;
  -- Audit 25.10.: Obergrenze, damit ein Skript die Liste nicht volllaufen lässt. Weiche Grenze: gleichzeitige
  -- Anmeldungen warten nicht aufeinander, es können ein paar mehr werden. Die Spielleitung trägt weiter nach.
  if (select count(*) from participants) >= 200 then
    raise exception 'Die Anmeldung ist voll. Melde dich bei der Spielleitung.' using errcode='P0001';
  end if;
  if exists (select 1 from participants where name_key = norm(v_name)) then
    raise exception 'Diesen Namen gibt es schon. Warst du das selbst, bist du schon dabei. Sonst ergänze etwas, zum Beispiel einen zweiten Vornamen.'
      using errcode='P0001';
  end if;
  begin
    insert into participants(name, name_key, token) values (v_name, norm(v_name), v_token);
  exception when unique_violation then
    -- Nachtrag 32: gleichzeitig angemeldet. Gehört der Schlüssel inzwischen einer Person, ist es dieselbe Anmeldung.
    select * into v_da from participants where token = v_token;
    if found then
      return json_build_object('name', v_da.name, 'token', v_da.token, 'count', (select count(*) from participants));
    end if;
    raise exception 'Diesen Namen gibt es schon. Warst du das selbst, bist du schon dabei. Sonst ergänze etwas, zum Beispiel einen zweiten Vornamen.'
      using errcode='P0001';
  end;
  return json_build_object('name', v_name, 'token', v_token, 'count', (select count(*) from participants));
end $function$;
revoke all on function public.register_participant(p_name text, p_token text) from public, anon, authenticated;
grant execute on function public.register_participant(p_name text, p_token text) to public, anon, authenticated;
