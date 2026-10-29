# Stadtjagd: Spiel und Code

Referenz für alle, die am Code arbeiten. Beschreibt, wie das Spiel funktioniert,
welche Zustände und Abläufe es gibt und wo das im Code steht. Den Verlauf der
Entscheidungen und die Betriebsnotizen (Zugänge, Umgebung, Historie) enthält
`HANDOFF.md`.

Stand: 05.10.2026, Nachträge 1 bis 32. Die Abschnitte 1 bis 10 beschreiben den Stand bis Nachtrag 22,
ergänzt um Regeln, die sich seitdem geändert haben; was seitdem dazukam, steht geschlossen in den
Abschnitten 11 bis 13.

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
| **Teilnehmende** | Link, Name bei der Anmeldung | sich anmelden (nur bis zum Auslosen), Team nachschauen | eigenes Team groß mit Emoji; ab dem Start alles, was die Teamleitung sieht (Geräte-Schlüssel aus der Anmeldung) |
| **Teamleitung** | `#/team`: automatisch auf dem Handy, mit dem sie sich angemeldet hat (Geräte-Schlüssel); Team-Code nur als Ausweg für die Spielleitung am Tablet | einchecken, Rätsel beantworten, Koffer-Code eingeben, Leitung abgeben | Station, Kompass, Rätsel, Ziffern, Platz |
| **Spielleitung** | Admin-PIN unter `#/admin` | auslosen, starten, beenden, fortsetzen, freischalten, Rätsel werten, Teamleitung wählen, Stationen pflegen, Leute eintragen, löschen, Testmodus | Reiter Karte und Teams (Karte, Teamliste mit "Braucht dich", Zuletzt), Zeitachse, Codes und Mitlese-Links, Koffer-Code |

Die Teamleitung wird beim Auslosen je Team zufällig bestimmt
(`teams.leader_participant_id`), und zwar unter den Personen mit Geräte-Schlüssel
(Token); wer nur eingetragen wurde, hat kein Handy für die Rolle. Dasselbe gilt
für die Nachfolge, wenn die Leitung gelöscht wird. Die Teamleitung kann
(`team_set_leader`) nur an selbst Angemeldete abgeben, die Spielleitung
(`admin_set_leader`) an jede Person im Team (Notweg).
Seit Nachtrag 22 meldet sich jede Person nur selbst an, auf dem eigenen Handy
(„Jemanden ohne eigenes Handy anmelden“ gibt es nicht mehr). Die Teamleitung
tippt keinen Code: ihr Handy holt ihn über `leader_code`. Wird die Leitung
gewechselt oder abgegeben, gibt das alte Handy sofort nichts mehr ein
(`leitungNochDa` nach jedem Abruf). Den Team-Code braucht nur noch die
Spielleitung, wenn sie am Tablet für ein Team eingibt. Dieser Notweg setzt den
Merker `sj.hand`: `leitungNochDa` meldet das Gerät dann nicht ab, weil der Code
nicht aus dem Geräte-Schlüssel stammt. Tippt die Teamleitung ihren eigenen Code
(`leaderName` gleich `S.myName` im geladenen Teamstand), bleibt der Merker weg:
wechselt die Leitung, meldet sich das Handy ab wie sonst. `leitungOhneCode`, Abmelden und
`codeUngueltig` löschen den Merker. Team-Codes haben vier oder sechs Ziffern
(Beispiel `FUCHS-123456`, siehe §7).

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

`admin_start` geht nur aus `drawn`; bei eingeschaltetem Testmodus warnt es
(Nachtrag 16, vorher verweigerte es). `admin_resume`
(Nachtrag 13) holt ein versehentlich beendetes Spiel zurück, ohne etwas zu
löschen.

| Zustand | Was gilt |
|---|---|
| `registration` | Selbstanmeldung offen. Keine Teams. |
| `drawn` | Teams und Codes stehen. Selbstanmeldung zu (Nachtrag 12), Nachzügler nur über die Spielleitung. Neu auslosen möglich (fragt nach). |
| `running` | Check-in, Antworten, Koffer-Code gehen. Teamleitungen melden ihre Position. Auslosen gesperrt. |
| `finished` | Keine Eingaben mehr, keine Positionen. Rangliste öffentlich. Routen bleiben bis zum Löschen. |

Zusätzliche Schalter in `game_state`: `test_mode` (siehe 9.), `prize_count`
(Zahl der Koffer, Vorgabe 3), `duration_min` (Spieldauer, Vorgabe 180; nur
Countdown, keine Sperre), `case_hint` (Text auf dem Koffer-Bildschirm),
`winner_team_id` (Platz 1, für Altes), `admin_pin`, `background`
(`klassisch`, `a`, `b`, `c`; in allen drei Zustandsfunktionen enthalten,
`admin_set_background`). `duration_min` und `case_hint` setzt
`admin_set_settings`.

---

## 4. Spielregeln im Detail

### Check-in (`check_in`)
- Nur `running`, nur die aktuelle Station (`current_station`: erste ungelöste
  in `position`-Reihenfolge).
- Braucht Koordinaten (Nachtrag 7 schloss die Lücke „null-Koordinaten gehen
  durch“). Nur im Testmodus geht es ohne Koordinaten und ohne Abstand.
- Erlaubt, wenn Abstand ≤ `stations.radius_m` + `min(GPS-Genauigkeit, 25 m)`.
  Radius Vorgabe 50 m, Rudolfstollen 60 m.
- Die App holt dafür eine frische Position (`freshPosition`). Sie nennt vorab
  keine Mindestentfernung; der Text "Einchecken ab etwa N m" ist gestrichen.
- Danach ist das Rätsel frei (`team_state.station.riddle`).

### Rätsel (`submit_answer`)
- Vergleich über `norm()`: klein, Umlaute und Sonderzeichen vereinheitlicht
  (auch Großbuchstaben mit Umlaut, unabhängig von der Locale). Seit
  Nachtrag 20 fallen auch Akzente und Háčeks auf den Grundbuchstaben:
  „Křižík“ und „Krizik“ sind dieselbe Antwort.
- Mehrere Lösungen mit `|` getrennt (`5|fünf`), geprüft von `answer_ok`.
  Leere Lösung oder leere Teile zählen nie als richtig (Platzhalter).
- Klemmt ein Rätsel, wertet die Spielleitung die Station für das Team
  (`admin_solve_station`: Check-in und gelöst in einem). Der Knopf schickt die
  Station mit (`p_position`); ist das Team schon weiter, wertet der Server
  nichts (Nachtrag 20).
- Richtig: `progress.solved_at`, Ziffer frei.
- Leer (nach `norm()` nichts übrig): außerhalb des Testmodus kein Fehlversuch,
  „Bitte gebt eine Antwort ein.“ (Nachtrag 32). Im Testmodus zählt jede
  Antwort als richtig, auch ein leeres Feld.
- Falsch: `failed_attempts` +1; beim dritten Fehlversuch 2 Minuten Sperre
  (`locked_until`), Zähler zurück auf 0, `pauses` +1. Die App zeigt einen
  Countdown und sperrt Feld und Knopf.
- Tipp (`stations.tip`, optional): nach der ersten Pause kann die Teamleitung
  ihn aufdecken (`reveal_tip` setzt `progress.tip_at`), danach steht er für
  alle im Team in `station.tip`; vorher nur `station.tipAvailable`.

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
- Seit Nachtrag 30 geht das Urteil des Kompass-Wächters mit (`p_kompass`:
  `ok` / `unzuverlaessig`, sonst null), bei einem Wechsel des Urteils sofort.
  Die App schickt immer nur eine Meldung zur Zeit und wiederholt ohne
  `p_kompass` nur bei PGRST202 (Datenbank ohne Nachtrag 30).

---

## 5. Abläufe

### 5.1 Anmeldung (`registration`)
1. `#/public`, Name eintragen → `register_participant`.
2. Antwort enthält `token` (64 Hex-Zeichen, Nachtrag 11). Die App speichert
   `sj.name` und `sj.token` im `localStorage`. Seit Nachtrag 32 erzeugt die App
   den Token selbst, legt ihn vor dem Aufruf ab und schickt ihn als `p_token`
   mit; kennt der Server den Token schon, gibt er die vorhandene Anmeldung
   zurück (Antwort im Funkloch verloren, auch nach Umbenennen). Für einen
   vorhandenen Namen gibt es nie einen neuen Token.
