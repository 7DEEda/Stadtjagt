#!/usr/bin/env python3
"""
Testläufe des Geräte-Tests (geraete-test.html) aus der Datenbank holen.

    python tools/testlaeufe.py

Schreibt je Lauf eine JSON-Datei nach testlaeufe/ und baut daraus
testlaeufe/UEBERSICHT.md: eine Matrix Test gegen Lauf, darunter die Messwerte
aller Ergebnisse, die nicht "ok" sind.

Der Zugang ist derselbe wie bei tools/sql.py (Personal Access Token in
%USERPROFILE%\\.supabase\\stadtjagt.token), gelesen wird read-only.

testlaeufe/ steht in .gitignore: der Workflow veröffentlicht das ganze Repo
auf GitHub Pages, und die Läufe enthalten Koordinaten.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sql  # noqa: E402  (setzt auch die Konsole auf UTF-8)

ZIEL = sql.REPO / "testlaeufe"
ABFRAGE = ("select run_key, created_at, updated_at, suite_version, label, payload "
           "from device_test_runs order by created_at")
KURZ = {"ok": "ok", "warn": "eingeschränkt", "err": "GEHT NICHT", "skip": "übersprungen"}


def dateiname(lauf: dict) -> str:
    zeit = re.sub(r"[^0-9]", "", lauf["created_at"])[:12]   # JJJJMMTTHHMM, Serverzeit UTC
    label = re.sub(r"[^A-Za-z0-9äöüÄÖÜß]+", "-", lauf["label"] or "ohne-namen").strip("-")[:40] or "ohne-namen"
    return f"{zeit[:4]}-{zeit[4:6]}-{zeit[6:8]}_{zeit[8:12]}_{label}_{lauf['run_key'][:4]}.json"


def suite_titel() -> dict:
    """Titel und Reihenfolge der Tests aus geraete-tests.js lesen, damit die Übersicht so sortiert ist wie die Seite."""
    text = (sql.REPO / "geraete-tests.js").read_text(encoding="utf-8")
    return dict(re.findall(r'id: "([^"]+)", titel: "([^"]+)"', text))


def kaputt(lauf: dict):
    """Grund, warum eine Zeile nicht die Form eines Laufs hat, sonst None. device_test_save prüft die Form erst seit
    Nachtrag 32; vorher konnte jeder mit dem öffentlichen Schlüssel etwa {"tests": "x"} ablegen (Bugjagd 03.10.2026,
    Fund 12), und die Übersicht brach dann ab."""
    p = lauf.get("payload")
    if isinstance(p, str):
        try:
            p = lauf["payload"] = json.loads(p)
        except ValueError:
            return "payload ist kein JSON"
    if not isinstance(p, dict):
        return "payload ist kein Objekt"
    for feld in ("tests", "bilanz"):
        if not isinstance(p.get(feld, {}), dict):
            return f"{feld} ist kein Objekt"
    for i, t in p.get("tests", {}).items():
        if not isinstance(t, dict) or not isinstance(t.get("mess") or {}, dict):
            return f"Test {i} hat nicht die Form eines Ergebnisses"
    if not isinstance(lauf.get("run_key"), str) or not isinstance(lauf.get("created_at"), str):
        return "run_key oder created_at fehlt"
    return None


def uebersicht(laeufe: list) -> str:
    titel = suite_titel()
    ids = list(titel)
    for lauf in laeufe:   # Tests aus alten Suiten, die es heute nicht mehr gibt, hinten anhängen
        ids += [i for i in lauf["payload"].get("tests", {}) if i not in ids]
    kopf = [f"{l['label'] or 'ohne Namen'} ({l['run_key'][:4]})" for l in laeufe]
    z = ["# Geräte-Test: Übersicht", "",
         f"{len(laeufe)} Läufe. Erzeugt von `tools/testlaeufe.py`, nicht von Hand ändern.", "",
         "| Test | " + " | ".join(kopf) + " |", "|---|" + "---|" * len(laeufe)]
    for i in ids:
        zellen = []
        for lauf in laeufe:
            t = lauf["payload"].get("tests", {}).get(i)
            zellen.append("nicht gelaufen" if not t else f"{KURZ.get(t.get('art'), t.get('art'))}: {t.get('wert', '')}".replace("|", "/"))
        z.append(f"| {titel.get(i, i)} | " + " | ".join(zellen) + " |")
    z += ["", "## Läufe", ""]
    for lauf in laeufe:
        p = lauf["payload"]
        b = p.get("bilanz", {})
        z += [f"### {lauf['label'] or 'ohne Namen'} ({lauf['run_key'][:4]})", "",
              f"- Zeit (UTC): {lauf['created_at'][:16].replace('T', ' ')}, Suite {lauf['suite_version']}",
              f"- Bilanz: {b.get('ok', 0)} ok, {b.get('warn', 0)} eingeschränkt, {b.get('err', 0)} geht nicht, {b.get('skip', 0)} übersprungen",
              f"- Kennung: `{p.get('ua', '')}`", ""]
        for i in ids:
            t = p.get("tests", {}).get(i)
            if not t or t.get("art") in ("ok", "skip"):
                continue
            z.append(f"**{titel.get(i, i)}: {t.get('wert', '')}** ({KURZ.get(t.get('art'), t.get('art'))})")
            z += [f"- {k}: {v}" for k, v in (t.get("mess") or {}).items()]
            z.append("")
    return "\n".join(z) + "\n"


def main() -> None:
    alle = sql.ausfuehren(ABFRAGE, read_only=True) or []
    # kaputte Zeilen überspringen und melden, damit eine einzige nicht die ganze Übersicht verhindert
    laeufe = []
    for lauf in alle:
        grund = kaputt(lauf)
        if grund:
            print(f"Übersprungen: Lauf {lauf.get('run_key')} ({grund}). Löschen per SQL: "
                  f"delete from device_test_runs where run_key = '{lauf.get('run_key')}';")
        else:
            laeufe.append(lauf)
    ZIEL.mkdir(exist_ok=True)
    neu = 0
    for lauf in laeufe:
        ziel = ZIEL / dateiname(lauf)
        inhalt = json.dumps(lauf, ensure_ascii=False, indent=2) + "\n"
        if not ziel.exists() or ziel.read_text(encoding="utf-8") != inhalt:
            ziel.write_text(inhalt, encoding="utf-8")
            neu += 1
    (ZIEL / "UEBERSICHT.md").write_text(uebersicht(laeufe), encoding="utf-8")
    print(f"{len(laeufe)} Läufe in der Datenbank ({len(alle) - len(laeufe)} übersprungen), {neu} neu oder geändert. Übersicht: {ZIEL / 'UEBERSICHT.md'}")


if __name__ == "__main__":
    main()
