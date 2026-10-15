#!/usr/bin/env python3
"""
Probelauf für die Längengrenze der Namenssuche (Code-Review 15.10.2026, Befund 3) gegen die echte Datenbank,
ohne Spuren.

    python tools/pruefstand/namenssuche_grenze_db.py          mit Migration 20261015090000 (grün)
    python tools/pruefstand/namenssuche_grenze_db.py --ohne   Stand der Datenbank ohne Migration (rot)

Wie namenssuche_db.py: EIN DO-Block spielt die Migration ein, legt erfundene Personen an, prüft und wirft am Ende
absichtlich einen Fehler. Auch wenn eine Prüfung scheitert, endet der Block mit einer Ausnahme: Postgres nimmt
alles zurück, auch die Migration und die Personen. Die langen Eingaben laufen erst nach der Prüfung, die ohne
Migration schon scheitert: der rote Lauf belastet die Datenbank nicht.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import sql  # noqa: E402

MIGRATION = sql.REPO / "supabase" / "migrations" / "20261015090000_namenssuche_grenze.sql"

# Interne Hilfsfunktionen wie in rechte_db.py, dazu name_abstand: weder anon noch authenticated
INTERN = ["norm(text)", "dist_m(double precision,double precision,double precision,double precision)",
          "team_by_code(text)", "current_station(uuid)", "require_admin(text)", "answer_ok(text,text)",
          "aktive_route()", "name_abstand(text,text)"]

PROBE = r"""
do $probe$
declare r json; v_n int := 0; t0 timestamptz; d interval; f text; ro text;
        v_lang text := 'Pommerzettel Pommerzettel Pommerzettel Pommerzettel Pommerzettel';   -- norm: 60 Zeichen
begin
  execute $mig$__MIGRATION__$mig$;

  insert into participants(name, name_key) values ('Quirin Zettel', norm('Quirin Zettel')), ('Laquirin Pomm', norm('Laquirin Pomm')),
    (v_lang, norm(v_lang)), ('Wendelinus ' || repeat('Langername', 7), norm('Wendelinus ' || repeat('Langername', 7)));
  if length(norm(v_lang)) <> 60 then raise exception 'PROBE FEHLT 0: Testname hat % statt 60 Zeichen', length(norm(v_lang)); end if;

  -- A: über 60 Zeichen keine Tippfehler-Suche (ein Zeichen zu viel am 60er-Namen fände ihn sonst als Vorschlag)
  r := lookup_participant(v_lang || 'x');
  if (r->>'found')::boolean or r->'candidates' is not null then raise exception 'PROBE FEHLT A1: 61 Zeichen gingen in die Tippfehler-Suche: %', r; end if;
  v_n := v_n + 1;

  -- B: genau 60 Zeichen gehen noch hinein; über 60 bleibt die genaue Suche
  r := lookup_participant(replace(v_lang, 'Pommerzettel Pommerzettel Pommerzettel Pommerzettel', 'Pommerzettel Pommerzettel Pommerzettel Pommerzetel'));
  if (r->>'fuzzy')::boolean is not true or r->'candidates'->>0 <> v_lang then raise exception 'PROBE FEHLT B1: Tippfehler bei 59 Zeichen nicht gefunden: %', r; end if;
  r := lookup_participant(v_lang);
  if (r->>'found')::boolean is not true then raise exception 'PROBE FEHLT B2: 60 Zeichen genau nicht gefunden: %', r; end if;
  r := lookup_participant('wendelinus ' || repeat('langername', 7));
  if (r->>'found')::boolean is not true then raise exception 'PROBE FEHLT B3: 80 Zeichen genau nicht gefunden: %', r; end if;
  v_n := v_n + 3;

  -- C: Tippfehler-Treffer wie bisher (wie namenssuche_db.py)
  r := lookup_participant('quirin zettel');
  if (r->>'found')::boolean is not true or r->>'name' <> 'Quirin Zettel' then raise exception 'PROBE FEHLT C1: %', r; end if;
  r := lookup_participant('Quirin');
  if (r->>'found')::boolean or r->'candidates'->>0 <> 'Quirin Zettel' or r->'candidates'->>1 <> 'Laquirin Pomm' or r->>'fuzzy' is not null then raise exception 'PROBE FEHLT C2: %', r; end if;
  r := lookup_participant('Quirn Zettel');
  if (r->>'fuzzy')::boolean is not true or r->'candidates'->>0 <> 'Quirin Zettel' then raise exception 'PROBE FEHLT C3: %', r; end if;
  r := lookup_participant('Zettel Quirin');
  if (r->>'fuzzy')::boolean is not true or r->'candidates'->>0 <> 'Quirin Zettel' then raise exception 'PROBE FEHLT C4: %', r; end if;
  r := lookup_participant('Zetel');
  if (r->>'found')::boolean or (r->>'fuzzy')::boolean is not true or r->'candidates'->>0 <> 'Quirin Zettel' then raise exception 'PROBE FEHLT C5: %', r; end if;
  r := lookup_participant('Xyzqwvb');
  if (r->>'found')::boolean or r->'candidates' is not null then raise exception 'PROBE FEHLT C6: %', r; end if;
  v_n := v_n + 6;

  -- D: lange Eingabe schnell und ohne Fehler
  t0 := clock_timestamp();
  r := lookup_participant(repeat('Quirin Zettel ', 400));
  d := clock_timestamp() - t0;
  if (r->>'found')::boolean or r->'candidates' is not null then raise exception 'PROBE FEHLT D1: %', r; end if;
  if d > interval '100 milliseconds' then raise exception 'PROBE FEHLT D2: 5600 Zeichen brauchten %', d; end if;
  v_n := v_n + 2;

  -- E: viele Personen, Eingabe mit 60 Zeichen ohne passende Länge: kein Levenshtein, schnell
  insert into participants(name, name_key) select 'Probeperson Nummer ' || i, norm('Probeperson Nummer ' || i) from generate_series(1, 150) i;
  t0 := clock_timestamp();
  r := lookup_participant(repeat('xq', 30));
  d := clock_timestamp() - t0;
  if (r->>'found')::boolean or r->'candidates' is not null then raise exception 'PROBE FEHLT E1: %', r; end if;
  if d > interval '300 milliseconds' then raise exception 'PROBE FEHLT E2: 60 Zeichen bei 150 Personen brauchten %', d; end if;
  v_n := v_n + 2;

  -- F: Rechte wie rechte_db.py
  foreach f in array array[__INTERN__] loop
    foreach ro in array array['anon', 'authenticated'] loop
      if has_function_privilege(ro, f, 'execute') then raise exception 'PROBE FEHLT F1: % darf % ausführen', ro, f; end if;
      v_n := v_n + 1;
    end loop;
  end loop;
  if not has_function_privilege('anon', 'lookup_participant(text)', 'execute') or not has_function_privilege('authenticated', 'lookup_participant(text)', 'execute') then
    raise exception 'PROBE FEHLT F2: lookup_participant gesperrt'; end if;
  v_n := v_n + 1;

  raise exception 'PROBELAUF_OK: % Prüfungen bestanden, alles zurückgenommen', v_n;
end $probe$;
"""


def main() -> None:
    migration = "" if "--ohne" in sys.argv else MIGRATION.read_text(encoding="utf-8")
    assert "$mig$" not in migration and "$probe$" not in migration
    intern = ", ".join("'" + f + "'" for f in INTERN)
    probe = PROBE.replace("__INTERN__", intern).replace(
        "execute $mig$__MIGRATION__$mig$;", f"execute $mig${migration}$mig$;" if migration.strip() else "")
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
