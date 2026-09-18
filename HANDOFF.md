# Handoff: Stadtjagd

Digital geführtes Geocaching für die TSE-Teamfahrt. Rund 100 Teilnehmende melden sich per Link an, werden per Knopfdruck in Teams zu etwa zehn Personen ausgelost und laufen dieselbe Route mit fünf Stationen ab. Jede Station gibt nach GPS-Check-in und gelöstem Rätsel eine Ziffer frei. Die sechste Ziffer ist die Einerstelle der Summe der fünf. Das erste Team, das den vollständigen Code eingibt, öffnet den Koffer und gewinnt.

Stand: live auf GitHub Pages, Datenbank eingerichtet, Ablauf gegen eine echte PostgreSQL-Instanz durchgetestet. Offen sind der Praxistest draußen sowie die echten Orte und Rätsel.

## Stack und Aufbau

| Teil | Technik | Datei |
|---|---|---|
| Frontend | eine HTML-Datei, kein Framework, kein Build | `index.html` |
| Verbindung | Supabase-URL und anon key | `config.js` |
| Backend | PostgreSQL-Funktionen (`security definer`) in Supabase | `supabase/migrations/*.sql` |
| Karte | Leaflet 1.9.4 mit OpenStreetMap, per CDN | in `index.html` |
| Hosting | GitHub Pages über Actions | `.github/workflows/pages.yml` |

Es gibt bewusst keine Edge Functions, kein React, kein npm. Die gesamte Spiellogik liegt in der Datenbank, das Frontend ruft ausschließlich RPC-Endpunkte auf.

## Sicherheitsmodell

Das ist der Kern, hier bitte nichts aufweichen:

- Alle Tabellen haben RLS aktiviert und **keine** Policies. Clients können also keine Tabelle direkt lesen oder schreiben.
- Zugriff läuft nur über Funktionen mit `security definer`, für die `anon` das Ausführungsrecht hat.
- Lösungen, Ziffern und der Koffercode verlassen die Datenbank nie. Der Rätseltext wird erst nach erfolgreichem Check-in ausgeliefert, eine Ziffer erst nach richtiger Antwort.
- Der Sieger wird atomar gesetzt: `update game_state ... where id = 1 and winner_team_id is null`. Zwei gleichzeitige Eingaben können nicht zu zwei Siegern führen.
- Die Admin-PIN wird serverseitig in `require_admin()` geprüft, nicht im Browser.
- Team-Codes sind vierstellig (`FUCHS-4711`) und stehen **nicht** in der öffentlichen Antwort.

Bekannte, bewusst akzeptierte Schwächen:

- Positionen kommen vom Gerät und lassen sich mit Entwicklerwerkzeugen fälschen. Für ein Firmenevent akzeptabel.
- Wer einen Team-Code kennt, kann für dieses Team mitspielen. Die Codes gibst du nur an die Teamleitungen.
- Die Admin-PIN liegt im Klartext in `game_state.admin_pin`.

## Datenmodell

- `participants` – Name, `name_key` (normalisiert, unique), `team_id`
- `teams` – Name, Code, `leader_participant_id`
- `stations` – `position` 1–5, Name, `lat`, `lng`, `radius_m`, `location_hint`, `riddle`, `answer`, `digit`
- `progress` – je Team und Station: `checked_in_at`, `solved_at`, `failed_attempts`, `locked_until`
- `team_positions` – letzte bekannte Position je Team (nur während des Spiels)
- `position_log` – jeder gemeldete Punkt, daraus entstehen die Routen auf der Karte
- `game_state` – Einzelzeile mit `status` (`registration` → `drawn` → `running` → `finished`), `winner_team_id`, `admin_pin`

## RPC-Endpunkte

Öffentlich: `public_state`, `register_participant`, `lookup_participant`
Team: `team_state`, `check_in`, `submit_answer`, `submit_final`, `report_position`
Admin (alle mit PIN): `admin_state`, `admin_tracks`, `admin_draw`, `admin_start`, `admin_finish`, `admin_reset`, `admin_clear_positions`, `admin_add_participant`, `admin_rename_participant`, `admin_delete_participant`, `admin_save_station`, `admin_unlock_station`, `admin_set_pin`

