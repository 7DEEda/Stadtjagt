#!/usr/bin/env python3
"""
Erzeugt supabase/migrations/20261004100000_bugjagd2.sql (Nachtrag 32: Bugjagd 03.10.2026, Funde 9, 12, 14, 16).

    python tools/migration_bugjagd2.py

Jede Funktion kommt aus ihrer NEUESTEN Fassung über alle Migrationen (letzte Definition in der letzten Datei,
die sie enthält; die Zieldatei selbst zählt nicht). Ersetzungen gelten genau einmal, sonst Abbruch.

  Fund 9   register_participant(p_name, p_token default null): mit dem Geräte-Schlüssel des Handys wiederholbar.
           Neue Signatur, also drop + create und danach ausdrücklich grant.
  Fund 12  device_test_save prüft die Form (tests und bilanz Objekte, suite Zahl, jeder Test ein Objekt).
  Fund 14  admin_set_test_mode verweigert im laufenden Spiel mit Plätzen das Umschalten in beide Richtungen.
  Fund 16  submit_answer: leere Antwort zählt außerhalb des Testmodus nicht als Fehlversuch.
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
MIG = REPO / "supabase" / "migrations"
ZIEL = MIG / "20261004100000_bugjagd2.sql"

KOPF = """-- Nachtrag 32: Bugjagd 03.10.2026, Funde 9, 12, 14 und 16. Erzeugt von tools/migration_bugjagd2.py, nicht von Hand
-- ändern. Probelauf: tools/pruefstand/bugjagd2_db.py. Mehrfach ausführbar, löscht keine Daten.
--   Fund 9   register_participant nimmt den Geräte-Schlüssel des Handys (p_token). Gehört der Schlüssel schon
--            einer Person: Erfolg wie beim ersten Mal (Antwort im Funkloch verloren, auch nach Umbenennen). Nie einen neuen Schlüssel für
--            einen vorhandenen Namen. Ohne p_token wie bisher (alte Clients).
--   Fund 12  device_test_save nimmt nur Läufe in der Form, die tools/testlaeufe.py erwartet.
--   Fund 14  admin_set_test_mode: im laufenden Spiel mit Plätzen kein Umschalten, weder aus noch an.
--   Fund 16  submit_answer: leere Antwort ist außerhalb des Testmodus kein Fehlversuch.
-- Regel (SPIEL.md §9): nach jedem drop + create einer Funktion die Rechte ausdrücklich setzen.

-- Neue Signatur: die alte Fassung muss weg, sonst fände PostgREST zwei Kandidaten für einen Aufruf mit p_name
drop function if exists register_participant(text);
"""

TOKEN_DECL_ALT = "        v_token text := replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', '');\n"
TOKEN_DECL_NEU = TOKEN_DECL_ALT + "        v_da participants;\n"
AUSLOSEN_ALT = "  -- Läuft gerade das Auslosen, warten wir, bis es durch ist; die Statusabfrage\n"
AUSLOSEN_NEU = """  -- Nachtrag 32: das Handy schickt seinen Geräte-Schlüssel selbst mit (gleiches Format wie unserer)
  if p_token is not null then
    if p_token !~ '^[0-9a-f]{64}$' then
      raise exception 'Ungültiger Geräte-Schlüssel. Bitte die Seite neu laden.' using errcode='P0001';
    end if;
    v_token := p_token;
  end if;
""" + AUSLOSEN_ALT
SPERRE_ALT = "  perform 1 from game_state where id = 1 for share;\n"
SPERRE_NEU = """  perform 1 from game_state where id = 1 for share;
  -- Wiederholung derselben Anmeldung (Antwort ging verloren): der Schlüssel gehört schon einer Person, also Erfolg
  -- wie beim ersten Mal, auch wenn inzwischen ausgelost ist oder die Spielleitung den Namen berichtigt hat (dann mit
  -- dem neuen Namen). Wer den Schlüssel nicht kennt, bekommt für einen vorhandenen Namen weiter den Fehler unten.
  if p_token is not null then
    select * into v_da from participants where token = p_token;
    if found then
      return json_build_object('name', v_da.name, 'token', v_da.token, 'count', (select count(*) from participants));
    end if;
  end if;
