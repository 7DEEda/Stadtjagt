#!/usr/bin/env python3
"""
Tests der Bremse in tools/sql.py, ohne Datenbank und ohne Token.

    python tools/test_sql_bremse.py

Läuft auch unter pytest. Geprüft: DO-Blöcke werden mitgeprüft (auch mit benannten Dollar-Quotes), Funktionskörper
nicht; "alter table t drop c" ohne COLUMN gilt als Spalte entfernen; die Migrationen in supabase/migrations lösen
keine falsche Ablehnung aus; die Probeläufe laufen an der Bremse vorbei (sql.ausfuehren), wie gewollt.
"""
import importlib
import io
import json
import pathlib
import re
import sys
import urllib.request

HIER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER / "pruefstand"))
import sql  # noqa: E402


def befund(text: str) -> set:
    t = sql.ohne_kommentare(text)
    return {name for muster, name in sql.GEFAEHRLICH if re.search(muster, t, flags=re.S)}


def abgelehnt(text: str) -> bool:
    try:
        sql.pruefen(text, force=False)
    except SystemExit as e:
        assert "Abgelehnt" in str(e), e
        return True
    return False


# ---------- DO-Blöcke laufen sofort: prüfen ----------

def test_do_block_delete_ohne_where():
    assert abgelehnt("do $$ begin delete from participants; end $$")


def test_do_block_mit_force():
    sql.pruefen("do $$ begin delete from participants; end $$", force=True)   # kein SystemExit


def test_do_block_benannter_quote():
    assert abgelehnt("do $probe$ begin update teams set code = 'x'; end $probe$;")
    assert abgelehnt("DO LANGUAGE plpgsql $mig$ BEGIN TRUNCATE finishes; END $mig$;")


def test_do_block_mit_where_geht_durch():
    assert not abgelehnt("do $$ begin delete from participants where name like '%(Test)'; end $$")


def test_execute_im_do_block_wird_geprueft():
    assert abgelehnt("do $$ begin execute $x$ delete from teams $x$; end $$")


# ---------- Funktionskörper laufen erst beim Aufruf: nicht prüfen ----------

def test_funktionskoerper_zaehlt_nicht():
    for q in ("$$", "$function$", "$body$"):
        f = (f"create or replace function f() returns void language plpgsql as {q}\n"
             f"begin delete from participants; update teams set code = 'x'; end {q};")
        assert not abgelehnt(f), q


def test_funktion_im_do_block_zaehlt_nicht():
    assert not abgelehnt("do $$ begin execute $f$ create function g() returns void as $b$ begin delete from teams; "
                         "end $b$ language plpgsql $f$; end $$")


def test_funktion_und_danach_delete():
    assert abgelehnt("create function f() returns int as $$ select 1 $$ language sql; delete from teams;")


def test_kommentar_mit_dollar_stoert_nicht():
    assert abgelehnt("-- hier steht $$ im Kommentar\ndelete from teams;")


# ---------- Spalte entfernen, auch ohne COLUMN ----------

def test_spalte_ohne_column():
    assert abgelehnt("alter table finishes drop place")
    assert abgelehnt("alter table finishes drop if exists place;")
    assert abgelehnt("alter table finishes drop column place")
    assert abgelehnt("ALTER TABLE public.finishes\n  DROP place CASCADE;")
    assert abgelehnt("do $$ begin alter table finishes drop place; end $$")


def test_drop_ohne_datenverlust():
    for s in ("alter table finishes drop constraint finishes_place_key",
              "alter table finishes drop constraint if exists finishes_place_key",
              "alter table teams alter column code drop default",
              "alter table teams alter column code drop not null",
              "alter table teams alter column id drop identity if exists",
              "alter table teams alter column x drop expression"):
        assert not abgelehnt(s), s


def test_drop_nur_in_derselben_anweisung():
    # früher reichte ein "alter table" irgendwo davor (".*" über Anweisungen hinweg)
    assert befund("alter table teams add column x int; drop function f(); select 'drop column'") == set()


# ---------- insert ... on conflict do update ----------

def test_upsert_ist_kein_update_ohne_where():
    assert not abgelehnt("insert into progress (team_id, station_id) values (1, 2)\n"
                         "  on conflict (team_id, station_id) do\n    update set failed_attempts = 2;")
    assert abgelehnt("update progress set failed_attempts = 2;")


# ---------- echte Dateien ----------

def test_migrationen_keine_falsche_ablehnung():
    mig = sorted((sql.REPO / "supabase" / "migrations").glob("*.sql"))
    assert len(mig) > 30
    for p in mig:
        b = befund(p.read_text(encoding="utf-8"))
        if p.name == "20260918120000_init.sql":
            assert b == {"tabelle oder schema löschen"}, (p.name, b)   # beginnt mit drop table ... cascade: richtig
        else:
            assert b == set(), (p.name, b)


def test_seeds_keine_falsche_ablehnung():
    for p in sorted((sql.REPO / "supabase").glob("seed*.sql")):
        assert befund(p.read_text(encoding="utf-8")) == set(), p.name


def test_probelaeufe_befund():
    # Die Probeläufe ändern absichtlich, in einem DO-Block, der immer zurückrollt. Bis auf die Spalte im Probelauf zur
    # Teststation (legt eine an und nimmt sie wieder weg) findet die Bremse nichts; durch die Bremse gehen sie nicht.
    erwartet = {"teststation_db": {"spalte entfernen"}}
    dateien = sorted((HIER / "pruefstand").glob("*_db.py"))
    assert dateien
    for p in dateien:
        probe = importlib.import_module(p.stem).PROBE
        assert befund(probe) == erwartet.get(p.stem, set()), (p.name, befund(probe))


def test_probelaeufe_rufen_ausfuehren_ohne_bremse():
    for p in sorted((HIER / "pruefstand").glob("*_db.py")):
        text = p.read_text(encoding="utf-8")
        assert "sql.ausfuehren(probe" in text and "sql.pruefen(" not in text, p.name


def test_ausfuehren_ruft_bremse_nicht():
    gesendet = {}

    class Antwort(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def urlopen(req, timeout=None):
        gesendet["sql"] = json.loads(req.data.decode("utf-8"))["query"]
        return Antwort(b"[]")

    def bremse(*a, **k):
        raise AssertionError("ausfuehren darf die Bremse nicht rufen")

    alt = (urllib.request.urlopen, sql.pruefen, sql.token, sql.project_ref)
    urllib.request.urlopen, sql.pruefen, sql.token, sql.project_ref = urlopen, bremse, lambda: "sbp_test", lambda: "test"
    try:
        assert sql.ausfuehren("do $$ begin delete from participants; end $$", read_only=False) == []
    finally:
        urllib.request.urlopen, sql.pruefen, sql.token, sql.project_ref = alt
    assert "delete from participants" in gesendet["sql"]


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    fehler = 0
    for name, f in tests:
        try:
            f()
            print("ok    ", name)
        except Exception as e:  # noqa: BLE001
            fehler += 1
            print("FEHLER", name, repr(e))
    print(f"{len(tests) - fehler} von {len(tests)} bestanden")
    sys.exit(1 if fehler else 0)