Hilfsfunktionen ohne Ausführungsrecht für `anon`: `norm`, `dist_m`, `team_by_code`, `current_station`, `require_admin`.

## Ansichten

- `#/public` – Anmeldung mit Namensfeld, nach der Auslosung Namenssuche, nach Spielende Rangliste
- `#/team` – Login per Team-Code, Zahlenschloss, Ortshinweis, Kompass mit Entfernung, Check-in, Rätsel, Endcode
- `#/admin` – Karte, Teams, Teilnehmende, Stationen, Daten löschen; Auslosen, Starten, Beenden

Jedes Team hat ein Tier-Emoji, passend zum Namen. Die Namen kommen aus
`admin_draw`, die Emoji aus `TEAM_EMOJI` in `index.html`. Beide Listen müssen
zusammenpassen, sonst erscheint eine Pfote als Platzhalter. Aktuell: Fuchs,
Wolf, Eule, Tiger, Panda, Einhorn, Flamingo, Pinguin, Delfin, Adler, Igel,
Otter, Krake, Biber, Koala, Drache. Alle ohne Umlaute, damit die Team-Codes
auf jeder Handytastatur leicht zu tippen sind.

## Auslosen

Im Reiter Teams steht ein Formular: entweder Personen pro Team oder Anzahl
Teams. Darunter steht sofort, was dabei herauskommt, etwa „Ergibt 4 Teams,
1 mit 4 und 3 mit 3 Personen“. Mehr als 16 Teams gehen nicht, so viele
Tiernamen gibt es.

Vorher rechnete `admin_draw` die Teamzahl fest als `round(Personen / 10)`.
Bei 13 Angemeldeten ergibt das 1, also blieb es beim Auslosen immer bei einem
Team. Das sah wie ein Fehler aus, war aber die Regel.

Ist schon ausgelost, fragt das erneute Auslosen über denselben Dialog nach wie
die Löschaktionen, denn es wirft die bestehenden Teams und ihre Codes weg.

## Hilfe für die Teilnehmenden

In der öffentlichen Ansicht und in der Team-Ansicht steht ein Knopf, der
WhatsApp mit einer vorbereiteten Nachricht öffnet. Die Nachricht nennt je nach
Ansicht Team, Code und aktuelle Station, damit die Spielleitung sofort weiß,
wer schreibt.

Die Nummer steht in `config.js` unter `support.phone`, international ohne
Pluszeichen, aus 0151 2345678 wird also `491512345678`. Ohne Nummer erscheint
kein Knopf. **Die Nummer wird öffentlich**: sie steht im Quelltext der Seite
und im öffentlichen Repo. Nimm eine, bei der das in Ordnung ist.

## Routen und Zeitachse

Auf der Karte hat jedes Team eine Farbe und seine gelaufene Route. Darunter
steht für jedes Team eine Zeitleiste: ausgefüllt heißt unterwegs, schraffiert
heißt an der Station am Rätsel, der Kreis mit der Ziffer markiert den Moment,
in dem die Antwort saß. Rechts die Gesamtzeit vom Start bis zur letzten Ziffer,
sortiert nach Schnelligkeit. Ein Klick auf ein Team blendet seine Route aus.

Der Schieber zieht die Karte auf einen früheren Zeitpunkt zurück, „Abspielen“
lässt den ganzen Ablauf in 45 Sekunden laufen, „Jetzt“ springt zurück auf den
aktuellen Stand. Weil alle Teams dieselbe Route laufen, liegen die Linien
größtenteils übereinander; zum Vergleichen einzelne Teams ausblenden.

Wie oft ein Punkt entsteht: Ein Team meldet seine Position, wenn es sich mehr
als 20 m bewegt hat oder die letzte Meldung älter als 60 Sekunden ist. Beim
Gehen ist das etwa alle 15 Sekunden, an einer Station einmal pro Minute. Für
90 Minuten sind das rund 250 Punkte je Team. `admin_tracks` liefert beim
Nachladen nur die Punkte seit dem letzten Abruf, damit nicht alle zehn
Sekunden der ganze Verlauf über die Leitung geht.

