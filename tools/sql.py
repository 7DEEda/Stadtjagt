#!/usr/bin/env python3
"""
SQL gegen die Stadtjagd-Datenbank ausführen, ohne den SQL-Editor im Browser.

    python tools/sql.py supabase/migrations/20260918160000_routes.sql
    python tools/sql.py -c "select count(*) from participants"
    python tools/sql.py --read-only -c "select status from game_state"

Der Zugang läuft über die Supabase Management-API. Sie braucht einen Personal
Access Token. Der Token steht NICHT im Repo, sondern in einer Datei daneben:

    %USERPROFILE%\\.supabase\\stadtjagt.token

Alternativ in der Umgebungsvariable SUPABASE_ACCESS_TOKEN. Neuen Token anlegen
unter https://supabase.com/dashboard/account/tokens. Achtung: so ein Token gilt
für das ganze Supabase-Konto, nicht nur für dieses Projekt. Nach dem Event
wieder zurückziehen.

Schutz vor Unfällen: Anweisungen, die Daten oder Tabellen vernichten, werden
abgelehnt, solange nicht --force dabeisteht. Die Init-Migration beginnt mit
"drop table ... cascade" und würde ohne diese Bremse alles löschen.
"""
import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

# Die Windows-Konsole läuft sonst auf cp1252 und macht aus Umlauten Fragezeichen
for strom in (sys.stdout, sys.stderr):
    try:
        strom.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

REPO = pathlib.Path(__file__).resolve().parent.parent
TOKEN_FILE = pathlib.Path(os.environ.get("USERPROFILE", pathlib.Path.home())) / ".supabase" / "stadtjagt.token"
API = "https://api.supabase.com/v1/projects/{ref}/database/query"

# Anweisungen, die ohne --force nicht durchgehen: hier gehen Daten verloren
# Die Muster schauen nur bis zum nächsten ";": ein WHERE oder SET in einer späteren
# Anweisung darf das Urteil über diese nicht ändern.
GEFAEHRLICH = [
    (r"\bdrop\s+(table|schema|database|materialized\s+view)\b", "tabelle oder schema löschen"),
    (r"\btruncate\b", "truncate"),
    (r"\bdelete\s+from\b(?:(?!\bwhere\b)[^;])*(?:;|$)", "delete ohne where"),
    (r"\bupdate\b[^;]*?\bset\b(?:(?!\bwhere\b)[^;])*(?:;|$)", "update ohne where"),
    (r"\balter\s+table\b.*\bdrop\s+column\b", "spalte entfernen"),
]

# Anweisungen, die auffallen sollen, aber durchgehen: sie ändern nur Definitionen
WARNUNG = [
    (r"\bdrop\s+(function|procedure|type|index|trigger|view)\b", "funktion oder index ersetzen"),
    (r"\brevoke\b", "rechte entziehen"),
]


def token() -> str:
    roh = os.environ.get("SUPABASE_ACCESS_TOKEN", "")
    quelle = "der Umgebungsvariable SUPABASE_ACCESS_TOKEN"
    if not roh.strip() and TOKEN_FILE.exists():
        # utf-8-sig, weil PowerShell beim Anlegen eine Byte-Order-Mark schreibt.
        # Die stünde sonst mitten im Authorization-Header und der Versand bricht ab.
        inhalt = TOKEN_FILE.read_text(encoding="utf-8-sig")
        zeilen = [z.strip() for z in inhalt.splitlines()]
        zeilen = [z for z in zeilen if z and not z.startswith("#")]
        roh = zeilen[0] if zeilen else ""
        quelle = str(TOKEN_FILE)
    t = roh.strip().strip('"').strip("'").lstrip("﻿").strip()
    if not t:
        sys.exit(
            f"Kein Token gefunden.\n"
            f"  Trag ihn ein in: {TOKEN_FILE}\n"
            f"  oder setze SUPABASE_ACCESS_TOKEN.\n"
            f"  Neuen Token anlegen: https://supabase.com/dashboard/account/tokens"
        )
    if not t.startswith("sbp_"):
        sys.exit(
            f"Was in {quelle} steht, sieht nicht nach einem Token aus.\n"
            f"  Erwartet wird eine Zeile, die mit sbp_ anfängt, gefunden wurde: {t[:12]}...\n"
            f"  Der anon oder Publishable key aus config.js ist hier der falsche Schlüssel."
        )
    if any(ord(c) > 127 or c.isspace() for c in t):
        sys.exit(f"Der Token in {quelle} enthält Leerzeichen oder Sonderzeichen. Bitte nur die reine Zeile einfügen.")
    return t


