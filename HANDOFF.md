# Handoff: Stadtjagd

Digital geführtes Geocaching für die TSE-Teamfahrt in **Prag**. Die Teilnehmenden
melden sich per Link an, werden per Knopfdruck in Teams ausgelost und laufen
dieselbe Route mit fünf Stationen ab. Jede Station gibt nach GPS-Check-in und
gelöstem Rätsel eine Ziffer frei. Die sechste Ziffer ist die Einerstelle der
Summe der fünf. Das erste Team, das den vollständigen Code eingibt, öffnet den
Koffer und gewinnt.

**Stand 18.09.2026:** Live auf GitHub Pages, Datenbank eingerichtet, Nachträge 1
bis 5 eingespielt. Die fünf Prager Stationen stehen mit Koordinaten in der
Datenbank. Offen sind der Praxistest draußen, die Prüfung der Rätsel vor Ort und
die WhatsApp-Nummer für den Hilfe-Knopf.

## Stack und Aufbau

| Teil | Technik | Datei |
|---|---|---|
| Frontend | eine HTML-Datei, kein Framework, kein Build | `index.html` |
| Verbindung | Supabase-URL, Publishable key, Support-Nummer | `config.js` |
| Backend | PostgreSQL-Funktionen (`security definer`) in Supabase | `supabase/migrations/*.sql` |
| Karte | Leaflet 1.9.4 mit OpenStreetMap, per CDN | in `index.html` |
| Hosting | GitHub Pages über Actions | `.github/workflows/pages.yml` |

Es gibt bewusst keine Edge Functions, kein React, kein npm. Die gesamte
Spiellogik liegt in der Datenbank, das Frontend ruft ausschließlich
RPC-Endpunkte auf.

### Alle Dateien

```
index.html                      die komplette App, kein Build nötig
config.js                       Supabase-Zugang und WhatsApp-Nummer
kompass-test.html               Diagnoseseite für Kompassprobleme, gehört nicht zum Spiel
tools/sql.py                    SQL an die Datenbank schicken, ohne den SQL-Editor
supabase/migrations/            Schema und Spiellogik, in dieser Reihenfolge einspielen
  20260918120000_init.sql         Tabellen, Rechte, alle Funktionen
  20260918150000_where_clauses.sql  WHERE-Klauseln für pg-safeupdate
  20260918160000_routes.sql       Verlaufstabelle, admin_tracks, Beenden löscht nicht mehr
  20260918170000_draw_size.sql    Auslosen mit Teamgröße oder Teamzahl
  20260918180000_tiernamen.sql    Tiernamen mit Emoji, ohne Umlaute
  20260918190000_anmeldung_leeren.sql  alle Teilnehmenden auf einmal löschen
supabase/seed-stationen-prag.sql  die fünf Prager Stationen
supabase/seed-personen.sql      100 erfundene Teilnehmende, nur zum Proben
mockups/kompass-einmessen.html  Entwurf für das Einmessen des Kompasses
mockups/karte-routen.html       Entwurf für Routen und Zeitachse, vor der Umsetzung,
                                zeigt noch Berlin. Historisches Dokument, keine Doku.
supabase/config.toml            Projektdatei der Supabase CLI, hier ungenutzt
.github/workflows/pages.yml     Deployment auf GitHub Pages
README.md                       Kurzfassung fuer den Einstieg
HANDOFF.md                      diese Datei
```

## Sicherheitsmodell

Das ist der Kern, hier bitte nichts aufweichen:

- Alle Tabellen haben RLS aktiviert und **keine** Policies. Clients können also
  keine Tabelle direkt lesen oder schreiben.
- Zugriff läuft nur über Funktionen mit `security definer`, für die `anon` das
  Ausführungsrecht hat.
- Lösungen, Ziffern und der Koffercode verlassen die Datenbank nie. Der
  Rätseltext wird erst nach erfolgreichem Check-in ausgeliefert, eine Ziffer
  erst nach richtiger Antwort.
- Der Sieger wird atomar gesetzt: `update game_state ... where id = 1 and
  winner_team_id is null`. Zwei gleichzeitige Eingaben können nicht zu zwei
  Siegern führen.
