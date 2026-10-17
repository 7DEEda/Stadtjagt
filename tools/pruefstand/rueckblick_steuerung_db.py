#!/usr/bin/env python3
"""
Probelauf für Nachtrag 37 (Fernbedienung der Rückblick-Show, Migration 20261017090000_rueckblick_steuerung.sql) gegen
die echte Datenbank, ohne Spuren.

    python tools/pruefstand/rueckblick_steuerung_db.py           mit Migration (grün)
    python tools/pruefstand/rueckblick_steuerung_db.py --ohne    ohne Migration (zeigt, was fehlt: rot)

EIN DO-Block spielt die Migration ein, prüft und wirft am Ende absichtlich einen Fehler. Auch wenn eine Prüfung
scheitert, endet der Block mit einer Ausnahme: der Server rollt die ganze Anweisung zurück (auch die Tabelle).
Geprüft: falsche PIN an allen fünf Funktionen, unbekannter Befehl, Zähler, Mindestabstand 250 ms, rb_poll liefert und
verwirft (älter als 30 s), Zähler übernehmen (p_seit null), Status setzen, holen, Größe, rb_ende löscht Status und
Befehl, Rechte (anon an den fünf Funktionen offen, die Tabelle gesperrt, interne Hilfsfunktionen gesperrt).
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sql  # noqa: E402
from rechte_db import INTERN  # noqa: E402

MIGRATION = sql.REPO / "supabase" / "migrations" / "20261017090000_rueckblick_steuerung.sql"
FUNKTIONEN = ["rb_befehl(text,text)", "rb_poll(text,bigint)", "rb_status_setzen(text,jsonb)", "rb_status_holen(text)", "rb_ende(text)"]

PROBE = r"""
do $probe$
declare v_pin text; v_n int := 0; r json; v_err text; f text; rr text; v_nr bigint; v_b text;
        v_falsch text := 'falsch-' || md5(random()::text);
