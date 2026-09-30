# Gruppenselfie an jeder Station: Spezifikation

Stand 30.09.2026. Freigegeben im Gespräch, Mockup: `mockups/gruppenselfie.html`.

## Entscheidungen

| Frage | Entscheidung |
|---|---|
| Zweck | fester Schritt an jeder Station und Galerie am Ende; geprüft wird nur im Streitfall |
| Zeitpunkt | nach der richtigen Antwort, das Foto schaltet die Ziffer frei |
| Sichtbar für | das eigene Team (Leitung, Mitglieder, Mitlesende) und die Spielleitung |
| Danach | bleibt einige Wochen abrufbar, Löschung zu einem festen Datum |
| Speicherort | Datenbank, Zugriff über die bestehenden Zugänge (Weg A) |

## Grundsatz: abschaltbar, und aus heißt unverändert

`game_state.selfie_on` (Standard `false`). Solange der Schalter aus ist, verhält
sich das Spiel genau wie vor diesem Nachtrag. Die Spielleitung schaltet im
neuen Reiter „Fotos“.

## Ablauf

1. `submit_answer` wertet wie bisher: `progress.solved_at` wird gesetzt, die
   Zeitmessung und die Rangliste ändern sich nicht.
2. Neu ist `progress.selfie_at`. Bei eingeschaltetem Selfie liefert
   `team_state` die Ziffer einer Station erst, wenn `selfie_at` gesetzt ist, und
   meldet die niedrigste gelöste Station ohne `selfie_at` als
   `selfie.pending`. Die sechste Ziffer gibt es erst, wenn nichts mehr offen ist.
3. Solange `selfie.pending` gesetzt ist, zeigt das Handy der Teamleitung statt
   der nächsten Station den Selfie-Schritt: aufnehmen (Frontkamera), Vorschau,
   „Das nehmen wir“ oder „Noch mal“.
4. `team_selfie` speichert das Foto und setzt `selfie_at`. Die Ziffer erscheint.
5. Kommt das Foto nicht durch: „Erneut senden“ oder „Ohne Hochladen weiter“
   (`team_selfie_skip` setzt nur `selfie_at`). Das Foto bleibt auf dem Handy
   (`localStorage`, `sj.foto.<position>`) und wird beim nächsten Abruf
   nachgereicht.
6. Ersetzen: erlaubt, solange das Team an der nächsten Station noch nicht
   eingecheckt hat. Nachreichen, wenn noch kein Foto da ist: immer.

Mitglieder und Mitlesende sehen während des Wartens „Richtig gelöst! Jetzt alle
zur Teamleitung fürs Gruppenselfie.“ und immer das Album.

## Daten

```
progress.selfie_at timestamptz
game_state.selfie_on boolean default false
game_state.photos_delete_on date
station_photos(team_id, station_id, photo bytea, thumb bytea, taken_at)
  primary key (team_id, station_id)
  foreign key (team_id, station_id) references progress on delete cascade
```

Der Fremdschlüssel auf `progress` sorgt dafür, dass Zurücksetzen, neues Auslosen
und Leeren der Anmeldung die Fotos mitnehmen, ohne dass diese Funktionen
angefasst werden. RLS an, keine Rechte für anon.

Das Handy verkleinert vor dem Senden: Foto längste Kante 1280 px, JPEG, Ziel
unter 300 KB; Vorschau 320 px. Der Server nimmt nur JPEG (Magic Bytes), Foto bis
700 KB, Vorschau bis 60 KB.

## Funktionen

| Funktion | Zugang | Aufgabe |
|---|---|---|
| `team_selfie(p_code, p_position, p_photo, p_thumb)` | Team-Code | Foto speichern oder ersetzen, `selfie_at` setzen, gibt `team_state` |
| `team_selfie_skip(p_code, p_position)` | Team-Code | `selfie_at` ohne Foto setzen |
| `team_photo(p_code, p_token, p_read_token, p_position, p_full)` | einer der drei Team-Zugänge | Foto oder Vorschau als `{ data: Base64 }` (die App nimmt von `rpc()` nur JSON-Objekte an) |
| `admin_photos(p_pin)` | PIN | Liste aller Fotos (Team, Station, Zeit) |
| `admin_photo(p_pin, p_team, p_position, p_full)` | PIN | ein Foto |
| `admin_set_selfie(p_pin, p_on, p_delete_on)` | PIN | Schalter und Löschdatum |
| `admin_delete_photos(p_pin)` | PIN | alle Fotos löschen |

Geändert werden nur `team_state` (Ziffern-Regel, Feld `selfie`), `public_state`
(Feld `selfieOn` für den Hinweis bei der Anmeldung) und `admin_state` (Felder
`selfieOn`, `photosDeleteOn`, `photoCount`). Fällige Fotos löscht `team_state`
und `admin_state` beim Abruf: ist `photos_delete_on` erreicht, sind sie weg.

## Oberfläche

- **Teamleitung:** Selfie-Schritt wie im Mockup, darunter „Eure Ziffern“ und
  „Euer Album“ (fünf Kacheln, Tipp zeigt groß, „Foto speichern“; bei der
  jüngsten Station „Neu aufnehmen“, solange erlaubt).
- **Mitglieder, Mitlesende:** Hinweis und Album.
- **Spielleitung, Reiter „Fotos“:** Schalter, Löschdatum, Galerie je Team,
  „Alle herunterladen“ (ZIP, im Browser gebaut, ohne Bibliothek), „Fotos
  löschen“.
- **Anmeldung:** bei eingeschaltetem Selfie ein Satz, wer die Fotos sieht und
  wann sie gelöscht werden.

## Prüfen

- Datenbank: Probelauf der Migration mit Prüfungen in einer Transaktion, die am
  Ende zurückgerollt wird (`tools/sql.py`), erst danach das echte Einspielen.
- Oberfläche: Prüfstand (`mock.js`) um die neuen RPCs und Szenarien erweitern,
  fotografieren. Echte Kamera: Friedrich auf Android und iPhone.

## Nicht enthalten

Prüfung, ob wirklich alle auf dem Foto sind; Fotos teamübergreifend zeigen;
Änderung an Zeitmessung oder Rangliste.