## GPS und Kompass

- Entfernung per Haversine, Richtung per Kurswinkel, beides in `index.html`.
- Blickrichtung: iOS über `webkitCompassHeading`, Android über `deviceorientationabsolute`. Auf iOS muss `DeviceOrientationEvent.requestPermission()` in einem Klick-Handler laufen, deshalb der Button „Standort und Kompass aktivieren“.
- Ohne Magnetometer wird die Laufrichtung aus zwei GPS-Punkten genutzt, sonst zeigt der Pfeil relativ zu Norden. Der Zustand steht immer unter dem Kompass.
- Beim Check-in wird eine frische Position geholt. Serverseitig gilt `radius_m` plus bis zu 25 m GPS-Toleranz.
- **Alles braucht HTTPS.** Eine lokal per Doppelklick geöffnete Datei (`file://` oder `content://`) bekommt keinen Standortzugriff.

## Standortdaten und Datenschutz

Die Team-Handys senden ihre Position nur, solange `status = 'running'`, und nur bei mehr als 20 m Bewegung oder älter als 60 Sekunden. In der Team-Ansicht steht sichtbar, dass der Standort geteilt wird. Betroffen sind nur die zehn Handys der Teamleitungen. Je nach Haus vorher mit dem Betriebsrat klären.

**Geändert am 18.09.2026:** „Spiel beenden“ löscht die Standortdaten nicht mehr,
sonst wären die Routen genau dann weg, wenn man sie auswerten will. Gelöscht
wird jetzt nur noch auf Knopfdruck über „Standortdaten löschen“ und beim
Zurücksetzen. Das ist bewusst mehr als vorher: Aus kurzen Positionsmeldungen
wird ein vollständiger Bewegungsverlauf der Teamleitungen über die ganze
Spielzeit. Den Teams vorher sagen, dass der Weg aufgezeichnet wird, und nach
der Auswertung löschen.

## Umgebung (Stand 18.09.2026, live)

| Was | Wert |
|---|---|
| GitHub-Repo | `7DEEda/Stadtjagt`, Branch **master** (nicht `main`) |
| Live-Seite | https://7deeda.github.io/Stadtjagt/ |
| Supabase URL | `https://lwdmwklyydhcvnhpjudk.supabase.co` |
| Publishable key | `sb_publishable_7uEQEkFwi27XJdGLSoso5w_TMxHJYUq` (steht in `config.js`, darf öffentlich sein) |
| Admin-PIN | in `game_state.admin_pin`, am 18.09.2026 geändert (Standard war 2026). Der aktuelle Wert steht bewusst nicht im Repo, das ist öffentlich. |

Erledigt: Migration ist im Supabase-Projekt eingespielt, Schema und Funktionen stehen, Status `registration`.
Nachträge 1 bis 4 (`where_clauses`, `routes`, `draw_size`, `tiernamen`) sind am 18.09.2026 eingespielt, geprüft über `pg_proc` und einen Aufruf von `admin_tracks`. Wer die Datenbank neu aufsetzt, spielt sie in dieser Reihenfolge nach der Init-Migration ein: ohne Nachtrag 1 schlägt „Teams auslosen“ mit „UPDATE requires a WHERE clause“ fehl, ohne Nachtrag 2 fehlen Routen und Zeitachse.
GitHub Pages läuft über Actions, erstes Deployment grün.

Wichtig für die Weiterarbeit:

