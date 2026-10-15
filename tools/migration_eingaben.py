#!/usr/bin/env python3
"""
Erzeugt supabase/migrations/20261016090000_eingaben_wiederholen.sql (Ausfallsicherheit, Abschnitt 3.3:
Eingaben im Funkloch, gleiche Eingabe bekommt die gleiche Antwort, nichts zählt doppelt).

    python tools/migration_eingaben.py

Jede Funktion kommt aus ihrer NEUESTEN Fassung über alle Migrationen (letzte Definition in der letzten Datei,
die sie enthält; die Zieldatei selbst zählt nicht). Ersetzungen gelten genau einmal, sonst Abbruch.

  submit_answer(p_code, p_answer, p_position default null): neue Signatur, also drop + create und danach
           ausdrücklich grant. Wiederholung nach dem Wechsel zur nächsten Station wird erkannt (p_position), dieselbe
           falsche Antwort wie zuletzt (progress.last_wrong) zählt nicht noch einmal.
  check_in: schon eingecheckt (Wiederholung nach verlorener Antwort) gibt die Erfolgsantwort ohne neue
           Entfernungsprüfung. Signatur bleibt, also create or replace (Rechte bleiben).
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
MIG = REPO / "supabase" / "migrations"
ZIEL = MIG / "20261016090000_eingaben_wiederholen.sql"

KOPF = """-- Ausfallsicherheit (Spezifikation 2026-10-15, Abschnitt 3.3): Eingaben im Funkloch. Erzeugt von
-- tools/migration_eingaben.py, nicht von Hand ändern. Probelauf: tools/pruefstand/eingaben_db.py.
-- Mehrfach ausführbar, löscht keine Daten. Verträglich mit der vorigen App-Fassung (p_position mit default).
--   submit_answer  nimmt p_position (Station, an der getippt wurde): ist das Team inzwischen weiter, wird nie gegen
--                  das nächste Rätsel geprüft. Dieselbe falsche Antwort wie zuletzt (norm, je Team und Station)
--                  zählt nicht noch einmal und bekommt dieselbe Antwort.
--   check_in       schon eingecheckt: dieselbe Erfolgsantwort, ohne die Entfernung neu zu prüfen.
-- Regel (SPIEL.md §9): nach jedem drop + create einer Funktion die Rechte ausdrücklich setzen.

-- norm() der letzten gezählten falschen Antwort an dieser Station
alter table progress add column if not exists last_wrong text;

-- Neue Signatur: die alte Fassung muss weg, sonst fände PostgREST mit zwei Argumenten zwei Kandidaten (PGRST203)
drop function if exists submit_answer(text, text);
"""

ERFOLG = """case when g.test_mode then 'Testmodus: jede Antwort zählt. Eine Ziffer ist frei.'
                      else 'Richtig. Eine Ziffer ist frei.' end"""

SA = [
    ("create or replace function submit_answer(p_code text, p_answer text)\n",
     "create or replace function submit_answer(p_code text, p_answer text, p_position int default null)\n"),
    ("        v_attempts int; v_locked boolean;\n",
     "        v_attempts int; v_locked boolean;\n"
     "        fr stations; fr_p progress; v_norm text := coalesce(norm(p_answer), ''); v_rest int;\n"),
    ("  cur := current_station(t.id);\n",
     """  cur := current_station(t.id);

  -- Wiederholung: die App nennt die Station, an der getippt wurde. Ist das Team inzwischen weiter (die erste Antwort
  -- kam an, nur ihre Antwort nicht; oder die Spielleitung hat gewertet), nie gegen das nächste Rätsel prüfen.
  if p_position is not null and (cur.id is null or cur.position <> p_position) then
    select * into fr from stations where position = p_position;
    select * into fr_p from progress where team_id = t.id and station_id = fr.id;
    if fr_p.solved_at is not null and (g.test_mode or answer_ok(p_answer, fr.answer)) then
      return json_build_object('ok', true,
        'message', """ + ERFOLG + """,
        'state', team_state(p_code));
    end if;
    return json_build_object('ok', false,
      'message', case when fr_p.solved_at is not null then 'Diese Station ist schon gelöst.'
                      else 'Das Rätsel hat gewechselt. Lest es noch mal.' end,
      'state', team_state(p_code));
  end if;

