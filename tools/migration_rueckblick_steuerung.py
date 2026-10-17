#!/usr/bin/env python3
"""
Erzeugt supabase/migrations/20261017090000_rueckblick_steuerung.sql (Nachtrag 37: das Handy der Spielleitung als
Fernbedienung der Rückblick-Show, rueckblick-fernbedienung.html).

    python tools/migration_rueckblick_steuerung.py

Neue Tabelle und fünf neue Funktionen, keine bestehende Funktion wird ersetzt. Darum gibt es hier keine
Ersetzungen (wie in migration_eingaben.py), sondern eine Prüfung: keiner der neuen Namen darf in einer älteren
Migration vorkommen, sonst wäre es eine Ersetzung und bräuchte deren Regeln (neueste Fassung als Vorlage, genau einmal
ersetzen). Probelauf: tools/pruefstand/rueckblick_steuerung_db.py.
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
MIG = REPO / "supabase" / "migrations"
ZIEL = MIG / "20261017090000_rueckblick_steuerung.sql"
NEU = ["rueckblick_steuerung", "rb_befehl", "rb_poll", "rb_status_setzen", "rb_status_holen", "rb_ende"]

SQL = """-- Nachtrag 37 (17.10.2026): das Handy der Spielleitung als Fernbedienung der Rückblick-Show. Erzeugt von
-- tools/migration_rueckblick_steuerung.py, nicht von Hand ändern. Probelauf: tools/pruefstand/rueckblick_steuerung_db.py.
-- Mehrfach ausführbar, löscht keine Daten, berührt keine Spielfunktion und nicht die Sicht stations.
--
-- Kein Realtime: das Handy (rueckblick-fernbedienung.html) schreibt einen Befehl (rb_befehl), der Laptop mit der Show
-- holt ihn im 1-s-Takt ab (rb_poll) und meldet seinen Stand (rb_status_setzen) bei jeder Änderung und alle 4 s; das
-- Handy liest ihn (rb_status_holen). Eine Zeile (id = 1): der letzte Befehl mit fortlaufender Nummer, der letzte Stand.
-- Der Stand trägt die Moderationshilfe mit Teamnamen und Mitgliedern: nur mit PIN lesbar, rb_ende löscht ihn.
-- Regel (SPIEL.md §9): neue Funktionen bekommen ihre Rechte ausdrücklich.

create table if not exists rueckblick_steuerung (
  id        int primary key default 1 check (id = 1),
  nr        bigint not null default 0,   -- zählt jeden angenommenen Befehl, wird nie zurückgesetzt
  befehl    text,
  befehl_um timestamptz,
  status    jsonb,                       -- Stand der Show (Kapitel, Zustand, Moderation), höchstens 20 KB
  status_um timestamptz,
  handy_um  timestamptz                  -- letzter Abruf des Stands durch das Handy ("Handy verbunden" am Laptop)
);
insert into rueckblick_steuerung (id) values (1) on conflict (id) do nothing;

alter table rueckblick_steuerung enable row level security;
revoke all on rueckblick_steuerung from anon, authenticated;

-- Befehl vom Handy. Feste Liste; zwischen zwei angenommenen Befehlen mindestens 250 ms (Doppeltipp, prellender Finger):
-- ein zu schneller zweiter Befehl ist kein Fehler, er wird nur nicht angenommen (ok false).
create or replace function rb_befehl(p_pin text, p_befehl text) returns json
language plpgsql security definer set search_path = public as $$
declare r rueckblick_steuerung;
begin
  perform require_admin(p_pin);
  if p_befehl is null or p_befehl not in ('weiter', 'zurueck', 'pause', 'schwarz', 'start', 'ende') then
    raise exception 'Unbekannter Befehl.' using errcode = 'P0001';
  end if;
  insert into rueckblick_steuerung (id) values (1) on conflict (id) do nothing;
  select * into r from rueckblick_steuerung where id = 1 for update;
  if r.befehl_um is not null and r.befehl_um > clock_timestamp() - interval '250 milliseconds' then
    return json_build_object('ok', false, 'nr', r.nr);
  end if;
  update rueckblick_steuerung set nr = nr + 1, befehl = p_befehl, befehl_um = clock_timestamp() where id = 1
    returning * into r;
  return json_build_object('ok', true, 'nr', r.nr);
end $$;

