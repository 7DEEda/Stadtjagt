#!/usr/bin/env python3
"""Erzeugt supabase/migrations/20261006090000_admin_fehlversuche.sql aus der jüngsten admin_state-Fassung."""
import pathlib, re, sys
REPO = pathlib.Path(__file__).resolve().parent.parent
MIG = REPO / "supabase" / "migrations"
quellen = sorted(p for p in MIG.glob("*.sql") if "function admin_state(" in p.read_text(encoding="utf-8") and p.name < "20261006")
text = quellen[-1].read_text(encoding="utf-8")
m = re.search(r"create or replace function admin_state\(.*?\nend \$\$;", text, re.S)
if not m: sys.exit("admin_state nicht gefunden in " + quellen[-1].name)
fn = m.group(0)
anker = '             from progress pr where pr.team_id = t.id) as "lastActivity",\n'
if fn.count(anker) != 1: sys.exit("Anker lastActivity nicht eindeutig")
neu = anker + (
  "          -- Umbau Weiterentwicklung: Fehlversuche und Pause an der aktuellen Station, für \"Braucht dich\"\n"
  "          coalesce((select pr.failed_attempts from stations s\n"
  "             left join progress pr on pr.station_id = s.id and pr.team_id = t.id\n"
  "             where pr.solved_at is null order by s.position limit 1), 0) as \"failedAttempts\",\n"
  "          (select pr.locked_until from stations s\n"
  "             left join progress pr on pr.station_id = s.id and pr.team_id = t.id\n"
  "             where pr.solved_at is null order by s.position limit 1) as \"lockedUntil\",\n")
kopf = ("-- Umbau Weiterentwicklung (06.10.2026): admin_state liefert je Team failedAttempts und lockedUntil der\n"
        f"-- aktuellen Station. Erzeugt von tools/migration_admin_fehlversuche.py aus {quellen[-1].name}, nicht von Hand ändern.\n"
        "-- Probelauf: tools/pruefstand/admin_fehlversuche_db.py. Mehrfach ausführbar, löscht keine Daten.\n\n")
rechte = "\n\ngrant execute on function admin_state(text) to anon, authenticated;\n"
(MIG / "20261006090000_admin_fehlversuche.sql").write_text(kopf + fn.replace(anker, neu) + rechte, encoding="utf-8")
print("geschrieben aus", quellen[-1].name)
