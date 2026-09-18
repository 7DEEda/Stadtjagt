# Stadtjagd

Digital geführtes Geocaching für die TSE-Teamfahrt in Prag: Anmeldung per Link,
zufällige Teamauslosung, fünf Stationen mit GPS-Check-in und Rätsel,
sechsstelliger Koffercode, Live-Karte mit den gelaufenen Routen und einer
Zeitachse für die Spielleitung.

Vollständiger Kontext, Architektur, Datenschutz und offene Punkte:
**[HANDOFF.md](HANDOFF.md)**

Wie Spiel und Code funktionieren (Regeln, Zustände, Abläufe, Aufbau): **[SPIEL.md](SPIEL.md)**

## Ansichten

| Pfad | Für wen |
|---|---|
| `#/public` | alle Teilnehmenden: anmelden, Team nachschlagen, Rangliste |
| `#/team` | Handy der Teamleitung, Login per Team-Code |
| `#/admin` | Spielleitung, Login per PIN |

Die PIN steht in `game_state.admin_pin` und bewusst nicht in diesem Repo, weil
es öffentlich ist. Ändern über den Endpunkt `admin_set_pin` oder direkt:

```sql
update game_state set admin_pin = 'neuePIN' where id = 1;
```

## Schnellstart

1. Supabase-Projekt anlegen, Region Frankfurt.
2. SQL einspielen, in dieser Reihenfolge, per `tools/sql.py` oder im
   SQL-Editor:

   ```
   supabase/migrations/20260918120000_init.sql
   supabase/migrations/20260918150000_where_clauses.sql
   supabase/migrations/20260918160000_routes.sql
   supabase/migrations/20260918170000_draw_size.sql
   supabase/migrations/20260918180000_tiernamen.sql
   supabase/migrations/20260918190000_anmeldung_leeren.sql
   supabase/migrations/20260918200000_drei_koffer.sql
   supabase/migrations/20260918210000_testmodus.sql
   supabase/migrations/20260918220000_durchsicht.sql
   supabase/migrations/20260918230000_viele_namen.sql
   supabase/migrations/20260919000000_nachmelden.sql
   supabase/migrations/20260919010000_mitlesen.sql
   supabase/migrations/20260919020000_anmeldung_bis_auslosen.sql
   ```

   Die Init-Datei beginnt mit `drop table ... cascade`. Auf einer Datenbank mit
   echten Daten niemals erneut ausführen.
3. In `config.js` eintragen: Project URL und **Publishable key**
   (`sb_publishable_…`, Supabase → Project Settings → API). Der Secret key
   (`sb_secret_…`) gehört dort nicht hinein.
4. In `config.js` die WhatsApp-Nummer unter `support.phone` eintragen, sonst
   erscheint kein Hilfe-Knopf. Achtung, die Nummer wird öffentlich.
5. Stationen setzen: `supabase/seed-stationen-prag.sql` einspielen oder im
   Reiter Stationen von Hand eintragen.
6. Repo nach GitHub pushen, unter Settings → Pages als Quelle „GitHub Actions“
   wählen.

## Aufbau

```
index.html                     komplette App, kein Build nötig
config.js                      Supabase-Zugang und WhatsApp-Nummer
kompass-test.html              Diagnoseseite für Kompassprobleme
tools/sql.py                   SQL an die Datenbank schicken, ohne den SQL-Editor
supabase/migrations/*.sql      Schema, Rechte und die gesamte Spiellogik
supabase/seed-*.sql            Prager Stationen und Testpersonen
.github/workflows/pages.yml    Deployment auf GitHub Pages
```

## SQL ausführen

```bash
python tools/sql.py supabase/seed-stationen-prag.sql
python tools/sql.py --read-only -c "select status from game_state"
```

Braucht einen Personal Access Token in `%USERPROFILE%\.supabase\stadtjagt.token`
oder in `SUPABASE_ACCESS_TOKEN`. Einzelheiten in
[HANDOFF.md](HANDOFF.md#sql-ausführen-ohne-den-browser).

## Lokal testen

```bash
python -m http.server
```

Dann `http://localhost:8000/` öffnen. Per Doppelklick auf die Datei geht es
nicht: ohne HTTPS oder localhost gibt es keinen Standortzugriff, und
OpenStreetMap liefert ohne Referer keine Kartenkacheln.
