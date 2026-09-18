# Stadtjagd: Spiel und Code

Referenz für alle, die am Code arbeiten. Beschreibt, wie das Spiel funktioniert,
welche Zustände und Abläufe es gibt und wo das im Code steht. Den Verlauf der
Entscheidungen und die Betriebsnotizen (Zugänge, Umgebung, Historie) enthält
`HANDOFF.md`.

Stand: 18.09.2026, Nachträge 1 bis 13.

---

## 1. Das Spiel in einem Absatz

Rund 90 Leute der TSE-Teamfahrt melden sich per Link an und werden in Teams
ausgelost. Alle Teams laufen dieselbe Route mit fünf Stationen in Prag. An jeder
Station checkt die Teamleitung per GPS ein, bekommt ein Rätsel und nach der
richtigen Antwort eine Ziffer. Die sechste Ziffer ist die Einerstelle der Summe
der fünf. Mit den sechs Ziffern öffnet man am Ziel einen Koffer. Es gibt drei
Koffer mit absteigendem Preisgeld, alle mit demselben Code; welches Team welchen
Koffer bekommt, entscheidet die Reihenfolge, in der die Teams den Code in der
App eingeben.

---

## 2. Rollen

| Rolle | Zugang | Kann | Sieht |
|---|---|---|---|
| **Teilnehmende** | Link, Name bei der Anmeldung | sich anmelden (nur bis zum Auslosen), Team nachschauen | eigenes Team groß mit Emoji; ab dem Start alles, was die Teamleitung sieht (nur wer auf diesem Handy angemeldet ist) |
| **Teamleitung** | Team-Code (`FUCHS-4711`) unter `#/team` | einchecken, Rätsel beantworten, Koffer-Code eingeben | Station, Kompass, Rätsel, Ziffern, Platz |
| **Spielleitung** | Admin-PIN unter `#/admin` | auslosen, starten, beenden, freischalten, Stationen pflegen, Leute eintragen, löschen, Testmodus | Karte mit Routen, Zeitachse, alle Teams mit Codes, Koffer-Code |

Die Teamleitung wird beim Auslosen je Team zufällig bestimmt
(`teams.leader_participant_id`). Den Team-Code gibt die Spielleitung ihr
persönlich.

---

## 3. Spielzustände

`game_state.status`, eine einzige Zeile (`id = 1`):

```
registration ──admin_draw──▶ drawn ──admin_start──▶ running ──admin_finish──▶ finished
      ▲                        │  ▲                    │  ▲                     │
      │                        │  │                    │  └────admin_resume─────┤
      │                        │  └────admin_reset─────┴────────────────────────┘
      └──admin_clear_participants (von überall)
```

`admin_start` geht nur aus `drawn` und nur mit Testmodus aus. `admin_resume`
(Nachtrag 13) holt ein versehentlich beendetes Spiel zurück, ohne etwas zu
löschen.

| Zustand | Was gilt |
|---|---|
| `registration` | Selbstanmeldung offen. Keine Teams. |
| `drawn` | Teams und Codes stehen. Selbstanmeldung zu (Nachtrag 12), Nachzügler nur über die Spielleitung. Neu auslosen möglich (fragt nach). |
| `running` | Check-in, Antworten, Koffer-Code gehen. Teamleitungen melden ihre Position. Auslosen gesperrt. |
| `finished` | Keine Eingaben mehr, keine Positionen. Rangliste öffentlich. Routen bleiben bis zum Löschen. |

Zusätzliche Schalter in `game_state`: `test_mode` (siehe 9.), `prize_count`
(Zahl der Koffer, Vorgabe 3), `winner_team_id` (Platz 1, für Altes),
`admin_pin`.

---

## 4. Spielregeln im Detail

### Check-in (`check_in`)
- Nur `running`, nur die aktuelle Station (`current_station`: erste ungelöste
  in `position`-Reihenfolge).
- Braucht Koordinaten (Nachtrag 7 schloss die Lücke „null-Koordinaten gehen
  durch“). Nur im Testmodus geht es ohne Koordinaten und ohne Abstand.