-- Abruf durch die Show. p_seit = die letzte Nummer, die die Show kennt; null beim Start der Show: dann nur die Nummer
-- übernehmen, damit kein alter Befehl noch einmal wirkt. Neu und höchstens 30 s alt: {nr, befehl}; neu, aber älter
-- (oder die Show kennt eine größere Nummer): {nr, befehl: null}, verworfen; nichts Neues: null.
create or replace function rb_poll(p_pin text, p_seit bigint) returns json
language plpgsql security definer set search_path = public as $$
declare r rueckblick_steuerung;
begin
  perform require_admin(p_pin);
  select * into r from rueckblick_steuerung where id = 1;
  if not found then return null; end if;
  if p_seit is null or r.nr < p_seit then return json_build_object('nr', r.nr, 'befehl', null); end if;
  if r.nr = p_seit then return null; end if;
  if r.befehl_um is null or r.befehl_um < clock_timestamp() - interval '30 seconds' then
    return json_build_object('nr', r.nr, 'befehl', null);
  end if;
  return json_build_object('nr', r.nr, 'befehl', r.befehl);
end $$;

-- Stand der Show. Antwortet, wie lange der letzte Abruf des Handys her ist (null: noch keiner seit rb_ende).
create or replace function rb_status_setzen(p_pin text, p_status jsonb) returns json
language plpgsql security definer set search_path = public as $$
declare r rueckblick_steuerung;
begin
  perform require_admin(p_pin);
  if p_status is null or jsonb_typeof(p_status) <> 'object' then
    raise exception 'Der Status fehlt.' using errcode = 'P0001';
  end if;
  if octet_length(p_status::text) > 20480 then
    raise exception 'Der Status ist zu groß.' using errcode = 'P0001';
  end if;
  insert into rueckblick_steuerung (id) values (1) on conflict (id) do nothing;
  update rueckblick_steuerung set status = p_status, status_um = clock_timestamp() where id = 1 returning * into r;
  return json_build_object('ok', true,
    'handy_alter_s', case when r.handy_um is null then null else round(extract(epoch from clock_timestamp() - r.handy_um)::numeric, 1) end);
end $$;

-- Stand für das Handy, mit seinem Alter in Sekunden (das Handy zeigt "Keine Show gefunden" ab 6 s). Merkt sich den
-- Abruf, damit der Laptop "Handy verbunden" zeigen kann.
create or replace function rb_status_holen(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
declare r rueckblick_steuerung;
begin
  perform require_admin(p_pin);
  insert into rueckblick_steuerung (id) values (1) on conflict (id) do nothing;
  update rueckblick_steuerung set handy_um = clock_timestamp() where id = 1 returning * into r;
  return json_build_object('status', r.status,
    'alter_s', case when r.status_um is null then null else round(extract(epoch from clock_timestamp() - r.status_um)::numeric, 1) end);
end $$;

-- Show verlassen: Stand (mit der Moderation), Befehl und Handy-Abruf weg. Die Nummer bleibt, sie zählt weiter.
create or replace function rb_ende(p_pin text) returns json
language plpgsql security definer set search_path = public as $$
begin
  perform require_admin(p_pin);
  update rueckblick_steuerung set status = null, status_um = null, befehl = null, befehl_um = null, handy_um = null
    where id = 1;
  return json_build_object('ok', true);
end $$;

revoke all on function rb_befehl(text, text) from public;
revoke all on function rb_poll(text, bigint) from public;
revoke all on function rb_status_setzen(text, jsonb) from public;
revoke all on function rb_status_holen(text) from public;
revoke all on function rb_ende(text) from public;
grant execute on function rb_befehl(text, text) to anon, authenticated;
grant execute on function rb_poll(text, bigint) to anon, authenticated;
grant execute on function rb_status_setzen(text, jsonb) to anon, authenticated;
grant execute on function rb_status_holen(text) to anon, authenticated;
grant execute on function rb_ende(text) to anon, authenticated;

notify pgrst, 'reload schema';
"""


def main() -> None:
    for datei in sorted(MIG.glob("*.sql")):
        if datei == ZIEL:
            continue
        text = datei.read_text(encoding="utf-8")
        for name in NEU:
            if re.search(rf"\b{name}\b", text):
                sys.exit(f"{name} steht schon in {datei.name}: das wäre eine Ersetzung, Regeln aus migration_eingaben.py nehmen")
    ZIEL.write_text(SQL, encoding="utf-8", newline="\n")
    print("geschrieben:", ZIEL.relative_to(REPO))


if __name__ == "__main__":
    main()
