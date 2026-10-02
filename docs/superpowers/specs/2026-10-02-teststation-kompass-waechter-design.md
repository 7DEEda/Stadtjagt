# Teststation, Kompass-Wächter, Rollen und Akku

Stand 02.10.2026. Drei Teile, in dieser Reihenfolge gebaut und einzeln geprüft:

1. eine eigene Teststation für Probeläufe vor Ort (Prag bleibt unberührt),
2. ein Kompass-Wächter, der einen schlechten Kompass im Spiel erkennt, dem Team
   zeigt und auf die Laufrichtung ausweicht,
3. eine Team-Ansicht, die sich der Rolle anpasst (Teamleitung oder Mitglied,
   Wechsel ohne Tippen), mit Akku-Warnung und Übergabe der Leitung.

Mockups: `mockups/kompass-waechter.html`, `mockups/akku-warnung.html`.

## Ziel und Erfolg

- Friedrich kann am TSE-Standort (Grenzallee 4, Berlin) ein Ein-Stationen-Spiel
  im Testmodus laufen, ohne die fünf Prager Stationen zu ändern oder zu löschen.
- Ein Handy mit schlechtem Kompass (Referenz: Xiaomi 22021211RG, im Geräte-Test
  48 %, 11 %, 124 % „folgt zu“, Sprünge bis 164°) wird im Spiel nach wenigen
  Drehungen erkannt; der Pfeil folgt dann der Laufrichtung, das Team und die
  Spielleitung sehen einen Hinweis.
- Ein gutes Handy (Referenz: Xiaomi 23113RKC6G, höchstens 5° bis 16° daneben,
  iPhone iOS 18.7) wird nie als schlecht gemeldet.
- Probeversion: der Wächter wirkt zunächst nur im Testmodus.

## Teil 1: Teststation

### Datenbank

- `stations` bekommt die Spalte `route text not null default 'echt'` mit den
  Werten `echt` und `test`. Die Eindeutigkeit von `position` gilt je Route:
  `unique (route, position)` statt `unique (position)`.
- Neue Funktion `aktive_route()`: `test`, wenn `game_state.test_mode` an ist und
  es eine Station mit `route = 'test'` gibt, sonst `echt`.
- Die Teststation ist genau eine Zeile, `route = 'test'`, `position = 1`
  (der Client rechnet mit `digits[position - 1]`). Erst-Anlage in der Migration
  bei EDEKA Grenzallee (52.470116, 13.462131), Radius 50 m, Name „EDEKA
  Grenzallee“, Ziffer 1, Entschlüsselung aus (beide Kreise leer), Rätsel und
  Lösung als Platzhalter.
- Alle Funktionen, die fürs Spielen `stations` lesen, filtern auf
  `route = aktive_route()`: `current_station`, `team_state`, `submit_final`,
  `public_state`, `admin_start`, `team_selfie`, `team_selfie_skip`,
  `team_photo`, `admin_photo`, `admin_photos`, `admin_tracks`. Ausnahme
  `admin_state`: dessen Liste `stations` bleibt immer die echte Route (zum
  Bearbeiten); Koffer-Code, `currentPosition` je Team und die Stationen auf
  der Karte der Spielleitung kommen aus der aktiven Route (neues Feld
  `aktiveStationen`). `check_in`,
  `submit_answer`, `reveal_tip`, `admin_solve_station`,
  `admin_unlock_station` laufen über `current_station` und brauchen nur dort
  den Filter. `progress` bleibt wie es ist: Fortschritt auf der Teststation
  hängt an deren `station_id` und stört die echte Route nicht.
- `admin_state` liefert zusätzlich `testStation` (die Zeile mit
  `route = 'test'`, alle Felder wie bei den Stationen) und `route`
  (`aktive_route()`), damit die Spielleitung sieht, welche Route gerade gilt.
- `admin_save_station` speichert weiterhin per `id`; damit ist die
  Teststation über dasselbe Formular bearbeitbar.
- Probelauf wie gewohnt: ein DO-Block führt die Migration aus, prüft
  `aktive_route()` mit Testmodus an und aus, `team_state` liefert
  `totalStations = 1` und die Teststation, die Prager Zeilen sind unverändert
  (Prüfsumme über alle Felder vorher und nachher), dann `PROBELAUF_OK` und
  Rollback.

### Spielleitung, Reiter „Stationen“