- Die Admin-PIN wird serverseitig in `require_admin()` geprüft, nicht im Browser.
- Team-Codes bestehen aus Tiername und vier Ziffern (`FUCHS-4711`) und stehen
  **nicht** in der öffentlichen Antwort.

Bekannte, bewusst akzeptierte Schwächen:

- Positionen kommen vom Gerät und lassen sich mit Entwicklerwerkzeugen
  fälschen. Für ein Firmenevent akzeptabel.
- Wer einen Team-Code kennt, kann für dieses Team mitspielen. Die Codes gibst du
  nur an die Teamleitungen.
- Die Admin-PIN liegt im Klartext in `game_state.admin_pin`.
- Die Support-Nummer in `config.js` ist öffentlich, siehe „Hilfe für die
  Teilnehmenden“.

## Datenmodell

- `participants` – Name, `name_key` (normalisiert, unique), `team_id`
- `teams` – Name, Code, `leader_participant_id`
- `stations` – `position` 1–5, Name, `lat`, `lng`, `radius_m`, `location_hint`,
  `riddle`, `answer`, `digit`
- `progress` – je Team und Station: `checked_in_at`, `solved_at`,
  `failed_attempts`, `locked_until`
- `team_positions` – letzte bekannte Position je Team
- `position_log` – jeder gemeldete Punkt, daraus entstehen die Routen
- `game_state` – Einzelzeile mit `status` (`registration` → `drawn` → `running`
  → `finished`), `winner_team_id`, `admin_pin`

## RPC-Endpunkte

Öffentlich: `public_state`, `register_participant`, `lookup_participant`

Team: `team_state`, `check_in`, `submit_answer`, `submit_final`,
`report_position`

Admin (alle mit PIN): `admin_state`, `admin_tracks`, `admin_draw`,
`admin_start`, `admin_finish`, `admin_reset`, `admin_clear_positions`,
`admin_clear_participants`, `admin_add_participant`,
`admin_rename_participant`, `admin_delete_participant`, `admin_save_station`,
`admin_unlock_station`, `admin_set_pin`

`admin_draw` hat seit Nachtrag 3 drei Parameter: `(p_pin, p_teams, p_size)`.
Die alte Fassung mit nur einem Parameter wurde entfernt, sonst wüsste PostgREST
bei einem Aufruf mit nur der PIN nicht, welche gemeint ist.

Hilfsfunktionen ohne Ausführungsrecht für `anon`: `norm`, `dist_m`,
`team_by_code`, `current_station`, `require_admin`.

## Ansichten

- `#/public` – Anmeldung mit Namensfeld, nach der Auslosung Namenssuche, nach
  Spielende Rangliste
- `#/team` – Login per Team-Code, Zahlenschloss, Ortshinweis, Kompass mit
  Entfernung, Check-in, Rätsel, Endcode
- `#/admin` – Karte, Teams, Teilnehmende, Stationen, Daten löschen; oben
  Auslosen, Starten, Beenden

Jedes Team hat ein Tier-Emoji, passend zum Namen. Die Namen kommen aus
`admin_draw`, die Emoji aus `TEAM_EMOJI` in `index.html`. Beide Listen müssen
zusammenpassen, sonst erscheint eine Pfote als Platzhalter. Aktuell: Fuchs,
Wolf, Eule, Tiger, Panda, Einhorn, Flamingo, Pinguin, Delfin, Adler, Igel,
Otter, Krake, Biber, Koala, Drache. Alle ohne Umlaute, damit die Team-Codes auf
jeder Handytastatur leicht zu tippen sind.

Der Hintergrund ist eine gezeichnete Wanderkarte mit Höhenlinien, Fluss,
gestrichelten Wegen und Wegpunkten. Das SVG ist erzeugt, nicht von Hand
gesetzt; das Skript dazu liegt nicht im Repo, die Formen sind fest eingebaut.
Farben kommen aus den vorhandenen Token, die Klassen heißen `c` und `c5` für
Höhenlinien, `w` und `wl` für Wasser, `t` für Wege, `p` für Wegpunkte.

## Auslosen

