-- Nachtrag 31: current_station(uuid) wieder für anon und authenticated sperren.
-- Nachtrag 28 (teststation) hat die Funktion gelöscht und neu angelegt; die Sperre aus init.sql galt nur der
-- alten Fassung. Die neue lief mit den Standardrechten und gab jedem mit dem Publishable Key Lösung, Ziffer,
-- Rätsel und Tipp der aktuellen Station eines Teams zurück (Bugjagd 03.10.2026).
-- Regel: nach jedem drop + create einer Hilfsfunktion das revoke wiederholen.
revoke all on function current_station(uuid) from public, anon, authenticated;