- Erlaubt, wenn Abstand ≤ `stations.radius_m` + `min(GPS-Genauigkeit, 25 m)`.
  Radius Vorgabe 50 m, Rudolfstollen 60 m.
- Die App holt dafür eine frische Position (`freshPosition`).
- Danach ist das Rätsel frei (`team_state.station.riddle`).

### Rätsel (`submit_answer`)
- Vergleich über `norm()`: klein, Umlaute und Sonderzeichen vereinheitlicht
  (auch Großbuchstaben mit Umlaut, unabhängig von der Locale).
- Mehrere Lösungen mit `|` getrennt (`5|fünf`), geprüft von `answer_ok`.
  Leere Lösung oder leere Teile zählen nie als richtig (Platzhalter).
- Klemmt ein Rätsel, wertet die Spielleitung die Station für das Team
  (`admin_solve_station`: Check-in und gelöst in einem).
- Richtig: `progress.solved_at`, Ziffer frei.
- Falsch: `failed_attempts` +1; beim dritten Fehlversuch 2 Minuten Sperre
  (`locked_until`), Zähler zurück auf 0. Die App zeigt einen Countdown und
  sperrt Feld und Knopf.

### Ziffern und Koffer-Code
- Jede Station hat `digit` (0 bis 9). Die sechste Ziffer ist
  `sum(digit) % 10`. Der Code ist für alle Teams gleich.
- `team_state.digits` liefert nur gelöste Ziffern, `finalDigit` erst, wenn
  alle fünf gelöst sind.

### Plätze (`submit_final`, Nachtrag 6)
- Nur `running`, nur mit allen Ziffern, nur am Koffer, nur mit richtigem Code.
- Am Koffer heißt (Nachtrag 13): Position im Radius der letzten Station plus
  GPS-Toleranz wie beim Check-in, im Testmodus nicht geprüft. Die App holt eine
  frische Position. Sonst könnte ein Team mit Ziffern aus einer Nachricht von
  überall einen Platz holen.
- Verglichen werden nur die Ziffern der Eingabe, alles andere (Leerzeichen,
  Bindestriche) fällt weg.
- Vergibt den nächsten Platz in `finishes`. Gleichzeitige Eingaben laufen
  nacheinander (`select … for update` auf `game_state`), `finishes.place` ist
  zusätzlich `unique`.
- Wer schon einen Platz hat, behält ihn (auch bei erneuter Eingabe).
- Platz ≤ `prize_count`: Koffer. Danach „im Ziel“ ohne Koffer. Das Spiel läuft
  weiter, bis die Spielleitung beendet.

### Positionen (`report_position`)
- Nur die Teamleitung, nur `running`.
- Die App sendet, wenn sich die Position um mehr als 20 m geändert hat oder die
  letzte Meldung älter als 60 s ist (`maybeReport`).
- Verworfen werden (App und Datenbank): fehlende Werte, 0/0, Genauigkeit ≤ 0
  oder > 1000 m. Die Admin-Karte ignoriert zusätzlich Punkte über 30 km von der
  ersten Station.
- `team_positions` hält den letzten Punkt, `position_log` die Route.

---

## 5. Abläufe

### 5.1 Anmeldung (`registration`)
1. `#/public`, Name eintragen → `register_participant`.
2. Antwort enthält `token` (64 Hex-Zeichen, Nachtrag 11). Die App speichert
   `sj.name` und `sj.token` im `localStorage`.
3. Doppelte Namen (über `name_key = norm(name)`) werden abgelehnt.
4. Die Spielleitung kann zusätzlich einzeln (`admin_add_participant`) oder
   viele auf einmal (`admin_add_participants`, eine Zeile pro Name, auch
   „Testdaten einfügen“ mit 90 Namen „… (Test)“) eintragen. Diese haben keinen
   Token. „Testdaten entfernen“ (`admin_delete_test_participants`) löscht nur
   die Namen mit „(Test)“.
5. Umbenennen (`admin_rename_participant`) folgt denselben Regeln wie die
   Anmeldung. Das Handy der Person übernimmt den neuen Namen über den Token
   (`namenUebernehmen`), statt sich abzumelden.