Im Reiter Teams steht ein Formular: entweder Personen pro Team oder Anzahl
Teams. Darunter steht sofort, was dabei herauskommt, etwa „Ergibt 4 Teams, 1 mit
4 und 3 mit 3 Personen“. Mehr als 16 Teams gehen nicht, so viele Tiernamen gibt
es.

Vorher rechnete `admin_draw` die Teamzahl fest als `round(Personen / 10)`. Bei
13 Angemeldeten ergibt das 1, also blieb es beim Auslosen immer bei einem Team.
Das sah wie ein Fehler aus, war aber die Regel.

Ist schon ausgelost, fragt das erneute Auslosen über denselben Dialog nach wie
die Löschaktionen, denn es wirft die bestehenden Teams und ihre Codes weg.

Läuft das Spiel schon oder ist es beendet, lehnt die Datenbank ein Auslosen ab,
sonst wäre der Fortschritt der Teams nichts mehr wert. Der Reiter Teams zeigt
dann keinen leeren Bereich, sondern erklärt das und bietet direkt „Fortschritt
zurücksetzen“ an. Danach steht das Spiel wieder auf `drawn` und das Formular ist
zurück.

## Löschen

Alles, was Daten entfernt, fragt zweimal: erst der Dialog, dann muss das Wort
`LÖSCHEN` getippt werden, bevor der Knopf überhaupt anklickbar wird. Escape und
„Abbrechen“ brechen ab.

Im Reiter **Daten löschen** stehen die großen Aktionen: Standortdaten löschen,
Fortschritt zurücksetzen und alle Teilnehmenden löschen. Der Reiter zeigt
vorher, wie viele Teams, Personen, Positionen und gelöste Stationen betroffen
sind. Oben im Kopf stehen nur noch Auslosen, Starten und Beenden.

Im Reiter **Teilnehmende** sitzt „Alle löschen“ direkt neben der Zahl. Das ruft
`admin_clear_participants` auf: alle Personen, alle Teams, Fortschritt und
Standortdaten weg, Status zurück auf `registration`, damit sich wieder jemand
anmelden kann. Stationen, Rätsel, Ziffern und die PIN bleiben. Praktisch nach
einem Probelauf mit Testeinträgen.

Das × bei einer einzelnen Person fragt ebenfalls nach, verlangt aber kein
getipptes Wort: eine Person zu streichen ist Routine, und der gesperrte Knopf
sah dort wie ein Fehler aus. Wer eine Aktion ohne Wort anlegen will, setzt
`wort: false` im Eintrag.

Neues Auslosen sitzt nicht hier, sondern im Reiter Teams, weil dort auch die
Teamgröße eingestellt wird. Es fragt trotzdem nach.

Neue Löschaktionen gehören in die Liste `DANGER` in `index.html`, dann bekommen
sie den Dialog automatisch. Titel, Beschreibung und Zusatz dürfen Funktionen des
Zustands sein, damit im Dialog echte Zahlen stehen.

## Routen und Zeitachse

Auf der Karte hat jedes Team eine Farbe und seine gelaufene Route. Darunter
steht für jedes Team eine Zeitleiste: ausgefüllt heißt unterwegs, schraffiert
heißt an der Station am Rätsel, der Kreis mit der Ziffer markiert den Moment, in
dem die Antwort saß. Rechts die Gesamtzeit vom Start bis zur letzten Ziffer,
sortiert nach Schnelligkeit. Ein Klick auf ein Team blendet seine Route aus.

Der Schieber zieht die Karte auf einen früheren Zeitpunkt zurück, „Abspielen“
lässt den ganzen Ablauf in 45 Sekunden laufen, „Jetzt“ springt zurück auf den
aktuellen Stand. Weil alle Teams dieselbe Route laufen, liegen die Linien
größtenteils übereinander; zum Vergleichen einzelne Teams ausblenden.

Wie oft ein Punkt entsteht: Ein Team meldet seine Position, wenn es sich mehr
als 20 m bewegt hat oder die letzte Meldung älter als 60 Sekunden ist. Beim
Gehen ist das etwa alle 15 Sekunden, an einer Station einmal pro Minute. Für 90
Minuten sind das rund 250 Punkte je Team. `admin_tracks` liefert beim Nachladen
nur die Punkte seit dem letzten Abruf, damit nicht alle zehn Sekunden der ganze
Verlauf über die Leitung geht.