begin
  __MIGRATION__
  -- ohne Migration: sagen, was fehlt (sonst bräche der Block an einem unbekannten Namen ab)
  foreach f in array array[__FUNKTIONEN__] loop
    if to_regprocedure(f) is null then raise exception 'PROBE FEHLT 0: Funktion % gibt es nicht', f; end if;
  end loop;
  if to_regclass('public.rueckblick_steuerung') is null then raise exception 'PROBE FEHLT 0: Tabelle rueckblick_steuerung gibt es nicht'; end if;
  v_n := v_n + 6;
  select admin_pin into v_pin from game_state where id = 1;

  -- ---------- 1: falsche PIN an jeder Funktion ----------
  begin perform rb_befehl(v_falsch, 'weiter'); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is distinct from 'Falsche PIN.' then raise exception 'PROBE FEHLT 1A: rb_befehl mit falscher PIN: %', coalesce(v_err, 'angenommen'); end if;
  begin perform rb_poll(v_falsch, 0); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is distinct from 'Falsche PIN.' then raise exception 'PROBE FEHLT 1B: rb_poll mit falscher PIN: %', coalesce(v_err, 'angenommen'); end if;
  begin perform rb_status_setzen(v_falsch, '{"a": 1}'::jsonb); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is distinct from 'Falsche PIN.' then raise exception 'PROBE FEHLT 1C: rb_status_setzen mit falscher PIN: %', coalesce(v_err, 'angenommen'); end if;
  begin perform rb_status_holen(v_falsch); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is distinct from 'Falsche PIN.' then raise exception 'PROBE FEHLT 1D: rb_status_holen mit falscher PIN: %', coalesce(v_err, 'angenommen'); end if;
  begin perform rb_ende(v_falsch); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is distinct from 'Falsche PIN.' then raise exception 'PROBE FEHLT 1E: rb_ende mit falscher PIN: %', coalesce(v_err, 'angenommen'); end if;
  begin perform rb_poll(null, 0); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is distinct from 'Falsche PIN.' then raise exception 'PROBE FEHLT 1F: rb_poll ohne PIN: %', coalesce(v_err, 'angenommen'); end if;
  v_n := v_n + 6;

  -- ---------- 2: unbekannter Befehl ----------
  foreach v_b in array array['loeschen', 'Weiter', '', 'weiter ', 'drop'] loop
    begin perform rb_befehl(v_pin, v_b); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is distinct from 'Unbekannter Befehl.' then raise exception 'PROBE FEHLT 2A: Befehl "%": %', v_b, coalesce(v_err, 'angenommen'); end if;
    v_n := v_n + 1;
  end loop;
  begin perform rb_befehl(v_pin, null); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is distinct from 'Unbekannter Befehl.' then raise exception 'PROBE FEHLT 2B: Befehl null: %', coalesce(v_err, 'angenommen'); end if;
  v_n := v_n + 1;

  -- ---------- 3: Zähler übernehmen, Befehl, Zähler steigt, rb_poll liefert genau einmal ----------
  update rueckblick_steuerung set befehl_um = clock_timestamp() - interval '1 minute' where id = 1;   -- kein Mindestabstand aus früheren Läufen
  r := rb_poll(v_pin, null);
  if r is null or r->>'nr' is null or r->>'befehl' is not null then raise exception 'PROBE FEHLT 3A: Zähler übernehmen: %', r; end if;
  v_nr := (r->>'nr')::bigint;
  r := rb_befehl(v_pin, 'weiter');
  if not coalesce((r->>'ok')::boolean, false) or (r->>'nr')::bigint <> v_nr + 1 then raise exception 'PROBE FEHLT 3B: Befehl, Zähler: %', r; end if;
  r := rb_poll(v_pin, v_nr);
  if r is null or (r->>'nr')::bigint <> v_nr + 1 or r->>'befehl' is distinct from 'weiter' then raise exception 'PROBE FEHLT 3C: rb_poll liefert: %', r; end if;
  r := rb_poll(v_pin, v_nr + 1);
  if r is not null then raise exception 'PROBE FEHLT 3D: rb_poll ohne neuen Befehl: %', r; end if;
  r := rb_poll(v_pin, v_nr + 50);   -- Zähler der Show größer (Tabelle neu angelegt): Zähler übernehmen, nichts ausführen
  if r is null or (r->>'nr')::bigint <> v_nr + 1 or r->>'befehl' is not null then raise exception 'PROBE FEHLT 3E: Zähler der Show zu groß: %', r; end if;
  v_n := v_n + 5;

  -- ---------- 4: Mindestabstand 250 ms ----------
  r := rb_befehl(v_pin, 'zurueck');
  if coalesce((r->>'ok')::boolean, true) or (select nr from rueckblick_steuerung where id = 1) <> v_nr + 1 then raise exception 'PROBE FEHLT 4A: zweiter Befehl sofort: %', r; end if;
  if (select befehl from rueckblick_steuerung where id = 1) <> 'weiter' then raise exception 'PROBE FEHLT 4B: abgewiesener Befehl überschreibt'; end if;
  perform pg_sleep(0.3);
  r := rb_befehl(v_pin, 'zurueck');
  if not coalesce((r->>'ok')::boolean, false) or (r->>'nr')::bigint <> v_nr + 2 then raise exception 'PROBE FEHLT 4C: nach 300 ms: %', r; end if;
  v_n := v_n + 3;

  -- ---------- 5: verwerfen: älter als 30 s ----------
  update rueckblick_steuerung set befehl_um = clock_timestamp() - interval '31 seconds' where id = 1;
  r := rb_poll(v_pin, v_nr + 1);
  if r is null or (r->>'nr')::bigint <> v_nr + 2 or r->>'befehl' is not null then raise exception 'PROBE FEHLT 5A: alter Befehl nicht verworfen: %', r; end if;
  update rueckblick_steuerung set befehl_um = clock_timestamp() - interval '29 seconds' where id = 1;
  r := rb_poll(v_pin, v_nr + 1);
  if r->>'befehl' is distinct from 'zurueck' then raise exception 'PROBE FEHLT 5B: 29 s alter Befehl verworfen: %', r; end if;
  v_n := v_n + 2;

  -- ---------- 6: alle sechs Befehle ----------
  foreach v_b in array array['weiter', 'zurueck', 'pause', 'schwarz', 'start', 'ende'] loop
    update rueckblick_steuerung set befehl_um = clock_timestamp() - interval '1 second' where id = 1;
    r := rb_befehl(v_pin, v_b);
    if not coalesce((r->>'ok')::boolean, false) then raise exception 'PROBE FEHLT 6: Befehl % abgewiesen: %', v_b, r; end if;
    v_n := v_n + 1;
  end loop;
  v_nr := (select nr from rueckblick_steuerung where id = 1);

  -- ---------- 7: Status setzen und holen, Handy gesehen ----------
  update rueckblick_steuerung set handy_um = null where id = 1;
  r := rb_status_setzen(v_pin, '{"kapitel": "Rangliste", "mod": ["Tiger, 8 Leute"]}'::jsonb);
  if not coalesce((r->>'ok')::boolean, false) or r->>'handy_alter_s' is not null then raise exception 'PROBE FEHLT 7A: Status setzen: %', r; end if;
  r := rb_status_holen(v_pin);
  if r->'status'->>'kapitel' is distinct from 'Rangliste' or (r->>'alter_s')::numeric > 5 or (r->>'alter_s')::numeric < 0 then raise exception 'PROBE FEHLT 7B: Status holen: %', r; end if;
  r := rb_status_setzen(v_pin, '{"kapitel": "Platz 3"}'::jsonb);
  if r->>'handy_alter_s' is null or (r->>'handy_alter_s')::numeric > 5 then raise exception 'PROBE FEHLT 7C: Show sieht das Handy nicht: %', r; end if;
  update rueckblick_steuerung set status_um = clock_timestamp() - interval '7 seconds' where id = 1;
  r := rb_status_holen(v_pin);
  if (r->>'alter_s')::numeric < 6.5 then raise exception 'PROBE FEHLT 7D: Alter des Status: %', r; end if;
  v_n := v_n + 4;

  -- ---------- 8: Größe und Form ----------
  begin perform rb_status_setzen(v_pin, jsonb_build_object('x', repeat('a', 21000))); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is distinct from 'Der Status ist zu groß.' then raise exception 'PROBE FEHLT 8A: 21 KB: %', coalesce(v_err, 'angenommen'); end if;
  r := rb_status_setzen(v_pin, jsonb_build_object('x', repeat('a', 19000)));
  if not coalesce((r->>'ok')::boolean, false) then raise exception 'PROBE FEHLT 8B: 19 KB abgewiesen'; end if;
  foreach f in array array['[1, 2]', '"text"', '3'] loop
    begin perform rb_status_setzen(v_pin, f::jsonb); v_err := null; exception when others then v_err := sqlerrm; end;
    if v_err is distinct from 'Der Status fehlt.' then raise exception 'PROBE FEHLT 8C: kein Objekt %: %', f, coalesce(v_err, 'angenommen'); end if;
    v_n := v_n + 1;
  end loop;
  begin perform rb_status_setzen(v_pin, null); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is distinct from 'Der Status fehlt.' then raise exception 'PROBE FEHLT 8D: Status null: %', coalesce(v_err, 'angenommen'); end if;
  v_n := v_n + 3;

  -- ---------- 9: rb_ende löscht Status, Befehl und Moderation; der Zähler bleibt ----------
  perform rb_status_setzen(v_pin, '{"mod": ["Tiger: Anna Kaya, Elif Keller"]}'::jsonb);
  r := rb_ende(v_pin);
  if not coalesce((r->>'ok')::boolean, false) then raise exception 'PROBE FEHLT 9A: rb_ende: %', r; end if;
  if exists (select 1 from rueckblick_steuerung where id = 1 and (status is not null or status_um is not null or befehl is not null
             or befehl_um is not null or handy_um is not null)) then raise exception 'PROBE FEHLT 9B: nach rb_ende steht noch etwas'; end if;
  if (select nr from rueckblick_steuerung where id = 1) <> v_nr then raise exception 'PROBE FEHLT 9C: Zähler nach rb_ende verändert'; end if;
  r := rb_status_holen(v_pin);
  if r->'status' is not null and json_typeof(r->'status') <> 'null' or r->>'alter_s' is not null then raise exception 'PROBE FEHLT 9D: Status nach rb_ende: %', r; end if;
  if rb_poll(v_pin, v_nr) is not null then raise exception 'PROBE FEHLT 9E: rb_poll nach rb_ende'; end if;
  r := rb_befehl(v_pin, 'weiter');   -- nach rb_ende sofort wieder bedienbar (kein Mindestabstand aus dem gelöschten Befehl)
  if not coalesce((r->>'ok')::boolean, false) or (r->>'nr')::bigint <> v_nr + 1 then raise exception 'PROBE FEHLT 9F: Befehl nach rb_ende: %', r; end if;
  v_n := v_n + 6;

  -- ---------- 10: Rechte ----------
  foreach f in array array[__FUNKTIONEN__] loop
    foreach rr in array array['anon', 'authenticated'] loop
      if not has_function_privilege(rr, f, 'execute') then raise exception 'PROBE FEHLT 10A: % darf % nicht ausführen', rr, f; end if;
      v_n := v_n + 1;
    end loop;
    if not (select prosecdef from pg_proc where oid = to_regprocedure(f)) then raise exception 'PROBE FEHLT 10B: % nicht security definer', f; end if;
    v_n := v_n + 1;
  end loop;
  foreach rr in array array['anon', 'authenticated'] loop
    foreach f in array array['select', 'insert', 'update', 'delete'] loop
      if has_table_privilege(rr, 'public.rueckblick_steuerung', f) then raise exception 'PROBE FEHLT 10C: % darf % auf rueckblick_steuerung', rr, f; end if;
      v_n := v_n + 1;
    end loop;
  end loop;
  if not (select relrowsecurity from pg_class where oid = 'public.rueckblick_steuerung'::regclass) then raise exception 'PROBE FEHLT 10D: RLS aus'; end if;
  foreach f in array array[__INTERN__] loop
    foreach rr in array array['anon', 'authenticated'] loop
      if has_function_privilege(rr, f, 'execute') then raise exception 'PROBE FEHLT 10E: % darf % ausführen', rr, f; end if;
      v_n := v_n + 1;
    end loop;
  end loop;
  -- genau eine Zeile, id 1
  if (select count(*) from rueckblick_steuerung) <> 1 then raise exception 'PROBE FEHLT 10F: nicht genau eine Zeile'; end if;
  begin insert into rueckblick_steuerung (id) values (2); v_err := null; exception when others then v_err := sqlerrm; end;
  if v_err is null then raise exception 'PROBE FEHLT 10G: zweite Zeile möglich'; end if;
  v_n := v_n + 3;

  raise exception 'PROBELAUF_OK: % Prüfungen bestanden, alles zurückgenommen', v_n;
end $probe$;
"""


def main() -> None:
    migration = "" if "--ohne" in sys.argv else MIGRATION.read_text(encoding="utf-8")
    assert "$mig$" not in migration and "$probe$" not in migration
    liste = lambda xs: ", ".join("'" + x + "'" for x in xs)  # noqa: E731
    probe = (PROBE.replace("__INTERN__", liste(INTERN)).replace("__FUNKTIONEN__", liste(FUNKTIONEN))
             .replace("__MIGRATION__", f"execute $mig${migration}$mig$;" if migration.strip() else ""))
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