- Neuer Abschnitt „Teststation“ oberhalb der Stationsliste, im selben Aufbau
  wie eine Station: Zusammenfassung mit „Bearbeiten“, im Bearbeiten das
  bekannte Formular mit Karte und ziehbaren Kreisen fürs Entschlüsseln (alle
  Funktionen `stationsKarte`, `ekZeichnen`, „Hier“, Vorschlag 30/60 %).
  Vorgänger für den Vorschlag ist der Start (keine Station davor).
- Darüber ein Satz, der sagt, was gilt: „Testmodus an: alle Teams spielen nur
  die Teststation.“ bzw. „Testmodus aus: es gilt die echte Route (5 Stationen).“
- Die Liste der echten Stationen bleibt sichtbar und bearbeitbar, mit dem
  Vermerk, dass sie im Testmodus nicht gespielt wird.

### Spiel

- Schloss und Texte rechnen mit `totalStations` statt fest mit fünf:
  `lockHTML` zeichnet `totalStations` Räder plus Schlussziffer, die Texte
  „Die 6. Ziffer … eurer fünf Ziffern“ und „sechs Ziffern“ werden aus der
  Zahl gebildet, `#tfin` bekommt `maxlength = totalStations + 1`. Bei einer
  Station ist der Koffer-Code zwei Ziffern (Ziffer und Schlussziffer).
- Fortschritt und Karte bei der Spielleitung nehmen `aktiveStationen`
  statt `stations` (heute `solved / stations.length`).

### Umschalten

- Testmodus aus und wieder an ändert nur `aktive_route()`. Fortschritt auf der
  Teststation bleibt erhalten; für einen frischen Lauf „Fortschritt
  zurücksetzen“ wie bisher.
- Vor dem Event: Testmodus aus (dann gilt Prag), Fortschritt zurücksetzen. Die
  Teststation darf liegen bleiben.

## Teil 2: Kompass-Wächter

### Messung (im Spiel, `index.html`)

- Neuer Zuhörer auf `devicemotion`, wie im Geräte-Test erprobt: Drehrate um
  die Senkrechte = `rotationRate` (alpha um x, beta um y, gamma um z, so auf
  Android-Chrome und iOS-Safari gemessen) projiziert auf „oben“ aus
  `accelerationIncludingGravity` (auf z > 0 gewendet). Daraus `gyroHoch`
  (aufsummierte Drehung, im Uhrzeigersinn positiv) und `drehRate` (°/s).
- iOS: `DeviceMotionEvent.requestPermission()` im selben Tipp wie die
  bestehende Kompass-Freigabe in `startGps` (kein `await` davor). Ohne
  Freigabe oder ohne Ereignisse: kein Wächter, alles wie heute.

### Prüfabschnitte

- **Drehung:** beginnt, wenn `drehRate` über 8°/s steigt; endet, wenn sie
  1 s lang unter 3°/s liegt oder nach 10 s. Gewertet nur, wenn das Gyroskop
  in dem Abschnitt mindestens 90° Drehung gemessen hat. Verglichen wird der
  Weg des Kompasses (Summe der Änderungen auf dem kürzesten Weg) mit dem Weg
  laut Gyroskop. Gut: höchstens 20° Unterschied. Schlecht: mehr als 45°.
  Dazwischen: zählt nicht.
- **Stillstand:** 3 s lang `drehRate` unter 3°/s. Schlecht, wenn der Kompass
  dabei mehr als 30° wandert; gut, wenn höchstens 10°.
- Kein Abschnitt, solange das Fenster „Kompass einmessen“ offen ist, die
  Seite verborgen ist oder in den letzten 3 s zurückkam (der bestehende
  Zustand „nach Pause“ regelt das).

### Urteil

- `unzuverlaessig`: 3 der letzten 4 gewerteten Abschnitte schlecht.
- zurück auf `ok`: 3 gute Abschnitte in Folge.
- Erfolgreiches Einmessen leert die Abschnitte (frische Chance).
- Wirkung bei `unzuverlaessig`: `S.gps.kompass = "kalibrieren"` (bestehender
  Zustand „ungenau“); `richtung()` nimmt dann schon heute die Laufrichtung,
  sobald sie bekannt ist. iOS: meldet iOS selbst eine schlechte Genauigkeit,
  gilt das wie bisher; der Wächter kann nur verschärfen, nie entwarnen.