"""),
    ("    update progress set solved_at = now(), failed_attempts = 0, locked_until = null\n",
     "    update progress set solved_at = now(), failed_attempts = 0, locked_until = null, last_wrong = null\n"),
    ("  v_attempts := case when row_p.locked_until is not null and row_p.locked_until <= now()\n",
     """  -- Dieselbe falsche Antwort wie zuletzt zählt nicht noch einmal: im Funkloch kam die erste an, nur ihre Antwort
  -- nicht. Antwortet genau wie beim ersten Mal. Eine laufende Denkpause greift schon oben.
  if v_norm = row_p.last_wrong then
    v_rest := case when row_p.locked_until is not null and row_p.locked_until <= now() then 3
                   else 3 - row_p.failed_attempts end;
    return json_build_object('ok', false,
      'message', 'Leider falsch. Noch ' || v_rest || case when v_rest = 1 then ' Versuch.' else ' Versuche.' end,
      'state', team_state(p_code));
  end if;

  v_attempts := case when row_p.locked_until is not null and row_p.locked_until <= now()
"""),
    ("        pauses          = pauses + case when v_locked then 1 else 0 end\n",
     "        pauses          = pauses + case when v_locked then 1 else 0 end,\n"
     "        last_wrong      = v_norm\n"),
]

CI = [
    ("""  if cur.id is null then
    return json_build_object('ok', false, 'message', 'Alle Stationen sind gelöst.', 'state', team_state(p_code));
  end if;
  if not g.test_mode then
""", """  if cur.id is null then
    return json_build_object('ok', false, 'message', 'Alle Stationen sind gelöst.', 'state', team_state(p_code));
  end if;
  -- Schon eingecheckt (Wiederholung nach verlorener Antwort): gleiche Antwort, ohne die Entfernung neu zu prüfen;
  -- das GPS darf inzwischen gesprungen sein
  if exists (select 1 from progress where team_id = t.id and station_id = cur.id and checked_in_at is not null) then
    return json_build_object('ok', true,
      'message', case when g.test_mode then 'Testmodus: eingecheckt ohne Entfernungsprüfung.'
                      else 'Angekommen. Das Rätsel ist frei.' end,
      'state', team_state(p_code));
  end if;
  if not g.test_mode then
"""),
]

AUFGABEN = [
    ("submit_answer", SA, "grant execute on function submit_answer(text, text, int) to anon, authenticated;"),
    ("check_in", CI, "-- Signatur unverändert: die Rechte bleiben."),
]


def neueste(name: str):
    """Letzte Definition über alle Migrationen in Dateinamen-Reihenfolge: (Dateiname, Text der Definition)."""
    treffer = None
    for datei in sorted(MIG.glob("*.sql")):
        if datei == ZIEL:
            continue
        text = datei.read_text(encoding="utf-8")
        starts = [m.start() for m in re.finditer(rf"create or replace function {name}\(", text)]
        if starts:
            a = starts[-1]
            auf = text.index("$$", a) + 2
            e = text.index("$$;", auf) + len("$$;")
            treffer = (datei.name, text[a:e])
    if not treffer:
        sys.exit(f"{name}: in keiner Migration gefunden")
    return treffer


def main() -> None:
    teile = [KOPF]
    for name, ersetzungen, rechte in AUFGABEN:
        datei, f = neueste(name)
        for alt, neu in ersetzungen:
            if f.count(alt) != 1:
                sys.exit(f"{name} (aus {datei}): '{alt.strip()[:60]}' kommt {f.count(alt)}x vor, erwartet genau 1x")
            f = f.replace(alt, neu)
        teile.append(f"-- ---------- {name} (aus {datei}) ----------\n{f}\n{rechte}\n")
        print(f"{name}: neueste Fassung aus {datei}")
    teile.append("notify pgrst, 'reload schema';\n")
    ZIEL.write_text("\n".join(teile), encoding="utf-8", newline="\n")
    print("geschrieben:", ZIEL.relative_to(REPO))


if __name__ == "__main__":
    main()