## Hilfe für die Teilnehmenden

In der öffentlichen Ansicht und in der Team-Ansicht steht ein Knopf, der
WhatsApp mit einer vorbereiteten Nachricht öffnet. Die Nachricht nennt je nach
Ansicht Team, Code und aktuelle Station, damit die Spielleitung sofort weiß, wer
schreibt.

Die Nummer steht in `config.js` unter `support.phone`, international ohne
Pluszeichen, aus 0151 2345678 wird also `491512345678`. Ohne Nummer erscheint
kein Knopf. **Die Nummer wird öffentlich**: sie steht im Quelltext der Seite und
im öffentlichen Repo, dessen Historie sie dauerhaft behält. Nimm eine, bei der
das in Ordnung ist, am besten ein Diensthandy.

## GPS und Kompass

- Entfernung per Haversine, Richtung per Kurswinkel, beides in `index.html`.
- Blickrichtung: iOS über `webkitCompassHeading`, Android über
  `deviceorientationabsolute`. Auf iOS muss
  `DeviceOrientationEvent.requestPermission()` in einem Klick-Handler laufen,
  deshalb der Knopf „Standort und Kompass aktivieren“.
- Ohne Magnetometer wird die Laufrichtung aus zwei GPS-Punkten genutzt. Bis sie
  bekannt ist, bleibt der Pfeil grau (`.needle.unsicher`), statt eine
  erfundene Richtung zu zeigen.
- Beim Check-in wird eine frische Position geholt. Serverseitig gilt `radius_m`
  plus bis zu 25 m GPS-Toleranz.
- **Alles braucht HTTPS.** Eine lokal per Doppelklick geöffnete Datei (`file://`
  oder `content://`) bekommt keinen Standortzugriff.
- **Der Kompass sagt, warum er nicht geht.** `S.gps.kompass` hält den Zustand,
  unter der Nadel steht er im Klartext: `wartet` (erlaubt, noch nichts
  gekommen), `an`, `kalibrieren` (ungenau oder ohne Nordbezug), `relativ`
  (Drehung ohne Nordbezug, andere Geräte), `abgelehnt`, `fehlt`. Vorher landete
  jeder Fehlschlag in einem leeren `catch` und sah gleich aus. Wechselt der
  Zustand, zeichnet die Team-Ansicht neu, damit Hinweis und Knöpfe sofort
  stimmen; aber nur, solange Kompass oder Einmessen zu sehen sind, sonst ginge
  eine halb getippte Rätselantwort verloren.
- **Erlaubnis auf dem iPhone:** Den Schalter „Bewegung und Ausrichtung“ in den
  Safari-Einstellungen gibt es seit iOS 13 nicht mehr, die Erlaubnis gilt je
  Seite und wird per `requestPermission()` erfragt. Nach einer Ablehnung
  antwortet sie oft sofort mit `denied`. Die App rät deshalb: Seite schließen,
  neu öffnen, „Erlauben“ tippen, notfalls den Browser ganz beenden. Der Knopf
  „Kompass erneut versuchen“ steht nur noch in diesem Hinweis.
- **Ohne Kompass:** Kommt 3 s nach dem Freigeben kein brauchbares Ereignis,
  gilt der Kompass als `fehlt`. Handys ohne Magnetsensor schweigen einfach oder
  schicken leere Ereignisse; vorher stand dort für immer „Kompass meldet sich
  noch nicht“. Ein ruhiger Hinweis erklärt, dass der Pfeil der Laufrichtung
  folgt und die Entfernung immer stimmt. Meldet sich der Kompass später doch,
  springt der Zustand zurück auf `an`.
- **Unkalibrierter Magnetsensor:** iOS liefert dann `webkitCompassAccuracy < 0`
  oder `webkitCompassHeading === null`. Abhilfe ist eine liegende Acht mit dem
  Handy. Das steht als Hinweis in der App.