3. Doppelte Namen (über `name_key = norm(name)`) werden abgelehnt (Meldung
   "Diesen Namen gibt es schon. Warst du das selbst, bist du schon dabei. Sonst
   ergänze etwas, zum Beispiel einen zweiten Vornamen."; sie deckt beide Fälle:
   jemand öffnet den Link ein zweites Mal oder steht schon auf der Liste der
   Spielleitung, oder zwei Personen heißen gleich; die App wertet den Text nicht
   aus), ebenso
   Namen ohne einen lateinischen Buchstaben oder eine Ziffer (leerer
   Schlüssel, Nachtrag 20). Die Anmeldung wartet mit `for share` auf ein
   laufendes Auslosen, das Auslosen sperrt `game_state` mit `for update`.
   Ab 200 Personen ist die Selbstanmeldung voll ("Die Anmeldung ist voll. Melde
   dich bei der Spielleitung."). Die Grenze ist weich: sie zählt Test- und
   nachgetragene Personen mit, die Spielleitung trägt weiter ein.
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
- Gehört das Handy der Teamleitung (Name = `leaderName`), steht auf der
  Team-Karte „Du bist Teamleitung: loslegen“ (Link zu `#/team`). Dort holt
  die App den Team-Code über den Geräte-Schlüssel (`leader_code`, Nachtrag
  18) und loggt ohne Tippen ein. Andere Handys sehen „Du leitest gerade kein
  Team“ bzw. „Eingeben kann nur die Teamleitung“; das Code-Feld steht nur
  hinter „Spielleitung: mit Team-Code eingeben“ (Nachtrag 22).
- Ab dem Start zeigen alle Ansichten im Kopf die Restzeit (`endsAt`, aus
  `duration_min`), rot in den letzten 15 Minuten, danach „Zeit ist um“.
- Nachzügler: nur über die Spielleitung (Hilfe-Knöpfe auf der Anmeldeseite).
  Der Mitlese-Link ohne Anmeldung ist gestrichen (F7, 29.10.2026): mitlesen kann nur, wer sich auf dem eigenen Handy angemeldet hat.
- Teamleitung: „Leitung
  abgeben“ steht im Reiter Team ihrer Ansicht (in den Phasen mit der alten langen Seite unten).

### 5.4 Spiel (`running`)
- Teamleitung (`#/team`): Station, Ortshinweis, Kompass und Entfernung,
  „Wir sind da“, danach Rätsel mit Eingabe, kleine Ziffern-Räder darunter
  (Variante B, siehe `mockups/team-reihenfolge.html`).
- Mitglieder mit Token (`#/public`): dieselbe Ansicht aus `member_state`, ohne
  Eingaben („Einchecken macht Silke“, „Die Antwort gibt Silke ein“).
  Kompass und Entfernung mit dem eigenen GPS, keine Positionsmeldung.
- Öffentliche Seite: „Zieleinlauf“ live, sobald das erste Team im Ziel ist.
- Spielleitung: Reiter Karte und Teams (Karte, Teamliste mit "Braucht dich" zuerst, Zuletzt), Reiter Zeitachse.
  Je Team steht, wo es ist und seit wann („unterwegs zu Station 2 seit 14 min“,
  „an Station 2 seit 22 min“), dazu das Alter der letzten GPS-Meldung, rot ab
  5 Minuten (Nachtrag 21: `checkedInAt`, `lastSolvedAt` in `admin_state`).
  Unterwegs steht nur „Freischalten“ (ersetzt den Check-in,
  `admin_unlock_station`), nach dem Check-in nur „Rätsel werten“
  (`admin_solve_station`, fragt nach). Rückmeldungen dazu stehen in der
  Zeile des Teams. Teamleitung wechseln fragt ebenfalls nach.

### 5.5 Ziel
- Alle fünf Ziffern: großes Zahlenschloss, Koffer-Hinweis
  (`game_state.case_hint`), Code-Eingabe nur bei der Teamleitung und nur am
  Koffer (die Meldung nennt sonst die Restentfernung).
- Nach richtigem Code: Platz-Bildschirm mit Medaille (1 bis 3) oder 🏁, auf
  allen Handys des Teams. Die Aufsicht am Koffer gibt nach Platz frei.

### 5.6 Ende (`finished`)
- `admin_finish` (fragt nach). Rangliste öffentlich; Teams ohne Platz nach
  gelösten Stationen. Zu früh gedrückt: „Spiel fortsetzen“ (`admin_resume`).
- Danach: Routen auswerten, „Standortdaten löschen“ (`admin_clear_positions`).

---

## 6. Wer sieht was (Sichtbarkeit)

| Daten | öffentlich (`public_state`) | Mitglied (`member_state`) | Teamleitung (`team_state`) | Spielleitung (`admin_state`) |
|---|---|---|---|---|
| Teams, Mitglieder, Teamleitung | ja | eigenes | eigenes | alle |
| Team-Code | nein | **nein** | eigener | alle |
| Mitlese-Schlüssel (ohne Funktion) | nein | **nein** | eigener | alle |
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
  `current_station`, `require_admin`, `answer_ok`, `aktive_route`) sind für
  `anon` und `authenticated` gesperrt. Prüfen: `tools/pruefstand/rechte_db.py`
  (Nachtrag 31: Nachtrag 28 hatte `current_station` neu angelegt und die Sperre
  verloren).
- Admin-Funktionen prüfen die PIN serverseitig (`require_admin`).
- Team-Codes: Tiername plus sechs Ziffern (`FUCHS-123456`); alte vierstellige
  Codes gelten bis zum nächsten Auslosen. `team_by_code` vergleicht nur
  Buchstaben und Ziffern (`EULE 8765` = `eule-8765`).
- Mitlesen nur mit Geräte-Token aus der eigenen Anmeldung, nie über den
  Namen: Namen sind öffentlich, und alle Teams haben dieselben Rätsel und
  Ziffern. Den Mitlese-Link (`teams.read_token`, `member_state_by_team`) gibt es
  seit F7 (29.10.2026) nicht mehr; die Spalte und das Feld `readToken` bleiben
  ohne Funktion stehen, die Funktion `member_state_by_team` fällt mit der
  Migration weg.
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
  lange PIN setzen. Seit Nachtrag 20 verlangt jede Änderung mindestens 12
  Zeichen (Trigger auf `game_state`); eine alte kurze PIN gilt, bis sie
  geändert wird. Ein Fehlversuchszähler geht nicht einfach: `require_admin`
  bricht mit einer Exception ab, die das Hochzählen zurückrollen würde.
