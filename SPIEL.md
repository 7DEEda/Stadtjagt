# Stadtjagd: Spiel und Code

Referenz für alle, die am Code arbeiten. Beschreibt, wie das Spiel funktioniert,
welche Zustände und Abläufe es gibt und wo das im Code steht. Den Verlauf der
Entscheidungen und die Betriebsnotizen (Zugänge, Umgebung, Historie) enthält
`HANDOFF.md`.

Stand: 01.10.2026, Nachträge 1 bis 27. Die Abschnitte 1 bis 10 beschreiben den Stand bis Nachtrag 22;
was seitdem dazukam, steht geschlossen in den Abschnitten 11 und 12.

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
| **Teilnehmende** | Link, Name bei der Anmeldung; oder Mitlese-Link des Teams | sich anmelden (nur bis zum Auslosen), Team nachschauen | eigenes Team groß mit Emoji; ab dem Start alles, was die Teamleitung sieht (Geräte-Schlüssel aus der Anmeldung oder Mitlese-Link) |
| **Teamleitung** | `#/team`: automatisch auf dem Handy, mit dem sie sich angemeldet hat (Geräte-Schlüssel); Team-Code nur als Ausweg für die Spielleitung am Tablet | einchecken, Rätsel beantworten, Koffer-Code eingeben, Mitlese-Link teilen, Leitung abgeben | Station, Kompass, Rätsel, Ziffern, Platz |
| **Spielleitung** | Admin-PIN unter `#/admin` | auslosen, starten, beenden, fortsetzen, freischalten, Rätsel werten, Teamleitung wählen, Stationen pflegen, Leute eintragen, löschen, Testmodus | Karte mit Routen, Zeitachse, alle Teams mit Codes und Mitlese-Links, Koffer-Code |

Die Teamleitung wird beim Auslosen je Team zufällig bestimmt
(`teams.leader_participant_id`); die Spielleitung kann sie ändern
(`admin_set_leader`), die Teamleitung selbst abgeben (`team_set_leader`).
Seit Nachtrag 22 meldet sich jede Person nur selbst an, auf dem eigenen Handy
(„Jemanden ohne eigenes Handy anmelden“ gibt es nicht mehr). Die Teamleitung
tippt keinen Code: ihr Handy holt ihn über `leader_code`. Wird die Leitung
gewechselt oder abgegeben, gibt das alte Handy sofort nichts mehr ein
(`leitungNochDa` nach jedem Abruf). Den Team-Code braucht nur noch die
Spielleitung, wenn sie am Tablet für ein Team eingibt.

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
- Die App holt dafür eine frische Position (`freshPosition`).
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

---

## 5. Abläufe

### 5.1 Anmeldung (`registration`)
1. `#/public`, Name eintragen → `register_participant`.
2. Antwort enthält `token` (64 Hex-Zeichen, Nachtrag 11). Die App speichert
   `sj.name` und `sj.token` im `localStorage`.
3. Doppelte Namen (über `name_key = norm(name)`) werden abgelehnt, ebenso
   Namen ohne einen lateinischen Buchstaben oder eine Ziffer (leerer
   Schlüssel, Nachtrag 20). Die Anmeldung wartet mit `for share` auf ein
   laufendes Auslosen, das Auslosen sperrt `game_state` mit `for update`.
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
  Zum Mitlesen bekommen sie den Mitlese-Link ihres Teams (Reiter Teams oder
  von der Teamleitung).
- Teamleitung: „Mitlesen fürs Team“ (Link teilen oder kopieren) und „Leitung
  abgeben“ stehen unten in ihrer Ansicht, in jeder Phase.

### 5.4 Spiel (`running`)
- Teamleitung (`#/team`): Station, Ortshinweis, Kompass und Entfernung,
  „Wir sind da“, danach Rätsel mit Eingabe, kleine Ziffern-Räder darunter
  (Variante B, siehe `mockups/team-reihenfolge.html`).
- Mitglieder mit Token (`#/public`): dieselbe Ansicht aus `member_state`, ohne
  Eingaben („Einchecken macht Silke“, „Die Antwort gibt Silke ein“).
  Kompass und Entfernung mit dem eigenen GPS, keine Positionsmeldung.
- Öffentliche Seite: „Zieleinlauf“ live, sobald das erste Team im Ziel ist.
- Spielleitung: Karte mit Routen, Zeitachse, Teams nach Platz und Fortschritt.
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