- Probeversion: der Wächter misst immer, wirkt (Zustand und Hinweis) aber nur
  bei `testMode`. Nach dem Feldversuch entscheidet Friedrich, ob er für das
  Event immer wirkt.

### Anzeige für das Team (Mockup Bild 1 und 2)

- Unter dem Kompass ein Hinweis in Warnfarbe: „Der Kompass dieses Handys
  zeigt gerade falsch“, darunter je nach Lage „Der Pfeil richtet sich jetzt
  nach eurer Laufrichtung. Haltet das Handy beim Gehen vor euch.“ oder
  „Geht ein paar Schritte, dann zeigt der Pfeil eure Laufrichtung. Die
  Entfernung stimmt immer.“, mit dem Knopf „Kompass einmessen“.
- Statuszeile unter der Entfernung: „Pfeil nach Laufrichtung“ bzw. „Erst ein
  paar Schritte gehen“.
- Der Hinweis verschwindet von selbst, wenn das Urteil auf `ok` zurückgeht.
- Mitlesende Handys messen ihren eigenen Kompass; jedes Handy urteilt für sich.
  Der Hinweis nennt das: „Tipp: Schaut auf ein anderes Handy aus eurem Team.
  Wer mitliest und den Standort freigibt, sieht dort den Pfeil mit dem eigenen
  Kompass.“ Bei der Teamleitung zusätzlich: „Oder gebt die Leitung an jemanden
  ab, dessen Handy richtig zeigt.“ mit dem Übergabe-Fenster aus Teil 3.

### Gedächtnis des Handys

- Wird ein Handy `unzuverlaessig`, merkt es sich das lokal (`sj.kompass` mit
  Datum, ohne Namen). Beim nächsten Öffnen startet der Wächter dort gleich als
  `unzuverlaessig` (Pfeil nach Laufrichtung, Hinweis), statt erst ein paar
  Drehungen lang falsch zu zeigen.
- Zurück auf `ok` braucht ein vorbelastetes Handy 5 gute Abschnitte in Folge
  statt 3; dann vergisst es den Vermerk. Einmessen leert die Abschnitte, der
  Vermerk bleibt aber, bis die 5 guten Abschnitte da sind.
- Einmessen, das nicht hilft: bleibt das Urteil nach dem Einmessen
  `unzuverlaessig` (die ersten 3 gewerteten Abschnitte danach nicht gut),
  zählt das Handy einen erfolglosen Versuch (lokal, `sj.kompass`). Hinweis nach
  einem Versuch: „Einmessen hat nicht geholfen. Probiert es noch einmal, mit
  etwas Abstand zu Metall, Magneten und Handyhüllen.“ mit „Noch einmal
  einmessen“. Ab zwei Versuchen: „Einmessen hilft bei diesem Handy nicht. Der
  Pfeil bleibt bei der Laufrichtung, die Entfernung stimmt immer.“, kein
  großer Knopf mehr, nur der Link „Trotzdem noch einmal einmessen“; die
  Teamleitung behält „Leitung abgeben“. Während das Handy nach dem Einmessen
  prüft: „Kompass wird geprüft … Dreht euch einmal um.“ Mockup:
  `mockups/rollen-akku-kompass.html` (Regler „Einmessen hilft“).

### Anzeige für die Spielleitung (Mockup Bild 3)

- `report_position` bekommt den optionalen Parameter `p_kompass text`
  (`ok`, `unzuverlaessig`, `null` = unbekannt); `team_positions` die Spalte
  `kompass`. Gemeldet wird das Urteil des Teamleitungs-Handys.
- `admin_state` liefert je Team `kompass`. In der Teamzeile erscheint bei
  `unzuverlaessig` der Vermerk „Kompass falsch, Pfeil nach Laufrichtung“.

## Teil 3: Rollen und Akku

### Eine Team-Ansicht, Rolle vom Server

- Es gibt eine Team-Ansicht. Ob das Handy die Teamleitung ist, entscheidet der
  Server: Ein Handy mit Personen-Kennung (`sj.token`) fragt bei jeder
  Aktualisierung `member_state`; ist die Person laut Server die Teamleitung,
  holt das Handy still `leader_code` und zeigt ab da Einchecken, Antworten und
  Koffer. Ist sie es nicht mehr, wechselt es ebenso still zurück aufs Mitlesen
  (statt sich wie heute abzumelden).