- **Migration nicht erneut ausführen.** Die Init-Datei beginnt mit `drop table … cascade`. Änderungen kommen als neue SQL-Anweisungen im SQL-Editor, zusätzlich als neue Datei unter `supabase/migrations/` im Repo abgelegt.
- **Neue Supabase-Schlüssel:** Das Projekt nutzt den Publishable key (`sb_publishable_…`), nicht den alten anon key. Der `sb_secret_…` gehört nirgends in Repo oder App.
- **Workflow horcht auf `[main, master]`**, weil der lokale Branch `master` heißt.
- **Auf dem Arbeitsrechner sind weder Node.js noch die GitHub CLI installiert**, und Adminrechte fehlen. Also keine Lösungen vorschlagen, die `npx`, `npm` oder `gh` voraussetzen. Supabase wird über den SQL-Editor im Browser bedient, Git über VS Code.
- **Das Projekt lag zunächst unter OneDrive.** Wenn es dort noch liegt: nach außerhalb verschieben, OneDrive synchronisiert den `.git`-Ordner mit und erzeugt Konflikte.
- **Kartenkacheln brauchen einen Referer.** `openstreetmap.org` antwortet auf Anfragen ohne Referer mit einem Sperrbild („Access blocked“) statt mit der Karte. Eine per Doppelklick geöffnete Datei (`file://`) sendet keinen, dort bleibt die Karte also leer. Auf der Live-Seite und über `http://localhost` funktioniert sie. Zum lokalen Testen `python -m http.server` im Projektordner starten, Python ist auf dem Arbeitsrechner vorhanden. Localhost gilt dem Browser außerdem als sicherer Kontext, Standortzugriff geht dort ohne HTTPS.
- **Jedes UPDATE und DELETE braucht ein WHERE.** Supabase lädt für API-Verbindungen die Erweiterung pg-safeupdate. Ohne WHERE bricht die Funktion mit „UPDATE requires a WHERE clause“ ab, auch innerhalb von security-definer-Funktionen. Für „alle Zeilen“ `where true` schreiben. Tests über eine direkte Datenbankverbindung zeigen das nicht, nur Aufrufe über die API.
- **Hintergrund:** Die Seite liegt auf einer gezeichneten Wanderkarte mit
  Höhenlinien, Fluss, gestrichelten Wegen und Wegpunkten. Das SVG ist erzeugt,
  nicht von Hand gesetzt; das Skript dazu liegt nicht im Repo, die Formen sind
  fest eingebaut. Farben kommen aus den vorhandenen Token, die Klassen heißen
  `c` und `c5` für Höhenlinien, `w` und `wl` für Wasser, `t` für Wege, `p` für
  Wegpunkte.
- **Beispieldaten:** `supabase/seed-stationen-prag.sql` setzt die fünf Prager Stationen (Pulverturm, Astronomische Uhr, Karlsbrücke, Lennon-Mauer, Petřín) mit Koordinaten, Ortshinweisen und Rätseln, Koffer-Code 371955. Rätsel und Antworten sind nach bestem Wissen gesetzt und vor Ort zu prüfen. `supabase/seed-personen.sql` legt 100 erfundene Teilnehmende an, nur zum Proben und nur vor dem Auslosen einspielen.

Offen an dieser Stelle: der Probelauf draußen. Ablauf: Station 1 per „Meinen Standort übernehmen“ setzen, auslosen, starten, mit dem Team-Code einloggen, Standort und Kompass aktivieren, Entfernung und Pfeil beim Gehen prüfen, einchecken, Rätsel lösen, danach die Karte im Admin-Bereich ansehen. Anschließend „Zurücksetzen“, damit der Testfortschritt verschwindet.

## Löschen

Alles, was Daten entfernt, steht im eigenen Reiter „Daten löschen“ und nirgends
sonst: Standortdaten löschen, Fortschritt zurücksetzen und, solange noch nicht
gestartet ist, neu auslosen. Oben im Kopf stehen nur noch Auslosen, Starten und
Beenden. Der Reiter zeigt vorher, wie viele Teams, Personen, Positionen und
gelöste Stationen betroffen sind.

Jede dieser Aktionen fragt zweimal: erst der Dialog, dann muss das Wort
`LÖSCHEN` getippt werden, bevor der Knopf überhaupt anklickbar wird. Escape und
„Abbrechen“ brechen ab. Dasselbe gilt für das × bei den Teilnehmenden, das
vorher ohne jede Rückfrage gelöscht hat. Neue Löschaktionen gehören in die
Liste `DANGER` in `index.html`, dann bekommen sie den Dialog automatisch.

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

Eingebaute Bremse: Anweisungen, die Daten oder Tabellen vernichten, lehnt das
Skript ab, solange nicht `--force` dabeisteht. Das schützt vor allem vor der
Init-Migration, die mit `drop table ... cascade` anfängt. UPDATE und DELETE
innerhalb von Funktionskörpern (`$$ ... $$`) zählen nicht mit, sonst käme jeder
Nachtrag durch die Bremse. Die Projektkennung liest das Skript aus `config.js`,
sie steht also nur an einer Stelle.