### 5.2 Auslosen (`admin_draw(p_pin, p_teams, p_size)`)
- Entweder Personen pro Team oder Anzahl Teams, höchstens 16 Teams (so viele
  Tiernamen). Vorschau im Admin (`drawPreview`).
- Löscht bestehende Teams, legt neue mit Tiernamen und Codes an, verteilt
  zufällig, wählt je Team eine Leitung. Status → `drawn`.
- Die Tiernamen stehen in `admin_draw` (Datenbank) und als Emoji in
  `TEAM_EMOJI` (`index.html`); beide Listen müssen passen.
- Die Handys der Angemeldeten zeigen nach der nächsten Abfrage (≤ 10 s) die
  große Team-Karte (`eigenesTeam`, `teamNachziehen`). Neu auslosen zieht das
  Team auf allen Handys nach; alte Team-Codes melden sich ab (`codeUngueltig`).

### 5.3 Vor dem Start (`drawn`)
- Teilnehmende: Team-Karte mit Emoji in Teamfarbe, „Zum Hochhalten“ (oder
  Emoji antippen) als Vollbild, Mitglieder, Teamleitung.
- Teamleitung und Mitglieder mit Token: „Schon mal vorbereiten“, also
  Standort und Kompass freigeben, Kompass einmessen, Übungsziel TSE AG Berlin
  (`PROBEZIEL`).
- Nachzügler: nur über die Spielleitung (Hilfe-Knöpfe auf der Anmeldeseite).

### 5.4 Spiel (`running`)
- Teamleitung (`#/team`): Station, Ortshinweis, Kompass und Entfernung,
  „Wir sind da“, danach Rätsel mit Eingabe, kleine Ziffern-Räder darunter
  (Variante B, siehe `mockups/team-reihenfolge.html`).
- Mitglieder mit Token (`#/public`): dieselbe Ansicht aus `member_state`, ohne
  Eingaben („Einchecken macht Silke“, „Die Antwort gibt Silke ein“).
  Kompass und Entfernung mit dem eigenen GPS, keine Positionsmeldung.
- Öffentliche Seite: „Zieleinlauf“ live, sobald das erste Team im Ziel ist.
- Spielleitung: Karte mit Routen, Zeitachse, Teams nach Platz und Fortschritt,
  „Freischalten“ ersetzt einen Check-in (`admin_unlock_station`), „Rätsel
  werten“ zählt die Station als gelöst (`admin_solve_station`, fragt nach).

### 5.5 Ziel
- Alle fünf Ziffern: großes Zahlenschloss, Koffer-Hinweis (Ortshinweis der
  Station 5), Code-Eingabe nur bei der Teamleitung und nur am Koffer (die
  Meldung nennt sonst die Restentfernung).
- Nach richtigem Code: Platz-Bildschirm mit Medaille (1 bis 3) oder 🏁, auf
  allen Handys des Teams. Die Aufsicht am Koffer gibt nach Platz frei.

### 5.6 Ende (`finished`)
- `admin_finish` (fragt nach). Rangliste öffentlich; Teams ohne Platz nach
  gelösten Stationen. Zu früh gedrückt: „Spiel fortsetzen“ (`admin_resume`).
- Danach: Routen auswerten, „Standortdaten löschen“ (`admin_clear_positions`).

---

## 6. Wer sieht was (Sichtbarkeit)

| Daten | öffentlich (`public_state`) | Mitglied mit Token (`member_state`) | Teamleitung (`team_state`) | Spielleitung (`admin_state`) |
|---|---|---|---|---|
| Teams, Mitglieder, Teamleitung | ja | eigenes | eigenes | alle |
| Team-Code | nein | **nein** | eigener | alle |
| Station, Ortshinweis, Koordinaten | nein | eigene | eigene | alle |
| Rätsel | nein | nach Check-in | nach Check-in | alle |
| Lösung | nein | nein | nein | alle |
| Ziffern | nein | gelöste | gelöste | alle, plus Koffer-Code |
| Platz | ja (Rangliste) | eigener | eigener | alle |
| Positionen, Routen | nein | nein | nein | alle |
| Geräte-Token | nein | nein | nein | nein |

Lösungen, Ziffern und Koffer-Code verlassen die Datenbank nur für die
Spielleitung. Eingaben (`check_in`, `submit_answer`, `submit_final`) gehen nur
mit dem Team-Code.

