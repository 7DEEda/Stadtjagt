# Stadtjagd

Digital geführtes Geocaching für die TSE-Teamfahrt in Prag: Anmeldung per Link,
zufällige Teamauslosung, fünf Stationen mit GPS-Check-in und Rätsel,
sechsstelliger Koffercode, Live-Karte mit den gelaufenen Routen und einer
Zeitachse für die Spielleitung.

Vollständiger Kontext, Architektur, Datenschutz und offene Punkte:
**[HANDOFF.md](HANDOFF.md)**

Wie Spiel und Code funktionieren (Regeln, Zustände, Abläufe, Aufbau): **[SPIEL.md](SPIEL.md)**

Nächster Schritt (Stand 06.10.2026): Der Umbau "Weiterentwicklung" ist auf Branch
`umbau-weiterentwicklung` gebaut, aber nicht gemerged und nicht gepusht. Er
wartet auf Friedrichs Okay und einen Handytest. Einzelheiten im HANDOFF unter
"Umbau Weiterentwicklung (Nachtrag 33)".

## Ansichten

| Pfad | Für wen |
|---|---|
| `#/public` | alle Teilnehmenden: anmelden, Team nachschlagen, Rangliste |
| `#/team` | Handy der Teamleitung, erkannt am eigenen Handy (ohne Code) |
| `#/admin` | Spielleitung, Login per PIN |

Die PIN steht in `game_state.admin_pin` und bewusst nicht in diesem Repo, weil
es öffentlich ist. Ändern über den Endpunkt `admin_set_pin` oder direkt, seit
Nachtrag 20 mit mindestens 12 Zeichen (am besten eine Passphrase):

```sql
update game_state set admin_pin = 'vier lange Wörter hier' where id = 1;
```

## Schnellstart

1. Supabase-Projekt anlegen, Region Frankfurt.
2. SQL einspielen: alle Dateien in `supabase/migrations` in
   Dateinamen-Reihenfolge, per `tools/sql.py` oder im SQL-Editor.

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
design-system/                 Regeln (MASTER.md) und Ansicht (index.html) des Design Systems
config.js                      Supabase-Zugang und WhatsApp-Nummer
geraete-test.html              Geräte-Test: prüft auf einem Handy alles, was das Spiel braucht
geraete-tests.js               die Suite dazu, ein Baustein je Test
kompass-test.html              leitet auf geraete-test.html weiter
tools/testlaeufe.py            Läufe des Geräte-Tests nach testlaeufe/ holen
vendor/qrcode.js               QR-Generator für den Mitlese-Link, lokal
tools/sql.py                   SQL an die Datenbank schicken, ohne den SQL-Editor
tools/pruefstand/              UI-Prüfstand: App ohne Datenbank in jedem Zustand fotografieren
supabase/migrations/*.sql      Schema, Rechte und die gesamte Spiellogik
supabase/seed-*.sql            Prager Stationen und Testpersonen
.github/workflows/pages.yml    Deployment auf GitHub Pages
```

## Seit dem 30.09.2026 dabei

- **Gruppenselfie** an jeder Station, abschaltbar im Reiter „Fotos“: erst das
  Foto, dann die Ziffer. Album fürs Team, Galerie und ZIP für die Spielleitung.
- **Verschlüsselter Stationsname:** löst sich auf, je näher das Team kommt.
  Die Kreise dafür stellt man beim Bearbeiten der Station auf einer Karte ein.
- **Mitlese-Link als QR-Code**, Hinweis bei ungefährem Standort, Kompass als
  Zeichen mit mitdrehender Nadel, Einmessen als Fenster.
- **Geräte-Test** (`geraete-test.html`): prüft auf einem Handy, was das Spiel
  braucht, und speichert den Lauf.
- **Seit dem 01.10.2026:** Schalter hell/dunkel oben rechts, Hinweis, wenn das
  Handy quer liegt, Zifferntastatur bei Zahlenlösungen, „Wir sind da“ zeigt die
  Entfernung. Das **Design System** liegt in `design-system/` (Regeln in
  `MASTER.md`, Ansicht in `index.html`, online unter `/design-system/`).
- **Seit dem 03.10.2026:** Teststation und Startpunkt je Route, **Kompass-Wächter**
  (erkennt im Testmodus einen falsch zeigenden Kompass, der Pfeil folgt dann der
  Laufrichtung, die Spielleitung sieht „Kompass falsch“), dazu die Funde einer
  Bugjagd (Nachtrag 31 und 32).

Prüfen ohne Datenbank: `python tools/pruefstand/selfie.py`, `name.py`,
`geraetetest.py`, `kritik.py`, `ziffer.py`, `teststation.py` (Probelauf `teststation_db.py`),
`waechter.py` (Kompass-Wächter, Probelauf `waechter_db.py`). Einzelheiten in `HANDOFF.md`, geordnet in `SPIEL.md`
Abschnitt 11 und 12.

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