def project_ref() -> str:
    """Projektkennung aus config.js lesen, damit sie nur an einer Stelle steht."""
    cfg = (REPO / "config.js").read_text(encoding="utf-8")
    m = re.search(r"https://([a-z0-9]+)\.supabase\.co", cfg)
    if not m:
        sys.exit("In config.js steht keine Supabase-URL, aus der sich die Projektkennung lesen ließe.")
    return m.group(1)


def ohne_kommentare(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", " ", sql)
    # Funktionskörper zwischen $$ ... $$ zählen nicht, dort steht das UPDATE
    # der Funktion, nicht eine Anweisung, die jetzt ausgeführt wird.
    sql = re.sub(r"\$\$.*?\$\$", " ", sql, flags=re.S)
    return sql.lower()


def pruefen(sql: str, force: bool) -> None:
    text = ohne_kommentare(sql)
    treffer = [name for muster, name in GEFAEHRLICH if re.search(muster, text, flags=re.S)]
    hinweis = [name for muster, name in WARNUNG if re.search(muster, text, flags=re.S)]
    if treffer and not force:
        sys.exit(
            "Abgelehnt. Hier gehen Daten verloren: " + ", ".join(sorted(set(treffer))) + ".\n"
            "Wenn das wirklich so gewollt ist, noch einmal mit --force aufrufen.\n"
            "Denk dran: die Init-Migration löscht alle Tabellen."
        )
    if treffer:
        print("Achtung, mit --force ausgeführt: " + ", ".join(sorted(set(treffer))), file=sys.stderr)
    if hinweis:
        print("Hinweis, geht ohne --force durch: " + ", ".join(sorted(set(hinweis))), file=sys.stderr)


def ausfuehren(sql: str, read_only: bool) -> object:
    url = API.format(ref=project_ref())
    if read_only:
        url += "/read-only"
    req = urllib.request.Request(
        url,
        data=json.dumps({"query": sql}).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + token(),
            "Content-Type": "application/json",
            "User-Agent": "stadtjagd-sql/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as e:
        leib = e.read().decode("utf-8", "replace")
        try:
            leib = json.dumps(json.loads(leib), ensure_ascii=False, indent=2)
        except ValueError:
            pass
        if e.code == 401:
            leib += "\n\nDer Token wird nicht akzeptiert. Abgelaufen oder zurückgezogen?"
        sys.exit(f"Die Datenbank antwortet mit HTTP {e.code}:\n{leib}")


def main() -> None:
    ap = argparse.ArgumentParser(description="SQL gegen die Stadtjagd-Datenbank ausführen.")
    ap.add_argument("datei", nargs="?", help="SQL-Datei, etwa eine Migration")
    ap.add_argument("-c", "--command", help="SQL direkt auf der Kommandozeile")
    ap.add_argument("--read-only", action="store_true", help="nur lesen, die Datenbank lehnt Schreiben ab")
    ap.add_argument("--force", action="store_true", help="auch Anweisungen ausführen, die Daten vernichten")
    a = ap.parse_args()

    if bool(a.datei) == bool(a.command):
        ap.error("Entweder eine SQL-Datei angeben oder -c, nicht beides und nicht keins.")
    sql = a.command if a.command else pathlib.Path(a.datei).read_text(encoding="utf-8")
    if not sql.strip():
        sys.exit("Die Datei ist leer.")

    pruefen(sql, a.force)
    quelle = a.datei if a.datei else "Kommandozeile"
    print(f"Sende {len(sql)} Zeichen aus {quelle} an Projekt {project_ref()} ...", file=sys.stderr)
    antwort = ausfuehren(sql, a.read_only)
    if antwort in (None, []):
        print("Fertig, die Datenbank hat nichts zurückgegeben.", file=sys.stderr)
    else:
        print(json.dumps(antwort, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