- Team-Codes (16 Tiere × 900000 Zahlen) lassen sich mit vielen Anfragen raten;
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
geraete-test.html, geraete-tests.js  Geräte-Test und seine Suite, gehört nicht zum Spiel (HANDOFF, Nachtrag 23)
kompass-test.html          leitet auf geraete-test.html weiter
hintergrund/a.svg, b.svg, c.svg  Hintergrund-Varianten, lädt render() nach; klassisch steht im HTML
sw.js                      Service Worker, App startet ohne Netz aus dem Cache (§15)
vendor/                    Leaflet 1.9.4, Schriften (woff2, OFL), QR-Generator; nichts kommt von einem CDN
rueckblick.js, .css        Rückblick-Show (§16), wird nur beim Öffnen von #/rueckblick nachgeladen
rueckblick-karte.js        Grundkarte von Prag aus OpenStreetMap für die Show (tools/rueckblick/karte.py)
supabase/migrations/*.sql  Schema und Spiellogik, in Dateinamen-Reihenfolge
supabase/schema/           heutiger Stand der Datenbank (Funktionen, Tabellen, Sichten, Rechte), erzeugt, nicht von Hand
supabase/seed-*.sql        Stationen der Prager Route, 100 Testpersonen
tools/sql.py               SQL über die Supabase Management-API ausführen
tools/schema_abzug.py      Schema-Abzug nach supabase/schema/ erzeugen und gegen die Live-Datenbank prüfen (nur lesend)
tools/hintergrund/         Generator für die Hintergrund-Varianten (OSM-Daten sind gitignored)
mockups/                   Entwürfe (Kompass einmessen, Reihenfolge, Hintergrund, Routen)
```

### Frontend (`index.html`)
- **Zustand:** ein Objekt `S` (`S.view`, `S.pub`, `S.team`, `S.admin`,
  `S.gps`, `S.mit`, `S.lookup`, …). `render()` baut `#app` komplett per
  `innerHTML` neu.
- **Ansichten:** `viewPublic`, `viewTeam` → `teamAnsicht(st, lesen)`,
  `viewAdmin` (Reiter Karte und Teams, Zeitachse, Auslosen, Teilnehmende, Stationen, Fotos, Daten löschen).
  Eine Setup-Ansicht gibt es nicht mehr: ohne `config.js` erscheint die Meldung
  aus `rpc()`. Routing über den Hash (`#/public`, `#/team`,
  `#/admin`).
- **Aktionen:** Klicks auf `[data-act]` rufen `ACT[name](dataset)`. Wirft eine
  Aktion oder setzt sie `S.msg` vom Typ `err`, bleiben die Eingaben stehen
  (Klick-Handler). `return false` heißt: nicht neu zeichnen.
- **Meldungen:** `S.msg = { type, text, ort? }`; `msgBox(ort)` zeigt sie,
  Erfolgsmeldungen verschwinden nach 12 s.
- **Datenbank:** `rpc(fn, args)` → `POST /rest/v1/rpc/<fn>`.
- **Abfragen:** alle 10 s je nach Ansicht `public_state` (+ `member_state`),
  `team_state` oder `admin_state` (+ `admin_tracks` auf der Karte). Nicht,
  solange ein Eingabefeld den Fokus hat oder die Seite verdeckt ist. Neu
  gezeichnet wird nicht, solange Hochhalten oder das Hilfe-Blatt offen ist
  (außer das Team oder die Leitung hat sich geändert); beim Schließen schon.
  Spielleitung in den Reitern Karte und Teams und Zeitachse: kein `render()`,
  Karte, Zuletzt, Zeitachse sowie Teamliste und Zähler im Kopf
  (`teamlisteNachziehen()`) ziehen sich selbst nach. Ein zweites Intervall
  (1 s) zählt die Denkpause herunter.
  Jede Ansicht hat einen Zähler (`ZAEHL`, `taktAbruf`): die Antwort eines
  Abrufs, der nach einem Wechsel der Ansicht zurückkommt, wird verworfen, und
  solange ein Abruf läuft, startet der Takt keinen neuen. Die Spielleitung
  behandelt "Falsche PIN" im Takt über `pinWeg()`; im Kopf der Spielleitung
  steht der Chip `#stand`. `syncTracks` merkt sich den laufenden Durchgang.
- **Löschen und Rückfragen:** alles über die Liste `DANGER` und einen Dialog,
  meist mit getipptem Wort `LÖSCHEN`; `wort: false` für Person und Spielende.
  `neutral: true` (Start, Teamleitung wechseln, Rätsel werten) zeigt den Dialog
  ohne Rot und mit orangem Knopf.
- **Meldungen:** `S.msg` mit optionalem `ort`. `msgBox(ort)` zeigt nur Meldungen
  mit genau diesem ort, `msgBox()` nur die ohne. Jede Ansicht ruft `msgBox()`
  genau einmal auf, sonst steht eine Meldung doppelt. Feste Orte: `anm`,
  `suche`, `karte`, `mit`, `abgeben`, `settings`, `bg`, `dlg`, `t:<Team-ID>`,
  `leiste` (Einchecken, Antwort und Koffer-Fehler in der Aktionsleiste, auf
  jedem Tab sichtbar).
  Knöpfe mit `data-ort` geben ihren ort an Fehler aus dem Klick-Handler weiter.
- **Eingaben:** `render()` rettet Getipptes und Fokus über jedes Neuzeichnen,
  solange derselbe Zustand zu sehen ist (`feldKontext`). Nach einer
  erfolgreichen Aktion leert es die Felder (`S.felderFrisch`).
- **Bildschirm an:** `wachHaltenPruefen()` hält per Wake Lock den Bildschirm an,
  beim Hochhalten und unterwegs mit Standort; nach der Rückkehr in die App
  (`visibilitychange`) neu, dabei lädt die Seite auch sofort nach.
- **Stand:** kommt 30 s nichts vom Server, steht im Kopf „Stand 13:27“.
- **Speicher im Browser:** `sj.name`, `sj.token`, `sj.code` (Teamleitung), `sj.kal` (Einmessen heute erledigt),
  `sj.gps` (Standort war schon freigegeben: nach Neuladen ohne Tipp wieder
  starten, den iOS-Kompass nur per Knopf), `sj.abgemeldet` (Teamleitung hat
  sich abgemeldet: nicht still per Geräte-Schlüssel wieder einloggen),
  `sj.letzter.team`/`sj.letzter.mit` (letzter Stand ohne Netz, §15),
  `sj.url`/`sj.key` (nur ohne `config.js`) im `localStorage`; `sj.pin` im
  `sessionStorage`. Zugriff nur über `LS`/`SS`: Blockiert der Browser
  Website-Daten oder ist der Speicher voll, fallen beide auf eine Map im
  Speicher zurück, `setItem` wirft nie, statt die Seite abzubrechen.
  `sj.hand` (Team-Code von Hand eingegeben, §2) kommt dazu.

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
- `START` (Hotel Mama Shelter): nur als Haus auf der Admin-Karte, nicht in
  der Datenbank.
- Alte Mitlese-Links (`#/mit/<schlüssel>`) leitet `mitLinkPruefen()` auf `#/public` um und löscht `sj.mit`;
  `mitlesen()` fragt `member_state` mit `sj.token`.
  `aktiverStand()` liefert `S.team.state` (Teamleitung) oder `S.mit` (Mitglied).
- Ohne Richtung zeigt der Kompass ein Fragezeichen statt eines Pfeils.

### Hintergrund
- Vier Varianten: `klassisch` (im HTML), `a`, `b`, `c` (`hintergrund/*.svg`,
  nachgeladen von `hintergrundSetzen()`). Die Wahl kommt aus
  `game_state.background` über alle drei Zustandsfunktionen; `render()` setzt
  sie um, `sj.bg` merkt sie für den nächsten Start. Umschalten im Reiter
  Stationen (`admin_set_background`).
- Linien überall gleich fein (`vector-effect: non-scaling-stroke`),
  Beschriftungen ab 700 px Breite ausgeblendet.
- Freier Text ohne Karte darunter (direkte Kinder von `main`, die keine
  Karte, Meldung oder Dialog sind) hat einen Lichthof in Papierfarbe
  (`text-shadow`); Knöpfe, Felder, Karten setzen ihn zurück.
- Scroll-Parallax ohne Skript: die Karte ist um `--px-hub` (40lvh) höher als
  das Fenster, eine scroll-gebundene CSS-Animation (`animation-timeline:
  scroll(root)`) schiebt sie über die Seitenlänge um den Überstand. `lvh`
  statt `vh`, sonst springt sie, wenn Android die Adressleiste ausblendet.
  Ohne Unterstützung oder bei „Bewegung reduzieren“ steht sie still.
- Neigungs-Parallax: `neigungStart()` hört `deviceorientation`, verschiebt
  den Rahmen `.topo` (ragt 18 px über das Fenster) bis 18 px in die
  Neigungsrichtung; Bezug ist die Ruhehaltung (Tiefpass), 25° = voller Weg.
  iOS erst nach der Bewegungsfreigabe aus `startGps()`.

### Datenbank
Tabellen: `participants` (Name, `name_key`, `team_id`, `token`), `teams`
(Name, Code, Leitung), `stations` (Position, Name, Koordinaten, Radius,
Ortshinweis, Rätsel, Lösung, Ziffer), `progress` (je Team und Station:
Check-in, gelöst, Fehlversuche, Sperre), `finishes` (Platz), `team_positions`,
`position_log`, `game_state`.

Endpunkte:
- öffentlich: `public_state`, `register_participant`, `lookup_participant`
  (auch Namensteile, bis zu acht Vorschläge), `member_state`
- Teamleitung: `leader_code` (Team-Code über den Geräte-Schlüssel),
  `team_state`, `check_in`, `submit_answer`, `reveal_tip`, `submit_final`,
  `report_position`, `team_set_leader`
- Spielleitung: `admin_state`, `admin_tracks`, `admin_draw`, `admin_start`,
  `admin_finish`, `admin_resume`, `admin_reset`, `admin_clear_positions`,
  `admin_clear_participants`, `admin_add_participant`,
  `admin_add_participants`, `admin_delete_test_participants`,
  `admin_rename_participant`, `admin_delete_participant`, `admin_set_leader`,
  `admin_save_station`, `admin_unlock_station`, `admin_solve_station`,
  `admin_set_pin`, `admin_set_test_mode`, `admin_set_settings`
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
  Nachtrag 7, `register_participant` in Nachtrag 32). Die letzte Definition
  findet `tools/migration_bugjagd2.py` (`neueste()`) über alle Migrationen.
- **Nach jedem `drop` + `create` einer Funktion die Rechte ausdrücklich
  setzen**: `revoke all ... from public, anon, authenticated` für
  Hilfsfunktionen, `grant execute ... to anon, authenticated` für
  Spielfunktionen. Supabase gibt neuen Funktionen von selbst Ausführungsrechte
  für `anon`; eine neu angelegte Hilfsfunktion ist sonst offen (so geschehen mit
  `current_station` in Nachtrag 28, behoben in Nachtrag 31). `create or
  replace` mit gleicher Signatur behält die Rechte. Der Probelauf zum Nachtrag
  prüft die Rechte mit (Muster: `tools/pruefstand/rechte_db.py`).
- **Wo die heutige Fassung einer Funktion steht:** `supabase/schema/funktionen/<name>.sql`
  (je Funktion die Live-Fassung mit Rechten, dazu `tabellen/`, `sichten/` und in
  der `README.md` die Übersicht, welche Funktion offen, nur per PIN oder intern ist).
  Als Vorlage für eine Änderung dient diese Datei, nicht die Suche durch die
  Migrationen. Nach jeder eingespielten Migration `python tools/schema_abzug.py`
  laufen lassen und das Ergebnis mitcommitten; vor jedem Einspielen
  `python tools/schema_abzug.py --pruefen` (Exit 1, wenn der Ordner vom Live-Stand
  abweicht; Warnungen, wo Migrationen und Live nicht zusammenpassen). Beides liest
  nur aus den Systemkatalogen, nie Tabelleninhalte.
- Einspielen: `python tools/sql.py supabase/migrations/<datei>.sql`. Token in
  `%USERPROFILE%\.supabase\stadtjagt.token`. Das Skript bremst zerstörerische
  Anweisungen außerhalb von Funktionskörpern. Die Bremse in `sql.py` prüft auch
  `DO`-Blöcke, nur Funktionskörper nicht. Sie schützt vor Versehen, nicht vor
  Absicht: Strings mit `--`, zusammengesetzte Befehle und eine Funktion, die
  angelegt und dann aufgerufen wird, gehen durch. Tests: `python
  tools/test_sql_bremse.py`. Probeläufe (`*_db.py`) rufen `sql.ausfuehren`
  direkt auf und unterliegen der Bremse nicht.
- Reihenfolge beim Ausliefern: erst die Datenbank, dann die App.

### Testmodus und Testdaten
- `admin_set_test_mode` (Reiter Stationen): Check-in und Koffer-Code ohne
  Entfernung, jede Antwort zählt, keine Denkpause; der Koffer-Code selbst wird
  weiter geprüft. Rotes „Testmodus an“ in Admin und Team-Ansicht.
  „Spiel starten“ warnt, solange er an ist (bleibt beim Testen dauerhaft an,
  Entscheidung 19.09.2026).
- Mit Plätzen lässt er sich in keinem Zustand umschalten (Nachtrag 32,
  Meldung "Es gibt schon Plätze."); Ausweg ist „Fortschritt zurücksetzen“. Nach
  einem echten Spiel geht auch das Einschalten erst danach. Vor dem Event also
  erst zurücksetzen, dann ausschalten.
- Im Testmodus spielen alle Teams nur die Teststation (Nachtrag 28), und der
  Kompass-Wächter wirkt (Nachtrag 30).
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

## 10. Offene Punkte (Stand 19.09.2026, abends, Nachträge 1 bis 22 live)

- Rätsel, Lösungen und Ortshinweise der fünf Stationen fehlen (Platzhalter).
- Öffentliche Auslieferung des ganzen Repos (siehe 7.), neuer Koffer-Code.
- Echte Nummer für die Hilfe-Knöpfe statt `491720000000`.
- Live-PIN verlängern (siehe 7.); `2026` ist sie nicht mehr, hat aber nur
  4 Zeichen. Neue PINs verlangen seit Nachtrag 20 mindestens 12.
- Hintergrund-Variante festlegen (umschaltbar im Reiter Stationen; aktiv ist
  A; B zeigt noch den Altstadt-Ausschnitt, Neuerzeugung siehe HANDOFF).
- Testumgebung und Testskripte ins Repo übernehmen.
- Probelauf draußen mit echten Handys, dabei die Punkte, die nur auf dem
  Gerät prüfbar sind (siehe HANDOFF, Offene Punkte).
- UI-Varianten A, B, C liegen als Mockup unter `mockups/ui-varianten/`,
  vorerst nicht gebaut; das bestehende Design wurde stattdessen verbessert
  (`mockups/ui-durchsicht/`).
- Gespeicherte Ideen für ein kniffligeres Spiel (Ort als Rätsel mit verborgener
  Entfernung, Hinweise plus Schlussrätsel statt sichtbarer Ziffern, versetzte
  Stationsreihenfolge je Team, Kompass entschärfen): siehe HANDOFF.md
  „Ideen für ein kniffligeres Spiel“. Entscheidung offen.

---

## 11. Nachträge 23 bis 26 (30.09.2026)

Einzelheiten und Entscheidungen je Nachtrag stehen in `HANDOFF.md`, die
Spezifikationen in `docs/superpowers/specs/`.

### Gruppenselfie (Nachtrag 25, abschaltbar)

`game_state.selfie_on`, Standard aus, geschaltet im Reiter „Fotos“.

- `submit_answer` ist unverändert und setzt `progress.solved_at`. Daran hängen
  Zeitmessung und Rangliste.
- Neu ist `progress.selfie_at`. Bei eingeschaltetem Selfie liefert
  `team_state` die Ziffer einer Station erst, wenn `selfie_at` gesetzt ist, und
  meldet die niedrigste gelöste Station ohne Foto als `selfie.pending`. Die
  sechste Ziffer und `allSolved` warten ebenfalls.
- Solange `selfie.pending` gesetzt ist, zeigt das Handy der Teamleitung den
  Selfie-Schritt statt der nächsten Station (`selfieHTML()`), Mitglieder sehen
  einen Hinweis.
- `team_selfie` speichert das Foto (JPEG, bis 700 KB, Vorschau bis 60 KB) und
  setzt `selfie_at`. `team_selfie_skip` setzt nur `selfie_at`: die Ziffer hängt
  nie am Netz. Ein nicht gesendetes Foto bleibt im `localStorage` und wird
  nachgereicht (`fotoNachreichen()`); "wird nachgereicht" steht nur da, wenn
  wirklich eines gemerkt ist (`sf.gemerkt`).
- Ersetzen geht für die zuletzt gelöste Station, bis an einer späteren
  eingecheckt ist.
- Album: `team_photo` mit Team-Code oder Geräte-Schlüssel.
  Spielleitung: `admin_photos`, `admin_photo`, `admin_set_selfie`,
  `admin_delete_photos`; das ZIP entsteht im Browser (`zipBauen()`).
- Fotos liegen in `station_photos`, mit Fremdschlüssel auf `progress`:
  Zurücksetzen, neu Auslosen und Leeren der Anmeldung nehmen sie mit. Das
  Löschdatum muss nach dem heutigen Prager Datum liegen, sonst wären alle Fotos
  sofort weg; gelöscht wird am gewählten Tag ab 1 Uhr (Winterzeit) bzw. 2 Uhr
  (Sommerzeit). Das schon gespeicherte Datum geht nur beim Ausschalten noch
  einmal durch (nach dem Löschtag), beim Einschalten nicht: ein altes Datum aus
  einer Probe wird am Eventtag abgelehnt. Ist `photos_delete_on` erreicht, löschen `team_state` und `admin_state` sie beim
  nächsten Abruf.
- Wird mitten im Spiel eingeschaltet, brauchen schon gelöste Stationen kein
  Foto mehr (`admin_set_selfie` setzt für sie `selfie_at`).

### Stationsname verschlüsselt (Nachtrag 26, je Station)

`stations.reveal_start_m` und `reveal_clear_m`; beide leer heißt unverschlüsselt.

- Nur die Anzeige: Der Name kommt im Klartext in `team_state`, das Handy
  verschleiert ihn nach dem eigenen Standort (`geheimStand()`).
- Zwischen den beiden Entfernungen rasten die Buchstaben ein, in zufälliger,
  je Name fester Reihenfolge (`geheimFolge()`). Der Ortshinweis erscheint erst
  mit dem lesbaren Namen (`stationsNameHTML()`).
- Schloss: der weiteste Stand je Station steht im `localStorage`
  (`sj.geheim.<team>.<position>`).
- Ohne freigegebenen Standort bleibt der Name verschlüsselt. Nach dem Check-in
  steht er im Rätsel-Kasten immer im Klartext.
- Testmodus: die Annäherung wird vorgespielt (3 s verschlüsselt, 7 s Auflösen).
- Spielleitung: „Bearbeiten“ einer Station zeigt eine Karte mit drei Kreisen
  (`stationsKarte()`, `ekZeichnen()`); `admin_save_station` hat dafür zwei
  Parameter mehr.

### Standort und Kompass

- **Ungefährer Standort:** Meldungen über ±1000 m verwirft das Spiel
  (`brauchbar()`). Kommt nichts Brauchbares, zeigt `grobHTML()`, wo man „Genauer
  Standort“ einschaltet.
- **Nach dem Neuladen:** `startGps(true)` hört auf Kompass-Ereignisse und bittet
  nur um den Tipp, wenn drei Sekunden nichts kommt. Am Vorhandensein von
  `requestPermission` lässt sich iOS nicht mehr erkennen, Chrome hat es auch.
- **Nach einer Pause** (Seite mindestens 3 s im Hintergrund, nur Android):
  Kompass gilt als unsicher, das Einmessen wird angeboten
  (`kompassNachPause()`).
- **Einmessen** ist ein Fenster über der Seite (`kalFensterHTML()`).
- **Zeichen im Kopf:** Kompass mit eigener Nadel, die überall mitdreht
  (`logoStart()`).
- **Bildschirm wach halten:** wird bei jedem Tipp erneut versucht.

### Spielleitung

- Reiter „Fotos“: Schalter, Löschdatum, Galerie, ZIP, Löschen.
- Karte: Strecken ohne GPS-Signal gestrichelt, ab zwei Minuten mit Dauer
  (`LUECKE_M`, `LUECKE_MS`). Im Testmodus werden auch Teams weit weg von der
  Route gezeichnet.
- „Freischalten“ fragt nach. Solange ein Finger aufliegt, wird nicht neu
  gezeichnet (`fingerSeit`).

### Neue Dateien

```
geraete-test.html, geraete-tests.js   Geräte-Test und seine Suite (gehört nicht zum Spiel)
vendor/qrcode.js                      QR-Generator für die Rückblick-Fernbedienung (MIT)
tools/testlaeufe.py                   Läufe des Geräte-Tests nach testlaeufe/ holen
tools/pruefstand/geraetetest.py       Geräte-Test mit gespielten Sensoren
tools/pruefstand/selfie.py, name.py   Selfie und verschlüsselter Name im Prüfstand
tools/pruefstand/selfie_db.py, name_db.py   Probelauf der Migration, nimmt alles zurück
supabase/migrations/20260930120000_geraetetest.sql          Nachtrag 23
supabase/migrations/20260930180000_gruppenselfie.sql        Nachtrag 25
supabase/migrations/20260930200000_name_verschluesselt.sql  Nachtrag 26
```

### Offene Punkte (Stand 30.09.2026)

Siehe den Kopf von `HANDOFF.md`: die Liste dessen, was nur am echten Gerät zu
klären ist, und was vor dem Event zurückgestellt werden muss (Testmodus aus,
Probedaten weg, Löschdatum für Fotos).

## 12. Nachtrag 27 und Design System (01.10.2026)

- **Design System:** `design-system/MASTER.md` (Regeln) und
  `design-system/index.html` (Ansicht, hell und dunkel). Neue Oberfläche hält
  sich daran: ein Orange pro Ansicht, Token statt Farbwerte, Schriftgrößen nur
  als `var(--fs-*)` (xs 13, s 15, m 17, l 19, xl 24, xxl 32, zahl 38/56,
  rad 32, schild 48). Ausnahme: Beschriftung der Hintergrundkarte `.topo`.
- **Hell/dunkel:** `themaBtn()` in jedem Kopf (`brand()`, Team-Kopf in
  `teamAnsicht`, Spielleitung neben den Aktionen), Aktion `thema` setzt
  `data-theme` auf `<html>` und merkt `sj.thema`, ohne neu zu zeichnen. Ein
  Skript im `<head>` setzt die Wahl vor dem ersten Zeichnen. Dunkle Token stehen
  zweimal: in `@media (prefers-color-scheme:dark)` mit
  `:root:not([data-theme="light"])` und als `:root[data-theme="dark"]`.
  Wer einen dunklen Token ändert, ändert beide.
- **Zahlenantwort:** `team_state` liefert `station.numeric`, dann bekommt
  `#tans` `inputmode="numeric"`.
- **„Wir sind da“:** `checkRest/checkWeit/checkText/checkNachziehen` halten den
  Knopf `#tcheck` mit der Entfernung aktuell, außerhalb des Radius als
  Nebenknopf `.btn.weit`.
- **Hochformat-Hinweis:** `#quer` nach `<main>`, `querPruefen()` aus `render()`
  und bei `resize`/`orientationchange`; ausgenommen Spielleitung,
  `S.gps.kal`, `S.hoch`, `S.gross`.
- **Kennungen einzeilig:** Werte mit Einheit („etwa 60 m“) stehen in
  `white-space:nowrap`.
- Prüfen: `python tools/pruefstand/kritik.py`; der Prüfstand lässt `sj.thema`
  beim Laden stehen.
- **Ziffer im laufenden Spiel ändern (02.10.):** Haben Teams die Station schon
  gelöst (`t.solved >= position`, alle laufen dieselbe Route), fragt `a-save`
  über `DANGER.ziffer` nach; gespeichert wird in `stationSpeichern()`. Das
  Getippte hält `confirm.felder`, `a-dlg-cancel` schreibt es über
  `S.felderZurueck` nach dem Neuzeichnen zurück. Test:
  `python tools/pruefstand/ziffer.py`.
- **Teststation (Nachtrag 28):** `stations_alle` mit `route`, Sicht `stations`
  (aktive Route über `aktive_route()`); alle Spielfunktionen lesen die Sicht.
  `admin_state` liefert `stations` (immer echt, zum Bearbeiten), `testStation`,
  `route`, `aktiveStationen`; `admin_photos` beide Routen mit `route`,
  `admin_photo(…, p_route)`. Client: `alleStationen(st)`, `aktiv(st)`,
  `stationZeile(s, st)`, `TEST_START`, `ANZ(st)` für Schloss und Texte.
  Neue Spalten an `stations_alle`: danach die Sicht mit `create or replace`
  neu anlegen (siehe Kopf der Migration 20261002120000).
- **Kompass-Wächter (Nachtrag 30, 03.10.):** `kompass-waechter.js`
  (`KompassWaechter(opt)` mit `gyro`, `kompass`, `pause`, `einmessen`; Getter
  `urteil`, `versuche`, `prueft`, `vorbelastet`; `onWechsel` nur bei Änderung).
  In `index.html`: `S.gps.waechter`, `waechterGrund`, `waechterSchlecht()`,
  `waechterRuht()` (senkrecht, Bildschirm unten, iOS `kompassRoh`
  „kalibrieren“, `nachPause`), `motionH` (Drehung um die Senkrechte),
  Gedächtnis `sj.kompass`. Anzeige: `kompassFolgt()`, `kompassKlasse()`,
  `kompassChip()`, `waechterHinweisHTML()`, `laufrichtung()` (Anker > 8 m und
  > Genauigkeit, gilt 30 s). Wirkung nur bei `testMode`. Meldung:
  `maybeReport` schickt `p_kompass`, eine Meldung zur Zeit (`g.meldet`),
  Wiederholung ohne `p_kompass` nur bei PGRST202. Spielleitung:
  `zustandHTML` zeigt den Vermerk bei Position < 3 min. Prüfen:
  `python tools/pruefstand/waechter.py`, Probelauf `waechter_db.py`.

## 13. Bugjagd 03.10.2026 (Nachtrag 31 und 32)

- **Rechte:** `current_station(uuid)` ist wieder für anon und authenticated
  gesperrt (Nachtrag 31). Nach jedem drop + create einer Funktion die Rechte
  ausdrücklich setzen (§9). Probelauf `tools/pruefstand/rechte_db.py` prüft
  alle internen Hilfsfunktionen.
- **`rpc()`:** bricht nach 15 s ab (Fotos 60 s) wie bei einem Netzfehler;
  Netzfehler tragen `netz: true`, die Meldung `kind: "netz"`, und `netzOk()`
  räumt sie nach der nächsten guten Antwort ab. Fehler tragen den
  PostgREST-Code als `e.code`.
- **Teamleitung ohne Code:** bei Netzfehler Meldung und neuer Versuch im
  10-s-Takt (`leitungOhneCode`, `S.team.ohneNetz`).
- **Spielleitung:** `koordAusFeldern()` zerlegt ein Koordinatenpaar im Feld
  Breite immer (Station, Teststation, Startpunkt); Enter im Formular geht an
  den Knopf mit `data-enter-ziel`; `felderFrisch` nur, wenn neu gezeichnet wird.
- **Standort:** Fehler Code 2 nach einem ersten Fix beendet die Ortung nicht
  mehr, der letzte Punkt bleibt mit seinem Alter stehen.
- **Merker je Station:** `merkerTeil()` hängt Route (test/echt) und
  Spielbeginn an die Schlüssel von `sj.geheim.*` und den Fotos, damit ein
  Testlauf nichts ins echte Spiel trägt.
- **Datenbank (Nachtrag 32):** `register_participant(p_name, p_token)`,
  `admin_set_test_mode` mit Sperre bei Plätzen, `submit_answer` mit leerer
  Antwort, `device_test_save` mit Formprüfung. Generator
  `tools/migration_bugjagd2.py`, Probelauf `tools/pruefstand/bugjagd2_db.py`.
- Prüfen: `python tools/pruefstand/bugjagd2.py`.

## 14. Code-Review 15.10.2026 (Nachtrag 34)

- **"Braucht dich":** kein GPS, GPS älter als 5 min, Denkpause nach dem
  3. Fehlversuch (`lockedUntil` in der Zukunft, Warnung "Denkpause bis
  HH:MM"), mindestens 2 Fehlversuche. Verfällt die Denkpause, gilt wieder die
  normale Regel.
- **Datenbank (Nachtrag 34, `20261015090000_namenssuche_grenze.sql`):**
  `lookup_participant` sucht über 60 Zeichen (nach `norm`) nur genau; die
  Tippfehler-Suche überspringt Kandidaten, deren Länge weiter als die erlaubte
  Distanz abweicht, ohne `name_abstand`. Probelauf
  `tools/pruefstand/namenssuche_grenze_db.py` (`--ohne` zeigt den alten Stand).
- **Karte der Spielleitung:** eine verworfene Leaflet-Karte wird mit
  `karteAbbauen()` (`map.remove()`) abgebaut; Auswahl eines Teams im Reiter
  Karte und Teams zeichnet nicht neu (`auswahlZeigen()`). Verlässt die
  Spielleitung den Reiter Zeitachse, stoppt das Abspielen und der Zeitpunkt
  steht auf jetzt.
- **Handy:** Erfolg von Einchecken und Antwort steht in der Leiste; Hochhalten
  endet, sobald sein Fenster nicht mehr gezeichnet ist (etwa nach Spielende).
- Prüfen: `python tools/pruefstand/review1510.py`.

## 15. Ausfallsicherheit (Nachtrag 35, 16.10.2026)

Spezifikation `docs/superpowers/specs/2026-10-15-ausfallsicherheit-design.md`,
mit den Änderungen aus der Gegenprüfung (gehen der Spezifikation vor).

- **Lokal statt CDN:** Leaflet 1.9.4 aus `vendor/leaflet-1.9.4/`
  (`loadLeaflet()`), Schriften als `@font-face` mit `vendor/fonts/*.woff2`
  (latin und latin-ext, `font-display: swap`).
- **Service Worker `sw.js`** (Scope des Ordners, registriert am Ende des
  App-Skripts nur auf `./` bzw. `./index.html`, über https oder lokal,
  `updateViaCache: "none"`; der Prüfstand mit `app.html` bekommt keinen):
  Hülle (index.html unter dem Schlüssel `./`, `config.js`,
  `kompass-waechter.js`) Netz zuerst mit `cache: "no-cache"` und 4 s Grenze,
  sonst der Cache, der Abruf legt im Hintergrund ab; Navigation per URL, nie
  das Request-Objekt im Modus navigate. Schriften, Leaflet, QR Cache zuerst;
  Hintergründe aus dem Cache und nachgeladen. Supabase, RPCs, Kacheln,
  Nicht-GET und andere Seiten im Ordner (Geräte-Test, Mockups, tools/) gehen
  unberührt ans Netz. Caches `sj-huelle-1`, `sj-dauer-1`; aufgeräumt werden
  nur Caches mit `sj-*` (CacheStorage gilt für den ganzen Origin). Die Nummer
  steigt nur, wenn sich Liste oder Strategie ändern. Dateien unter `vendor/`
  sind über den Namen versioniert: wer eine tauscht, gibt ihr einen neuen
  Namen. Kein Manifest, kein Installieren-Hinweis. Notausgang
  `tools/sw-aus.js` (löscht nur `sj-*`, meldet die eigene Registrierung ab).
- **Speicher und Denkpause (Audit 25.10.):** `LS`/`SS.setItem` werfen nie, auch
  nicht bei vollem Speicher. Die Denkpause rechnet die Restzeit beim ersten
  Sehen aus (höchstens 120 s, eine schiefe Handyuhr verlängert sie nicht), das
  Ende ist Empfangszeit `Date.now()` plus Rest, verglichen wird mit
  `Date.now()`. Nicht `performance.now()`: das steht auf iOS und Android still,
  solange das Handy gesperrt ist.
- **Datenbank-Änderungen bleiben mit der vorigen App-Fassung verträglich**
  (neue Parameter nur mit `default`, keine Felder aus Antworten entfernen):
  alte Fassungen laufen eine Weile weiter (offener Tab, Laden im Funkloch).
- **Letzter Stand:** `teamStandSetzen` merkt `sj.letzter.team`
  (`{ code, at, state }`), `mitlesen()` merkt `sj.letzter.mit`
  (`{ key, at, pub, mit }`). Scheitert beim Start der Abruf mit `netz: true`,
  nimmt `letzterStand()` den gemerkten Stand, wenn Code bzw. Schlüssel passen,
  er höchstens 12 h alt ist und das Spiel `drawn` oder `running` ist;
  `S.zuletzt = at` (oben "Stand 13:27"). Gelöscht von `standVergessen()` bei
  Abmelden, Abgeben, `codeUngueltig()`, `nameNochDa()` und `leitungNochDa()`.
  Die Spielleitung merkt nichts (Lösungen).
- **`rpc()`:** HTTP 5xx und Antworten, die kein JSON sind, werfen
  `keineVerbindung()` (`netz: true`), wie ein Funkloch. `S.zuletzt` nur bei
  einer guten Antwort.
- **Eingaben ohne Netz** (`t-check`, `t-answer`, `t-final` über `eingabe()`):
  Meldung "Keine Verbindung. Tippt noch mal, sobald ihr Netz habt. Doppelt
  zählt nichts." in der Leiste, `S.offen = { act, phase }`. Der nächste
  `team_state` gleicht in `teamStandSetzen` ab (`abgleich()`): Phase weiter
  ergibt die Erfolgsmeldung (Angekommen, Ziffer, Platz), sonst "Wieder Netz.
  Tippt noch mal.". Kein automatisches Nachreichen außer dem Selfie. Die
  Antwort schickt `p_position` (Rückfall ohne bei PGRST202). Selfie: zeigt ein
  Abruf das Foto, ist "Erneut senden" weg ("Foto ist drin.").
- **Datenbank (Migration `20261016090000_eingaben_wiederholen.sql`, Generator
  `tools/migration_eingaben.py`):** `progress.last_wrong`; dieselbe falsche
  Antwort zählt nicht noch einmal und bekommt dieselbe Antwort.
  `submit_answer(p_code, p_answer, p_position default null)` (drop + create,
  Rechte ausdrücklich): ist das Team weiter, nie gegen das nächste Rätsel
  prüfen ("Diese Station ist schon gelöst.", "Das Rätsel hat gewechselt. Lest
  es noch mal."). `check_in`: schon eingecheckt gibt die Erfolgsantwort ohne
  neue Entfernungsprüfung.
- **Version:** `nav()` hängt `versionZeile()` an, "Version 15.10., 22:26" aus
  `document.lastModified` (Last-Modified von Pages; weniger als 5 s vor dem
  Laden: keine Zeile). `versionPruefen()` fragt per HEAD beim Zurückkehren in
  die App und höchstens alle 10 Minuten aus dem 10-s-Takt; neuer: Link "Neue
  Version laden", ohne Neuzeichnen, nie Neuladen von selbst.
- **Notfallmappe:** Reiter Stationen, Knopf "Notfallmappe" (`S.admin.mappe`),
  `mappeHTML()` nur aus `admin_state` im Browser. Koffer-Code aus den
  Stationen der echten Route (`mappeCode()`, nicht `caseCode`), Haken im
  Laufzettel nicht im Testmodus, "Daten vom" aus `S.admin.stateAt` (letzter
  `admin_state`). `.papier` setzt helle Token, `@media print` druckt nur das
  Blatt und jede Ansicht hell.
- **Prüfen** (Prüfstand, im Vordergrund mit Timeout): `lokal.py` (Leaflet und
  Schriften lokal), `version.py`, `mappe.py`, `funkloch.py` (Schalter
  `window.__netz` in `mock.js`), `offline.py` (Service Worker, mock.js inline,
  Prüfserver unter `/Stadtjagt/` stoppbar). Probelauf
  `tools/pruefstand/eingaben_db.py` (`--ohne` rot). Am Handy (iPhone Safari,
  Android Chrome, alle Geräte der Spielleitung): mit Netz laden, Flugmodus, neu
  laden (letzter Stand), Eingabe im Flugmodus (Meldung), Flugmodus aus
  (Abgleich), Push und Neuladen (Version wechselt), kein
  Installieren-Hinweis, Notfallmappe am iPad als PDF; Notausgang einmal auf
  iPhone und Android proben.

## 16. Rückblick-Show (Nachtrag 36, 16.10.2026; Fassung v2 vom 17.10.2026)

Spezifikation `docs/superpowers/specs/2026-10-15-rueckblick-show-design.md` mit
allen Nachträgen (die vom 17.10. ersetzen den alten Ablauf); Vorlage für Aussehen
und Verhalten `mockups/rueckblick-v2/index.html`; Kritik und Muss-Befunde
`docs/superpowers/specs/2026-10-17-rueckblick-kritik.md`; Gestaltung
`design-system/pages/rueckblick.md`. Nach dem Spielende zeigt ein Beamer (16:9)
den Rückblick, gesteuert von der Spielleitung. Keine neue RPC, keine Migration.

- **Ablauf:** Splash mit Kompass (hält als Startbild), Fun Facts (drei Kacheln:
  Personenkilometer, Schritte, Kalorien; Halt auf den Brathähnchen, Weiter
  schaltet auf Liter Bier), Die Gruppen (nur bei mehr als einer Startgruppe:
  Teams je Gruppe mit Tier und Namen, Ausgang: die Kreise drehen sich zu „?“ und
  fliegen auf die Ringplätze am Start), ein anonymer Zeitraffer (70 s, Laufzeit
  ab 0:00, „im Ziel x von n“, Kamera um alle Köpfe und den Start, „?“-Köpfe,
  graue Routen, Kopf springt beim Lösen, Ankerlinien im Ring; seit 18.10.
  gibt es keinen Check-in-Umkreis mehr auf der Karte, nur die Stationen),
  Rangliste Teil 1 (alles rattert, Halt; Weiter
  deckt die Plätze ab 4 von unten auf, rechts der Abstand zum Ersten; die
  Zeiten der ersten drei rattern weiter, auch wenn Teil 1 am Ende hält), Awards
  (Auftakt, bis zu sechs, Koffer-Teams ohne Award), Rangliste Teil 2 (die
  Zeiten der ersten drei rasten ein), Drei Spalten (Platz 2, 1, 3 mit Zeit und
  Weg, verdeckte Teams als Reihe darunter), Platz 3, Platz 2, Platz 1 (je Halt
  davor und danach, Platz 1 eskaliert), Siegerbild, Abspann (zufällige
  Fotorolle, endlos, 40 px/s, OSM-Nennung klein). **Nichts läuft von selbst
  durch:** jedes Kapitel hält am Ende („…, wartet auf Weiter“), nur der Abspann
  ist endlos. Weiter am letzten Halt kurz vor dem Kapitelende (Splash, nach dem
  Aufdecken, Siegerbild) geht gleich ins nächste Kapitel.
- **Steuerung:** Tasten wie im Mockup (Leertaste, K, F5, Pfeile, Bild auf/ab,
  Enter, N, P, Pos1, Ende = Rangliste, F, B/., T, R = Rand für Fernseher, H).
  Schutz: Weiter in den ersten 600 ms nach einem Wechsel (auch nach dem Lösen
  eines Halts) und gehaltene Tasten wirken nicht, zu frühes Weiter springt auf den Halt, während des Aufdeckens
  wirken Weiter und Zurück nicht (M2), Weiter setzt aus Pause und Schwarzbild
  fort (M3), im Durchsehen startet nichts, Starten baut die Kapitel neu (M8).
  Leiste unten nur bei Mausbewegung, pausiert bleibt sie stehen; Klick und
  Ziehen an jede Stelle wie bei einem Video, Tooltip mit Kapitel und Zeit.
  Schalter im Vorbereiten: Gruppenfotos, Halt vor und nach jedem Koffer-Platz,
  Rand für Fernseher, Bewegung reduzieren (Bewegung ist immer an, auch wenn der
  Laptop reduzierte Bewegung meldet). Direktsprünge zu jedem Kapitel.
- **Verlassen (M5):** Zurück im Browser, Maus-Seitentaste und „Zur
  Spielleitung“ fragen erst („Rückblick verlassen? Die Fotos werden danach neu
  geladen.“, Bleiben/Verlassen; Verlassen schaltet erst schwarz), Neuladen
  fragt der Browser (`beforeunload`). Das zuletzt gezeigte Kapitel steht in
  `sessionStorage` (`sj.rb.kapitel`); nach einem Neuladen bietet Vorbereiten
  „Weiter bei …“ an. Eine direkt geänderte Adresse schließt die Show ohne Frage.
- **Dateien:** `rueckblick.js` (eine Funktion, nichts global außer
  `RueckblickShow` und der Prüfhilfe `RB`), `rueckblick.css` (alle Regeln unter
  `#rueckblick`, Token `--park`, `--strasse`, `--fluss`, `--anon`, `--ring` und
  die Bühnenstufen `--bs-*` gelten nur dort) und `rueckblick-karte.js` (1,8 MB,
  `window.PRAG_KARTE`). `rueckblickLaden()` in `index.html` lädt alles erst beim
  Öffnen, mit `?v=` aus `VERSION`; `host.api` gegen `API` verhindert gemischte
  Fassungen. Nicht im Service Worker (die Handys tragen nichts davon).
- **Route:** `#/rueckblick` (PIN aus `sj.pin` oder eigenes PIN-Feld),
  `#/rueckblick/probe` (Beispieldaten mit drei Startgruppen, keine Abrufe von
  Spieldaten, „Probe“ im Splash und in der Leiste; die Fernbedienung, §17,
  geht nach dem Aktivieren mit PIN auch hier über die Datenbank). Knopf „Rückblick“ im Admin-Kopf und
  unter der Zeitachse bei `finished`.
- **Schutz vor dem Neuzeichnen:** eigener Container `#rueckblick` am `body`,
  `#app` ist `inert`; `render()` und `refresh()` kehren bei `S.view` mit Präfix
  `rueckblick` sofort zurück; die Knöpfe der Show tragen kein `data-act`.
- **Laden (`laden()`):** `admin_state` (Sperre vor dem Spielende und im
  Testmodus), `admin_tracks` ohne `p_since`, `admin_photos` (nur `route =
  echt`), je Foto `admin_photo` drei gleichzeitig: erster Versuch voll mit 20 s
  Zeitlimit, dann noch einmal voll, dann Vorschau. Nach 20 s erscheint „Ohne die
  restlichen Fotos weiter“; Vorbereiten nennt fehlende Fotos mit Team und
  Station und bietet „Erneut versuchen“. Ladezeile ohne Listenraster. „Alles
  geladen“ erst nach Karte und allen Schriftschnitten (Mustertext mit
  latin-ext); scheitert das Rastern der Karte, warnt eine Zeile („Karte nicht
  vorbereitet, die Kartenkapitel ruckeln“, Erneut versuchen). Ohne Netz:
  „Keine Verbindung zum Server. Prüfe das WLAN und versuche es erneut.“
- **Aufbereiten (`aufbereiten()`, reine Funktion):** Startgruppen vorbereitet:
  liefern die Daten je Team `startedAt` (oder `startGroup`), gilt dessen Start,
  alle Zeiten wandern auf 0:00 und gewertet wird nach Gesamtzeit; heute starten
  alle mit dem Spiel (eine Gruppe, Kapitel „Die Gruppen“ entfällt, Wertung wie
  `finishedAt` minus Spielstart). Je Team: Punkte nur bis 2 min nach dem
  Koffer-Code (M6, auch für die Kilometer), Ausreißer aus einem bis drei Punkten
  fallen weg (S15, eine Tramfahrt bleibt), Lücken gestrichelt, Ausdünnen auf
  8 m (S14; im Stand bleibt der letzte Punkt vor dem Aufbruch, damit der Kopf
  steht), Check-ins und Lösungen ohne GPS-Punkt innerhalb von 3 min und ein
  Startpunkt vor einem GPS-Beginn später als 5 min kommen als gestrichelte
  Punkte dazu (M7; Vorbereiten: „Tiger: GPS nur bis 14:25, danach aus den
  Check-ins“). Gleichstand in derselben Sekunde: „0,3 s vor Platz 2“ (K12). Der Abstand zum
  Ersten (Rangliste, Moderation, "vor Platz 2") wird aus einzeln auf Sekunden
  gerundeten Zeiten gebildet, damit er zu den angezeigten Zeiten passt. Ab
  13 Teams Ring mit 16 Plätzen, ab 14 Rangliste in zwei Spalten (K11).
  Uhrzeiten in `Europe/Prague` (K14).
- **Awards:** aus Spuren und Check-ins (Navi, Sightseeing, Rätselfüchse,
  Philosophen, Sprinter, Flaneure), je Team höchstens einer, ein Award fällt
  weg, wenn weniger als drei Teams die Kennzahl haben. Tempo nur aus Stücken von
  mindestens 60 s und 100 m, Weg und Zeit desselben Stücks; Punkte mit
  Genauigkeit über 25 m zählen nicht, falls die Daten sie tragen
  (`admin_tracks` liefert heute keine Genauigkeit).
- **Bildrate:** Karte einmal gerastert, `zeichneKarte()` nur bei Änderung,
  Spuren in Stücken zu 16 Punkten (mit 48 und spärlichen Punkten 31 bis 41
  Bilder/s), Überblendung nach echter Zeit (kein Halt friert sie ein). Gemessen
  17.10.: 60 Bilder/s in allen Kapiteln, auch mit 6.000 Punkten je Team.
- **Ausgenommene Fotos** stehen als `teamId:position` im `sessionStorage`
  (`sj.rb.aus`); Fotos nur als Blob-URL im Speicher, nie in `localStorage`.
- **Texte der App:** Anmeldung und Album „Sehen können es euer Team, die
  Spielleitung und beim Abendessen alle im Rückblick“, Selfie-Schritt, Reiter
  Fotos, Standort-Zeile „Euer Weg erscheint beim Abendessen im Rückblick.“; am
  17.10. gegen den neuen Ablauf geprüft (Fotos im Abspann, Wege im Zeitraffer
  anonym, in Awards, Spalten und Abspann in Teamfarbe): passen, unverändert.
  Warnung zum Löschdatum im Reiter Fotos schon im laufenden Spiel.
- **Ablauf am Abend:** Vorbereiten und „Fotos durchsehen“ am Laptop, bevor der
  Beamer gespiegelt wird; Rückblick vor dem Essen mit Netz laden, Tab offen
  lassen; „Standortdaten löschen“ erst nach der Show, danach die Fotos.
- **Prüfen:** `tools/pruefstand/rueckblick.py` (14 Gruppen: Texte, Sperren und
  PIN, Laden, Kapitel, Aufbereiten, Tasten und Schutz, Neuzeichnen, ohne Netz,
  Fotos, Bühne 1920x1080 und 1280x720 hell und dunkel, Probe, Verlassen,
  Bildrate, Awards gegen eine Rechnung in Python; Bildschirmfotos nach `RB_SHOTS`
  oder `tools/pruefstand/shots`). Szenarien `rueckblick*` in `mock.js`, darunter
  `rueckblick-dicht` (6.000 Punkte je Team) und `rueckblick-niemand`; Schalter
  `window.__fotoFehler`, `__haengt`, `__netz`, `__rbGeduld`. Am Gerät: einmal
  `#/rueckblick/probe` auf dem Beamer des Restaurants, Lesbarkeit aus der letzten
  Reihe, Klicker.

## 17. Handy als Fernbedienung der Rückblick-Show (Nachtrag 37, 17.10.2026)

Spezifikation: `docs/superpowers/specs/2026-10-15-rueckblick-show-design.md`,
Nachtrag „Fernbedienung“. Die Show läuft am Laptop wie in §16; das Handy der
Spielleitung steuert sie zusätzlich und zeigt eine Moderationshilfe. Die Show
bleibt ohne Handy voll bedienbar (Tastatur, Presenter).

- **Seite:** `rueckblick-fernbedienung.html` im Repo-Wurzelordner, mobile first
  (390 px Hochformat, auch 360 px ohne seitliches Scrollen), Farben und Schriften
  der App (`vendor/fonts`), hell/dunkel über `sj.thema` wie die App, Zugang aus
  `config.js`. PIN der Spielleitung, nur in `sessionStorage` (`sj.pin`), nie in
  der Adresse. Bedienfeld unten: großer „Weiter“ (104 px, im Vorbereiten
  „Start“), daneben „Zurück“, darüber „Pause“/„Abspielen“, „Schwarzbild“/„Bild
  zeigen“, „Zum Ende“ (erst der zweite Tipp binnen 4 s wirkt: „Springt zur
  Rangliste. Noch einmal tippen.“, wie die Taste Ende). Kurzes Vibrieren und
  sichtbarer Druck, Rahmen am Knopf, bis die Show den Befehl ausgeführt hat.
  Im Halt und Endhalt wirkt `pause` nicht, der Knopf ist dort deaktiviert; dort
  gibt es nur Weiter. Die Leertaste am Laptop bleibt unverändert.
  Doppeltipp: solange ein Befehl unterwegs ist und 400 ms danach zählt kein
  Tipp. Wake Lock, solange die Seite offen ist. Ohne verbundene Show sind die
  Knöpfe gesperrt.
- **Statuskarte:** „Show verbunden“ (letzte Meldung der Show höchstens 6 s alt),
  „Keine Show gefunden“, „Keine Verbindung zum Server“; Kapitel, Zustand
  („wartet auf Weiter“, „Pause“, „Schwarzbild an“, „läuft“), „Kapitel 7 von 18“,
  Fortschritt und Zeit wie in der Leiste. In der Probe heißt der Kopf
  „Rückblick, Probe“.
- **Moderationskarte (nur am Handy, nie am Beamer):** die Show berechnet je
  Kapitel kurze Bausteine (`moderation()` in `rueckblick.js`) und schickt sie mit
  dem Stand: vor dem Aufdecken „Als Nächstes wird Platz 3 aufgedeckt: Tiger,
  8 Leute (Anna Kaya, Elif Keller, …), Zeit 1:30:20, 6:47 hinter dem Ersten.“ und
  „Danach: Platz 2.“; nach dem Aufdecken Zeit, „Kofferübergabe an Tiger,
  Teamleitung …“ und alle Namen; Awards „Navi auf zwei Beinen: Delfin, nur 8 %
  Umweg vom idealen Weg.“ (schon am Ende des Kapitels davor als „Danach: …“);
  Fun Facts mit den Zahlen und „Weiter schaltet auf … Liter Bier.“; Rangliste,
  Zeitraffer („Läuft. Gleich: Rangliste.“), Siegerbild, Abspann („Läuft
  endlos.“). Texte ohne Gedankenstrich und Mittelpunkt, Teamnamen am Handy nur
  als Text (nie HTML).
- **Weg der Befehle (kein Realtime, nur Abfragen):** das Handy schreibt
  (`rb_befehl`), der Laptop holt im 1-s-Takt (`rb_poll`, eine Anfrage zugleich,
  nichts im Bild-Takt) und führt den Befehl aus wie die Taste (`fernBefehl`:
  `weiter`, `zurueck`, `spielPause`, `schwarz`, `zumEnde`, `starten` nur im
  Vorbereiten; dieselben Sperren M1, M2, M3, M8; im Schwarzbild holt jeder
  Befehl außer Schwarzbild erst das Bild zurück; bei offener Rückfrage
  „verlassen?“ nichts). Stand der Show (`rb_status_setzen`) bei jeder Änderung
  von Kapitel, Zustand oder Befehlsnummer und sonst alle 4 s; das Handy liest im
  1-s-Takt (`rb_status_holen`), verdeckt alle 5 s. Beim Öffnen übernimmt die Show
  den Zähler (`p_seit = null`): ein Befehl von vorher wirkt nicht. Beim
  Verlassen löscht `rb_ende` Stand, Moderation und Befehl. Fehler der Abrufe
  bleiben still (nächster Takt); ohne die Migration (PGRST202) fragt die Show
  nicht weiter und das Vorbereiten sagt es; falsche PIN schaltet die
  Fernbedienung aus.
- **Vorbereiten:** Block „Handy als Fernbedienung“ rechts neben dem Panel (nicht
  darin, das Panel wird nicht kleiner): QR-Code des Links (ohne PIN),
  „PIN am Handy eingeben“, „Handy verbunden“, sobald das Handy in den letzten
  10 s abgefragt oder einen Befehl geschickt hat. **Probe:** dieselbe
  Fernbedienung über die Datenbank, mit den Demo-Teams in der Moderation; der
  Block fragt beim Aktivieren die PIN der Spielleitung ab (nur
  `sessionStorage`), ist sie aus der Spielleitung schon da, läuft sie gleich.
- **Datenbank (Migration `20261017090000_rueckblick_steuerung.sql`):** Tabelle
  `rueckblick_steuerung` (eine Zeile, `id = 1`: `nr`, `befehl`, `befehl_um`,
  `status` jsonb, `status_um`, `handy_um`), RLS an, für anon und authenticated
  gesperrt. Funktionen, alle `security definer` mit `require_admin` und
  ausdrücklichen Rechten: `rb_befehl(p_pin, p_befehl)` (feste Liste weiter,
  zurueck, pause, schwarz, start, ende; 250 ms Mindestabstand, sonst `ok false`),
  `rb_poll(p_pin, p_seit)` (`{nr, befehl}`; älter als 30 s: `befehl null`;
  nichts Neues: `null`), `rb_status_setzen(p_pin, p_status)` (Objekt, höchstens
  20 KB; antwortet `handy_alter_s`), `rb_status_holen(p_pin)` (`{status,
  alter_s}`, merkt `handy_um`), `rb_ende(p_pin)`. Die Nummer bleibt bei
  `rb_ende`. Keine Spielfunktion und nicht die Sicht `stations` berührt.
- **Service Worker:** lässt die Seite in Ruhe (Navigation nur auf `./` und
  `index.html` abgefangen); sie braucht Netz.
- **Prüfen:** `tools/pruefstand/fernbedienung.py` (Show und Handy zugleich, rb_*
  über `page.route` auf ein gemeinsames Python-Objekt nach der Migration; PIN,
  Start, Weiter, Doppeltipp, Zurück, Pause, Schwarzbild, Zum Ende, Stand folgt
  auch Tasten am Laptop, Moderation vor Platz 3, „Keine Show gefunden“ nach
  6 s, alte Befehle, `rb_ende`, Server 500, Bildrate, Probe, 390 und 360 px,
  Tippziele, hell und dunkel; Bildschirmfotos `fern-*.png` nach `FERN_SHOTS`).
  Probelauf `tools/pruefstand/rueckblick_steuerung_db.py` (mit `--ohne` rot).
  Bekannte Grenze: zwei Befehle innerhalb derselben Sekunde, dann wirkt nur der
  letzte (eine Zeile, kein Puffer).

## 18. Startbild beim ersten Öffnen (27.10.2026)

- **Wann:** nur beim allerersten Öffnen auf einem Handy (`sj.intro` in
  `localStorage`, gesetzt schon beim Start des Intros). Nie bei der
  Spielleitung (`#/admin`) und in der Rückblick-Show; Anmeldung, Teamleitung,
  und Mitglied bekommen es. Ohne Speicher (gesperrt) kommt es bei
  jedem Neuladen.
- **Start:** Das Startbild steht sofort (Papier, `#app` unsichtbar dahinter),
  alle Animationen angehalten auf ihrem ersten Bild. Los geht es 0,5 s nach dem
  vollständigen Laden der Seite (`load`, Friedrich 27.10., erst 1 s, dann nach
  den Varianten 0,5 s); ein Tipp vorher
  beendet es ebenso.
- **Ablauf, 5 s:** Ein großer Kompass läuft ein und deckt die Karte von seiner
  Mitte aus auf (eine Fläche in Papierfarbe mit Loch wächst, nur `transform`;
  die Linien einzeln zu zeichnen flackerte und ruckelte am Handy, 27.10.), die Nadel pendelt gedämpft auf Norden (gespielt, kein Sensor),
  "Stadtjagd" und "Prag" steigen auf (wie der Vorspann der Rückblick-Show).
  Bei 3,6 s misst `introStarten()` das Logo `#app .flag` und die Überschrift
  `#app .brand h1` und lässt Kompass und Schriftzug in 1 s genau dorthin fliegen;
  heißt die Überschrift nicht "Stadtjagd" (Teamleitung: Teamname), blendet der
  Schriftzug aus. Der Rest der Seite kommt von unten (`body.intro-landet`), bei
  5 s übernimmt das echte Logo. Animiert werden nur `transform` und `opacity`
  auf eigenen Ebenen (Nadel als eigenes Element), dazu der kleine Ring; die
  Karte selbst nie.
- **Die App wartet nicht:** sie lädt und zeichnet dahinter normal
  (`body.intro`: `#app` unsichtbar). Ein Tipp beendet das Intro sofort
  (`introEnde()`). "Bewegung reduzieren": nur 1,5 s Überblenden.
- **Kopf:** die Ansichten für Teilnehmende zeigen nur Logo und "Stadtjagd",
  ohne Unterzeile ("Anmeldung offen", "Das Spiel läuft" usw. sind weg);
  `brand(sub)` zeigt die Unterzeile nur noch bei der Spielleitung und im
  Rückblick-Fehler.
- **Prüfen:** `tools/pruefstand/intro.py` (Port 8872). `mock.js` merkt das
  Intro als gesehen, damit es keine andere Prüfung verdeckt; `&intro=1` in der
  Adresse zeigt es.