- Übergabe: die alte Teamleitung wählt eine Person, „Übergeben“ nutzt
  `team_set_leader`. Das Handy der neuen Leitung schaltet beim nächsten Abruf
  (spätestens nach dem üblichen Takt) von selbst um und zeigt kurz „Du leitest
  jetzt Team Fuchs“. Wer nur über den Mitlese-Link ohne eigene Anmeldung dabei
  ist, kann nicht Teamleitung werden: die Liste zeigt nur angemeldete
  Personen, mit Akku-Stand, wenn bekannt, und „Handy nicht verbunden“, wenn
  die Person in den letzten 2 Minuten nicht abgerufen hat. Auch sie ist
  wählbar; sie wird Teamleitung, sobald ihr Handy die Seite öffnet.
- Die Spielleitung kann wie bisher im Reiter „Teams“ die Leitung setzen; das
  Handy der Person schaltet ebenso von selbst um.

### Akku

- Jedes Handy liest den Akku (`navigator.getBattery()`, Android-Chrome; Safari
  auf dem iPhone gibt ihn nicht heraus) und schickt Stand und „lädt“ mit:
  Teamleitung über `report_position` (neu `p_akku int`, `p_laedt bool`),
  Mitglieder über `member_state` (neu `p_akku`, `p_laedt`). Gespeichert je
  Person (`participants.akku`, `akku_laedt`, `akku_at`).
- `team_state` liefert je Teammitglied Akku und letzte Meldung; die
  Team-Ansicht zeigt bei allen Handys des Teams einen Hinweis, wenn ein
  Handy unter 20 % ist und nicht lädt: „Akku knapp: dein Handy 18 %, Julia
  15 %“, darunter „Ladet das Handy, wenn ihr könnt.“ Ist es das Handy der
  Teamleitung, steht auf den anderen Handys „Das Handy der Teamleitung geht
  bald aus. Anna sollte die Leitung rechtzeitig abgeben.“ und auf dem Handy der
  Teamleitung selbst „Gib die Leitung rechtzeitig an jemanden mit vollerem
  Akku ab.“ mit dem Knopf „Leitung abgeben“ (öffnet das Übergabe-Fenster).
- Auf dem Handy der Teamleitung springt bei 20 % und bei 10 % (nicht ladend,
  je einmal pro Schwelle und Handy) das Fenster aus dem Mockup auf: Personen
  zum Antippen mit ihrem Akku, „Übergeben“ oder „Später“.
- Spielleitung: Akku der Teamleitung in der Teamzeile, ab 20 % als Vermerk.
- Geräte-Test: eigene Zeile „Akku“ (ok mit Stand, „liest das Handy nicht
  vor“ auf dem iPhone).

## Prüfen

- Prüfstand (`tools/pruefstand/`): neues Prüfskript `waechter.py` mit
  gespielten Sensoren: gesunder Kompass (nie unzuverlässig, auch bei
  Rauschen ±25°), Kompass folgt zu 40 % (nach 3 Drehungen unzuverlässig),
  wandernder Kompass im Stillstand, Rückkehr nach 3 guten Abschnitten,
  Einmessen leert, Wächter ohne Wirkung bei Testmodus aus, kein
  `devicemotion` = kein Urteil. Dazu `teststation_db.py` als Probelauf der
  Migration und ein Szenario „Teststation“ in `mock.js` mit einer Station
  (Schloss mit zwei Rädern, Texte, Spielleitung).
- Prüfstand für Teil 3: Szenarien „Mitglied wird Teamleitung“ (Ansicht
  schaltet ohne Tippen um), „Teamleitung gibt ab“ (wechselt aufs Mitlesen),
  Akku-Fenster bei 20 % und 10 % (gespielter Akku), Hinweis bei knappem Akku
  eines Mitglieds, kein Fenster beim Laden.
- Bestehende Prüfungen (`kritik.py`, `name.py`, `selfie.py`, `ziffer.py`)
  laufen weiter durch.
- Feldversuch: Teststation EDEKA, Testmodus an, schlechtes und gutes Xiaomi
  und ein iPhone; Läufe mit dem Geräte-Test zum Vergleich.

## Nicht Teil davon

- Eigener Prüfschritt vor dem Start (Drehen auf dem Tisch) im Spiel.
- Mehrere Teststationen oder eine Test-Route.
- Benachrichtigungen und Vibration.
