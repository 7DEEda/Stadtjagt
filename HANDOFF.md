# Handoff: Stadtjagd

Digital geführtes Geocaching für die TSE-Teamfahrt. Rund 100 Teilnehmende melden sich per Link an, werden per Knopfdruck in Teams zu etwa zehn Personen ausgelost und laufen dieselbe Route mit fünf Stationen ab. Jede Station gibt nach GPS-Check-in und gelöstem Rätsel eine Ziffer frei. Die sechste Ziffer ist die Einerstelle der Summe der fünf. Das erste Team, das den vollständigen Code eingibt, öffnet den Koffer und gewinnt.

Stand: lauffähig und gegen eine echte PostgreSQL-Instanz durchgetestet. Offen sind die echten Orte und Rätsel.

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
- `game_state` – Einzelzeile mit `status` (`registration` → `drawn` → `running` → `finished`), `winner_team_id`, `admin_pin`

## RPC-Endpunkte

Öffentlich: `public_state`, `register_participant`, `lookup_participant`
Team: `team_state`, `check_in`, `submit_answer`, `submit_final`, `report_position`
Admin (alle mit PIN): `admin_state`, `admin_draw`, `admin_start`, `admin_finish`, `admin_reset`, `admin_clear_positions`, `admin_add_participant`, `admin_rename_participant`, `admin_delete_participant`, `admin_save_station`, `admin_unlock_station`, `admin_set_pin`

Hilfsfunktionen ohne Ausführungsrecht für `anon`: `norm`, `dist_m`, `team_by_code`, `current_station`, `require_admin`.

## Ansichten

- `#/public` – Anmeldung mit Namensfeld, nach der Auslosung Namenssuche, nach Spielende Rangliste
- `#/team` – Login per Team-Code, Zahlenschloss, Ortshinweis, Kompass mit Entfernung, Check-in, Rätsel, Endcode
- `#/admin` – Karte, Teams, Teilnehmende, Stationen; Auslosen, Starten, Beenden, Zurücksetzen

## GPS und Kompass

- Entfernung per Haversine, Richtung per Kurswinkel, beides in `index.html`.
- Blickrichtung: iOS über `webkitCompassHeading`, Android über `deviceorientationabsolute`. Auf iOS muss `DeviceOrientationEvent.requestPermission()` in einem Klick-Handler laufen, deshalb der Button „Standort und Kompass aktivieren“.
- Ohne Magnetometer wird die Laufrichtung aus zwei GPS-Punkten genutzt, sonst zeigt der Pfeil relativ zu Norden. Der Zustand steht immer unter dem Kompass.
- Beim Check-in wird eine frische Position geholt. Serverseitig gilt `radius_m` plus bis zu 25 m GPS-Toleranz.
- **Alles braucht HTTPS.** Eine lokal per Doppelklick geöffnete Datei (`file://` oder `content://`) bekommt keinen Standortzugriff.

## Standortdaten und Datenschutz

Die Team-Handys senden ihre Position nur, solange `status = 'running'`, und nur bei mehr als 20 m Bewegung oder älter als 60 Sekunden. In der Team-Ansicht steht sichtbar, dass der Standort geteilt wird. Beim Beenden des Spiels werden alle Positionen gelöscht, zusätzlich gibt es den Button „Standortdaten löschen“. Betroffen sind nur die zehn Handys der Teamleitungen. Je nach Haus vorher mit dem Betriebsrat klären.

## Einrichtung

### Supabase
1. Projekt auf supabase.com anlegen, Region Frankfurt.
2. Migration einspielen, entweder per SQL-Editor (Inhalt der Datei aus `supabase/migrations/` einfügen) oder per CLI:
   ```
   npx supabase@latest login
   npx supabase@latest link --project-ref <ref>
   npx supabase@latest db push
   ```
   `npx` vermeidet eine Installation, praktisch auf Rechnern ohne Adminrechte.
3. Project Settings → API: Project URL und anon public key nach `config.js` kopieren.

**Achtung:** Die Init-Migration beginnt mit `drop table ... cascade` und ist damit absichtlich wiederholbar. Sobald echte Daten drin sind, keine neue Version dieser Datei pushen, sondern eine zusätzliche Migration schreiben.

### GitHub Pages
Repo anlegen, Ordner pushen, unter Settings → Pages als Quelle „GitHub Actions“ wählen. Der Workflow im Ordner `.github/workflows` veröffentlicht bei jedem Push auf `main`.

### Lokal in VS Code
`index.html` braucht keinen Build. Zum Testen reicht die Erweiterung „Live Server“ oder `npx serve`. Für GPS-Tests am Handy brauchst du HTTPS, also entweder die veröffentlichte Seite oder einen Tunnel.

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