"""
# zwei Anmeldungen gleichzeitig (gleicher Name oder dieselbe Wiederholung zweimal): Unique-Fehler verständlich machen
INSERT_ALT = "  insert into participants(name, name_key, token) values (v_name, norm(v_name), v_token);\n"
INSERT_NEU = """  begin
    insert into participants(name, name_key, token) values (v_name, norm(v_name), v_token);
  exception when unique_violation then
    -- Nachtrag 32: gleichzeitig angemeldet. Gehört der Schlüssel inzwischen einer Person, ist es dieselbe Anmeldung.
    select * into v_da from participants where token = v_token;
    if found then
      return json_build_object('name', v_da.name, 'token', v_da.token, 'count', (select count(*) from participants));
    end if;
    raise exception 'Dieser Name ist schon angemeldet. Hast du dich schon eingetragen? Dann bist du dabei.'
      using errcode='P0001';
  end;
"""

FORM_ALT = "  if octet_length(p_payload::text) > 65536 then\n"
FORM_NEU = """  -- Nachtrag 32: die Form, die tools/testlaeufe.py liest; sonst brach die Übersicht an einer einzigen Zeile ab
  if jsonb_typeof(p_payload->'tests') is distinct from 'object' or jsonb_typeof(p_payload->'bilanz') is distinct from 'object'
     or jsonb_typeof(p_payload->'suite') is distinct from 'number' then
    raise exception 'Der Lauf hat nicht die erwartete Form.' using errcode='P0001';
  end if;
  if exists (select 1 from jsonb_each(p_payload->'tests') e where jsonb_typeof(e.value) <> 'object') then
    raise exception 'Der Lauf hat nicht die erwartete Form.' using errcode='P0001';
  end if;
""" + FORM_ALT

TEST_ALT = "  update game_state set test_mode = coalesce(p_on, false) where id = 1;\n"
TEST_NEU = """  -- Nachtrag 32: Plätze aus dem Testlauf überlebten das Ausschalten und standen dann in der echten Rangliste. Im
  -- laufenden Spiel mit Plätzen darum in keine Richtung umschalten (Entscheidung 04.10.2026: auch nicht einschalten,
  -- sonst käme die Spielleitung nur über „Fortschritt zurücksetzen“ wieder heraus). Ohne Platz ist beides frei.
  if exists (select 1 from game_state where id = 1 and status = 'running' and test_mode is distinct from coalesce(p_on, false))
     and exists (select 1 from finishes) then
    if coalesce(p_on, false) then
      raise exception 'Im laufenden Spiel gibt es schon Plätze. Den Testmodus jetzt einzuschalten würde die Rangliste durcheinanderbringen.'
        using errcode='P0001';
    end if;
    raise exception 'Im Testlauf gibt es schon Plätze. Erst im Reiter Daten löschen „Fortschritt zurücksetzen“, dann den Testmodus ausschalten.'
      using errcode='P0001';
  end if;
""" + TEST_ALT

LEER_ALT = "  v_attempts := case when row_p.locked_until is not null and row_p.locked_until <= now()\n"
LEER_NEU = """  -- Nachtrag 32: ein leeres Feld (oder nur Satzzeichen) ist kein Versuch. Erst hier, nach dem Erfolgszweig: im
  -- Testmodus zählt auch ein leeres Feld als richtig.
  if coalesce(norm(p_answer), '') = '' then
    return json_build_object('ok', false, 'message', 'Bitte gebt eine Antwort ein.', 'state', team_state(p_code));
  end if;

""" + LEER_ALT

# (Funktion, [(alt, neu)], Rechte danach)
AUFGABEN = [
    ("register_participant",
     [("create or replace function register_participant(p_name text) returns json",
       "create or replace function register_participant(p_name text, p_token text default null) returns json"),
      (TOKEN_DECL_ALT, TOKEN_DECL_NEU), (AUSLOSEN_ALT, AUSLOSEN_NEU), (SPERRE_ALT, SPERRE_NEU), (INSERT_ALT, INSERT_NEU)],
     "grant execute on function register_participant(text, text) to anon, authenticated;"),
    ("device_test_save", [(FORM_ALT, FORM_NEU)],
     "grant execute on function device_test_save(text, jsonb) to anon, authenticated;"),
    ("admin_set_test_mode", [(TEST_ALT, TEST_NEU)],
     "grant execute on function admin_set_test_mode(text, boolean) to anon, authenticated;"),
    ("submit_answer", [(LEER_ALT, LEER_NEU)],
     "grant execute on function submit_answer(text, text) to anon, authenticated;"),
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