- **Eine große positive Genauigkeit ist genauso unbrauchbar.** Gemessen auf
  einem iPhone 17 Pro (iOS 27, Chrome für iOS) am 18.09.2026: Erlaubnis
  erteilt, 1143 Ereignisse empfangen, `webkitCompassHeading` vorhanden, aber
  `webkitCompassAccuracy` bei **±74°**, und der Wert bewegte sich über zwölf
  aufeinanderfolgende Ereignisse um keine einzige Nachkommastelle. Der Sensor
  antwortet also, führt aber nicht nach. Die erste Fassung prüfte nur auf
  negative Werte und meldete deshalb fröhlich „Kompass aktiv“, während der
  Pfeil um einen Viertelkreis danebenlag.
- **Grenze:** `KOMPASS_GRENZE` in `index.html`, aktuell 25 Grad; zurück auf
  „aktiv“ erst unter 20 Grad, damit Hinweis und Knopf nicht flackern. Darüber gilt
  die Richtung als unbrauchbar, die App sagt das mit dem gemessenen Wert und
  schaltet auf die Laufrichtung aus zwei GPS-Punkten um, sobald das Team ein
  paar Schritte gegangen ist. Dafür wird die Laufrichtung jetzt auch dann
  mitgerechnet, wenn der Kompass etwas liefert; vorher unterblieb das, sobald
  irgendeine Richtung ankam, und es gab keinen Ersatz.
- **Was gegen einen schlechten Sensor hilft:** liegende Acht mit dem Gerät,
  weg von Magneten (MagSafe-Hüllen, Autohalterungen, Magnetbörsen, Kopfhörer),
  und in den Einstellungen unter Datenschutz, Ortungsdienste, Systemdienste den
  Dienst Kompasskalibrierung einschalten.
- **Einmessen (liegende Acht):** Meldet sich zum ersten Mal am Tag ein echter
  Kompass (`an` oder `kalibrieren`), zeigt die Team-Ansicht statt des Kompasses
  eine Anleitung mit Animation und Fortschrittsbalken. Eine Webseite kann das
  Kalibrieren weder auslösen noch prüfen, nur das Schwenken messen
  (Winkelgeschwindigkeit aus `beta`/`gamma` über 80°/s, Zittern zählt nicht).
  Fertig nach 5 s Schwenken, auf dem iPhone schon nach 2 s, sobald
  `webkitCompassAccuracy` ±15° oder besser meldet; Android verrät keine
  Genauigkeit. „Überspringen“ geht immer. Beides merkt sich das Handy in
  `localStorage` unter `sj.kal` mit dem Datum, danach bleibt der Link „Kompass
  neu einmessen“. Wird der Kompass später ungenau, trägt der Hinweis den Knopf
  „Jetzt einmessen“. Bleibt er nach dem Einmessen über der Grenze, nennt die App
  Magnete und die iOS-Kompasskalibrierung. Die Werte stehen als `KAL_*` im
  Abschnitt „GPS und Kompass“ in `index.html`. Entwurf:
  `mockups/kompass-einmessen.html`.
- **Testseite:** `kompass-test.html`, live unter
  https://7deeda.github.io/Stadtjagt/kompass-test.html. Zeigt Erlaubnis,
  Ereigniszahl, `webkitCompassHeading`, Genauigkeit und Rohwerte und fällt nach
  fünf Sekunden ein Urteil. Sie zählt, wie viele der 36 Richtungen beim Drehen
  ankommen (ab 30: funktioniert), und schreibt nur Änderungen ins Protokoll;
  ein still liegendes Handy liefert sonst zwölf gleiche Zeilen, was wie ein
  eingefrorener Sensor aussieht. Ein Knopf legt den Bericht in die
  Zwischenablage.

## Standortdaten und Datenschutz

Die Team-Handys senden ihre Position nur, solange `status = 'running'`, und nur
bei mehr als 20 m Bewegung oder älter als 60 Sekunden. In der Team-Ansicht steht
sichtbar, dass der Standort geteilt wird. Betroffen sind nur die Handys der
Teamleitungen, also so viele wie es Teams gibt. Je nach Haus vorher mit dem
Betriebsrat klären.

