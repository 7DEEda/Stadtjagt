#!/usr/bin/env python3
"""
Probelauf für Nachtrag 25 (Gruppenselfie) gegen die echte Datenbank, ohne Spuren.

    python tools/pruefstand/selfie_db.py

Spielt die Migration ein, legt ein Probe-Team an, prüft die neuen Funktionen
und wirft am Ende absichtlich einen Fehler. Das Ganze ist EIN DO-Block, also
eine einzige Anweisung: Postgres nimmt mit dem Fehler alles zurück, auch die
Migration selbst. Übrig bleibt nichts, egal wie die Verbindung die Anweisung
verpackt.

Während des Laufs (unter einer Sekunde) ist die Zeile game_state gesperrt;
Abfragen der App warten so lange. Nicht während eines laufenden Spiels starten.

Ausgabe: PROBELAUF_OK mit der Zahl der bestandenen Prüfungen, oder die erste
Prüfung, die nicht bestanden wurde.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import sql  # noqa: E402

MIGRATION = sql.REPO / "supabase" / "migrations" / "20260930180000_gruppenselfie.sql"

PROBE = r"""
do $probe$
declare
  v_pin text; v_code text := 'PROBE-' || upper(substr(md5(random()::text), 1, 6)); v_read text := md5(random()::text);
  t_id uuid; s1 stations; s2 stations; s3 stations; st json; r json; v_jpg text; v_n int := 0; v_max int;
