-- ============================================================
--  STADTJAGD – Nachtrag 5: Anmeldung komplett leeren
--
--  Bisher ließen sich Teilnehmende nur einzeln über das × entfernen.
--  Nach einem Probelauf mit Testeinträgen ist das mühsam, und es gab
--  keinen Weg, wieder bei null anzufangen.
--
--  admin_clear_participants räumt alles ab, was an Personen und Teams
--  hängt, und stellt das Spiel zurück auf "registration", damit sich
--  wieder jemand anmelden kann. Stationen, Rätsel, Ziffern und die
--  Admin-PIN bleiben unberührt.
--
--  Einspielen: nach Nachtrag 4. Mehrfach ausführbar.
-- ============================================================

create or replace function admin_clear_participants(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  -- Reihenfolge: erst was an Teams hängt, dann die Teams, dann die Personen
  delete from progress where true;
  delete from team_positions where true;
  delete from position_log where true;
  update game_state set winner_team_id = null where id = 1;
  update participants set team_id = null where team_id is not null;
  delete from teams where true;
  delete from participants where true;
  update game_state set status = 'registration', started_at = null, finished_at = null
    where id = 1;
  return admin_state(p_pin);
end $$;

grant execute on function admin_clear_participants(text) to anon, authenticated;

notify pgrst, 'reload schema';