**Geändert am 18.09.2026:** „Spiel beenden“ löscht die Standortdaten nicht mehr,
sonst wären die Routen genau dann weg, wenn man sie auswerten will. Gelöscht
wird nur noch auf Knopfdruck über „Standortdaten löschen“, beim Zurücksetzen und
beim Leeren der Anmeldung. Das ist bewusst mehr als vorher: Aus kurzen
Positionsmeldungen wird ein vollständiger Bewegungsverlauf der Teamleitungen
über die ganze Spielzeit. Den Teams vorher sagen, dass der Weg aufgezeichnet
wird, und nach der Auswertung löschen.

## Umgebung (Stand 18.09.2026, live)

| Was | Wert |
|---|---|
| GitHub-Repo | `7DEEda/Stadtjagt`, Branch **master** (nicht `main`) |
| Live-Seite | https://7deeda.github.io/Stadtjagt/ |
| Supabase URL | `https://lwdmwklyydhcvnhpjudk.supabase.co` |
| Publishable key | `sb_publishable_7uEQEkFwi27XJdGLSoso5w_TMxHJYUq` (steht in `config.js`, darf öffentlich sein) |
| Admin-PIN | in `game_state.admin_pin`, am 18.09.2026 geändert (Standard war 2026). Der aktuelle Wert steht bewusst nicht im Repo, das ist öffentlich. |

Init-Migration und Nachträge 1 bis 5 sind eingespielt, geprüft über `pg_proc`
und Aufrufe der Endpunkte. Wer die Datenbank neu aufsetzt, spielt sie in der
Reihenfolge ein, in der sie unter „Alle Dateien“ stehen: ohne Nachtrag 1
schlägt „Teams auslosen“ mit „UPDATE requires a WHERE clause“ fehl, ohne
Nachtrag 2 fehlen Routen und Zeitachse, ohne Nachtrag 3 bleibt die Teamgröße
fest.

Wichtig für die Weiterarbeit:

- **Init-Migration nicht erneut ausführen.** Sie beginnt mit `drop table …
  cascade`. Änderungen kommen als neue Datei unter `supabase/migrations/`.
- **Neue Supabase-Schlüssel:** Das Projekt nutzt den Publishable key
  (`sb_publishable_…`), nicht den alten anon key. Der `sb_secret_…` gehört
  nirgends in Repo oder App.
- **Workflow horcht auf `[main, master]`**, weil der lokale Branch `master`
  heißt.
- **Auf dem Arbeitsrechner sind weder Node.js noch die GitHub CLI installiert**,
  und Adminrechte fehlen. Also keine Lösungen vorschlagen, die `npx`, `npm` oder
  `gh` voraussetzen. Python ist vorhanden, Git läuft über VS Code, SQL über
  `tools/sql.py` oder den SQL-Editor.
- **Das Projekt lag zunächst unter OneDrive.** Wenn es dort noch liegt: nach
  außerhalb verschieben, OneDrive synchronisiert den `.git`-Ordner mit und
  erzeugt Konflikte.
- **Kartenkacheln brauchen einen Referer.** `openstreetmap.org` antwortet auf
  Anfragen ohne Referer mit einem Sperrbild („Access blocked“) statt mit der
  Karte. Eine per Doppelklick geöffnete Datei (`file://`) sendet keinen, dort
  bleibt die Karte leer. Auf der Live-Seite und über `http://localhost`
  funktioniert sie. Zum lokalen Testen `python -m http.server` im Projektordner
  starten. Localhost gilt dem Browser außerdem als sicherer Kontext,
  Standortzugriff geht dort ohne HTTPS.
- **Jedes UPDATE und DELETE braucht ein WHERE.** Supabase lädt für
  API-Verbindungen die Erweiterung pg-safeupdate. Ohne WHERE bricht die Funktion
  mit „UPDATE requires a WHERE clause“ ab, auch innerhalb von
  security-definer-Funktionen. Für „alle Zeilen“ `where true` schreiben. Tests
  über eine direkte Datenbankverbindung zeigen das nicht, nur Aufrufe über die
  API.
- **Beispieldaten:** `supabase/seed-stationen-prag.sql` setzt die fünf Prager
  Stationen mit Koordinaten, Ortshinweisen und Rätseln, Koffer-Code 371955.
  Rätsel und Antworten sind nach bestem Wissen gesetzt und vor Ort zu prüfen.
  `supabase/seed-personen.sql` legt 100 erfundene Teilnehmende an, nur zum
  Proben und nur vor dem Auslosen einspielen.

