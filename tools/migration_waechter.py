#!/usr/bin/env python3
"""
Erzeugt supabase/migrations/20261002160000_kompass_waechter.sql (Nachtrag 30: Kompass-Wächter).

    python tools/migration_waechter.py

Das Handy der Teamleitung meldet das Urteil des Wächters mit der Position (report_position bekommt
p_kompass, Standard null), team_positions merkt es, admin_state liefert es als position.kompass.
admin_state wird aus der neuesten Fassung (20261002140000_startpunkt.sql) übernommen und um das Feld ergänzt.
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
MIG = REPO / "supabase" / "migrations"
ZIEL = MIG / "20261002160000_kompass_waechter.sql"

KOPF = """-- Nachtrag 30: Kompass-Wächter. Das Handy der Teamleitung meldet sein Urteil mit der Position.
alter table team_positions add column kompass text;
drop function report_position(text, double precision, double precision, double precision);
create function report_position(p_code text, p_lat double precision, p_lng double precision,
                                p_acc double precision, p_kompass text default null)
returns void language plpgsql security definer set search_path = public as $$
declare t teams;
begin
  if (select status from game_state where id = 1) <> 'running' then return; end if;
  if p_lat is null or p_lng is null or abs(p_lat) > 90 or abs(p_lng) > 180
     or (abs(p_lat) < 0.01 and abs(p_lng) < 0.01)
     or p_acc is null or p_acc <= 0 or p_acc > 1000 then
    return;
  end if;
  t := team_by_code(p_code);
  insert into team_positions(team_id, lat, lng, accuracy_m, updated_at, kompass)
  values (t.id, p_lat, p_lng, p_acc, now(), case when p_kompass in ('ok', 'unzuverlaessig') then p_kompass end)
  on conflict (team_id) do update
    set lat = excluded.lat, lng = excluded.lng, accuracy_m = excluded.accuracy_m, updated_at = now(), kompass = excluded.kompass;
  insert into position_log(team_id, lat, lng, accuracy_m) values (t.id, p_lat, p_lng, p_acc);
end $$;
grant execute on function report_position(text, double precision, double precision, double precision, text) to anon, authenticated;
"""

ALT = "'accuracy', tp.accuracy_m, 'updatedAt', tp.updated_at)"
NEU = "'accuracy', tp.accuracy_m, 'updatedAt', tp.updated_at, 'kompass', tp.kompass)"


def main() -> None:
    text = (MIG / "20261002140000_startpunkt.sql").read_text(encoding="utf-8")
    a = [m.start() for m in re.finditer(r"create or replace function admin_state\(", text)][-1]
    e = text.index("$$;", text.index("$$", a) + 2) + 3
    f = text[a:e]
    if f.count(ALT) != 1:
        sys.exit("admin_state: Einfügestelle 'updatedAt' nicht genau einmal gefunden")
    f = f.replace(ALT, NEU)
    ZIEL.write_text(KOPF + "\n-- ---------- admin_state (aus 20261002140000_startpunkt.sql) plus position.kompass ----------\n"
                    + f + "\n\nnotify pgrst, 'reload schema';\n", encoding="utf-8", newline="\n")
    print("geschrieben:", ZIEL.relative_to(REPO))


if __name__ == "__main__":
    main()
