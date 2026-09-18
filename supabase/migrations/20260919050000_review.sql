-- ============================================================
--  STADTJAGD – Nachtrag 15: zwei Punkte aus dem Code-Review vom 19.09.2026
--
--  1. Nachtrag 13 hat norm() geändert (Großbuchstaben mit Umlaut werden selbst
--     gefaltet), aber die gespeicherten participants.name_key nicht nachgezogen.
--     Live wich keine Zeile ab (die Supabase-Locale faltet lower() korrekt),
--     trotzdem gehört der Nachzug zu jeder Änderung an norm().
--  2. submit_answer las den Fehlversuchszähler ohne Zeilensperre. Zwei
--     gleichzeitige Falschantworten desselben Teams konnten denselben Stand
--     lesen und die Denkpause um einen Versuch verzögern. Jetzt sperrt die
--     Funktion die progress-Zeile (select ... for update).
--
--  Einspielen: nach Nachtrag 14. Mehrfach ausführbar, löscht keine Daten.
-- ============================================================

-- ---------- 1. name_key nachziehen ----------
update participants set name_key = norm(name) where name_key <> norm(name);

-- ---------- 2. Fehlversuche unter Zeilensperre zählen ----------
create or replace function submit_answer(p_code text, p_answer text)
returns json language plpgsql security definer set search_path = public as $$
declare t teams; g game_state; cur stations; row_p progress;
        v_attempts int; v_locked boolean;
begin
  t := team_by_code(p_code);
  select * into g from game_state where id = 1;
  if g.status <> 'running' then
    return json_build_object('ok', false, 'message', 'Das Spiel läuft gerade nicht.', 'state', team_state(p_code));
  end if;
  cur := current_station(t.id);
  if cur.id is null then
    return json_build_object('ok', false, 'message', 'Alle Stationen sind gelöst.', 'state', team_state(p_code));
  end if;
  -- Sperre: gleichzeitige Antworten desselben Teams laufen nacheinander, der Zähler stimmt
  select * into row_p from progress where team_id = t.id and station_id = cur.id for update;
  if row_p.checked_in_at is null then
    return json_build_object('ok', false, 'message', 'Erst am Ort einchecken, dann gibt es das Rätsel.',
      'state', team_state(p_code));
  end if;
  if not g.test_mode and row_p.locked_until is not null and row_p.locked_until > now() then
    return json_build_object('ok', false,
      'message', 'Denkpause: noch ' || ceil(extract(epoch from row_p.locked_until - now())) || ' Sekunden.',
      'state', team_state(p_code));
  end if;

  if g.test_mode or answer_ok(p_answer, cur.answer) then
    update progress set solved_at = now(), failed_attempts = 0, locked_until = null
      where team_id = t.id and station_id = cur.id;
    return json_build_object('ok', true,
      'message', case when g.test_mode then 'Testmodus: jede Antwort zählt. Eine Ziffer ist frei.'
                      else 'Richtig. Eine Ziffer ist frei.' end,
      'state', team_state(p_code));
  end if;

  v_attempts := case when row_p.locked_until is not null and row_p.locked_until <= now()
                     then 1 else row_p.failed_attempts + 1 end;
  v_locked := v_attempts >= 3;
  update progress
    set failed_attempts = case when v_locked then 0 else v_attempts end,
        locked_until    = case when v_locked then now() + interval '2 minutes' else null end
    where team_id = t.id and station_id = cur.id;
  return json_build_object('ok', false,
    'message', case when v_locked then 'Dreimal falsch. Zwei Minuten Denkpause für euer Team.'
                    else 'Leider falsch. Noch ' || (3 - v_attempts)
                         || case when 3 - v_attempts = 1 then ' Versuch.' else ' Versuche.' end end,
    'state', team_state(p_code));
end $$;

notify pgrst, 'reload schema';