## SQL ausführen ohne den Browser

`tools/sql.py` schickt SQL über die Supabase Management-API an die Datenbank,
damit Migrationen nicht mehr von Hand in den SQL-Editor kopiert werden müssen.

```
python tools/sql.py supabase/migrations/20260918160000_routes.sql
python tools/sql.py --read-only -c "select status from game_state"
```

Der Zugang braucht einen Personal Access Token von
https://supabase.com/dashboard/account/tokens. Er steht **nicht** im Repo,
sondern in `%USERPROFILE%\.supabase\stadtjagt.token`, also außerhalb von
OneDrive, oder in der Umgebungsvariable `SUPABASE_ACCESS_TOKEN`. Ein solcher
Token gilt fürs ganze Supabase-Konto, nicht nur für dieses Projekt; nach dem
Event auf derselben Seite zurückziehen. Der Publishable key aus `config.js` ist
hier der falsche Schlüssel, das Skript sagt das auch.

Eingebaute Bremse: Anweisungen, die Daten vernichten, lehnt das Skript ab,
solange nicht `--force` dabeisteht. Das schützt vor allem vor der
Init-Migration, die mit `drop table ... cascade` anfängt. Eine Funktion oder
einen Index zu ersetzen geht ohne `--force` durch, wird aber gemeldet. UPDATE
und DELETE innerhalb von Funktionskörpern (`$$ ... $$`) zählen nicht mit, sonst
käme kein Nachtrag durch. Die Projektkennung liest das Skript aus `config.js`,
sie steht also nur an einer Stelle.

## Einrichtung

### Supabase
1. Projekt auf supabase.com anlegen, Region Frankfurt.
2. Init-Migration und danach die Nachträge einspielen, per `tools/sql.py` oder
   im SQL-Editor.
3. Project Settings → API: Project URL und Publishable key (`sb_publishable_…`)
   nach `config.js` kopieren. Der Secret key (`sb_secret_…`) gehört nicht
   dorthin.
4. Support-Nummer in `config.js` eintragen, sonst fehlt der Hilfe-Knopf.

### GitHub Pages
Repo anlegen, Ordner pushen, unter Settings → Pages als Quelle „GitHub Actions“
wählen. Der Workflow im Ordner `.github/workflows` veröffentlicht bei jedem Push
auf `main` oder `master`.

### Lokal in VS Code
`index.html` braucht keinen Build. Zum Testen reicht die Erweiterung „Live
Server“, ohne Node.js, oder `python -m http.server` im Projektordner. Für
GPS-Tests am Handy brauchst du HTTPS, also entweder die veröffentlichte Seite
oder einen Tunnel.

## Ablauf am Eventtag

1. **Vorher:** Route ablaufen, jede Station im Reiter Stationen prüfen, Rätsel
   und Antworten vor Ort bestätigen, notfalls „Meinen Standort übernehmen“
   drücken. Koffer auf den Code aus dem Reiter Stationen stellen.
2. **Vorher:** Support-Nummer in `config.js` eintragen und pushen.
3. Anmeldelink verteilen, Teilnehmende tragen sich ein.
4. Vor dem Start: Testeinträge über „Alle löschen“ im Reiter Teilnehmende
   entfernen, damit nur echte Namen übrig bleiben.
5. Am Treffpunkt: Reiter Teams, Teamgröße wählen, auslosen, Codes an die
   Teamleitungen geben. Den Teams sagen, dass der Weg aufgezeichnet wird.
6. „Spiel starten“, danach die Karte offen lassen.
7. Wenn ein Team hängt: „Freischalten“ im Reiter Teams ersetzt den Check-in, das
   Rätsel bleibt.
8. Nach dem Sieg: „Spiel beenden“. Die Rangliste erscheint öffentlich, die
   Routen bleiben zum Auswerten erhalten.
9. **Danach:** Zeitachse und Routen ansehen, dann „Standortdaten löschen“.

## Offene Punkte

- **Probelauf draußen** mit einem echten Handy steht aus. Ablauf: auslosen,
  starten, mit dem Team-Code einloggen, Standort und Kompass aktivieren,
  Entfernung und Pfeil beim Gehen prüfen, einchecken, Rätsel lösen, danach die
  Karte und die Zeitachse im Admin-Bereich ansehen. Anschließend „Fortschritt
  zurücksetzen“.