## Einrichtung


### Supabase
1. Projekt auf supabase.com anlegen, Region Frankfurt.
2. Migration einspielen. Auf dem Arbeitsrechner ohne Node.js per SQL-Editor (Inhalt der Datei aus `supabase/migrations/` einfügen). Wo Node.js vorhanden ist, geht alternativ die CLI:
   ```
   npx supabase@latest login
   npx supabase@latest link --project-ref <ref>
   npx supabase@latest db push
   ```
   `npx` vermeidet eine globale Installation, braucht aber Node.js. Auf dem Arbeitsrechner fehlt das, siehe „Umgebung“.
3. Project Settings → API: Project URL und Publishable key (`sb_publishable_…`) nach `config.js` kopieren. Der Secret key (`sb_secret_…`) gehört nicht dorthin.

**Achtung:** Die Init-Migration beginnt mit `drop table ... cascade` und ist damit absichtlich wiederholbar. Sobald echte Daten drin sind, keine neue Version dieser Datei pushen, sondern eine zusätzliche Migration schreiben.

### GitHub Pages
Repo anlegen, Ordner pushen, unter Settings → Pages als Quelle „GitHub Actions“ wählen. Der Workflow im Ordner `.github/workflows` veröffentlicht bei jedem Push auf `main` oder `master`.

### Lokal in VS Code
`index.html` braucht keinen Build. Zum Testen reicht die Erweiterung „Live Server“ in VS Code, ohne Node.js. Mit Node.js geht auch `npx serve`. Für GPS-Tests am Handy brauchst du HTTPS, also entweder die veröffentlichte Seite oder einen Tunnel.

## Ablauf am Eventtag

1. Vorher: Route ablaufen, je Station „Meinen Standort übernehmen“, Rätsel eintragen, Ziffern setzen. Koffer auf den Code aus dem Admin-Bereich stellen.
2. Anmeldelink verteilen, Teilnehmende tragen sich ein.
3. Am Treffpunkt: „Teams auslosen“, Codes an die Teamleitungen geben.
4. „Spiel starten“, danach die Karte offen lassen.
5. Wenn ein Team hängt: „Freischalten“ ersetzt den Check-in, das Rätsel bleibt.
6. Nach dem Sieg: „Spiel beenden“. Rangliste erscheint öffentlich, Standortdaten werden gelöscht.

## Offene Punkte

- Die fünf echten Orte samt Koordinaten und die dazu passenden Rätsel fehlen. Die Platzhalter sind erfunden.
- Rätsel sollten nur vor Ort lösbar sein, etwa über Jahreszahlen, Figuren oder Zählaufgaben.
- Die Ortshinweise selbst als kleines Rätsel formulieren, sonst laufen langsamere Teams einfach dem Führungsteam hinterher.
- Am Koffer sollte jemand von der Spielleitung stehen und erst nach dem Signal der App öffnen lassen.
- Probelauf draußen mit einem echten Handy steht aus.
- Optional: Startreihenfolge versetzen, Team-Chat, Fotoaufgaben.

## Historie und Entscheidungen

- Zuerst als Klick-Prototyp ohne Backend gebaut, um den Ablauf zu klären.
- Danach eine Version in Lovable (React, TanStack Start, Supabase). Projekt-ID `c04743bb-e316-45db-b53c-0808ce46ae52`. Aufgegeben, weil das Guthaben mitten in der Live-Karte ausging. Der Stand dort funktioniert, hat aber keine Karte und liefert Team-Codes öffentlich aus.
- Aktuelle Version bewusst ohne Framework: eine HTML-Datei plus SQL, damit sie ohne Build, ohne Abo und ohne fremde Plattform läuft.
- Geprüft wurde der komplette Ablauf gegen eine echte PostgreSQL-Instanz inklusive Sperre nach drei Fehlversuchen und der Frage, ob zwei Teams gleichzeitig gewinnen können. Können sie nicht.