| Daten | öffentlich (`public_state`) | Mitglied (`member_state`, `member_state_by_team`) | Teamleitung (`team_state`) | Spielleitung (`admin_state`) |
|---|---|---|---|---|
| Teams, Mitglieder, Teamleitung | ja | eigenes | eigenes | alle |
| Team-Code | nein | **nein** | eigener | alle |
| Mitlese-Schlüssel | nein | **nein** | eigener | alle |
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
- Mitlesen nur mit Geräte-Token aus der eigenen Anmeldung oder mit dem
  Mitlese-Schlüssel des Teams (`teams.read_token`, kommt nur von der
  Teamleitung oder Spielleitung), nie über den Namen: Namen sind öffentlich,
  und alle Teams haben dieselben Rätsel und Ziffern. Wer den Mitlese-Link
  weitergibt, gibt Einblick ins eigene Team, nichts weiter; eingeben kann er
  nichts.
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
geraete-test.html, geraete-tests.js  Geräte-Test und seine Suite, gehört nicht zum Spiel (HANDOFF, Nachtrag 23)
kompass-test.html          leitet auf geraete-test.html weiter
hintergrund/a.svg, b.svg, c.svg  Hintergrund-Varianten, lädt render() nach; klassisch steht im HTML
supabase/migrations/*.sql  Schema und Spiellogik, in Dateinamen-Reihenfolge
supabase/seed-*.sql        Stationen der Prager Route, 100 Testpersonen
tools/sql.py               SQL über die Supabase Management-API ausführen
tools/hintergrund/         Generator für die Hintergrund-Varianten (OSM-Daten sind gitignored)
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
- **Löschen und Rückfragen:** alles über die Liste `DANGER` und einen Dialog,
  meist mit getipptem Wort `LÖSCHEN`; `wort: false` für Person und Spielende.
  `neutral: true` (Start, Teamleitung wechseln, Rätsel werten) zeigt den Dialog
  ohne Rot und mit orangem Knopf.
- **Meldungen:** `S.msg` mit optionalem `ort`. `msgBox(ort)` zeigt nur Meldungen
  mit genau diesem ort, `msgBox()` nur die ohne. Jede Ansicht ruft `msgBox()`
  genau einmal auf, sonst steht eine Meldung doppelt. Feste Orte: `anm`,
  `suche`, `karte`, `mit`, `abgeben`, `settings`, `bg`, `dlg`, `t:<Team-ID>`.
  Knöpfe mit `data-ort` geben ihren ort an Fehler aus dem Klick-Handler weiter.
- **Eingaben:** `render()` rettet Getipptes und Fokus über jedes Neuzeichnen,
  solange derselbe Zustand zu sehen ist (`feldKontext`). Nach einer
  erfolgreichen Aktion leert es die Felder (`S.felderFrisch`).
- **Bildschirm an:** `wachHaltenPruefen()` hält per Wake Lock den Bildschirm an,
  beim Hochhalten und unterwegs mit Standort; nach der Rückkehr in die App
  (`visibilitychange`) neu, dabei lädt die Seite auch sofort nach.
- **Stand:** kommt 30 s nichts vom Server, steht im Kopf „Stand 13:27“.
- **Speicher im Browser:** `sj.name`, `sj.token`, `sj.mit` (Mitlese-Schlüssel
  des Teams), `sj.code` (Teamleitung), `sj.kal` (Einmessen heute erledigt),
  `sj.gps` (Standort war schon freigegeben: nach Neuladen ohne Tipp wieder
  starten, den iOS-Kompass nur per Knopf), `sj.abgemeldet` (Teamleitung hat
  sich abgemeldet: nicht still per Geräte-Schlüssel wieder einloggen),
  `sj.url`/`sj.key` (nur ohne `config.js`) im `localStorage`; `sj.pin` im
  `sessionStorage`. Zugriff nur über `LS`/`SS`: Blockiert der Browser
  Website-Daten, fallen beide auf eine Map im Speicher zurück, statt die
  Seite beim Laden abzubrechen.

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
- Mitlese-Link: `#/mit/<schlüssel>` → `mitLinkPruefen()` speichert `sj.mit`
  und leitet auf `#/public`; `mitlesen()` nimmt `sj.token` vor `sj.mit`.
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
  (auch Namensteile, bis zu acht Vorschläge), `member_state`,
  `member_state_by_team`
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
  Nachtrag 7, `register_participant` in Nachtrag 12).
- Einspielen: `python tools/sql.py supabase/migrations/<datei>.sql`. Token in
  `%USERPROFILE%\.supabase\stadtjagt.token`. Das Skript bremst zerstörerische
  Anweisungen außerhalb von Funktionskörpern.
- Reihenfolge beim Ausliefern: erst die Datenbank, dann die App.

### Testmodus und Testdaten
- `admin_set_test_mode` (Reiter Stationen): Check-in und Koffer-Code ohne
  Entfernung, jede Antwort zählt, keine Denkpause; der Koffer-Code selbst wird
  weiter geprüft. Rotes „Testmodus an“ in Admin und Team-Ansicht.
  „Spiel starten“ warnt, solange er an ist (bleibt beim Testen dauerhaft an,
  Entscheidung 19.09.2026).
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
  nachgereicht (`fotoNachreichen()`).
- Ersetzen geht für die zuletzt gelöste Station, bis an einer späteren
  eingecheckt ist.
- Album: `team_photo` mit Team-Code, Geräte-Schlüssel oder Mitlese-Link.
  Spielleitung: `admin_photos`, `admin_photo`, `admin_set_selfie`,
  `admin_delete_photos`; das ZIP entsteht im Browser (`zipBauen()`).
- Fotos liegen in `station_photos`, mit Fremdschlüssel auf `progress`:
  Zurücksetzen, neu Auslosen und Leeren der Anmeldung nehmen sie mit. Ist
  `photos_delete_on` erreicht, löschen `team_state` und `admin_state` sie beim
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
- „Link teilen“ zeigt den Mitlese-Link auch als QR-Code (`qrSvg()`,
  `vendor/qrcode.js`).

### Neue Dateien

```
geraete-test.html, geraete-tests.js   Geräte-Test und seine Suite (gehört nicht zum Spiel)
vendor/qrcode.js                      QR-Generator für den Mitlese-Link (MIT)
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