---

## 7. Sicherheitsmodell

- Alle Tabellen: RLS an, **keine** Policies, `revoke all … from anon`. Kein
  direkter Tabellenzugriff.
- Alles läuft über `security definer`-Funktionen, `anon` hat nur
  Ausführungsrecht. Hilfsfunktionen (`norm`, `dist_m`, `team_by_code`,
  `current_station`, `require_admin`) sind für `anon` gesperrt.
- Admin-Funktionen prüfen die PIN serverseitig (`require_admin`).
- Team-Codes: Tiername plus vier Ziffern. `team_by_code` vergleicht nur
  Buchstaben und Ziffern (`EULE 8765` = `eule-8765`).
- Mitlesen nur mit Geräte-Token aus der eigenen Anmeldung, nie über den Namen:
  Namen sind öffentlich, und alle Teams haben dieselben Rätsel und Ziffern.
- Selbstanmeldung nur bis zum Auslosen, sonst bekäme ein erfundener Name
  mitten im Spiel Einblick in ein fremdes Team.
- Supabase lädt `pg-safeupdate`: **jedes** `UPDATE`/`DELETE` braucht ein
  `WHERE` (für alle Zeilen `where true`), auch in Funktionen.

Bewusst akzeptiert oder offen:
- GPS lässt sich mit Entwicklerwerkzeugen fälschen.
- Wer einen Team-Code kennt, spielt für dieses Team.
- Vor dem Auslosen kann jemand einen erfundenen Namen zusätzlich anmelden
  (Abhilfe: Zahl mit der Gästeliste abgleichen, steht im Admin beim Auslosen).
- Mitglieder können Ziffern an andere Teams weitergeben (nicht technisch zu
  verhindern). Seit Nachtrag 13 bringt das nur noch den Weg ab, nicht den
  Platz: den Code muss man am Koffer eingeben.
- Admin-PIN im Klartext in `game_state.admin_pin`, ohne Bremse gegen
  Durchprobieren. Die Vorgabe `2026` steht im öffentlichen Repo: live eine
  lange PIN setzen.
- Team-Codes (16 Tiere × 9000 Zahlen) lassen sich mit vielen Anfragen raten;
  unter Kollegen hingenommen.
- **Offen und vor dem Event zu lösen:** Das Repo ist öffentlich, und GitHub
  Pages liefert es zusätzlich komplett aus (`path: .` in
  `.github/workflows/pages.yml`). Damit sind `supabase/seed-stationen-prag.sql`
  mit den Ziffern (und später Lösungen, falls sie dort landen) für alle
  lesbar, auch unter `…/Stadtjagt/supabase/seed-stationen-prag.sql`. Abhilfe:
  echte Ziffern, Lösungen und Ortshinweise nur in der Datenbank pflegen
  (Reiter Stationen), nie im Repo; Pages nur die Dateien ausliefern lassen,
  die die App braucht. Die bisherigen Ziffern stehen in der Git-Historie und
  sind damit verbrannt: vor dem Event neue setzen.

---

## 8. Code-Aufbau

### Dateien
```
index.html                 die ganze App (HTML, CSS, JS), kein Build
config.js                  Supabase-URL, Publishable key, Hilfe-Nummer (support.phone)
kompass-test.html          Diagnoseseite für den Kompass einzelner Geräte
supabase/migrations/*.sql  Schema und Spiellogik, in Dateinamen-Reihenfolge
supabase/seed-*.sql        Stationen der Prager Route, 100 Testpersonen
tools/sql.py               SQL über die Supabase Management-API ausführen
tools/hintergrund/         Generator für die Hintergrund-Varianten (offen)
mockups/                   Entwürfe (Kompass einmessen, Reihenfolge, Hintergrund, Routen)
```

### Frontend (`index.html`)
- **Zustand:** ein Objekt `S` (`S.view`, `S.pub`, `S.team`, `S.admin`,
  `S.gps`, `S.mit`, `S.lookup`, …). `render()` baut `#app` komplett per
  `innerHTML` neu.
