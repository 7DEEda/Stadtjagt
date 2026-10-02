#!/usr/bin/env python3
"""
Den Geräte-Test neutral veröffentlichen: eigenes Repo 7DEEda/geraetetest, Adresse
https://7deeda.github.io/geraetetest/ (nichts in der Adresse oder im Quelltext verrät das Spiel).

    python tools/geraetetest_veroeffentlichen.py

Quelle bleibt geraete-test.html und geraete-tests.js in diesem Repo. Das Skript
- kopiert geraete-test.html als index.html und entfernt dabei den Block zwischen
  <!-- WEITERLEITUNG --> und <!-- /WEITERLEITUNG --> (der leitet die alte Adresse um),
- schreibt eine eigene config.js nur mit Server-Adresse und öffentlichem Schlüssel
  (window.GT_CONFIG; keine Hilfe-Nummer, kein Spieltext),
- prüft alle Dateien auf verräterische Wörter und bricht dann ab,
- committet und pusht in den Arbeitsordner .geraetetest-repo/ (nicht in diesem Repo).
"""
import pathlib
import re
import subprocess
import sys

for strom in (sys.stdout, sys.stderr):
    try:
        strom.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

REPO = pathlib.Path(__file__).resolve().parent.parent
ZIEL = REPO / ".geraetetest-repo"
REMOTE = "https://github.com/7DEEda/geraetetest.git"
# Wörter, die im veröffentlichten Test nicht vorkommen dürfen
VERBOTEN = re.compile(r"stadtj|\bspiel|\bprag|station|koffer|rätsel|teamfahrt|public_state|SJ_TESTS", re.I)   # \b: "Beispiel" ist erlaubt


def git(*args, pruefen=True):
    return subprocess.run(["git", "-c", "windows.appendAtomically=false", *args], cwd=ZIEL, check=pruefen,
                          capture_output=True, text=True, encoding="utf-8")


def main() -> int:
    html = (REPO / "geraete-test.html").read_text(encoding="utf-8")
    html, n = re.subn(r"<!-- WEITERLEITUNG -->.*?<!-- /WEITERLEITUNG -->\n?", "", html, flags=re.S)
    if n != 1:
        print("Block WEITERLEITUNG nicht genau einmal gefunden"); return 1
    tests = (REPO / "geraete-tests.js").read_text(encoding="utf-8")
    cfg = (REPO / "config.js").read_text(encoding="utf-8")
    url = re.search(r'url:\s*"([^"]+)"', cfg).group(1)
    key = re.search(r'key:\s*"([^"]+)"', cfg).group(1)
    config = ("// Verbindung zum Server. Der öffentliche Schlüssel ist zur Veröffentlichung gedacht.\n"
              f'window.GT_CONFIG = {{ url: "{url}", key: "{key}" }};\n')
    readme = ("# Geräte-Test\n\nPrüft im Browser, was eine Web-App auf einem Handy nutzen kann: "
              "Standort, Kompass, Bewegung, Kamera und mehr. Anonym, die Position wird nicht gespeichert.\n\n"
              "https://7deeda.github.io/geraetetest/\n")
    dateien = {"index.html": html, "geraete-tests.js": tests, "config.js": config, "README.md": readme, ".nojekyll": ""}

    fund = [(name, m.group(0)) for name, inhalt in dateien.items() for m in VERBOTEN.finditer(inhalt)]
    if fund:
        print("Abbruch, verräterische Wörter gefunden:")
        for name, wort in fund[:20]:
            print(f"  {name}: {wort}")
        return 1

    if not (ZIEL / ".git").exists():
        ZIEL.mkdir(exist_ok=True)
        git("init", "-b", "main")
        git("remote", "add", "origin", REMOTE)
        git("config", "user.name", "TSE Apps")
        git("config", "user.email", subprocess.run(["git", "config", "user.email"], cwd=REPO, capture_output=True, text=True).stdout.strip() or "apps@example.invalid")
    for name, inhalt in dateien.items():
        (ZIEL / name).write_text(inhalt, encoding="utf-8", newline="\n")
    git("add", "-A")
    if not git("status", "--porcelain").stdout.strip():
        print("Keine Änderung, nichts zu veröffentlichen."); return 0
    git("commit", "-q", "-m", "Geräte-Test aktualisiert")
    r = git("push", "-u", "origin", "main", pruefen=False)
    if r.returncode != 0:
        print("Push fehlgeschlagen:", r.stderr.strip()); return 1
    print("Veröffentlicht:", git("log", "--oneline", "-1").stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