- **Rätsel vor Ort prüfen.** Die fünf Prager Rätsel und ihre Antworten sind nach
  bestem Wissen gesetzt, aber niemand von uns stand davor. Besonders die Anzahl
  der Statuengruppen auf der Karlsbrücke und die Stufenzahl am Petřín gehören
  bestätigt.
- **Kompass auf dem iPhone 17 Pro:** Ursache gefunden, siehe GPS und Kompass.
  Der Sensor meldet ±74° Unsicherheit und einen eingefrorenen Wert. Die App
  erkennt das jetzt und weicht auf die Laufrichtung aus. Ob das Gerät nach
  Kalibrierung brauchbare Werte liefert, ist noch nicht bestätigt: Testseite
  erneut aufrufen, dabei auf die Zeile „Kompassgenauigkeit“ achten. Bleibt sie
  über 25°, nimmt das Team als Ersatz die Laufrichtung, und die Entfernung in
  Metern stimmt ohnehin unabhängig vom Kompass. Zum Vergleich ein iPhone 17
  (kein Pro, iOS 27, Chrome) am selben Tag: Erlaubnis erteilt,
  `webkitCompassHeading` mit ±10°, also brauchbar. Die zwölf gleichen Werte im
  Bericht kamen dort vom still liegenden Handy. Beim Pro deshalb erneut testen
  und sich dabei einmal im Kreis drehen.
- **WhatsApp-Nummer** fehlt in `config.js`, deshalb erscheint kein Hilfe-Knopf.
- Am Koffer sollte jemand von der Spielleitung stehen und erst nach dem Signal
  der App öffnen lassen.
- Optional: Startreihenfolge versetzen, Team-Chat, Fotoaufgaben.

## Historie und Entscheidungen

- Zuerst als Klick-Prototyp ohne Backend gebaut, um den Ablauf zu klären.
- Danach eine Version in Lovable (React, TanStack Start, Supabase). Projekt-ID
  `c04743bb-e316-45db-b53c-0808ce46ae52`. Aufgegeben, weil das Guthaben mitten
  in der Live-Karte ausging. Der Stand dort funktioniert, hat aber keine Karte
  und liefert Team-Codes öffentlich aus.
- Aktuelle Version bewusst ohne Framework: eine HTML-Datei plus SQL, damit sie
  ohne Build, ohne Abo und ohne fremde Plattform läuft.
- Geprüft wurde der komplette Ablauf gegen eine echte PostgreSQL-Instanz
  inklusive Sperre nach drei Fehlversuchen und der Frage, ob zwei Teams
  gleichzeitig gewinnen können. Können sie nicht.
- **18.09.2026, Routen behalten statt löschen.** Gegen das ursprüngliche
  Versprechen im Datenschutzabschnitt entschieden, weil die Auswertung sonst
  unmöglich wäre. Dafür löscht jetzt nur noch ein ausdrücklicher Knopf.
- **18.09.2026, Löschen in einen eigenen Bereich.** Vorher lagen „Zurücksetzen“
  und „Standortdaten löschen“ zwischen den Alltagsknöpfen. Jetzt ein eigener
  Reiter plus getipptes Wort. Ausnahme ist das × bei einer einzelnen Person: die
  volle Zeremonie sah dort wie ein Fehler aus.
- **18.09.2026, Teamgröße einstellbar.** Die feste Regel `round(Personen / 10)`
  ergab bei kleinen Gruppen immer ein Team und wirkte wie ein Fehler.
- **18.09.2026, Tiernamen nach Emoji ausgewählt.** Tiere ohne eigenes Emoji
  (Reiher, Marder, Iltis, Specht, Kranich, Luchs, Steinbock, Dachs, Hirsch,
  Falke) sind raus, dafür bekanntere mit Emoji und ohne Umlaute.
- **18.09.2026, Management-API statt SQL-Editor.** Weil auf dem Arbeitsrechner
  kein Node.js liegt, war die Supabase CLI keine Option. `tools/sql.py` spricht
  direkt die HTTP-API an.