- **Ansichten:** `viewPublic`, `viewTeam` → `teamAnsicht(st, lesen)`,
  `viewAdmin` (Reiter Karte, Teams, Teilnehmende, Stationen, Daten löschen),
  `viewSetup` (ohne `config.js`). Routing über den Hash (`#/public`, `#/team`,
  `#/admin`).
- **Aktionen:** Klicks auf `[data-act]` rufen `ACT[name](dataset)`. Wirft eine
  Aktion oder setzt sie `S.msg` vom Typ `err`, bleiben die Eingaben stehen
  (Klick-Handler). `return false` heißt: nicht neu zeichnen.
- **Meldungen:** `S.msg = { type, text, ort? }`; `msgBox(ort)` zeigt sie,
  Erfolgsmeldungen verschwinden nach 12 s.
- **Datenbank:** `rpc(fn, args)` → `POST /rest/v1/rpc/<fn>`.
- **Abfragen:** alle 10 s je nach Ansicht `public_state` (+ `member_state`),
  `team_state` oder `admin_state` (+ `admin_tracks` auf der Karte). Nicht,
  solange ein Eingabefeld den Fokus hat, die Seite verdeckt ist oder die
  Vollbild-Ansicht zum Hochhalten offen ist (außer das Team hat sich geändert).
  Ein zweites Intervall (1 s) zählt die Denkpause herunter.
- **Löschen:** alles über die Liste `DANGER` und einen Dialog, meist mit
  getipptem Wort `LÖSCHEN`; `wort: false` für Person und Spielende.
- **Speicher im Browser:** `sj.name`, `sj.token`, `sj.code` (Teamleitung),
  `sj.kal` (Einmessen heute erledigt), `sj.url`/`sj.key` (nur ohne
  `config.js`) im `localStorage`; `sj.pin` im `sessionStorage`.

### GPS und Kompass
- `startGps` (Standort beobachten, Kompass-Erlaubnis auf iOS aus einem Klick),
  `addOrient` (Ereignisse `deviceorientationabsolute` bzw. `deviceorientation`
  mit `webkitCompassHeading`), `liveUpdate` (Entfernung, Nadel).
- `S.gps.kompass`: `unbekannt`, `wartet`, `an`, `kalibrieren`, `relativ`,
  `abgelehnt`, `fehlt`. Ohne Ereignis nach 3 s: `fehlt`.
- `KOMPASS_GRENZE` 25°: darüber gilt der iOS-Kompass als ungenau, `richtung()`
  nimmt dann die Laufrichtung aus zwei GPS-Punkten (> 6 m).
- Einmessen: `KAL_*`-Konstanten; einmal pro Handy und Tag, überspringbar.
- `aktuellesZiel()`: Station, vor dem Start `PROBEZIEL` (TSE AG Berlin).
  `aktiverStand()` liefert `S.team.state` (Teamleitung) oder `S.mit` (Mitglied).
- Ohne Richtung zeigt der Kompass ein Fragezeichen statt eines Pfeils.

### Datenbank
Tabellen: `participants` (Name, `name_key`, `team_id`, `token`), `teams`
(Name, Code, Leitung), `stations` (Position, Name, Koordinaten, Radius,
Ortshinweis, Rätsel, Lösung, Ziffer), `progress` (je Team und Station:
Check-in, gelöst, Fehlversuche, Sperre), `finishes` (Platz), `team_positions`,
`position_log`, `game_state`.

Endpunkte:
- öffentlich: `public_state`, `register_participant`, `lookup_participant`
  (auch Namensteile, bis zu acht Vorschläge), `member_state`
- Teamleitung: `team_state`, `check_in`, `submit_answer`, `submit_final`,
  `report_position`
- Spielleitung: `admin_state`, `admin_tracks`, `admin_draw`, `admin_start`,
  `admin_finish`, `admin_resume`, `admin_reset`, `admin_clear_positions`,
  `admin_clear_participants`, `admin_add_participant`,
  `admin_add_participants`, `admin_delete_test_participants`,
  `admin_rename_participant`, `admin_delete_participant`,
  `admin_save_station`, `admin_unlock_station`, `admin_solve_station`,
  `admin_set_pin`, `admin_set_test_mode`
