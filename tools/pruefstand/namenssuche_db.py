#!/usr/bin/env python3
"""
Probelauf für die fehlertolerante Namenssuche (05.10.2026) gegen die echte Datenbank, ohne Spuren.

    python tools/pruefstand/namenssuche_db.py

Wie name_db.py: EIN DO-Block spielt die Migration ein, legt zwei erfundene Personen an, prüft und wirft
am Ende absichtlich einen Fehler. Postgres nimmt damit alles zurück, auch die Migration und die Personen.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import sql  # noqa: E402

MIGRATION = sql.REPO / "supabase" / "migrations" / "20261005120000_namenssuche.sql"

PROBE = r"""
do $probe$
declare r json; v_n int := 0;
begin
  execute $mig$__MIGRATION__$mig$;

  insert into participants(name, name_key) values ('Quirin Zettel', norm('Quirin Zettel')), ('Laquirin Pomm', norm('Laquirin Pomm'));

  -- A: genauer Treffer wie bisher
  r := lookup_participant('quirin zettel');
  if (r->>'found')::boolean is not true or r->>'name' <> 'Quirin Zettel' then raise exception 'PROBE FEHLT A1: %', r; end if;
  v_n := v_n + 1;

  -- B: Namensteil mit mehreren Treffern, Wortanfang zuerst
  r := lookup_participant('Quirin');
  if (r->>'found')::boolean or r->'candidates'->>0 <> 'Quirin Zettel' or r->'candidates'->>1 <> 'Laquirin Pomm' then raise exception 'PROBE FEHLT B1: %', r; end if;
  if r->>'fuzzy' is not null then raise exception 'PROBE FEHLT B2: Teiltreffer als fuzzy markiert: %', r; end if;
  v_n := v_n + 2;

  -- C: Tippfehler im ganzen Namen
  r := lookup_participant('Quirn Zettel');
  if (r->>'fuzzy')::boolean is not true or r->'candidates'->>0 <> 'Quirin Zettel' then raise exception 'PROBE FEHLT C1: %', r; end if;
  v_n := v_n + 1;

  -- D: vertauschte Wortfolge
  r := lookup_participant('Zettel Quirin');
  if (r->>'fuzzy')::boolean is not true or r->'candidates'->>0 <> 'Quirin Zettel' then raise exception 'PROBE FEHLT D1: %', r; end if;
  v_n := v_n + 1;

  -- E: Tippfehler in einem einzelnen Wort; ein einziger Vorschlag wird trotzdem nicht übernommen
  r := lookup_participant('Zetel');
  if (r->>'found')::boolean or (r->>'fuzzy')::boolean is not true or r->'candidates'->>0 <> 'Quirin Zettel' then raise exception 'PROBE FEHLT E1: %', r; end if;
  v_n := v_n + 1;

  -- F: nichts Ähnliches, zu kurz
  r := lookup_participant('Xyzqwvb');
  if (r->>'found')::boolean or r->'candidates' is not null then raise exception 'PROBE FEHLT F1: %', r; end if;
  r := lookup_participant('Qu');
  if (r->>'found')::boolean or r->'candidates' is not null then raise exception 'PROBE FEHLT F2: %', r; end if;
  v_n := v_n + 2;

  -- G: Abstand stimmt, Hilfsfunktion nicht von außen aufrufbar, Suche schon
  if name_abstand('kitten', 'sitting') <> 3 or name_abstand('', 'abc') <> 3 or name_abstand('anna', 'anna') <> 0 then raise exception 'PROBE FEHLT G1: Abstand falsch'; end if;
  if has_function_privilege('anon', 'name_abstand(text, text)', 'execute') then raise exception 'PROBE FEHLT G2: anon darf name_abstand aufrufen'; end if;
  if not has_function_privilege('anon', 'lookup_participant(text)', 'execute') then raise exception 'PROBE FEHLT G3: anon darf lookup_participant nicht mehr aufrufen'; end if;
  v_n := v_n + 3;

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