begin
  execute $mig$__MIGRATION__$mig$;

  select admin_pin into v_pin from game_state where id = 1;
  -- drei Stationen braucht der Lauf; fehlen welche, kommen Probe-Stationen hinten dran
  while (select count(*) from stations) < 3 loop
    select coalesce(max(position), 0) into v_max from stations;
    insert into stations (position, name, answer) values (v_max + 1, 'Probe ' || (v_max + 1), 'x');
  end loop;
  select * into s1 from stations order by position limit 1;
  select * into s2 from stations order by position offset 1 limit 1;
  select * into s3 from stations order by position offset 2 limit 1;
  insert into teams (name, code, read_token) values ('Probelauf', v_code, v_read) returning id into t_id;
  update game_state set status = 'running', started_at = now(), test_mode = true,
    selfie_on = false, photos_delete_on = null where id = 1;

  -- A: Schalter aus, alles wie bisher
  insert into progress (team_id, station_id, checked_in_at) values (t_id, s1.id, now());
  r := submit_answer(v_code, 'x');
  if not coalesce((r->>'ok')::boolean, false) then raise exception 'PROBE FEHLT A1: Antwort nicht gewertet: %', r->>'message'; end if;
  st := team_state(v_code);
  if (st->'digits'->>0) is null then raise exception 'PROBE FEHLT A2: Schalter aus, aber die Ziffer fehlt'; end if;
  if (st->'selfie'->>'on') <> 'false' or (st->'selfie'->>'pending') is not null then raise exception 'PROBE FEHLT A3: selfie-Feld bei Schalter aus: %', st->'selfie'; end if;
  if (public_state()->>'selfieOn') <> 'false' then raise exception 'PROBE FEHLT A4: public_state.selfieOn'; end if;
  v_n := v_n + 4;

  -- B: Einschalten mitten im Spiel, das schon Gelöste braucht kein Foto
  perform admin_set_selfie(v_pin, true, current_date + 30);
  st := team_state(v_code);
  if (st->'selfie'->>'on') <> 'true' then raise exception 'PROBE FEHLT B1: Schalter nicht an'; end if;
  if (st->'digits'->>0) is null or (st->'selfie'->>'pending') is not null then raise exception 'PROBE FEHLT B2: alte Station verlangt ein Foto'; end if;
  if (public_state()->>'selfieOn') <> 'true' or (public_state()->>'photosDeleteOn') is null then raise exception 'PROBE FEHLT B3: public_state'; end if;
  v_n := v_n + 3;

  -- C: nächste Station lösen, die Ziffer wartet auf das Foto, die Zählung nicht
  insert into progress (team_id, station_id, checked_in_at) values (t_id, s2.id, now());
  r := submit_answer(v_code, 'x'); st := r->'state';
  if (st->'digits'->>1) is not null then raise exception 'PROBE FEHLT C1: Ziffer ohne Foto sichtbar'; end if;
  if (st->'selfie'->'pending'->>'position')::int is distinct from s2.position then raise exception 'PROBE FEHLT C2: pending = %', st->'selfie'->'pending'; end if;
  if (st->>'solvedCount')::int <> 2 then raise exception 'PROBE FEHLT C3: solvedCount = %', st->>'solvedCount'; end if;
  if (st->'station'->>'position')::int is distinct from s3.position then raise exception 'PROBE FEHLT C4: nächste Station = %', st->'station'->>'position'; end if;
  v_n := v_n + 4;

  -- D: nur JPEG, nur nach dem Lösen
  begin
    perform team_selfie(v_code, s2.position, encode('hallo'::bytea, 'base64'), encode('hallo'::bytea, 'base64'));
    raise exception 'PROBE FEHLT D1: Nicht-JPEG angenommen';
  exception when sqlstate 'P0001' then if sqlerrm like 'PROBE FEHLT%' then raise; end if; end;
  v_jpg := encode('\xffd8ffe000104a46494600'::bytea, 'base64');
  begin
    perform team_selfie(v_code, s3.position, v_jpg, v_jpg);
    raise exception 'PROBE FEHLT D2: Foto für ungelöste Station angenommen';
  exception when sqlstate 'P0001' then if sqlerrm like 'PROBE FEHLT%' then raise; end if; end;
  v_n := v_n + 2;

  -- E: Foto speichern, die Ziffer erscheint
  r := team_selfie(v_code, s2.position, v_jpg, v_jpg);
  if (r->'digits'->>1) is null or (r->'selfie'->>'pending') is not null then raise exception 'PROBE FEHLT E1: nach dem Foto fehlt die Ziffer'; end if;
  if json_array_length(r->'selfie'->'photos') <> 1 then raise exception 'PROBE FEHLT E2: photos = %', r->'selfie'->'photos'; end if;
  if (r->'selfie'->>'replaceable')::int is distinct from s2.position then raise exception 'PROBE FEHLT E3: replaceable = %', r->'selfie'->>'replaceable'; end if;
  perform team_selfie(v_code, s2.position, v_jpg, v_jpg);   -- ersetzen geht, solange an Station 3 nicht eingecheckt ist
  v_n := v_n + 4;

  -- F: abrufen mit Code und Mitlese-Schlüssel, nicht ohne Zugang
  if decode(replace(team_photo(v_code, null, null, s2.position, true)->>'data', E'\n', ''), 'base64') <> decode(v_jpg, 'base64') then raise exception 'PROBE FEHLT F1: Foto kommt verändert zurück'; end if;
  if (team_photo(null, null, v_read, s2.position, false)->>'data') is null then raise exception 'PROBE FEHLT F2: Mitlese-Schlüssel sieht das Foto nicht'; end if;
  if (team_photo(v_code, null, null, s1.position, false)->>'data') is not null then raise exception 'PROBE FEHLT F3: Foto, wo keines ist'; end if;
  begin
    perform team_photo(null, null, 'gibtesnicht', s2.position, false);
    raise exception 'PROBE FEHLT F4: Foto ohne Zugang';
  exception when sqlstate 'P0001' then if sqlerrm like 'PROBE FEHLT%' then raise; end if; end;
  begin
    perform team_photo(null, null, null, s2.position, false);
    raise exception 'PROBE FEHLT F5: Foto ganz ohne Schlüssel';
  exception when sqlstate 'P0001' then if sqlerrm like 'PROBE FEHLT%' then raise; end if; end;
  v_n := v_n + 5;

  -- G: Spielleitung
  if not exists (select 1 from json_array_elements(admin_photos(v_pin)) e where e->>'teamId' = t_id::text) then raise exception 'PROBE FEHLT G1: admin_photos'; end if;
  if (admin_photo(v_pin, t_id, s2.position, false)->>'data') is null then raise exception 'PROBE FEHLT G2: admin_photo'; end if;
  if (admin_state(v_pin)->>'photoCount')::int < 1 or (admin_state(v_pin)->>'selfieOn') <> 'true' then raise exception 'PROBE FEHLT G3: admin_state'; end if;
  begin
    perform admin_photos('falsch');
    raise exception 'PROBE FEHLT G4: admin_photos ohne PIN';
  exception when sqlstate 'P0001' then if sqlerrm like 'PROBE FEHLT%' then raise; end if; end;
  v_n := v_n + 4;

  -- H: an Station 3 eingecheckt, das Foto von Station 2 ist fest
  insert into progress (team_id, station_id, checked_in_at) values (t_id, s3.id, now());
  begin
    perform team_selfie(v_code, s2.position, v_jpg, v_jpg);
    raise exception 'PROBE FEHLT H1: Foto nach dem nächsten Check-in ersetzt';
  exception when sqlstate 'P0001' then if sqlerrm like 'PROBE FEHLT%' then raise; end if; end;
  if (team_state(v_code)->'selfie'->>'replaceable') is not null then raise exception 'PROBE FEHLT H2: replaceable trotz Check-in'; end if;
  v_n := v_n + 2;

  -- I: ohne Foto weiter, später nachreichen
  perform submit_answer(v_code, 'x');
  r := team_selfie_skip(v_code, s3.position);
  if (r->'digits'->>2) is null or (r->'selfie'->>'pending') is not null then raise exception 'PROBE FEHLT I1: Überspringen gibt die Ziffer nicht frei'; end if;
  if json_array_length(r->'selfie'->'photos') <> 1 then raise exception 'PROBE FEHLT I2: Überspringen legt ein Foto an'; end if;
  r := team_selfie(v_code, s3.position, v_jpg, v_jpg);
  if json_array_length(r->'selfie'->'photos') <> 2 then raise exception 'PROBE FEHLT I3: Nachreichen geht nicht'; end if;
  v_n := v_n + 3;

  -- J: Löschdatum erreicht, die Fotos verschwinden beim nächsten Abruf, der Fortschritt bleibt
  update game_state set photos_delete_on = current_date where id = 1;
  st := team_state(v_code);
  if exists (select 1 from station_photos where team_id = t_id) then raise exception 'PROBE FEHLT J1: fällige Fotos bleiben liegen'; end if;
  if (st->'digits'->>2) is null then raise exception 'PROBE FEHLT J2: mit den Fotos ging der Fortschritt verloren'; end if;
  v_n := v_n + 2;

  -- K: Zurücksetzen nimmt die Fotos mit (Fremdschlüssel auf progress)
  update game_state set photos_delete_on = null where id = 1;
  perform team_selfie(v_code, s3.position, v_jpg, v_jpg);
  delete from progress where team_id = t_id;
  if exists (select 1 from station_photos where team_id = t_id) then raise exception 'PROBE FEHLT K1: Fotos überleben das Zurücksetzen'; end if;
  v_n := v_n + 1;

  raise exception 'PROBELAUF_OK: % Prüfungen bestanden, alles zurückgenommen', v_n;
end $probe$;
"""


def main() -> None:
    migration = MIGRATION.read_text(encoding="utf-8")
    assert "$mig$" not in migration and "$probe$" not in migration
    probe = PROBE.replace("__MIGRATION__", migration)
    print(f"Sende den Probelauf ({len(probe)} Zeichen) an Projekt {sql.project_ref()} ...", file=sys.stderr)
    try:
        sql.ausfuehren(probe, read_only=False)
    except SystemExit as e:
        text = str(e)
        m = re.search(r"PROBELAUF_OK[^\"\\]*", text)
        if m:
            print(m.group(0))
            return
        m = re.search(r"PROBE FEHLT[^\"\\]*", text)
        sys.exit(m.group(0) if m else "Der Probelauf ist abgebrochen:\n" + text)
    sys.exit("Der Probelauf lief ohne den erwarteten Abbruch durch. Bitte prüfen, ob etwas stehen geblieben ist.")


if __name__ == "__main__":
    main()