- intern (für `anon` gesperrt): `norm`, `answer_ok`, `dist_m`, `team_by_code`,
  `current_station`, `require_admin`

Neue Funktionen immer mit `create or replace`, Rechte mit `grant execute … to
anon, authenticated`, am Ende `notify pgrst, 'reload schema';`.

---

## 9. Arbeiten am Code

### Änderungen an der Datenbank
- **Nie die Init-Migration erneut ausführen** (beginnt mit `drop table …
  cascade`). Jede Änderung ist ein neuer Nachtrag in `supabase/migrations/`,
  mehrfach ausführbar, ohne Datenverlust.
- Wird eine bestehende Funktion geändert, die neueste Fassung als Vorlage
  nehmen (manche wurden mehrfach ersetzt, z. B. `team_state` zuletzt in
  Nachtrag 7, `register_participant` in Nachtrag 12).
- Einspielen: `python tools/sql.py supabase/migrations/<datei>.sql`. Token in
  `%USERPROFILE%\.supabase\stadtjagt.token`. Das Skript bremst zerstörerische
  Anweisungen außerhalb von Funktionskörpern.
- Reihenfolge beim Ausliefern: erst die Datenbank, dann die App.

### Testmodus und Testdaten
- `admin_set_test_mode` (Reiter Stationen): Check-in und Koffer-Code ohne
  Entfernung, jede Antwort zählt, keine Denkpause; der Koffer-Code selbst wird
  weiter geprüft. Rotes „Testmodus an“ in Admin und Team-Ansicht.
  „Spiel starten“ verweigert, solange er an ist.
- „Testdaten einfügen“ im Reiter Teilnehmende: 90 Namen mit „(Test)“;
  „Testdaten entfernen“ nimmt genau die wieder raus.

### Lokal testen
Bisher genutzt, liegt noch nicht im Repo:
- portables PostgreSQL 15 (ZIP von EnterpriseDB, kein Admin nötig) mit allen
  Migrationen und Seeds, Rollen `anon` und `authenticated` angelegt;
- eine kleine Brücke in Python, die `index.html` ausliefert, `config.js` auf
  sich selbst umbiegt und `POST /rest/v1/rpc/<fn>` an `psql` weiterreicht;
- Testskripte je Nachtrag (Koffer, Testmodus, Durchsicht, Mitlesen), unter
  anderem mit gleichzeitigen `submit_final`-Aufrufen;
- Oberfläche mit Chrome DevTools, GPS und Kompass per nachgebauten Ereignissen.

Syntaxprüfung der App mit Node (auf dem Privatrechner vorhanden):
```
node -e 'const h=require("fs").readFileSync("index.html","utf8");[...h.matchAll(/<script(?![^>]*src)[^>]*>([\s\S]*?)<\/script>/g)].forEach(m=>new Function(m[1]));console.log("ok")'
```

### Regeln für Texte in der Oberfläche
- Echte Umlaute, keine Gedankenstriche (– —) in sichtbaren Texten.
- Teilnehmende werden mit Vornamen angesprochen (`vorname()`), Listen zeigen den
  vollen Namen.
- Kennungen wie Team-Codes, Uhrzeiten, Koordinaten brechen nicht um
  (`white-space: nowrap`).
- Tippziele mindestens 42 px.

---

## 10. Offene Punkte (Stand 18.09.2026)

- Rätsel, Lösungen und Ortshinweise der fünf Stationen fehlen (Platzhalter).
- Öffentliche Auslieferung des ganzen Repos (siehe 7.), neuer Koffer-Code.
- Echte Nummer für die Hilfe-Knöpfe statt `491720000000`.
- Mitlesen nur auf dem Gerät der Anmeldung: Nachzügler aus dem Admin, wer sich
  am Rechner angemeldet hat oder die Seite in einem anderen Browser öffnet,
  liest nicht mit (Idee: Mitlese-QR oder -Link von der Teamleitung mit einem
  Lese-Token je Team).
- Live-PIN prüfen und verlängern (siehe 7.).
- Hintergrund-Variante wählen (`mockups/hintergrund-varianten.html`).
- Testumgebung und Testskripte ins Repo übernehmen.
- Probelauf draußen mit echten Handys.
